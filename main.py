import tkinter as tk
from editor import PDFEditor

try:
    import customtkinter as ctk
except Exception:
    ctk = None

if __name__ == "__main__":
    if ctk is not None:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        root = ctk.CTk()
    else:
        root = tk.Tk()
    app = PDFEditor(root)
    root.mainloop()