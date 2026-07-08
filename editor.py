# -*- coding: utf-8 -*-
# editor.py - Word-like Super PDF Editor
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import os
from PIL import Image, ImageTk
from pdf_utils import PDFUtils
from new_file_template import create_blank_pdf
import tempfile


from gui_components import create_toolbar, create_formatting_toolbar, create_property_panel
from tools.text_tool import add_text_tool
from tools.image_tool import add_image_tool
from tools.drawing_tool import DrawingTool
from text_formatting import FormattingManager
from undo_redo import UndoRedoManager
from editor_services import CanvasInteractionManager, DocumentManager

class PDFEditor:
        def __init__(self, root):

        self.root = root
        # i18n
        from i18n import get_i18n, normalize_lang, LANG_VI, LANG_EN
        # default language (VI). can be changed in UI.
        self.lang = LANG_VI
        self._t = get_i18n(self.lang)
        self.root.title(self._t["app_title"])

        self.root.geometry("1400x850")
        
        # Core components
        self.pdf_utils = PDFUtils()
        self.current_pdf = None
        self.elements = []
        self.element_images = []
        self.selected_element = None
        self.drawing_tool = DrawingTool(self)
        
        # Formatting and undo/redo
        self.formatting_manager = FormattingManager()
        self.undo_redo_manager = UndoRedoManager()

        # Services / Managers
        from editor_services import CanvasInteractionManager, DocumentManager, OCRManager, ElementManager
        self.canvas_interaction = CanvasInteractionManager(self)
        self.document_manager = DocumentManager(self)
        self.ocr_manager = OCRManager(self)
        self.element_manager = ElementManager(self)
        
        # UI state
        self.zoom_level = 100
        self.current_page = 0
        self.total_pages = 0
        self.selection_mode = False

        # OCR state
        self.ocr_running = False
        self.ocr_job_id = 0


        # Resize state
        self.resizing = False
        self.resize_handle = None
        self.resize_start = None
        self.resize_orig_params = None

        # Drag (move) state for elements
        self.dragging = False
        self.drag_start = None          # (event.x, event.y) canvas coords (for delta if needed)
        self.drag_orig_params = None    # snapshot of params at drag start
        self.dragged_element_type = None  # element type being dragged
        self.drag_offset = None         # (offset_x_pts, offset_y_pts) cursor-to-element position in editor points


        
        # New-file/temp document state
        self.is_temp_document = False
        self.temp_doc_path = None
        self.current_document_dir = None

        self.create_gui()
        self.update_info_panel()

        
    def create_gui(self):
        """Create the GUI layout"""
        # Menu bar
        self.create_menu_bar()
        
        # Top toolbar container
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        create_toolbar(self, parent=toolbar_frame)
        create_formatting_toolbar(self, parent=toolbar_frame)
        
        # Main content area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)
        
        # Left: Canvas
        canvas_frame = ttk.LabelFrame(main_frame, text="Trình chỉnh sửa", padding=5)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        
        # Canvas with scrollbars
        self.canvas_preview = tk.Canvas(canvas_frame, bg="#f8f9fa", width=800, height=600, cursor="cross")
        self.canvas_preview.pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events
        self.canvas_preview.bind("<Button-1>", self.on_canvas_click)
        self.canvas_preview.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas_preview.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas_preview.bind("<Motion>", self.on_canvas_motion)
        self.canvas_preview.bind("<Button-3>", self.show_context_menu)
        self.canvas_preview.bind("<Delete>", lambda e: self.delete_selected_element())
        
        # Right: Property panel
        property_panel = create_property_panel(self, parent=main_frame)
        property_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        
        # Status bar
        self.status = ttk.Label(self.root, text="Sẵn sàng", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_menu_bar(self):
        """Create menu bar with all options"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New (Temp)", command=self.new_temp_document, accelerator="Ctrl+N")
        file_menu.add_command(label="Mở PDF", command=self.open_pdf, accelerator="Ctrl+O")
        file_menu.add_command(label="Lưu PDF", command=self.save_pdf, accelerator="Ctrl+S")
        file_menu.add_command(label="Lưu thành...", command=self.save_as_pdf)
        file_menu.add_command(label="Xuất PDF", command=self.export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="In PDF", command=self.print_pdf, accelerator="Ctrl+P")
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.root.quit)
        menubar.add_cascade(label="Tệp", menu=file_menu)

        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Hoàn tác", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Làm lại", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Xóa tất cả", command=self.clear_elements)
        menubar.add_cascade(label="Chỉnh sửa", menu=edit_menu)
        
        # Insert menu
        insert_menu = tk.Menu(menubar, tearoff=0)
        insert_menu.add_command(label="Chữ", command=self.add_text)
        insert_menu.add_command(label="Ảnh", command=self.add_image)
        insert_menu.add_separator()
        insert_menu.add_command(label="OCR Trang hiện tại...", command=self.ocr_current_page_dialog)
        insert_menu.add_command(label="OCR Tất cả các trang...", command=self.ocr_all_pages_dialog)
        insert_menu.add_separator()
        insert_menu.add_command(label="Đường", command=lambda: self.start_drawing("line"))
        insert_menu.add_command(label="Hình chữ nhật", command=lambda: self.start_drawing("rect"))
        insert_menu.add_command(label="Ellipse", command=lambda: self.start_drawing("ellipse"))
        insert_menu.add_command(label="Tam giác", command=lambda: self.start_drawing("triangle"))
        menubar.add_cascade(label="Chèn", menu=insert_menu)

        
        # Format menu
        format_menu = tk.Menu(menubar, tearoff=0)
        format_menu.add_command(label="Tô đậm", command=self.toggle_bold, accelerator="Ctrl+B")
        format_menu.add_command(label="Nghiêng", command=self.toggle_italic, accelerator="Ctrl+I")
        format_menu.add_command(label="Gạch chân", command=self.toggle_underline, accelerator="Ctrl+U")
        format_menu.add_separator()
        format_menu.add_command(label="Căn trái", command=lambda: self.set_alignment("left"))
        format_menu.add_command(label="Căn giữa", command=lambda: self.set_alignment("center"))
        format_menu.add_command(label="Căn phải", command=lambda: self.set_alignment("right"))
        menubar.add_cascade(label="Định dạng", menu=format_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Trang trước", command=self.previous_page, accelerator="Ctrl+Left")
        view_menu.add_command(label="Trang sau", command=self.next_page, accelerator="Ctrl+Right")
        view_menu.add_separator()
        view_menu.add_command(label="Phóng to", command=lambda: self.set_zoom(self.zoom_level + 10), accelerator="Ctrl++")
        view_menu.add_command(label="Thu nhỏ", command=lambda: self.set_zoom(self.zoom_level - 10), accelerator="Ctrl+-")
        view_menu.add_command(label="Phù hợp trang", command=lambda: self.set_zoom(100))
        menubar.add_cascade(label="Xem", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Về ứng dụng", command=self.show_about)
        menubar.add_cascade(label="Trợ giúp", menu=help_menu)
        
        self.root.configure(menu=menubar)
        
        # Bind keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
                self.root.bind("<Control-s>", lambda e: self.save_pdf())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as_pdf())
        self.root.bind("<Control-Shift-s>", lambda e: self.save_as_pdf())

        self.root.bind("<Control-p>", lambda e: self.print_pdf())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-b>", lambda e: self.toggle_bold())
        self.root.bind("<Control-i>", lambda e: self.toggle_italic())
        self.root.bind("<Control-u>", lambda e: self.toggle_underline())
        self.root.bind("<Delete>", lambda e: self.delete_selected_element())
        self.root.bind("<Control-Left>", lambda e: self.previous_page())
        self.root.bind("<Control-Right>", lambda e: self.next_page())
        
        def open_pdf(self):
        """Open a PDF file"""
        self.document_manager.open_pdf()

    def delete_selected_element(self):
        """Delete selected element"""
        self.element_manager.delete_selected()

        def delete_selected_element(self): self.element_manager.delete_selected()\n    def edit_selected_element(self): self.element_manager.edit_selected()\n    def ocr_current_page_dialog(self): self.ocr_manager.ocr_dialog(all_pages=False)\n    def ocr_all_pages_dialog(self): self.ocr_manager.ocr_dialog(all_pages=True)
    
    def toggle_bold(self):
        """Toggle bold formatting"""
        self.formatting_manager.set_bold(not self.formatting_manager.current_style.bold)
        self.status.configure(text=f"Tô đậm: {'Bật' if self.formatting_manager.current_style.bold else 'Tắt'}")
        
    def toggle_italic(self):
        """Toggle italic formatting"""
        self.formatting_manager.set_italic(not self.formatting_manager.current_style.italic)
        self.status.configure(text=f"Nghiêng: {'Bật' if self.formatting_manager.current_style.italic else 'Tắt'}")
        
    def toggle_underline(self):
        """Toggle underline formatting"""
        self.formatting_manager.set_underline(not self.formatting_manager.current_style.underline)
        self.status.configure(text=f"Gạch chân: {'Bật' if self.formatting_manager.current_style.underline else 'Tắt'}")
        
    def set_font(self, font_name):
        """Set font"""
        self.formatting_manager.set_font(font_name)
        self.status.configure(text=f"Font: {font_name}")
        
    def set_font_size(self, size):
        """Set font size"""
        self.formatting_manager.set_font_size(size)
        self.status.configure(text=f"Kích thước: {size}pt")
        
    def set_alignment(self, alignment):
        """Set text alignment"""
        self.formatting_manager.set_alignment(alignment)
        align_text = {"left": "Căn trái", "center": "Căn giữa", "right": "Căn phải"}
        self.status.configure(text=align_text.get(alignment, ""))
        
    def pick_color(self):
        """Pick color"""
        color = colorchooser.askcolor()[1]
        if color:
            self.formatting_manager.set_color(color)
            self.status.configure(text=f"Màu: {color}")
    
    def set_zoom(self, level):
        """Set zoom level"""
        self.zoom_level = max(50, min(200, level))
        self.zoom_label.configure(text=f"{self.zoom_level}%")
        self.update_preview()
    
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_element = None
            self.update_preview()
            self.status.configure(text=f"Trang {self.current_page + 1} / {self.total_pages}")
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_element = None
            self.update_preview()
            self.status.configure(text=f"Trang {self.current_page + 1} / {self.total_pages}")
    
    def undo(self):
        """Undo last action"""
        if self.undo_redo_manager.can_undo():
            self.elements = self.undo_redo_manager.undo(self.elements)
            self.update_preview()
            self.status.configure(text="Hoàn tác")
            self.update_info_panel()
    
    def redo(self):
        """Redo last undone action"""
        if self.undo_redo_manager.can_redo():
            self.elements = self.undo_redo_manager.redo(self.elements)
            self.update_preview()
            self.status.configure(text="Làm lại")
            self.update_info_panel()
    
    def _should_prompt_save_as(self):
        """Return True for temp documents that should prompt for a target path."""
        if hasattr(self, "document_manager") and self.document_manager is not None:
            return self.document_manager._should_prompt_save_as()
        return bool(getattr(self, "is_temp_document", False))

    def save_pdf(self):
        """Save PDF with all edits (Ctrl+S). For temp docs this opens Save As."""
        self.document_manager.save_pdf()
    
    def save_as_pdf(self):
        """Save As (always prompts Save As dialog)."""
        self.document_manager.save_as_pdf()

    def new_temp_document(self):
        """Create a new temporary blank PDF for editing."""
        self.document_manager.new_temp_document()

    def export_pdf(self):
        """Export as new PDF"""
        # For temp docs, ensure Save As behavior.
        return self.save_as_pdf()


    
    def print_pdf(self):
        """Print PDF"""
        if not self.current_pdf:
            messagebox.showwarning("Cảnh báo", "Chưa có file PDF để in!")
            return
        
        try:
            import subprocess
            if os.name == 'nt':
                subprocess.run(['start', self.current_pdf], shell=True)
            else:
                subprocess.run(['lp', self.current_pdf])
            messagebox.showinfo("In", "Đang gửi file đến máy in...")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể in: {str(e)}")
    
    def clear_elements(self):
        """Clear all elements"""
        if messagebox.askyesno("Xác nhận", "Xóa tất cả chỉnh sửa?"):
            self.undo_redo_manager.save_state(self.elements)
            self.elements.clear()
            self.selected_element = None
            self.update_preview()
            self.update_info_panel()
    
    def update_info_panel(self):
        """Update information panel"""
        if not hasattr(self, 'element_info'):
            return
        
        self.element_info.configure(text=f"{len(self.elements)} phần tử")
        
        # Count element types
        text_count = sum(1 for e in self.elements if e[0] == "text")
        image_count = sum(1 for e in self.elements if e[0] == "image")
        shape_count = sum(1 for e in self.elements if e[0] in ["line", "rect", "ellipse", "triangle"])
        
        stats = f"Chữ: {text_count}\nHình: {image_count}\nĐường: {shape_count}"
        self.stats_info.configure(text=stats)
        
        if self.total_pages > 0:
            self.page_info.configure(text=f"Trang {self.current_page + 1} / {self.total_pages}")
        self.update_selected_properties()
    
    def update_selected_properties(self):
        """Update the selected-item info panel"""
        if not hasattr(self, 'selected_props_frame'):
            return
        for child in self.selected_props_frame.winfo_children():
            child.destroy()

        if self.selected_element is None or self.selected_element >= len(self.elements):
            self.selected_title.configure(text="Không có phần tử nào")
            return

        elem = self.elements[self.selected_element]
        etype, params = elem
        if params.get('page', 0) != self.current_page:
            self.selected_title.configure(text="Không có phần tử nào")
            return

        self.selected_title.configure(text=f"Đã chọn: {etype.title()} #{self.selected_element + 1}")
        tk.Label(self.selected_props_frame, text=f"Trang: {params.get('page', 0)+1}", anchor="w").pack(anchor="w")
        if etype == "text":
            tk.Label(self.selected_props_frame, text=f"Nội dung: {params.get('text', '')}", wraplength=180, justify="left").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Vị trí: ({params.get('x',0)/72:.2f}, {params.get('y',0)/72:.2f}) inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Font: {params.get('font_name','Arial')} {params.get('size',12)}pt", anchor="w").pack(anchor="w")
        elif etype == "image":
            tk.Label(self.selected_props_frame, text=f"Vị trí: ({params.get('x',0)/72:.2f}, {params.get('y',0)/72:.2f}) inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Kích thước: {params.get('w',0)/72:.2f} x {params.get('h',0)/72:.2f} inch", anchor="w").pack(anchor="w")
        elif etype == "line":
            tk.Label(self.selected_props_frame, text=f"Tọa độ: ({params.get('x1',0)/72:.2f}, {params.get('y1',0)/72:.2f}) → ({params.get('x2',0)/72:.2f}, {params.get('y2',0)/72:.2f}) inch", wraplength=180, justify="left").pack(anchor="w")
        else:
            tk.Label(self.selected_props_frame, text=f"Vị trí: ({params.get('x',0)/72:.2f}, {params.get('y',0)/72:.2f}) inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Kích thước: {params.get('w',0)/72:.2f} x {params.get('h',0)/72:.2f} inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Màu: {params.get('color','')}", anchor="w").pack(anchor="w")

            # Fill toggle for shapes (rect/ellipse/triangle) and also line for consistency.
            # "Full" requirement: always show UI like Word.
            filled_var = tk.BooleanVar(value=bool(params.get('filled', False)))
            fill_color_var = tk.StringVar(value=params.get('fill_color', params.get('color', 'red')))

            def pick_fill_color():
                c = colorchooser.askcolor(initialcolor=fill_color_var.get())[1]
                if c:
                    fill_color_var.set(c)
                    fill_color_btn.configure(bg=c)

            ttk_frame = ttk.Frame(self.selected_props_frame)
            ttk_frame.pack(anchor="w", pady=(6, 2))

            ttk.Checkbutton(ttk_frame, text="Đổ màu (Fill)", variable=filled_var).pack(anchor="w")

            # Color picker button (Word-like: enabled when Fill checked)
            fill_color_btn = tk.Button(ttk_frame, text="Chọn màu fill", bg=fill_color_var.get(), fg="white", command=pick_fill_color)
            fill_color_btn.pack(anchor="w", pady=(4, 2))

            def apply_fill():
                params['filled'] = bool(filled_var.get())
                params['fill_color'] = fill_color_var.get()
                self.update_preview()
                self.update_info_panel()

            ttk.Button(self.selected_props_frame, text="Áp dụng Fill", command=apply_fill).pack(anchor="w", pady=(0, 6))

    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("Về ứng dụng",
                          "Word-like Super PDF Editor v2.0\n\n"
                          "Một trình chỉnh sửa PDF mạnh mẽ với giao diện tương tự MS Word\n\n"
                          "Tính năng:\n"
                          "- Chèn và định dạng chữ\n"
                          "- Chèn hình ảnh\n"
                          "- Vẽ các hình dạng\n"
                          "- Hoàn tác/Làm lại\n"
                          "- Phóng to/Thu nhỏ\n"
                          "- Xuất PDF")





