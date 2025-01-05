import mysql.connector
from tkinter import ttk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from dotenv import load_dotenv
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from tkinter import Tk, BOTH, LEFT, END, WORD, Text

load_dotenv()
current_page = 1
emails_per_page = 10
email_history = []
mail = None

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
    return user

def attempt_login():    
    global user, mail 
    username = entry_username.get()
    password = entry_password.get()
    user = login(username, password) 
    global mail

    if user:
        try:
            user_email = user[3]  
            smtp_password = user[4] 

            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(user_email, smtp_password)  
            print(f"Terhubung ke email: {user_email}")
        except imaplib.IMAP4.error as e:
            messagebox.showerror("Email Error", f"Gagal login ke email: {str(e)}")
            return

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
    
def get_employee():
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "SELECT email FROM users WHERE  role = 'employee'"
    cursor.execute(query)
    employees = cursor.fetchall()
    conn.close()
    return [employee[0] for employee in employees]

def filter_emails(search_term, all_emails, listbox):
    listbox.delete(0, 'end') 
    filtered_emails = [email for email in all_emails if search_term.lower() in email.lower()]
    for email in filtered_emails:
        listbox.insert('end', email)

def fetch_inbox(mail, page=1, emails_per_page=10):
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

        label_subject = ctk.CTkLabel(root, text=f"Subjek: {subject}", font=("Helvetica", 15))
        label_subject.pack(pady=5)

        label_sender = ctk.CTkLabel(root, text=f"Dari: {sender}", font=("Helvetica", 12))
        label_sender.pack(pady=5)

        label_date = ctk.CTkLabel(root, text=f"Tanggal: {date}", font=("Helvetica", 12))
        label_date.pack(pady=5)

        # Menampilkan daftar lampiran dengan tombol untuk membuka
        if attachments:
            label_attachments = ctk.CTkLabel(root, text="Lampiran:", font=("Helvetica", 12))
            label_attachments.pack(pady=5)

            for filename, filedata in attachments:
                button_attachment = ctk.CTkButton(
                    root,
                    text=f"Buka Lampiran: {filename}",
                    command=lambda data=filedata, name=filename: open_attachment(data, name),
                )
                button_attachment.pack(pady=2)
        else:
            label_no_attachments = ctk.CTkLabel(root, text="Lampiran: Tidak ada", font=("Helvetica", 12))
            label_no_attachments.pack(pady=5)

        # Menampilkan konten email
        text_content = Text(root, wrap=WORD)  # Gunakan widget Text bawaan tkinter
        text_content.insert("1.0", email_content)  # Gunakan indeks tkinter
        text_content.configure(state="disabled", font=("Helvetica", 12))  # Atur font di sini
        text_content.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Tombol kembali ke dashboard
        button_back = ctk.CTkButton(root, text="Kembali", font=("Helvetica", 12), command=show_employee_dashboard)
        button_back.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error", f"Gagal menampilkan pesan: {e}")


def send_email(recipient_email, subject, body, attachment_path=None):
    
        try:
            sender_email = user[3]  
            sender_password = user[4]

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email if isinstance(recipient_email, str) else ', '.join(recipient_email)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            if attachment_path:
                attachment = MIMEBase('application', 'octet-stream')
                with open(attachment_path, 'rb') as attachment_file:
                    attachment.set_payload(attachment_file.read())
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                msg.attach(attachment)

            server = smtplib.SMTP(os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT"))# tambahkan envnya disini
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipient_email if isinstance(recipient_email, str) else recipient_email, text)
            server.quit()

            messagebox.showinfo("Sukses", f"Email berhasil dikirim ke {recipient_email}!")
        except Exception as e:
            messagebox.showerror("Gagal", f"Gagal mengirim email ke {recipient_email}: {str(e)}")

