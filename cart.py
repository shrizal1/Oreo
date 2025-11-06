import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import mysql.connector
import io
import requests
import os
from checkout import CheckoutWindow
# ---------- Database Connection ----------
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="mkkapri",
        database="oreo"
    )

# ---------- Cart Window ----------
# ---------- Cart Window ----------
class CartWindow(tk.Toplevel):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.title("Your Cart")
        self.geometry("900x600")
        self.config(bg="white")
        self.user_id = user_id

        # Header
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", pady=10, padx=20)
        tk.Label(header, text="Your Cart 🛒", bg="white",
                 font=("Arial", 18, "bold")).pack(side="left")
        tk.Button(header, text="Close", bg="#7B0000", fg="white",
                  font=("Arial", 10, "bold"), relief="flat",
                  command=self.destroy).pack(side="right")

        # Frames
        self.items_frame = tk.Frame(self, bg="white")
        self.items_frame.pack(side="left", fill="y", padx=20, pady=20)

        self.checkout_frame = tk.Frame(self, bg="#D3D3D3", width=300, height=500)
        self.checkout_frame.pack(side="right", padx=20, pady=20, fill="both", expand=True)
        self.checkout_frame.pack_propagate(False)

        tk.Label(self.checkout_frame, text="Checkout", bg="#D3D3D3",
                 font=("Arial", 14, "bold")).pack(anchor="nw", pady=10, padx=10)

        self.checkout_items = tk.Frame(self.checkout_frame, bg="#D3D3D3")
        self.checkout_items.pack(anchor="nw", padx=10)

        self.total_label = tk.Label(self.checkout_frame, text="Total: $0.00",
                                    bg="#D3D3D3", font=("Arial", 14, "bold"))
        self.total_label.pack(anchor="s", pady=10)

        tk.Button(self.checkout_frame, text="Checkout", bg="green", fg="white",
                  font=("Arial", 12, "bold"), relief="flat",
                  command=self.checkout).pack(side="bottom", pady=20)

        self.load_cart()

    # ---------- Load Cart ----------
    def load_cart(self):
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT c.cart_id, c.quantity, p.product_id, p.name, p.price, p.image_url
            FROM cart c
            JOIN product p ON c.product_id = p.product_id
            WHERE c.user_id=%s
        """, (self.user_id,))
        cart_items = cursor.fetchall()
        db.close()

        # Clear previous widgets
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        for widget in self.checkout_items.winfo_children():
            widget.destroy()

        if not cart_items:
            tk.Label(self.items_frame, text="Cart is empty", bg="white",
                     font=("Arial", 12, "bold")).pack()
            self.total_label.config(text="Total: $0.00")
            return

        self.total_price = 0
        for item in cart_items:
            cart_id, quantity, product_id, name, price, image_url = item
            self.total_price += price * quantity

            frame = tk.Frame(self.items_frame, bg="white", pady=10)
            frame.pack(anchor="nw")

            # Load image
            try:
                if os.path.exists(image_url):
                    img = Image.open(image_url)
                else:
                    response = requests.get(image_url, timeout=5)
                    img = Image.open(io.BytesIO(response.content))
                img = img.resize((100, 100))
                photo = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error loading image for {name}: {e}")
                img = Image.new("RGB", (100, 100), color="lightgrey")
                photo = ImageTk.PhotoImage(img)

            lbl_img = tk.Label(frame, image=photo, bg="white")
            lbl_img.image = photo
            lbl_img.pack(side="left")

            info_frame = tk.Frame(frame, bg="white")
            info_frame.pack(side="left", padx=10)

            tk.Label(info_frame, text=name, bg="white",
                     font=("Arial", 12, "bold")).pack(anchor="w")
            tk.Label(info_frame, text=f"Price: ${price:.2f}", bg="white",
                     font=("Arial", 12)).pack(anchor="w")
            tk.Label(info_frame, text=f"Quantity: {quantity}", bg="white",
                     font=("Arial", 12)).pack(anchor="w")

            # Increase quantity button
            tk.Button(info_frame, text="+", bg="white", font=("Arial", 12),
                      relief="flat",
                      command=lambda cid=cart_id: self.add_quantity(cid)).pack(anchor="w", pady=5)

            # Remove item button
            tk.Button(info_frame, text="Remove", bg="#FF5555", fg="white", font=("Arial", 12),
                      relief="flat",
                      command=lambda cid=cart_id: self.remove_item(cid)).pack(anchor="w", pady=5)

            # Add to checkout summary
            tk.Label(self.checkout_items, text=f"{name} × {quantity} ........... ${price*quantity:.2f}",
                     bg="#D3D3D3", font=("Arial", 12)).pack(anchor="w")

        self.total_label.config(text=f"Total: ${self.total_price:.2f}")

    # ---------- Add Quantity ----------
    def add_quantity(self, cart_id):
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE cart_id=%s", (cart_id,))
        db.commit()
        db.close()
        self.load_cart()

    # ---------- Remove Item ----------
    def remove_item(self, cart_id):
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM cart WHERE cart_id=%s", (cart_id,))
        db.commit()
        db.close()
        self.load_cart()

    # ---------- Checkout ----------
    def checkout(self):
        if getattr(self, "total_price", 0) == 0:
            messagebox.showwarning("Cart Empty", "Your cart is empty. Add items before checkout!")
            return
        CheckoutWindow(self, self.user_id)