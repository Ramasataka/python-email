import mysql.connector
import tkinter as tk
from tkinter import *
from tkinter import ttk
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

    # Pagination variables
    emails_per_page = 5
    current_page = 0
    total_pages = (len(emails) - 1) // emails_per_page + 1
    

    label_inbox = tk.Label(root, text="Inbox updated", font=("Helvetica", 20))
    label_inbox.pack(pady=20)

# Pagination controls
    def next_page():
        nonlocal current_page
        if current_page < total_pages - 1:
            current_page += 1
            update_inbox()

    def previous_page():
        nonlocal current_page
        if current_page > 0:
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

    def update_inbox():
        inboxlist.delete(*inboxlist.get_children())  # Clear existing rows
        start_index = current_page * emails_per_page
        end_index = start_index + emails_per_page
        for index, email in enumerate(emails[start_index:end_index], start=start_index):
            inboxlist.insert("", END, values=(email["from"], email["subject"], email["time"]))

    update_inbox()

        

    # email_ids = list(range(len(emails)))  # Buat daftar indeks untuk email
    # for index, email in enumerate(emails):
    #     inboxlist.insert("", END, iid=email_ids[index],values=(email["from"], email["subject"], email["time"]))

    def on_select(event):
        selection = inboxlist.selection()
        if selection:
            selected_item = selection[0]
            email_id = len(emails) - (current_page * emails_per_page + int(inboxlist.index(selected_item)))
            print(email_id)
            show_email_messages(mail, email_id)

    inboxlist.bind("<<TreeviewSelect>>", on_select)




def access_email(email_user, email_pass):
    try:
        mail = imaplib.IMAP4_SSL(os.getenv("IMAP_SERVER"), os.getenv("IMAP_PORT"))
        mail.login(email_user, email_pass)
        return mail
    except Exception as e:
        return str(e)
    
def fetch_inbox(mail):
    try:
        mail.select("inbox")
        _, search_data = mail.search(None, "ALL")
        email_ids = search_data[0].split()
        print(f"Email IDs: {email_ids}") 

        emails = []
        for e_id in email_ids:
            e_id = e_id.decode()
            print(f"Fetching email with ID: {e_id}")
            _, data = mail.fetch(e_id, "(RFC822)")
            if _ == "OK":
                raw_email = data[0][1]  # Raw email data from fetch
                msg = email.message_from_bytes(raw_email)

                # Extract email details
                subject = msg["subject"]
                sender = msg["from"]
                # If you have time info, extract it here (for example, 'Date' field)
                time = msg["date"]  # You can format it based on your needs
                emails.append({"from": f"{sender}", "subject": f"{subject}", f"time": {time}})
            else:
                print(f"Failed to fetch email with ID: {e_id}")  
        
        # emails.sort(key=lambda x: datetime.strptime(x['time'], "%I:%M %p"), reverse=True)
        emails.reverse()
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