def read_sent_email_history():
    global current_page
    try:
        # Koneksi ke server IMAP Gmail
        imap = imaplib.IMAP4_SSL(os.getenv("IMAP_SERVER"), os.getenv("IMAP_PORT"))
        imap.login(user[3], user[4])

        # Pilih folder "Sent Mail"
        status, messages = imap.select('"[Gmail]/Surat Terkirim"')
        if status != "OK":
            messagebox.showerror("Error", "Gagal memilih folder 'Sent Mail'.")
            imap.logout()
            return

        status, message_count = imap.search(None, "ALL")
        if status != "OK":
            messagebox.showerror("Error", "Gagal mencari email di folder 'Sent Mail'.")
            imap.logout()
            return

        email_ids = message_count[0].split()[::-1]  # Membalik urutan email ID
        total_emails = len(email_ids)
        start = (current_page - 1) * emails_per_page
        end = start + emails_per_page

        email_history = []
        for email_id in reversed(email_ids[start:end]):
            status, msg_data = imap.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    to_email = msg.get("To")
                    date = msg.get("Date")
                    email_history.append({
                        "id": email_id.decode(),
                        "subject": subject,
                        "to": to_email,
                        "date": date
                    })

        if email_history:
            show_email_list(imap, email_history, total_emails)
        else:
            messagebox.showinfo("Info", "Tidak ada email terkirim yang ditemukan.")

    except Exception as e:
        messagebox.showerror("Error", f"Gagal membaca riwayat email: {str(e)}")


def show_email_list(mail, email_history, total_emails):
    global current_page, emails_per_page

    for widget in root.winfo_children():
        widget.destroy()

    ctk.CTkLabel(root, text="Riwayat Pesan", font=("Helvetica", 18, "bold")).pack(pady=10)

    inboxlist = ttk.Treeview(root, columns=("to", "subject", "time"), show="headings", height=15)
    inboxlist.pack(side=LEFT, fill=BOTH, expand=True)

    inboxlist.heading("to", text="To")
    inboxlist.heading("subject", text="Subject")
    inboxlist.heading("time", text="Time")

    inboxlist.column("to", width=200)
    inboxlist.column("subject", width=400)
    inboxlist.column("time", width=150)

    for email_data in email_history:
        inboxlist.insert("", END, values=(email_data["to"], email_data["subject"], email_data["date"]), tags=(email_data["id"],))

    def on_select(event):
        selection = inboxlist.selection()
        if selection:
            selected_item = selection[0]
            email_id = inboxlist.item(selected_item, "tags")[0]
            show_email_messages_send(mail, email_id)

    inboxlist.bind("<<TreeviewSelect>>", on_select)

    navigation_frame = ctk.CTkFrame(root)
    navigation_frame.pack(fill=BOTH, pady=10)

    if current_page > 1:
        prev_button = ctk.CTkButton(navigation_frame, text="Sebelumnya", command=previous_page)
        prev_button.pack(pady=5)

    if current_page * emails_per_page < total_emails:
        next_button = ctk.CTkButton(navigation_frame, text="Berikutnya", command=next_page)
        next_button.pack(pady=5)
        
    button_back = ctk.CTkButton(root, text="Kembali", font=("Helvetica", 12), command=show_admin_dashboard)
    button_back.pack(pady=10)


def previous_page():
    global current_page
    if current_page > 1:
        current_page -= 1
        read_sent_email_history()


def next_page():
    global current_page
    current_page += 1
    read_sent_email_history()


def show_email_messages_send(mail, email_id):
    try:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            messagebox.showerror("Error", "Gagal mengambil detail email.")
            return

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                to_email = msg.get("To")
                date = msg.get("Date")
                content = ""
                attachments = []

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))

                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            content = part.get_payload(decode=True).decode()
                        elif "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                attachments.append((filename, part.get_payload(decode=True)))
                else:
                    content = msg.get_payload(decode=True).decode()

                for widget in root.winfo_children():
                    widget.destroy()

                ctk.CTkLabel(root, text=f"Subjek: {subject}", font=("Helvetica", 15)).pack(pady=5)
                ctk.CTkLabel(root, text=f"Kepada: {to_email}", font=("Helvetica", 12)).pack(pady=5)
                ctk.CTkLabel(root, text=f"Tanggal: {date}", font=("Helvetica", 12)).pack(pady=5)

                text_content = Text(root, wrap=WORD)
                text_content.insert(END, content)
                text_content.configure(state="disabled")
                text_content.pack(fill=BOTH, expand=True, padx=10, pady=10)

                if attachments:
                    ctk.CTkLabel(root, text="Lampiran:", font=("Helvetica", 12, "bold")).pack(pady=5)
                    for filename, data in attachments:
                        ctk.CTkButton(root, text=filename, command=lambda d=data, f=filename: open_attachment(d, f)).pack(pady=2)

                ctk.CTkButton(root, text="Kembali", font=("Helvetica", 12), command=read_sent_email_history).pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error", f"Gagal membaca detail email: {str(e)}")

