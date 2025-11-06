import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import mysql.connector
from cart import CartWindow
import io
import requests
import os

from login import login_window

# ---------- Database Connection ----------
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="mkkapri",
        database="oreo"
    )

# ---------- Dashboard ----------
class Dashboard(tk.Tk):
    def __init__(self, user_id, username):
        super().__init__()
        self.title("Oreo Dashboard")
        self.state("zoomed")
        self.config(bg="white")
        self.username = username
        self.user_id = user_id

        # Logo
        try:
            img = Image.open("oreo.png")
            img = img.resize((80, 80))
            self.logo = ImageTk.PhotoImage(img)
        except:
            self.logo = None

        # Header
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", pady=10, padx=20)

        if self.logo:
            tk.Label(header, image=self.logo, bg="white").pack(side="left")

        tk.Label(header, text=f"Welcome To Oreo, {username}", bg="white",
                 font=("Arial", 14, "bold")).pack(side="left", padx=10)

        cart_btn = tk.Button(header, text="🛒", bg="white", font=("Arial", 16),
                             relief="flat", command=self.open_cart)
        cart_btn.pack(side="right", padx=10)

        logout_btn = tk.Button(header, text="Log Out", bg="#7B0000", fg="white",
                               font=("Arial", 10, "bold"), relief="flat",
                               command=self.logout)
        logout_btn.pack(side="right", padx=10)

        # ---------- Scrollable Products Frame ----------
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, pady=20)

        self.canvas = tk.Canvas(container, bg="white")
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.products_frame = tk.Frame(self.canvas, bg="white")

        # Configure scrolling region
        self.products_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Add products_frame to canvas
        self.canvas.create_window((0, 0), window=self.products_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Load products
        self.load_products()

    # ---------- Mousewheel scrolling ----------
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # ---------- Load Products ----------
    def load_products(self):
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT product_id, name, description, price, image_url FROM product")
        products = cursor.fetchall()
        db.close()

        if not products:
            tk.Label(self.products_frame, text="No products found!", bg="white",
                     font=("Arial", 12, "bold")).pack()
            return

        columns = 5
        for i, product in enumerate(products):
            frame = tk.Frame(self.products_frame, bg="white", padx=20, pady=20)
            frame.grid(row=i // columns, column=i % columns)

            # --- Load Image (local path or URL) ---
            try:
                if product[4] and os.path.exists(product[4]):
                    # Local file
                    img = Image.open(product[4])
                elif product[4]:
                    # URL
                    response = requests.get(product[4], timeout=5)
                    img = Image.open(io.BytesIO(response.content))
                else:
                    raise Exception("No image provided")

                img = img.resize((150, 150))
                photo = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error loading image for {product[1]}: {e}")
                img = Image.new("RGB", (150, 150), color="lightgrey")
                photo = ImageTk.PhotoImage(img)

            lbl_img = tk.Label(frame, image=photo, bg="white")
            lbl_img.image = photo  
            lbl_img.pack()

            tk.Label(frame, text=product[1], bg="white",
                     font=("Arial", 10, "bold")).pack(pady=2)
            tk.Label(frame, text=f"Price: ${product[3]:.2f}", bg="white",
                     font=("Arial", 10)).pack()

            add_btn = tk.Button(frame, text="🛒", font=("Arial", 12),
                                bg="white", relief="flat",
                                command=lambda p=product: self.add_to_cart(p))
            add_btn.pack(pady=3)

    # ---------- Add to Cart ----------
    def add_to_cart(self, product):
        product_id = product[0]
        db = connect_db()
        cursor = db.cursor()

        cursor.execute("SELECT quantity FROM cart WHERE user_id=%s AND product_id=%s",
                       (self.user_id, product_id))
        result = cursor.fetchone()

        if result:
            new_qty = result[0] + 1
            cursor.execute("UPDATE cart SET quantity=%s WHERE user_id=%s AND product_id=%s",
                           (new_qty, self.user_id, product_id))
        else:
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                           (self.user_id, product_id, 1))

        db.commit()
        db.close()
        messagebox.showinfo("Cart", f"Added {product[1]} to cart!")

    # ---------- Open Cart ----------
    def open_cart(self):
        CartWindow(self, self.user_id)

    # ---------- Logout ----------
    def logout(self):
        self.destroy()

def start_dashboard(user_id, username):
    app = Dashboard(user_id, username)
    app.mainloop()

if __name__ == "__main__":
    login_window(on_success=start_dashboard)
