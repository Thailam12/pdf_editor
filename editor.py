import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import os

from pdf_utils import PDFUtils
from services import (
    CanvasManager, InteractionManager, DocumentManager,
    FormattingManager, UndoRedoManager, OCRManager,
)
from ui.menu_bar import create_menu_bar
from ui.toolbar import create_toolbar
from ui.formatting_bar import create_formatting_toolbar
from ui.property_panel import create_property_panel
from ui.dialogs import edit_element_dialog, show_about as _show_about
from tools.text_tool import add_text_tool
from tools.image_tool import add_image_tool
from tools.drawing_tool import DrawingTool
from i18n import get_i18n, LANG_VI


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.lang = LANG_VI
        self._t = get_i18n(self.lang)
        self.root.title(self._t["app_title"])
        self.root.geometry("1400x850")

        self.pdf_utils = PDFUtils()
        self.current_pdf = None
        self.is_temp_document = False
        self.elements = []
        self.element_images = []
        self.selected_element = None
        self.zoom_level = 100
        self.current_page = 0
        self.total_pages = 0
        self.selection_mode = False
        self.ocr_running = False
        self.ocr_job_id = 0

        self.formatting_manager = FormattingManager()
        self.undo_manager = UndoRedoManager()
        self.drawing_tool = DrawingTool(self)
        self.canvas_manager = CanvasManager(self)
        self.interaction_manager = InteractionManager(self)
        self.document_manager = DocumentManager(self)
        self.ocr_manager = OCRManager(self)

        self.create_gui()
        self.update_info_panel()

    def create_gui(self):
        create_menu_bar(self)
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        create_toolbar(self, parent=toolbar_frame)
        create_formatting_toolbar(self, parent=toolbar_frame)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)

        canvas_frame = ttk.LabelFrame(main_frame, text="Trình chỉnh sửa", padding=5)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)

        self.canvas_preview = tk.Canvas(
            canvas_frame, bg="#f8f9fa", width=800, height=600, cursor="cross"
        )
        self.canvas_preview.pack(fill=tk.BOTH, expand=True)

        self.canvas_preview.bind("<Button-1>", self.on_canvas_click)
        self.canvas_preview.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas_preview.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas_preview.bind("<Motion>", self.on_canvas_motion)
        self.canvas_preview.bind("<Button-3>", self.show_context_menu)
        self.canvas_preview.bind("<Delete>", lambda e: self.delete_selected_element())

        property_panel = create_property_panel(self, parent=main_frame)
        property_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)

        self.status = ttk.Label(self.root, text="Sẵn sàng", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

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

    def on_canvas_click(self, event):
        self.interaction_manager.on_canvas_click(event)
        self.update_info_panel()

    def on_canvas_drag(self, event):
        self.interaction_manager.on_canvas_drag(event)

    def on_canvas_release(self, event):
        self.interaction_manager.on_canvas_release(event)
        self.update_info_panel()

    def on_canvas_motion(self, event):
        self.interaction_manager.on_canvas_motion(event)

    def show_context_menu(self, event):
        self.interaction_manager.show_context_menu(event)

    def open_pdf(self):
        self.document_manager.open_pdf()

    def save_pdf(self):
        self.document_manager.save_pdf()

    def save_as_pdf(self):
        self.document_manager.save_as_pdf()

    def new_temp_document(self):
        self.document_manager.new_temp_document()

    def export_pdf(self):
        self.save_as_pdf()

    def print_pdf(self):
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

    def add_text(self):
        add_text_tool(self)

    def add_image(self):
        add_image_tool(self)

    def start_drawing(self, shape_type):
        self.drawing_tool.start_drawing(self.canvas_preview, shape_type)

    def toggle_selection_mode(self):
        self.selection_mode = not self.selection_mode
        self.status.configure(
            text=f"Chế độ chọn: {'Bật' if self.selection_mode else 'Tắt'}"
        )

    def delete_selected_element(self):
        if self.selected_element is None:
            return
        self.undo_manager.save_state(self.elements)
        del self.elements[self.selected_element]
        self.element_images.clear()
        self.selected_element = None
        self.canvas_manager.update_preview()
        self.update_info_panel()

    def edit_selected_element(self):
        edit_element_dialog(self)

    def clear_elements(self):
        if messagebox.askyesno("Xác nhận", "Xóa tất cả chỉnh sửa?"):
            self.undo_manager.save_state(self.elements)
            self.elements.clear()
            self.element_images.clear()
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.update_info_panel()

    def toggle_bold(self):
        self.formatting_manager.set_bold(not self.formatting_manager.current_style.bold)
        self.status.configure(
            text=f"Tô đậm: {'Bật' if self.formatting_manager.current_style.bold else 'Tắt'}"
        )

    def toggle_italic(self):
        self.formatting_manager.set_italic(not self.formatting_manager.current_style.italic)
        self.status.configure(
            text=f"Nghiêng: {'Bật' if self.formatting_manager.current_style.italic else 'Tắt'}"
        )

    def toggle_underline(self):
        self.formatting_manager.set_underline(not self.formatting_manager.current_style.underline)
        self.status.configure(
            text=f"Gạch chân: {'Bật' if self.formatting_manager.current_style.underline else 'Tắt'}"
        )

    def set_font(self, font_name):
        self.formatting_manager.set_font(font_name)
        self.status.configure(text=f"Font: {font_name}")

    def set_font_size(self, size):
        self.formatting_manager.set_font_size(size)
        self.status.configure(text=f"Kích thước: {size}pt")

    def set_alignment(self, alignment):
        self.formatting_manager.set_alignment(alignment)
        align_text = {"left": "Căn trái", "center": "Căn giữa", "right": "Căn phải"}
        self.status.configure(text=align_text.get(alignment, ""))

    def pick_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.formatting_manager.set_color(color)
            self.status.configure(text=f"Màu: {color}")

    def set_zoom(self, level):
        self.zoom_level = max(50, min(200, level))
        if hasattr(self, 'zoom_label'):
            self.zoom_label.configure(text=f"{self.zoom_level}%")
        self.canvas_manager.update_preview()

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.update_info_panel()
            self.status.configure(
                text=f"Trang {self.current_page + 1} / {self.total_pages}"
            )

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.update_info_panel()
            self.status.configure(
                text=f"Trang {self.current_page + 1} / {self.total_pages}"
            )

    def undo(self):
        if self.undo_manager.can_undo():
            self.elements = self.undo_manager.undo(self.elements)
            self.element_images.clear()
            self.canvas_manager.update_preview()
            self.update_info_panel()
            self.status.configure(text="Hoàn tác")

    def redo(self):
        if self.undo_manager.can_redo():
            self.elements = self.undo_manager.redo(self.elements)
            self.element_images.clear()
            self.canvas_manager.update_preview()
            self.update_info_panel()
            self.status.configure(text="Làm lại")

    def _should_prompt_save_as(self):
        if hasattr(self, "document_manager") and self.document_manager is not None:
            return self.document_manager._should_prompt_save_as()
        return bool(getattr(self, "is_temp_document", False))

    def update_info_panel(self):
        if not hasattr(self, 'element_info'):
            return
        self.element_info.configure(text=f"{len(self.elements)} phần tử")
        text_count = sum(1 for e in self.elements if hasattr(e, 'type_name') and e.type_name == "text")
        image_count = sum(1 for e in self.elements if hasattr(e, 'type_name') and e.type_name == "image")
        shape_count = sum(
            1 for e in self.elements
            if hasattr(e, 'type_name') and e.type_name in ("shape", "line")
        )
        self.stats_info.configure(text=f"Chữ: {text_count}\nHình: {image_count}\nĐường: {shape_count}")
        if self.total_pages > 0:
            self.page_info.configure(text=f"Trang {self.current_page + 1} / {self.total_pages}")
        self.update_selected_properties()

    def update_selected_properties(self):
        if not hasattr(self, 'selected_props_frame'):
            return
        for child in self.selected_props_frame.winfo_children():
            child.destroy()
        if self.selected_element is None or self.selected_element >= len(self.elements):
            self.selected_title.configure(text="Không có phần tử nào")
            return
        elem = self.elements[self.selected_element]
        if getattr(elem, 'page', 0) != self.current_page:
            self.selected_title.configure(text="Không có phần tử nào")
            return
        self.selected_title.configure(
            text=f"Đã chọn: {(elem.type_name or type(elem).__name__).title()} #{self.selected_element + 1}"
        )
        from models import TextElement, ImageElement, ShapeElement, LineElement
        tk.Label(self.selected_props_frame, text=f"Trang: {elem.page + 1}", anchor="w").pack(anchor="w")
        if isinstance(elem, TextElement):
            tk.Label(self.selected_props_frame, text=f"Nội dung: {elem.text}", wraplength=180, justify="left").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Vị trí: ({elem.x/72:.2f}, {elem.y/72:.2f}) inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Font: {elem.font_name} {elem.size}pt", anchor="w").pack(anchor="w")
        elif isinstance(elem, ImageElement):
            tk.Label(self.selected_props_frame, text=f"Vị trí: ({elem.x/72:.2f}, {elem.y/72:.2f}) inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Kích thước: {elem.w/72:.2f} x {elem.h/72:.2f} inch", anchor="w").pack(anchor="w")
        elif isinstance(elem, LineElement):
            tk.Label(self.selected_props_frame, text=f"Tọa độ: ({elem.x1/72:.2f},{elem.y1/72:.2f})->({elem.x2/72:.2f},{elem.y2/72:.2f})", wraplength=180, justify="left").pack(anchor="w")
        elif isinstance(elem, ShapeElement):
            tk.Label(self.selected_props_frame, text=f"Vị trí: ({elem.x/72:.2f}, {elem.y/72:.2f}) inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Kích thước: {elem.w/72:.2f} x {elem.h/72:.2f} inch", anchor="w").pack(anchor="w")
            tk.Label(self.selected_props_frame, text=f"Màu: {elem.color}", anchor="w").pack(anchor="w")
            self._add_fill_controls(elem)

    def _add_fill_controls(self, elem):
        filled_var = tk.BooleanVar(value=bool(elem.filled))
        fill_color_var = tk.StringVar(value=elem.fill_color or elem.color)

        def pick_fill():
            c = colorchooser.askcolor(initialcolor=fill_color_var.get())[1]
            if c:
                fill_color_var.set(c)
                fill_color_btn.configure(bg=c)

        ttk_frame = ttk.Frame(self.selected_props_frame)
        ttk_frame.pack(anchor="w", pady=(6, 2))
        ttk.Checkbutton(ttk_frame, text="Đổ màu (Fill)", variable=filled_var).pack(anchor="w")
        fill_color_btn = tk.Button(ttk_frame, text="Chọn màu fill", bg=fill_color_var.get(), fg="white", command=pick_fill)
        fill_color_btn.pack(anchor="w", pady=(4, 2))

        def apply_fill():
            elem.filled = bool(filled_var.get())
            elem.fill_color = fill_color_var.get()
            self.canvas_manager.update_preview()
            self.update_info_panel()

        ttk.Button(self.selected_props_frame, text="Áp dụng Fill", command=apply_fill).pack(anchor="w", pady=(0, 6))

    def ocr_current_page_dialog(self):
        self.ocr_manager.ocr_dialog(all_pages=False)

    def ocr_all_pages_dialog(self):
        self.ocr_manager.ocr_dialog(all_pages=True)

    def _ocr_image_to_boxes(self, img, lang="en"):
        from ocr_utils import ocr_page_to_boxes
        return ocr_page_to_boxes(img, lang=lang)

    def show_about(self):
        _show_about()
