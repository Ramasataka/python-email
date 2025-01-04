import mysql.connector
import tkinter as tk
import imaplib
import email
import os
import io
import smtplib
from tkinter import messagebox
from tkinter import filedialog
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from tkinter import ttk

load_dotenv()

logged_in_user = None
current_page = 1  
def connect_to_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),  
            database=os.getenv("DB_NAME")
        )
        
        print("Connection to database successful!")  
        cursor = conn.cursor()
        cursor.execute(f"USE python_uas;")
        cursor.execute("SELECT DATABASE();")  
        current_db = cursor.fetchone()
        print(f"Current database: {current_db}")  
        
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}") 
        return None
    
def login(username, password):
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()
    print(user)
    return user


def fetch_employees():
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "SELECT email FROM users WHERE role = 'employee'"
    cursor.execute(query)
    employees = [row[0] for row in cursor.fetchall()]
    conn.close()
    return employees

def send_email(sender_email, smtp_password, receiver_email, subject, body, attachment_path=None):
    try:
        server = smtplib.SMTP(os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT"))
        server.starttls()
        server.login(sender_email, smtp_password)

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        if attachment_path:
            attachment_name = os.path.basename(attachment_path)
            with open(attachment_path, 'rb') as attachment_file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment_file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={attachment_name}')
                msg.attach(part)

        server.send_message(msg)
        server.quit()

        messagebox.showinfo("Success", "Email berhasil dikirim!")

    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengirim email: {e}")

def fetch_emails(page=1, emails_per_page=10):
    try:
        # Ambil data pengguna login
        email_user = logged_in_user[3]
        email_password = logged_in_user[4]

        # Hubungkan ke server IMAP
        mail = imaplib.IMAP4_SSL(os.getenv("IMAP_SERVER"), os.getenv("IMAP_PORT"))
        mail.login(email_user, email_password)
        mail.select("inbox")

        # Ambil semua email
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        total_emails = len(email_ids)

        # Pagination logic
        start_index = total_emails - (page * emails_per_page)
        end_index = start_index + emails_per_page
        if start_index < 0:
            start_index = 0
        email_ids = email_ids[start_index:end_index]

        email_list = []
        for email_id in email_ids[::-1]:  # Iterasi dari email terbaru
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    from_ = msg.get("From")
                    email_list.append({"id": email_id, "from": from_, "subject": subject, "message": msg})

        mail.logout()
        return email_list, total_emails
    except Exception as e:
        messagebox.showerror("Error", f"Terjadi kesalahan saat membaca email:\n{e}")
        return [], 0
    
def read_sent_email_history():
    try:
        # Koneksi ke server IMAP Gmail
        imap = imaplib.IMAP4_SSL(os.getenv("IMAP_SERVER"), os.getenv("IMAP_PORT"))
        imap.login(logged_in_user[3], logged_in_user[4])

        # Pilih folder "Sent Mail" (Pastikan nama folder sesuai dengan akun Gmail Anda)
        #status, folders = imap.list()
        # for folder in folders:
            # print(folder.decode())
            
        status, messages = imap.select('"[Gmail]/Surat Terkirim"')  # "[Gmail]/Sent Mail" adalah nama default untuk folder email terkirim
        if status != "OK":
            messagebox.showerror("Error", "Gagal memilih folder 'Sent Mail'.")
            imap.logout()
            return

        status, messages = imap.search(None, "ALL")
        if status != "OK":
            messagebox.showerror("Error", "Gagal mencari email di folder 'Sent Mail'.")
            imap.logout()
            return

        # Ambil ID email
        email_ids = messages[0].split()
        emails_to_show = 10  # Batas jumlah email yang akan ditampilkan
        latest_email_ids = email_ids[-emails_to_show:]

        # Loop melalui email dan baca informasi penting
        email_history = []
        for email_id in reversed(latest_email_ids):
            status, msg_data = imap.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    from_email = msg.get("From")
                    date = msg.get("Date")
                    email_history.append(f"Subject: {subject}\nFrom: {from_email}\nDate: {date}\n")

        # Tampilkan hasil di jendela baru
        if email_history:
            history_window = tk.Toplevel(root)
            history_window.title("Riwayat Email Terkirim")
            history_text = tk.Text(history_window, wrap="word", font=("Helvetica", 12))
            history_text.pack(expand=True, fill="both", padx=10, pady=10)
            history_text.insert("1.0", "\n\n".join(email_history))
            history_text.config(state="disabled")
        else:
            messagebox.showinfo("Info", "Tidak ada email terkirim yang ditemukan.")

        # Logout dari server IMAP
        imap.logout()
    except Exception as e:
        messagebox.showerror("Error", f"Gagal membaca riwayat email: {str(e)}")


def show_email_detail(email_data):
    print(email_data)
    for widget in root.winfo_children():
        widget.destroy()

    subject = email_data["subject"]
    sender = email_data["from"]
    msg = email_data["message"]

    label_title = tk.Label(root, text="Detail Email", font=("Helvetica", 20))
    label_title.pack(pady=10)

    label_subject = tk.Label(root, text=f"Subject: {subject}", font=("Helvetica", 14), wraplength=350, justify="left")
    label_subject.pack(pady=5)

    label_sender = tk.Label(root, text=f"From: {sender}", font=("Helvetica", 14), wraplength=350, justify="left")
    label_sender.pack(pady=5)

    label_body = tk.Label(root, text="Body:", font=("Helvetica", 14))
    label_body.pack(pady=5)

    # Frame untuk Scrollable Canvas
    frame_canvas = tk.Frame(root)
    frame_canvas.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame_canvas)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    frame_content = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame_content, anchor="nw")

    email_body = ""
    attachments = []

    # Parsing konten email
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))


            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Store attachment in memory
                    attachment_data = io.BytesIO(part.get_payload(decode=True))
                    attachments.append((filename, attachment_data))

            elif content_type == "text/plain":
                email_body = part.get_payload(decode=True).decode()
            elif content_type == "text/html":
                email_body = part.get_payload(decode=True).decode()
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            email_body = msg.get_payload(decode=True).decode()
        elif content_type == "text/html":
            email_body = msg.get_payload(decode=True).decode()

    # Tampilkan body email (text atau HTML)
    text_body = tk.Text(frame_content, height=15, width=50, font=("Helvetica", 12), wrap="word")
    text_body.insert("1.0", email_body)
    text_body.configure(state="disabled")
    text_body.pack(pady=10, fill="both", expand=True)

    # Tampilkan lampiran jika ada
    if attachments:
            label_attachments = tk.Label(frame_content, text="Attachments:", font=("Helvetica", 14))
            label_attachments.pack(pady=5)
            for filename, attachment_data in attachments:
                button_open = tk.Button(
                    frame_content,
                    text=filename,
                    font=("Helvetica", 12),
                    command=lambda data=attachment_data: open_attachment(data, filename)
                )
                button_open.pack(pady=2)

    button_back = tk.Button(root, text="Kembali", font=("Helvetica", 12), command=show_read_email_screen)
    button_back.pack(pady=10)



