import mysql.connector
import tkinter as tk
from tkinter import *
import os
from dotenv import load_dotenv
import imaplib
import email

mail = None
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
    
    query_login = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query_login, (username, password))

    user = cursor.fetchone()
    conn.close()
    print(user)
    return user

def attempt_login():
    username = entry_username.get()
    password = entry_password.get()
    user = login(username, password)
    global mail
    mail = access_email(user[3], user[4])
    if isinstance(mail, str):
        print(f"Error: {mail}")
        return
    else:
        print(f"Terhubung ke email {mail}")
    
    if user:
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

    label_dashboard = tk.Label(root, text="Admin Dashboard\nSelamat datang, Admin!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    kirim_email_button = tk.Button(root, text="Kirim Email", font=("Helvetica", 14), command=show_send_email_screen)
    kirim_email_button.pack(pady=20)

# Tampilan Dashboard Karyawan
def show_employee_dashboard():
    for widget in root.winfo_children():
        widget.destroy()

    label_dashboard = tk.Label(root, text="Karyawan Dashboard\nSelamat datang, Karyawan!", font=("Helvetica", 20))
    label_dashboard.pack(pady=50)

    global mail
    emails = fetch_inbox(mail)

    label_inbox = tk.Label(root, text="Inbox updated", font=("Helvetica", 20))
    label_inbox.pack(pady=50)

    inbox_list = tk.Listbox(root, height=15)
    inbox_list.delete(0, END)

    email_ids = list(range(len(emails)))  # Buat daftar indeks untuk email
    for email in emails:
        inbox_list.insert(END, email)
    inbox_list.pack(fill=BOTH, expand=True, side=LEFT)

    scrollbar = tk.Scrollbar(root, orient=VERTICAL, command=inbox_list.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    inbox_list.config(yscrollcommand=scrollbar.set)



    def on_select(event):
        # Ambil indeks item yang dipilih
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            email_id = email_ids[index]
            email_id = str(email_id).strip()
            print(email_id)
            show_email_messages(mail, email_id)  # Panggil fungsi untuk menampilkan isi email

    inbox_list.bind("<<ListboxSelect>>", on_select)


def access_email(email_user, email_pass):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_user, email_pass)
        return mail
    except Exception as e:
        return str(e)
    
def fetch_inbox(mail):
    try:
        mail.select("inbox")
        _, search_data = mail.search(None, "ALL")
        email_ids = search_data[0].split()

        emails = []
        for e_id in email_ids:
            e_id = e_id.decode()
            _, data = mail.fetch(e_id, "(RFC822)")
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg["subject"]
            sender = msg["from"]
            emails.append(f"{sender} - {subject}")
        print(email_ids)
        return emails
    except Exception as e:
        return [str(e)]


def show_email_messages(mail, email_id):
    """Tampilkan isi email berdasarkan ID."""
    try:
        # Validasi format email_id
        email_id = str(email_id).strip()

        # FETCH email dengan ID yang valid
        _, data = mail.fetch(email_id, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Ambil isi email (hanya text/plain)
        email_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    email_content = part.get_payload(decode=True).decode()
                    break
        else:
            email_content = msg.get_payload(decode=True).decode()

        # Buat jendela baru untuk menampilkan isi email
        for widget in root.winfo_children():
            widget.destroy()

        label_subject = tk.Label(root, text=f"Subjek: {msg['subject']}", font=("Helvetica", 15))
        label_subject.pack(pady=10)

        text_content = tk.Text(root, wrap=tk.WORD)
        text_content.insert(tk.END, email_content)
        text_content.configure(state="disabled")  # Nonaktifkan edit
        text_content.pack(fill=BOTH, expand=True, padx=10, pady=10)

        button_back = tk.Button(root, text="Kembali", font=("Helvetica", 12), command=show_employee_dashboard)
        button_back.pack(pady=10)
    except Exception as e:
        print(f"Error: {e}")

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

# Membuat window utama
root = tk.Tk()
root.title("Company Email System")
root.geometry("400x400")

# Menampilkan tampilan login
show_login_screen()

root.mainloop()
