import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import mysql.connector

from database import increment_login_counter, connect_db
from admin import AdminPanel


# POS Staff Login Window
def login_window(on_success):
    # Color palette (black & red)
    BG_MAIN = "#050505"
    BG_CARD = "#151515"
    FG_TEXT = "#FFFFFF"
    ACCENT = "#FF3B3B"

    root = tk.Tk()
    root.title("Oreo POS - Staff Login")
    root.state("zoomed")
    root.config(bg=BG_MAIN)

    # ---------- Load Logo ----------
    try:
        logo_img = Image.open("OREO.png")
        logo_img = logo_img.resize((120, 120))
        logo = ImageTk.PhotoImage(logo_img)
    except Exception:
        logo = None

    # Center card
    card = tk.Frame(root, bg=BG_CARD, padx=40, pady=40)
    card.place(relx=0.5, rely=0.5, anchor="center")

    if logo:
        tk.Label(card, image=logo, bg=BG_CARD).pack(pady=(0, 10))

    tk.Label(
        card,
        text="Oreo POS",
        font=("Arial", 22, "bold"),
        bg=BG_CARD,
        fg=ACCENT,
    ).pack(pady=(0, 20))

    tk.Label(card, text="Staff Username:", font=("Arial", 10, "bold"), bg=BG_CARD, fg=FG_TEXT).pack(anchor="w")
    username_entry = tk.Entry(card, width=30, bd=0, bg="#222222", fg=FG_TEXT, insertbackground=FG_TEXT)
    username_entry.pack(pady=5)

    tk.Label(card, text="Password:", font=("Arial", 10, "bold"), bg=BG_CARD, fg=FG_TEXT).pack(anchor="w")
    password_entry = tk.Entry(card, show="*", width=30, bd=0, bg="#222222", fg=FG_TEXT, insertbackground=FG_TEXT)
    password_entry.pack(pady=5)

    # ---------- Login Function ----------
    def login_user():
        username = username_entry.get().strip()
        password = password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Input Error", "Please fill all fields!")
            return

        db = connect_db()
        cursor = db.cursor()
        try:
            # Staff only: admin or employee
            cursor.execute(
                """
                SELECT user_id, username, role
                FROM users
                WHERE username=%s AND password=%s AND role IN ('admin','employee')
                """,
                (username, password),
            )
            user = cursor.fetchone()
            if not user:
                messagebox.showerror("Error", "Invalid credentials or not a staff account.")
                return

            user_id, uname, role = user
            try:
                increment_login_counter(user_id)
            except Exception:
                pass

            root.destroy()
            if role == "admin":
                # Open admin panel directly
                admin_panel = AdminPanel()
                admin_panel.mainloop()
            else:
                # Employee dashboard (POS screen)
                on_success(user_id, uname)
        except mysql.connector.Error as err:
            messagebox.showerror("DB Error", str(err))
        finally:
            db.close()

    # ---------- Forgot Password (staff only) ----------
    def forgot_password():
        email = simpledialog.askstring("Forgot Password", "Enter your staff email:", parent=root)
        if email is None:
            return
        email = email.strip()
        if not email:
            messagebox.showwarning("Input Error", "Email cannot be empty.")
            return

        try:
            db = connect_db()
            cursor = db.cursor()
            cursor.execute(
                "SELECT password FROM users WHERE email=%s AND role IN ('admin','employee')",
                (email,),
            )
            row = cursor.fetchone()
            if row:
                saved_password = row[0]
                messagebox.showinfo("Your Password", f"Password for {email}:\n{saved_password}")
            else:
                messagebox.showerror("Not Found", "No staff account found with that email.")
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Database Error: {err}")
        finally:
            try:
                db.close()
            except Exception:
                pass

    # Buttons
    btn_frame = tk.Frame(card, bg=BG_CARD)
    btn_frame.pack(pady=15, fill="x")

    tk.Button(
        btn_frame,
        text="Login",
        bg=ACCENT,
        fg="white",
        font=("Arial", 10, "bold"),
        relief="flat",
        command=login_user,
    ).pack(fill="x", pady=(0, 5))

    tk.Button(
        btn_frame,
        text="Forgot Password?",
        bg=BG_CARD,
        fg=ACCENT,
        font=("Arial", 10, "bold"),
        relief="flat",
        command=forgot_password,
    ).pack(fill="x")

    # Enter key triggers login
    root.bind("<Return>", lambda e: login_user())

    root.mainloop()
