import mysql.connector
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import *
from tkinter import ttk
import os
from dotenv import load_dotenv
import imaplib
import email

mail = None
EMAILS_PER_PAGE = 13 
current_page = 1
load_dotenv()
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
        cursor.execute("USE python_uas;")
        cursor.execute("SELECT DATABASE();")  
        current_db = cursor.fetchone()
        print(f"Current database: {current_db[0]}")  
        
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

def attempt_login():
    username = entry_username.get()
    password = entry_password.get()
    user = login(username, password)
    global mail
    
    if user:
        role = user[5]
        if role == "admin":
            show_admin_dashboard()
        else:
            mail = access_email(user[3], user[4])
            if isinstance(mail, str):
                print(f"Error: {mail}")
                return
            else:
                print(f"Terhubung ke email {mail}")
            show_employee_dashboard()
    else:
        messagebox.showerror("Login Error", "Username atau password salah")




def access_email(email_user, email_pass):
    try:
        mail = imaplib.IMAP4_SSL(os.getenv("IMAP_SERVER"), os.getenv("IMAP_PORT"))
        mail.login(email_user, email_pass)
        return mail
    except Exception as e:
        return str(e)


def fetch_inbox(mail, page=1, emails_per_page=13):
    mail.select("inbox")  # Select inbox folder
    _, data = mail.search(None, "ALL")  # Search all emails
    email_ids = data[0].split()

    total_emails = len(email_ids)
    total_pages = (total_emails + emails_per_page - 1) // emails_per_page  # Calculate total pages

    # Determine the range of email IDs for the current page
    start_idx = total_emails - (page * emails_per_page)
    end_idx = start_idx + emails_per_page

    if start_idx < 0:
        start_idx = 0

    paginated_ids = email_ids[start_idx:end_idx]

    emails = []
    for e_id in paginated_ids:
        e_id = e_id.decode()
        print(f"Fetching email with ID: {e_id}")
        _, data = mail.fetch(e_id, "(RFC822)")
        if _ == "OK":
            raw_email = data[0][1]  # Raw email data from fetch
            msg = email.message_from_bytes(raw_email)

            # Extract email details
            subject = msg["subject"]
            sender = msg["from"]
            time = msg["date"]  # Extract time (date)
            emails.append({"id": e_id, "from": sender, "subject": subject, "time": time})
        else:
            print(f"Failed to fetch email with ID: {e_id}")

    emails.reverse()  # Reverse to show newest first
    return {
        "emails": emails,
        "page": page,
        "total_pages": total_pages,
    }