def open_attachment(attachment_data, filename):
    try:
        # Dialog untuk memilih lokasi penyimpanan file
        save_path = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(filename)[1],
            filetypes=[("All Files", "*.*"), ("Images", "*.jpg;*.png;*.jpeg")],
            initialfile=filename,
            title="Simpan File Lampiran"
        )
        
        # Jika pengguna tidak memilih lokasi, batalkan
        if not save_path:
            return
        
        # Simpan file di lokasi yang dipilih pengguna
        with open(save_path, "wb") as file:
            file.write(attachment_data.getbuffer())
        
        # Buka file
        os.startfile(save_path)  # Hanya untuk Windows
    except Exception as e:
        messagebox.showerror("Error", f"Gagal membuka lampiran: {e}")

def attempt_login():
    global logged_in_user
    username = entry_username.get()
    password = entry_password.get()
    user = login(username, password)
    
    if user:
        logged_in_user = user
        role = user[5]
        if role == "admin":
            show_admin_dashboard()
        else:
            show_employee_dashboard()
    else:
        messagebox.showerror("Login Error", "Username atau password salah")



def show_admin_dashboard():
    for widget in root.winfo_children():
        widget.destroy()

    username_label = tk.Label(root, text=f"Logged in as: {logged_in_user[1]}", font=("Helvetica", 12), anchor="e")
    username_label.pack(anchor="ne", padx=10, pady=5)

    label_dashboard = tk.Label(root, text="Admin Dashboard\nSelamat datang, Admin!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    kirim_email_button = tk.Button(root, text="Kirim Email", font=("Helvetica", 14), command=show_send_email_screen)
    kirim_email_button.pack(pady=20)

    read_history_button = tk.Button(root, text="Read History Send Email", font=("Helvetica", 14), command=read_sent_email_history)
    read_history_button.pack(pady=20)

    add_employee_button = tk.Button(root, text="Tambah Karyawan Baru", font=("Helvetica", 14), command=show_add_employee_page)
    add_employee_button.pack(pady=20)

    logout_button = tk.Button(root, text="Logout", font=("Helvetica", 12), command=logout)
    logout_button.pack(pady=10, side="bottom")

# Tampilan Dashboard Karyawan
def show_employee_dashboard():
    for widget in root.winfo_children():
        widget.destroy()

    username_label = tk.Label(root, text=f"Logged in as: {logged_in_user[1]}", font=("Helvetica", 12), anchor="e")
    username_label.pack(anchor="ne", padx=10, pady=5)

    label_dashboard = tk.Label(root, text="Karyawan Dashboard\nSelamat datang, Karyawan!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    read_email_button = tk.Button(root, text="Baca Email", font=("Helvetica", 14), command=show_read_email_screen)
    read_email_button.pack(pady=20)

    logout_button = tk.Button(root, text="Logout", font=("Helvetica", 12), command=logout)
    logout_button.pack(pady=10)


def show_add_employee_page():
    for widget in root.winfo_children():
        widget.destroy()

    label_add_employee = tk.Label(root, text="Tambah Karyawan Baru", font=("Helvetica", 20))
    label_add_employee.pack(pady=50)

    # Create fields for employee data input
    username_label = tk.Label(root, text="Username:")
    username_label.pack(pady=5)
    username_entry = tk.Entry(root)
    username_entry.pack(pady=5)

    password_label = tk.Label(root, text="Password:")
    password_label.pack(pady=5)
    password_entry = tk.Entry(root, show="*")
    password_entry.pack(pady=5)

    email_label = tk.Label(root, text="Email:")
    email_label.pack(pady=5)
    email_entry = tk.Entry(root)
    email_entry.pack(pady=5)

    smtp_password_label = tk.Label(root, text="SMTP Password:")
    smtp_password_label.pack(pady=5)
    smtp_password_entry = tk.Entry(root, show="*")
    smtp_password_entry.pack(pady=5)

    # Hardcode the role as 'employee'
    role = "employee"

    def add_employee_to_db():
        username = username_entry.get()
        password = password_entry.get()
        email = email_entry.get()
        smtp_password = smtp_password_entry.get()

        if not username or not password or not email or not smtp_password:
            messagebox.showwarning("Input Error", "Semua field harus diisi!")
            return

        conn = connect_to_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                # If the username already exists, show an error message
                messagebox.showwarning("Username Error", "Username sudah digunakan!")
                conn.close()
                return

            # Insert new user into the database
            query = ("INSERT INTO users (username, password, email, smtp_password, role) "
                     "VALUES (%s, %s, %s, %s, %s)")
            cursor.execute(query, (username, password, email, smtp_password, role))
            conn.commit()
            conn.close()

            # Clear the input fields after successful insert
            username_entry.delete(0, tk.END)
            password_entry.delete(0, tk.END)
            email_entry.delete(0, tk.END)
            smtp_password_entry.delete(0, tk.END)

            # Show success message
            messagebox.showinfo("Success", "Karyawan berhasil ditambahkan!")

        # Go back to the dashboard after adding
        show_admin_dashboard()

    add_employee_button = tk.Button(root, text="Add Employee", font=("Helvetica", 14), command=add_employee_to_db)
    add_employee_button.pack(pady=20)

    back_button = tk.Button(root, text="Back", font=("Helvetica", 12), command=show_admin_dashboard)
    back_button.pack(pady=10)


def show_read_email_screen():
    global current_page

    for widget in root.winfo_children():
        widget.destroy()

    username_label = tk.Label(root, text=f"Logged in as: {logged_in_user[1]}", font=("Helvetica", 12), anchor="e")
    username_label.pack(anchor="ne", padx=10, pady=5)

    label_title = tk.Label(root, text="Inbox Email", font=("Helvetica", 20))
    label_title.pack(pady=20)

    # Frame untuk Scrollable Canvas
    frame_canvas = tk.Frame(root)
    frame_canvas.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame_canvas)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    frame_content = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame_content, anchor="nw")

    email_list, total_emails = fetch_emails(current_page)

    if email_list:
        for email_data in email_list:
            button_email = tk.Button(
                frame_content,
                text=f"From: {email_data['from']} | Subject: {email_data['subject']}",
                font=("Helvetica", 12),
                justify="left",
                wraplength=350,
                command=lambda e=email_data: show_email_detail(e)
            )
            button_email.pack(pady=5, fill="x")
    else:
        label_no_email = tk.Label(frame_content, text="Tidak ada email baru.", font=("Helvetica", 14))
        label_no_email.pack(pady=20)

    # Pagination Buttons
    frame_pagination = tk.Frame(root)
    frame_pagination.pack(pady=10)

    if current_page > 1:
        button_prev = tk.Button(frame_pagination, text="Previous", font=("Helvetica", 12), command=lambda: change_page(-1))
        button_prev.pack(side="left", padx=5)

    if current_page * 10 < total_emails:
        button_next = tk.Button(frame_pagination, text="Next", font=("Helvetica", 12), command=lambda: change_page(1))
        button_next.pack(side="left", padx=5)

    button_back = tk.Button(root, text="Kembali", font=("Helvetica", 12), command=show_employee_dashboard)
    button_back.pack(pady=10)