def open_attachment(attachment_data, filename):
    try:
        save_path = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(filename)[1],
            filetypes=[("All Files", "*.*"), ("Images", "*.jpg;*.png;*.jpeg")],
            initialfile=filename,
            title="Simpan File Lampiran"
        )

        if not save_path:
            return

        with open(save_path, "wb") as file:
            file.write(attachment_data)

        os.startfile(save_path)
    except Exception as e:
        messagebox.showerror("Error", f"Gagal membuka lampiran: {e}")

def show_admin_dashboard():
    for widget in root.winfo_children():
        widget.destroy()
        
    label_dashboard = ctk.CTkLabel(root, text="Admin Dashboard\nSelamat datang, Admin!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    kirim_email_button = ctk.CTkButton(root, text="Kirim Email", font=("Helvetica", 14), command=show_send_email_screen)
    kirim_email_button.pack(pady=20)
    
    read_history_button = ctk.CTkButton(root, text="Read History Send Email", font=("Helvetica", 14), command=read_sent_email_history)
    read_history_button.pack(pady=20)
    
    frame_logout = ctk.CTkFrame(root)
    frame_logout.pack(pady=10)

    button_logout = ctk.CTkButton(frame_logout, text="Logout", font=("Helvetica", 12), command=logout)
    button_logout.pack(pady=5)

def show_employee_dashboard():
    global current_page, emails_per_page

    # Clear previous widgets
    for widget in root.winfo_children():
        widget.destroy()

    # Top frame with logout button
    frame_top = ctk.CTkFrame(root)
    frame_top.pack(pady=10)

    button_logout = ctk.CTkButton(frame_top, text="Logout", font=("Helvetica", 12), command=logout)
    button_logout.pack(pady=5)

    label_dashboard = ctk.CTkLabel(root, text="Karyawan Dashboard\nSelamat datang, Karyawan!", font=("Helvetica", 20))
    label_dashboard.pack(pady=30)

    # Function to update inbox
    def update_inbox():
        result = fetch_inbox(mail, page=current_page, emails_per_page=emails_per_page)
        emails = result["emails"]
        total_pages = result["total_pages"]

        inboxlist.delete(*inboxlist.get_children())

        for email_data in emails:
            inboxlist.insert("", END, values=(email_data["from"], email_data["subject"], email_data["time"]), tags=(email_data["id"],))

        button_previous.configure(state=("normal" if current_page > 1 else "disabled"))
        button_next.configure(state=("normal" if current_page < total_pages else "disabled"))

    # Pagination controls
    def next_page():
        global current_page
        current_page += 1
        update_inbox()

    def previous_page():
        global current_page
        current_page -= 1
        update_inbox()

    # Pagination buttons
    frame_buttons = ctk.CTkFrame(root)
    frame_buttons.pack(pady=10)

    button_previous = ctk.CTkButton(frame_buttons, text="Previous", font=("Helvetica", 12), command=previous_page)
    button_previous.pack(side=LEFT, padx=5)

    button_next = ctk.CTkButton(frame_buttons, text="Next", font=("Helvetica", 12), command=next_page)
    button_next.pack(side=LEFT, padx=5)

    # Treeview to display inbox
    inboxlist = ttk.Treeview(root, columns=("from", "subject", "time"), show="headings", height=15)
    inboxlist.pack(side=LEFT, fill=BOTH, expand=True, pady=10)

    # Define column headers
    inboxlist.heading("from", text="From")
    inboxlist.heading("subject", text="Subject")
    inboxlist.heading("time", text="Time")

    # Define column width
    inboxlist.column("from", width=150)
    inboxlist.column("subject", width=300)
    inboxlist.column("time", width=100)

    # Bind item selection to email detail view
    def on_select(event):
        selection = inboxlist.selection()
        if selection:
            selected_item = selection[0]
            email_id = inboxlist.item(selected_item, "tags")[0]
            show_email_messages(mail, email_id)

    inboxlist.bind("<<TreeviewSelect>>", on_select)

    update_inbox()
    
    
def show_send_email_screen():
    global label_attachment_path, frame_email_results, selected_emails, frame_selected_emails
    for widget in root.winfo_children():
        widget.destroy()

    label_title = ctk.CTkLabel(root, text="Kirim Email", font=("Helvetica", 20))
    label_title.pack(pady=20)

    employees = get_employee()
    search_var = ctk.StringVar()

    # Frame utama untuk membagi tampilan kiri dan kanan
    main_frame = ctk.CTkScrollableFrame(root)
    main_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Frame kiri untuk hasil pencarian email
    frame_left = ctk.CTkFrame(main_frame, width=200)
    frame_left.pack(side="left", padx=5, fill="y")

    label_search = ctk.CTkLabel(frame_left, text="Cari Email:", font=("Helvetica", 14))
    label_search.pack(pady=5)

    entry_search = ctk.CTkEntry(frame_left, textvariable=search_var, font=("Helvetica", 14), placeholder_text="Cari email...")
    entry_search.pack(pady=5)

    # Scrollable frame untuk hasil email
    frame_email_results = ctk.CTkScrollableFrame(frame_left, width=500, height=50)
    frame_email_results.pack(pady=10, fill="both", expand=True)

    # Frame kanan untuk email yang dipilih
    frame_right = ctk.CTkFrame(main_frame, width=200)
    frame_right.pack(side="right", padx=10, fill="y")

    label_selected = ctk.CTkLabel(frame_right, text="Email yang Dipilih:", font=("Helvetica", 14))
    label_selected.pack(pady=5)

    # Scrollable frame untuk email yang dipilih
    frame_selected_emails = ctk.CTkScrollableFrame(frame_right, width=500, height=50)
    frame_selected_emails.pack(pady=10, fill="both", expand=True)

    selected_emails = []  # List untuk menyimpan email yang dipilih

    def update_selected_emails():
        """Tampilkan daftar email yang dipilih."""
        for widget in frame_selected_emails.winfo_children():
            widget.destroy()

        for email in selected_emails:
            frame = ctk.CTkFrame(frame_selected_emails)
            frame.pack(fill="x", pady=5)

            label_email = ctk.CTkLabel(frame, text=email, font=("Helvetica", 12), anchor="w")
            label_email.pack(side="left", padx=5, expand=True)

            button_remove = ctk.CTkButton(
                frame,
                text="X",
                font=("Helvetica", 12),
                command=lambda e=email: remove_email(e)
            )
            button_remove.pack(side="right", padx=5)

    def remove_email(email):
        """Hapus email dari daftar."""
        selected_emails.remove(email)
        update_selected_emails()

    def display_emails(email_list):
        """Tampilkan daftar email berdasarkan pencarian."""
        for widget in frame_email_results.winfo_children():
            widget.destroy()

        if email_list:
            for email in email_list:
                frame = ctk.CTkFrame(frame_email_results)
                frame.pack(fill="x", pady=5)

                label_email = ctk.CTkLabel(frame, text=email, font=("Helvetica", 12), anchor="w")
                label_email.pack(side="left", padx=5, expand=True)

                def add_email(e=email):
                    if e not in selected_emails:
                        selected_emails.append(e)
                        update_selected_emails()

                button_select = ctk.CTkButton(
                    frame,
                    text="Pilih Email",
                    font=("Helvetica", 12),
                    command=lambda e=email: add_email(e)
                )
                button_select.pack(side="right", padx=5)
        else:
            label_no_results = ctk.CTkLabel(
                frame_email_results,
                text="Tidak ada hasil pencarian.",
                font=("Helvetica", 12),
                anchor="center"
            )
            label_no_results.pack(pady=10)

    def on_search(*args):
        search_term = search_var.get().strip()
        if search_term == "":
            display_emails([])  
        else:
            filtered_emails = [email for email in employees if search_term.lower() in email.lower()]
            display_emails(filtered_emails)

    search_var.trace_add("write", on_search)
    display_emails    # Default frame kosong

    # Input subject dan body email
    label_subject = ctk.CTkLabel(root, text="Subject", font=("Helvetica", 14))
    label_subject.pack(pady=5)
    entry_subject = ctk.CTkEntry(root, font=("Helvetica", 14))
    entry_subject.pack(pady=5)

    label_body = ctk.CTkLabel(root, text="Isi Email", font=("Helvetica", 14))
    label_body.pack(pady=5)
    text_body = ctk.CTkTextbox(root, height=120, width=600, font=("Helvetica", 12))  # Perbesar ukuran teks
    text_body.pack(pady=10)

    # File attachment
    label_attachment = ctk.CTkLabel(root, text="Lampiran", font=("Helvetica", 14))
    label_attachment.pack(pady=5)

    label_attachment_path = ctk.CTkLabel(root, text="Tidak ada file yang dipilih", font=("Helvetica", 12), anchor="w")
    label_attachment_path.pack(pady=5)

    button_browse = ctk.CTkButton(root, text="Browse", font=("Helvetica", 12), command=browse_file)
    button_browse.pack(pady=5)

    def send_email_action():
        if not selected_emails:
            messagebox.showerror("Error", "Tidak ada email yang dipilih.")
            return

        subject = entry_subject.get().strip()
        body = text_body.get("1.0", "end").strip()
        attachment_path = label_attachment_path.cget("text")

        # Check if subject and body are not empty
        if not subject:
            messagebox.showerror("Error", "Subject tidak boleh kosong.")
            return
        
        if not body:
            messagebox.showerror("Error", "Isi email tidak boleh kosong.")
            return

        if attachment_path == "Tidak ada file yang dipilih":
            attachment_path = None

        
        for email in selected_emails:
            send_email(email, subject, body, attachment_path)

        selected_emails.clear()
        update_selected_emails()
        entry_subject.delete(0, "end")
        text_body.delete("1.0", "end")
        label_attachment_path.configure(text="Tidak ada file yang dipilih")
    button_send_email = ctk.CTkButton(root, text="Kirim Email", font=("Helvetica", 14), command=send_email_action)
    button_send_email.pack(pady=20)

    button_back = ctk.CTkButton(root, text="Kembali", font=("Helvetica", 12), command=show_admin_dashboard)
    button_back.pack(pady=10)



def browse_file():
    filename = filedialog.askopenfilename(filetypes=[("All Files", "*.*"), ("Images", "*.png;*.jpg;*.jpeg"), ("PDF Files", "*.pdf"), ("Word Files", "*.docx")])
    if filename:
        label_attachment_path.configure(text=filename)  # Menampilkan path file di label
    else:
        label_attachment_path.configure(text="Tidak ada file yang dipilih")  # Reset jika tidak ada file yang dipilih

def show_login_screen():
    global entry_username, entry_password

    label_title = ctk.CTkLabel(root, text="COMPANY EMAIL SYSTEM", font=("Helvetica", 24))
    label_title.pack(pady=20)

    separator = ctk.CTkLabel(root, text="----------------------------", font=("Helvetica", 14))
    separator.pack()

    label_login = ctk.CTkLabel(root, text="LOGIN", font=("Helvetica", 18))
    label_login.pack(pady=10)
    label_username = ctk.CTkLabel(root, text="USERNAME", font=("Helvetica", 14))
    label_username.pack(pady=5)
    entry_username = ctk.CTkEntry(root, font=("Helvetica", 14))
    entry_username.pack(pady=5)

    label_password = ctk.CTkLabel(root, text="PASSWORD", font=("Helvetica", 14))
    label_password.pack(pady=5)
    entry_password = ctk.CTkEntry(root, show="*", font=("Helvetica", 14))
    entry_password.pack(pady=5)

    submit_button = ctk.CTkButton(root, text="SUBMIT", font=("Helvetica", 14), command=attempt_login)
    submit_button.pack(pady=20)

def logout():
    global mail, email_history
    global current_page
    current_page = 1
    email_history = []
    mail = None
    for widget in root.winfo_children():
        widget.destroy()
    show_login_screen()
    
ctk.set_appearance_mode("dark") 
ctk.set_default_color_theme("blue")  # Pilihan tema: "blue", "green", "dark-blue"

root = ctk.CTk()
root.title("Company Email System")
root.geometry("400x500")

show_login_screen()

root.mainloop()
