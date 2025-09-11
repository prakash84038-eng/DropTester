import os
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from .utils import load_login_data, hash_password
from . import constants

# ---------- Modern BIS Login window ----------
def show_login() -> bool:
    login_data = load_login_data()

    win = tk.Tk()
    win.title("Login")

    WIN_WIDTH = 450
    WIN_HEIGHT = 600  # Reduced from 700

    win.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
    win.resizable(False, False)

    # --- Gradient background ---
    gradient = tk.Canvas(win, width=WIN_WIDTH, height=WIN_HEIGHT, highlightthickness=0)
    gradient.pack(fill="both", expand=True)

    start_color = (210, 225, 240)
    end_color = (235, 242, 250)

    for i in range(WIN_HEIGHT):
        r = int(start_color[0] + (end_color[0] - start_color[0]) * i / WIN_HEIGHT)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * i / WIN_HEIGHT)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * i / WIN_HEIGHT)
        gradient.create_line(0, i, WIN_WIDTH, i, fill=f"#{r:02x}{g:02x}{b:02x}")

    # --- BIS Logo ---
    try:
        if hasattr(constants, 'LOGIN_LOGO_FILE') and os.path.exists(constants.LOGIN_LOGO_FILE):
            original_img = Image.open(constants.LOGIN_LOGO_FILE).convert("RGBA")
            
            # Calculate new size while preserving aspect ratio
            target_width = 200
            w, h = original_img.size
            aspect_ratio = h / w
            target_height = int(target_width * aspect_ratio)

            logo_img = original_img.resize((target_width, target_height), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(win, image=logo_photo, borderwidth=0)
            logo_label.image = logo_photo
            
            logo_y = 75
            logo_bg_r = int(start_color[0] + (end_color[0] - start_color[0]) * logo_y / WIN_HEIGHT)
            logo_bg_g = int(start_color[1] + (end_color[1] - start_color[1]) * logo_y / WIN_HEIGHT)
            logo_bg_b = int(start_color[2] + (end_color[2] - start_color[2]) * logo_y / WIN_HEIGHT)
            logo_label.config(bg=f"#{logo_bg_r:02x}{logo_bg_g:02x}{logo_bg_b:02x}")
            logo_label.place(relx=0.5, y=logo_y, anchor="center")
    except Exception as e:
        print(f"Logo error: {e}")

    # --- Title ---
    title_y = 160
    title_bg_r = int(start_color[0] + (end_color[0] - start_color[0]) * title_y / WIN_HEIGHT)
    title_bg_g = int(start_color[1] + (end_color[1] - start_color[1]) * title_y / WIN_HEIGHT)
    title_bg_b = int(start_color[2] + (end_color[2] - start_color[2]) * title_y / WIN_HEIGHT)
    title_bg_color = f"#{title_bg_r:02x}{title_bg_g:02x}{title_bg_b:02x}"

    tk.Label(win, text="Bottle Drop Tester", font=("Segoe UI", 28, "bold"),
             fg="#003366", bg=title_bg_color).place(relx=0.5, y=title_y, anchor="center")

    # --- Main card ---
    card = tk.Frame(win, bg="white", relief="solid", bd=1)
    card.place(relx=0.5, rely=0.65, anchor="center", width=360, height=380)

    content_frame = tk.Frame(card, bg="white", padx=30, pady=20)
    content_frame.pack(fill="both", expand=True)

    tk.Label(content_frame, text="Username", font=("Segoe UI", 14),
             fg="black", bg="white").pack(anchor="w", pady=(10, 2))
    username_var = tk.StringVar()
    username_entry = ttk.Entry(content_frame, textvariable=username_var,
                               font=("Segoe UI", 12), justify="left")
    username_entry.pack(pady=(0, 15), ipady=8, fill="x")

    tk.Label(content_frame, text="Password", font=("Segoe UI", 14),
             fg="black", bg="white").pack(anchor="w", pady=(5, 2))
    password_var = tk.StringVar()
    password_entry = ttk.Entry(content_frame, textvariable=password_var,
                               font=("Segoe UI", 12), justify="left", show="*")
    password_entry.pack(pady=(0, 20), ipady=8, fill="x")

    login_successful = {"ok": False}

    def do_login():
        user, pwd = username_var.get().strip(), password_var.get().strip()
        if not user or not pwd:
            messagebox.showerror("Error", "Enter both username and password", parent=win)
            return
        if user == login_data["username"] and hash_password(pwd) == login_data["password_hash"]:
            login_successful["ok"] = True
            win.destroy()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password", parent=win)
            password_var.set("")
            password_entry.focus_set()

    def do_cancel():
        login_successful["ok"] = False
        win.destroy()

    login_btn = tk.Button(content_frame, text="Login", command=do_login,
                          font=("Segoe UI", 14, "bold"),
                          bg="#F39C12", fg="white",
                          relief="flat", cursor="hand2", activebackground="#E88D02", activeforeground="white")
    login_btn.pack(pady=(15, 8), fill="x", ipady=10)

    cancel_btn = tk.Button(content_frame, text="Cancel", command=do_cancel,
                           font=("Segoe UI", 14),
                           bg="white", fg="black",
                           relief="solid", bd=1, cursor="hand2", activebackground="#F0F0F0")
    cancel_btn.pack(pady=(0, 12), fill="x", ipady=9)

    username_entry.focus_set()
    win.bind("<Return>", lambda e: do_login())
    win.protocol("WM_DELETE_WINDOW", do_cancel)
    win.mainloop()

    return login_successful["ok"]