def change_page(delta):
    global current_page
    current_page += delta
    show_read_email_screen()

def validate_and_send_email():
    global entry_attachment, selected_receiver_email, username_label, entry_subject, text_body 
    subject = entry_subject.get()
    body = text_body.get("1.0", tk.END).strip()
    if not subject or not body:
        tk.messagebox.showwarning("Peringatan", "Subject dan Isi Email tidak boleh kosong!")
    else:
        send_email(
            logged_in_user[3],
            logged_in_user[4],
            selected_receiver_email.get(),
            subject,
            body,
            entry_attachment.get()
        )
        entry_subject.delete(0, tk.END)
        text_body.delete("1.0", tk.END)
        entry_attachment.delete(0, tk.END)


def show_send_email_screen():
    global entry_attachment, selected_receiver_email, username_label, entry_subject, text_body 


    for widget in root.winfo_children():
        widget.destroy()

    username_label = tk.Label(root, text=f"Logged in as: {logged_in_user[1]}", font=("Helvetica", 12), anchor="e")
    username_label.pack(anchor="ne", padx=10, pady=5)

    label_title = tk.Label(root, text="Kirim Email", font=("Helvetica", 20))
    label_title.pack(pady=20)
    label_receiver_email = tk.Label(root, text="Kirim ke (Email)", font=("Helvetica", 14))
    label_receiver_email.pack(pady=5)

    employees = fetch_employees()
    selected_receiver_email = tk.StringVar(root)
    selected_receiver_email.set(employees[0])
    dropdown_receiver_email = tk.OptionMenu(root, selected_receiver_email, *employees)
    dropdown_receiver_email.pack(pady=5)

    label_subject = tk.Label(root, text="Subject", font=("Helvetica", 14))
    label_subject.pack(pady=5)
    entry_subject = tk.Entry(root, font=("Helvetica", 14))
    entry_subject.pack(pady=5)

    label_body = tk.Label(root, text="Isi Email", font=("Helvetica", 14))
    label_body.pack(pady=5)
    text_body = tk.Text(root, height=6, width=40, font=("Helvetica", 12))
    text_body.pack(pady=10)

    label_attachment = tk.Label(root, text="Lampiran (File)", font=("Helvetica", 14))
    label_attachment.pack(pady=5)
    entry_attachment = tk.Entry(root, font=("Helvetica", 14))
    entry_attachment.pack(pady=5)
    button_browse = tk.Button(root, text="Browse", font=("Helvetica", 12), command=browse_file)
    button_browse.pack(pady=5)

    button_send_email = tk.Button(
        root,
        text="Kirim Email",
        font=("Helvetica", 14),
        command=validate_and_send_email
    )
    button_send_email.pack(pady=20)

    button_back = tk.Button(root, text="Kembali", font=("Helvetica", 12), command=show_admin_dashboard)
    button_back.pack(pady=10)

    logout_button = tk.Button(root, text="Logout", font=("Helvetica", 12), command=logout)
    logout_button.pack(pady=10, side="bottom")