def show_email_messages(mail, email_id):
    try:
        _, data = mail.fetch(email_id, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg["subject"] or "(No Subject)"
        sender = msg["from"]
        date = msg["date"]
        attachments = []

        # Proses email untuk mendapatkan konten teks dan lampiran
        email_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    email_content = part.get_payload(decode=True).decode()
                elif part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename:
                        # Menambahkan lampiran ke daftar
                        attachments.append((filename, part.get_payload(decode=True)))
        else:
            email_content = msg.get_payload(decode=True).decode()

        # Membersihkan tampilan sebelumnya
        for widget in root.winfo_children():
            widget.destroy()

        # Menampilkan subjek, pengirim, dan tanggal
        label_subject = tk.Label(root, text=f"Subjek: {subject}", font=("Helvetica", 15))
        label_subject.pack(pady=5)

        label_sender = tk.Label(root, text=f"Dari: {sender}", font=("Helvetica", 12))
        label_sender.pack(pady=5)

        label_date = tk.Label(root, text=f"Tanggal: {date}", font=("Helvetica", 12))
        label_date.pack(pady=5)

        # Menampilkan daftar lampiran dengan tombol untuk membuka
        if attachments:
            label_attachments = tk.Label(root, text="Lampiran:", font=("Helvetica", 12))
            label_attachments.pack(pady=5)

            for filename, filedata in attachments:
                button_attachment = tk.Button(
                    root,
                    text=f"Buka Lampiran: {filename}",
                    font=("Helvetica", 10),
                    command=lambda data=filedata, name=filename: open_attachment(data, name)
                )
                button_attachment.pack(pady=2)
        else:
            label_no_attachments = tk.Label(root, text="Lampiran: Tidak ada", font=("Helvetica", 12))
            label_no_attachments.pack(pady=5)

        # Menampilkan konten email
        text_content = tk.Text(root, wrap=tk.WORD)
        text_content.insert(tk.END, email_content)
        text_content.configure(state="disabled")
        text_content.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Tombol kembali ke dashboard
        button_back = tk.Button(root, text="Kembali", font=("Helvetica", 12), command=show_employee_dashboard)
        button_back.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error", f"Gagal menampilkan pesan: {e}")

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
            file.write(attachment_data)  # Tulis langsung data bytes

        # Buka file
        os.startfile(save_path)  # Hanya untuk Windows
    except Exception as e:
        messagebox.showerror("Error", f"Gagal membuka lampiran: {e}")
        
# Tampilan Dashboard Karyawan
def show_employee_dashboard():
    global current_page, EMAILS_PER_PAGE

    for widget in root.winfo_children():
        widget.destroy()

    frame_top = tk.Frame(root)
    frame_top.pack(fill=X, side=TOP, pady=5)

    button_logout = tk.Button(frame_top, text="Logout", font=("Helvetica", 12), command=logout)
    button_logout.pack(side=RIGHT, padx=10)
    label_dashboard = tk.Label(root, text="Karyawan Dashboard\nSelamat datang, Karyawan!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    global mail

    def update_inbox():
        result = fetch_inbox(mail, page=current_page, emails_per_page=EMAILS_PER_PAGE)
        emails = result["emails"]
        total_pages = result["total_pages"]

        inboxlist.delete(*inboxlist.get_children())

        for email in emails:
            inboxlist.insert("", END, values=(email["from"], email["subject"], email["time"]), tags=(email["id"],))

        button_previous.config(state=("normal" if current_page > 1 else "disabled"))
        button_next.config(state=("normal" if current_page < total_pages else "disabled"))

    # Pagination controls
    def next_page():
        global current_page
        current_page += 1
        update_inbox()

    def previous_page():
        global current_page
        current_page -= 1
        update_inbox()

    frame_buttons = tk.Frame(root)
    frame_buttons.pack()
    button_previous = tk.Button(frame_buttons, text="Previous", font=("Helvetica", 12), command=previous_page)
    button_previous.pack(side=LEFT, padx=5, pady=10)

    button_next = tk.Button(frame_buttons, text="Next", font=("Helvetica", 12), command=next_page)
    button_next.pack(side=LEFT, padx=5, pady=10)

    # Create Treeview
    inboxlist = ttk.Treeview(root, columns=("from", "subject", "time"), show="headings", height=15)
    inboxlist.pack(side=LEFT, fill=BOTH, expand=True)

    style = ttk.Style()
    style.configure("Treeview", rowheight=30)  # Adds space between rows

    # Define columns
    inboxlist.heading("from", text="From")
    inboxlist.heading("subject", text="Subject")
    inboxlist.heading("time", text="Time")

    inboxlist.column("from", width=150)
    inboxlist.column("subject", width=300)
    inboxlist.column("time", width=100)

    def on_select(event):
        selection = inboxlist.selection()
        if selection:
            selected_item = selection[0]
            email_id = inboxlist.item(selected_item, "tags")[0]  # Get email ID from tags
            show_email_messages(mail, email_id)

    inboxlist.bind("<<TreeviewSelect>>", on_select)

    update_inbox()

def show_admin_dashboard():
    for widget in root.winfo_children():
        widget.destroy()

    label_dashboard = tk.Label(root, text="Admin Dashboard\nSelamat datang, Admin!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    kirim_email_button = tk.Button(root, text="Kirim Email", font=("Helvetica", 14), command=show_send_email_screen)
    kirim_email_button.pack(pady=20)
def show_send_email_screen():
    global entry_attachment  # Tambahkan deklarasi global
    for widget in root.winfo_children():
        widget.destroy()

    label_title = tk.Label(root, text="Kirim Email", font=("Helvetica", 20))
    label_title.pack(pady=20)

    label_receiver_email = tk.Label(root, text="Kirim ke (Email)", font=("Helvetica", 14))
    label_receiver_email.pack(pady=5)
    entry_receiver_email = tk.Entry(root, font=("Helvetica", 14))
    entry_receiver_email.pack(pady=5)

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
    entry_attachment = tk.Entry(root, font=("Helvetica", 14))  # Entry diatur sebagai global
    entry_attachment.pack(pady=5)
    button_browse = tk.Button(root, text="Browse", font=("Helvetica", 12), command=browse_file)
    button_browse.pack(pady=5)

    button_send_email = tk.Button(root, text="Kirim Email", font=("Helvetica", 14))
    button_send_email.pack(pady=20)

    button_back = tk.Button(root, text="Kembali", font=("Helvetica", 12), command=show_admin_dashboard)
    button_back.pack(pady=10)



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

def logout():
    global mail
    global current_page
    mail = None
    current_page = 1
    for widget in root.winfo_children():
        widget.destroy()
    show_login_screen()
# Membuat window utama
root = tk.Tk()
root.title("Company Email System")
root.geometry("400x400")

# Menampilkan tampilan login
show_login_screen()

root.mainloop()
