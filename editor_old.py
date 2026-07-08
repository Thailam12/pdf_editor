# editor.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
from pdf_utils import PDFUtils
from gui_components import create_toolbar
from tools.text_tool import add_text_tool
from tools.image_tool import add_image_tool
from tools.drawing_tool import DrawingTool

class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor - Python")
        self.root.geometry("1000x750")
        
        self.pdf_utils = PDFUtils()
        self.current_pdf = None
        self.elements = []          # Danh sách các phần tử đã thêm
        self.drawing_tool = DrawingTool(self)
        
        self.create_gui()
        
    def create_gui(self):
        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Mở PDF", command=self.open_pdf)
        filemenu.add_command(label="Lưu PDF", command=self.save_pdf)
        filemenu.add_command(label="In PDF", command=self.print_pdf)
        filemenu.add_separator()
        filemenu.add_command(label="Thoát", command=self.root.quit)
        menubar.add_cascade(label="Tệp", menu=filemenu)
        self.root.config(menu=menubar)
        
        # Toolbar
        create_toolbar(self)
        
        # Preview Area
        self.preview_frame = ttk.LabelFrame(self.root, text="Preview")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas_preview = tk.Canvas(self.preview_frame, bg="#f8f9fa", width=650, height=850)
        self.canvas_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status
        self.status = ttk.Label(self.root, text="Sẵn sàng", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.current_pdf = path
            self.elements.clear()
            self.pdf_utils.load_pdf(path)
            self.update_preview()
            self.status.config(text=f"Đã mở: {os.path.basename(path)}")
            
    def update_preview(self):
        self.canvas_preview.delete("all")
        img_tk = self.pdf_utils.get_preview_image()
        if img_tk:
            self.canvas_preview.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.pdf_utils.preview_photo = img_tk  # Giữ reference
        
        # Vẽ lại các elements đã thêm
        for elem in self.elements:
            self.pdf_utils.draw_element_on_canvas(self.canvas_preview, elem)
            
    def add_text(self):
        add_text_tool(self)
        
    def add_image(self):
        add_image_tool(self)
        
    def start_drawing(self, shape_type):
        self.drawing_tool.start_drawing(self.canvas_preview, shape_type)
        
    def save_pdf(self):
        if not self.current_pdf:
            messagebox.showwarning("Cảnh báo", "Chưa mở file PDF nào!")
            return
        output_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if output_path:
            success = self.pdf_utils.save_edited_pdf(self.current_pdf, output_path, self.elements)
            if success:
                messagebox.showinfo("Thành công", f"Đã lưu file tại:\n{output_path}")
                
    def print_pdf(self):
        if not self.current_pdf:
            messagebox.showwarning("Cảnh báo", "Chưa có file PDF để in!")
            return
        try:
            import subprocess
            if os.name == 'nt':  # Windows
                subprocess.run(['start', self.current_pdf], shell=True)
            else:
                subprocess.run(['lp', self.current_pdf])
            messagebox.showinfo("In", "Đang gửi file đến máy in...")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể in: {str(e)}")
            
    def clear_elements(self):
        if messagebox.askyesno("Xác nhận", "Xóa tất cả chỉnh sửa?"):
            self.elements.clear()
            self.update_preview()