def logout():
    global logged_in_user
    global current_page
    logged_in_user = None
    current_page = 1
    for widget in root.winfo_children():
        widget.destroy()
    show_login_screen()



def browse_file():
    filename = filedialog.askopenfilename(filetypes=[("All Files", "*.*"), ("Images", "*.png;*.jpg;*.jpeg"), ("PDF Files", "*.pdf"), ("Word Files", "*.docx")])
    entry_attachment.delete(0, tk.END)  # Menghapus teks sebelumnya
    entry_attachment.insert(0, filename)  # Menampilkan path file yang dipilih

def show_login_screen():
    global entry_username, entry_password
    
    label_title = tk.Label(root, text="COMPANY EMAIL SYSTEM", font=("Helvetica", 24))
    label_title.pack(pady=20)

    separator = tk.Label(root, text="----------------------------", font=("Helvetica", 14))
    separator.pack()

    label_login = tk.Label(root, text="LOGIN", font=("Helvetica", 18))
    label_login.pack(pady=10)

    label_username = tk.Label(root, text="USERNAME", font=("Helvetica", 14))
    label_username.pack(pady=5)
    entry_username = tk.Entry(root, font=("Helvetica", 14))
    entry_username.pack(pady=5)

    label_password = tk.Label(root, text="PASSWORD", font=("Helvetica", 14))
    label_password.pack(pady=5)
    entry_password = tk.Entry(root, show="*", font=("Helvetica", 14))
    entry_password.pack(pady=5)

    submit_button = tk.Button(root, text="SUBMIT", font=("Helvetica", 14), command=attempt_login)
    submit_button.pack(pady=20)

# Membuat window utama
root = tk.Tk()
root.title("Company Email System")
root.geometry("400x400")

# Menampilkan tampilan login
show_login_screen()

root.mainloop()
