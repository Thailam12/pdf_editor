import os
import sys
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from PIL import Image, ImageTk

from pdf_utils import PDFUtils
from services import (
    CanvasManager, InteractionManager, DocumentManager,
    FormattingManager, UndoRedoManager, OCRManager,
    PageService, WatermarkService, BookmarkService,
    SearchService, SecurityService, RedactionService,
    ExportService, AIService, FormService,
    LinkService, HeaderFooterService,
)
from ui.ribbon import create_ribbon, update_ribbon_state
from ui.page_panel import PagePanel
from ui.layers_panel import LayersPanel
from ui.status_bar import create_status_bar, update_status
from ui.feature_dialogs import (
    stamp_dialog, signature_dialog, watermark_dialog,
    ocr_dialog, protect_dialog, bookmarks_dialog,
    split_dialog, find_replace_dialog, about_dialog,
    header_footer_dialog, form_field_dialog,
)
from models.elements import (
    TextElement, ImageElement, ShapeElement, LineElement,
    HighlightElement, AnnotationElement, NoteElement,
    StampElement, SignatureElement, FreehandElement,
    LinkElement, RedactElement, WatermarkElement,
    FormFieldElement, PREDEFINED_STAMPS,
)
from i18n import get_i18n
from easter_eggs import should_show_easter_egg, pick_easter_egg


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor Ultimate v3.0")
        self.root.geometry("1400x900")
        self.root.minsize(1024, 600)

        self.lang = "vi"
        self._t = get_i18n(self.lang)

        self.current_pdf = None
        self.is_temp_document = False
        self.elements = []
        self.element_images = []
        self.selected_element = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 100
        self.active_tool = "select"
        self.stroke_color = "#FF0000"
        self.stroke_width = 2
        self.fill_color = "#4A90D9"

        self.pdf_utils = PDFUtils()

        self.undo_manager = UndoRedoManager()
        self.canvas_manager = CanvasManager(self)
        self.interaction_manager = InteractionManager(self)
        self.document_manager = DocumentManager(self)
        self.formatting_manager = FormattingManager()

        self.page_service = PageService(self)
        self.watermark_service = WatermarkService(self)
        self.bookmark_service = BookmarkService(self)
        self.search_service = SearchService(self)
        self.security_service = SecurityService(self)
        self.redaction_service = RedactionService(self)
        self.export_service = ExportService(self)
        self.ai_service = AIService(self)
        self.form_service = FormService(self)
        self.link_service = LinkService(self)
        self.header_footer_service = HeaderFooterService(self)
        self.ocr_manager = OCRManager(self)

        self._action_counter = 0

        self._apply_theme()
        self._build_ui()
        self._bind_shortcuts()

    def _apply_theme(self):
        self.colors = {
            "bg": "#1e1e2e",
            "bg_secondary": "#313244",
            "bg_surface": "#45475a",
            "text": "#cdd6f4",
            "text_dim": "#a6adc8",
            "accent": "#89b4fa",
            "accent_hover": "#b4d0fb",
            "danger": "#f38ba8",
            "success": "#a6e3a1",
            "warning": "#fab387",
        }
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TButton", background=self.colors["bg_surface"],
                        foreground=self.colors["text"], borderwidth=0, padding=4)
        style.map("TButton", background=[("active", self.colors["accent"])])
        style.configure("Accent.TButton", background=self.colors["accent"], foreground="#000")
        style.map("Accent.TButton", background=[("active", self.colors["accent_hover"])])

    def _build_ui(self):
        menubar = tk.Menu(self.root, bg=self.colors["bg_secondary"], fg=self.colors["text"],
                          activebackground=self.colors["accent"], activeforeground="#000")
        self._build_menu(menubar)
        self.root.config(menu=menubar)

        top_frame = tk.Frame(self.root, bg=self.colors["bg"])
        top_frame.pack(side=tk.TOP, fill=tk.X)
        self.ribbon = create_ribbon(self, top_frame)

        main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.page_panel_frame = tk.Frame(main_frame, bg=self.colors["bg_secondary"], width=140)
        self.page_panel_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.page_panel_frame.pack_propagate(False)
        self.page_panel = PagePanel(self, self.page_panel_frame)

        canvas_frame = tk.Frame(main_frame, bg=self.colors["bg_surface"])
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.canvas_preview = tk.Canvas(
            canvas_frame, bg="#2a2a3a", highlightthickness=0,
            xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set,
        )
        h_scroll.config(command=self.canvas_preview.xview)
        v_scroll.config(command=self.canvas_preview.yview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_preview.bind("<Button-1>", self.interaction_manager.on_canvas_click)
        self.canvas_preview.bind("<B1-Motion>", self.interaction_manager.on_canvas_drag)
        self.canvas_preview.bind("<ButtonRelease-1>", self.interaction_manager.on_canvas_release)
        self.canvas_preview.bind("<Motion>", self.interaction_manager.on_canvas_motion)
        self.canvas_preview.bind("<Button-3>", self.interaction_manager.show_context_menu)

        self.layers_panel_frame = tk.Frame(main_frame, bg=self.colors["bg_secondary"], width=200)
        self.layers_panel_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.layers_panel_frame.pack_propagate(False)
        self.layers_panel = LayersPanel(self, self.layers_panel_frame)

        status_frame = tk.Frame(self.root, bg=self.colors["bg_secondary"], height=28)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status = create_status_bar(self, status_frame)

    def _build_menu(self, menubar):
        t = self._t
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        file_menu.add_command(label=t.get("new", "New"), command=self.new_document, accelerator="Ctrl+N")
        file_menu.add_command(label=t.get("open", "Open"), command=self.open_pdf, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label=t.get("save", "Save"), command=self.save_pdf, accelerator="Ctrl+S")
        file_menu.add_command(label=t.get("save_as", "Save As"), command=self.save_as_pdf, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export to Images", command=self.export_images)
        file_menu.add_command(label="Export to DOCX", command=self.export_docx)
        file_menu.add_command(label="Export to HTML", command=self.export_html)
        file_menu.add_separator()
        file_menu.add_command(label=t.get("print", "Print"), command=self.print_pdf, accelerator="Ctrl+P")
        file_menu.add_separator()
        file_menu.add_command(label=t.get("exit", "Exit"), command=self.root.quit)
        menubar.add_cascade(label=t.get("file", "File"), menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=self.cut_selected, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self.copy_selected, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self.paste_clipboard, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="Deselect", command=self.deselect_all, accelerator="Escape")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find & Replace", command=self.show_find_replace, accelerator="Ctrl+H")
        menubar.add_cascade(label=t.get("edit", "Edit"), menu=edit_menu)

        insert_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        insert_menu.add_command(label="Text", command=lambda: self.set_tool("text"))
        insert_menu.add_command(label="Image", command=self.insert_image)
        insert_menu.add_separator()
        insert_menu.add_command(label="Rectangle", command=lambda: self.set_tool("rect"))
        insert_menu.add_command(label="Ellipse", command=lambda: self.set_tool("ellipse"))
        insert_menu.add_command(label="Triangle", command=lambda: self.set_tool("triangle"))
        insert_menu.add_command(label="Line", command=lambda: self.set_tool("line"))
        insert_menu.add_command(label="Arrow", command=lambda: self.set_tool("arrow"))
        insert_menu.add_separator()
        insert_menu.add_command(label="Stamp", command=self.show_stamp_dialog)
        insert_menu.add_command(label="Signature", command=self.show_signature_dialog)
        insert_menu.add_command(label="Link", command=lambda: self.set_tool("link"))
        insert_menu.add_command(label="Watermark", command=self.show_watermark_dialog)
        insert_menu.add_command(label="Header/Footer", command=self.show_header_footer_dialog)
        insert_menu.add_command(label="Form Field", command=self.show_form_field_dialog)
        menubar.add_cascade(label=t.get("insert", "Insert"), menu=insert_menu)

        annotate_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        annotate_menu.add_command(label="Highlight", command=lambda: self.set_tool("highlight"))
        annotate_menu.add_command(label="Underline", command=lambda: self.set_tool("underline"))
        annotate_menu.add_command(label="Strikethrough", command=lambda: self.set_tool("strikethrough"))
        annotate_menu.add_command(label="Squiggly", command=lambda: self.set_tool("squiggly"))
        annotate_menu.add_separator()
        annotate_menu.add_command(label="Sticky Note", command=lambda: self.set_tool("note"))
        annotate_menu.add_command(label="Freehand", command=lambda: self.set_tool("freehand"))
        annotate_menu.add_separator()
        annotate_menu.add_command(label="Redact", command=self.mark_redaction)
        menubar.add_cascade(label="Annotate", menu=annotate_menu)

        page_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        page_menu.add_command(label="Insert Page", command=self.insert_page)
        page_menu.add_command(label="Delete Page", command=self.delete_page)
        page_menu.add_command(label="Duplicate Page", command=self.duplicate_page)
        page_menu.add_separator()
        page_menu.add_command(label="Rotate Clockwise", command=self.rotate_cw)
        page_menu.add_command(label="Rotate Counter-CW", command=self.rotate_ccw)
        page_menu.add_separator()
        page_menu.add_command(label="Crop Page", command=self.crop_page)
        page_menu.add_command(label="Merge PDFs", command=self.merge_pdfs)
        page_menu.add_command(label="Split PDF", command=self.show_split_dialog)
        menubar.add_cascade(label="Page", menu=page_menu)

        tools_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        tools_menu.add_command(label="OCR - Current Page", command=self.ocr_current_page)
        tools_menu.add_command(label="OCR - All Pages", command=self.ocr_all_pages)
        tools_menu.add_separator()
        tools_menu.add_command(label="Password Protect", command=self.show_protect_dialog)
        tools_menu.add_command(label="Flatten PDF", command=self.flatten_pdf)
        tools_menu.add_separator()
        tools_menu.add_command(label="Bookmarks", command=self.show_bookmarks_dialog)
        tools_menu.add_command(label="AI: Extract Text", command=self.ai_extract_text)
        tools_menu.add_command(label="AI: Summarize", command=self.ai_summarize)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl+=")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Fit Page", command=self.zoom_fit)
        view_menu.add_command(label="Fit Width", command=self.zoom_width)
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Grid", command=self.toggle_grid)
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_document())
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-s>", lambda e: self.save_pdf())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as_pdf())
        self.root.bind("<Control-p>", lambda e: self.print_pdf())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-Z>", lambda e: self.redo())
        self.root.bind("<Control-x>", lambda e: self.cut_selected())
        self.root.bind("<Control-c>", lambda e: self.copy_selected())
        self.root.bind("<Control-v>", lambda e: self.paste_clipboard())
        self.root.bind("<Control-a>", lambda e: self.select_all())
        self.root.bind("<Control-h>", lambda e: self.show_find_replace())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Escape>", lambda e: self.deselect_all())
        self.root.bind("<Delete>", lambda e: self.delete_selected_element())
        self.root.bind("<Left>", lambda e: self.prev_page())
        self.root.bind("<Right>", lambda e: self.next_page())
        self.root.bind("<Control-Left>", lambda e: self.prev_page())
        self.root.bind("<Control-Right>", lambda e: self.next_page())
        self.root.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.delta > 0:
            self.prev_page()
        else:
            self.next_page()

    def _track_action(self):
        self._action_counter += 1
        if should_show_easter_egg(self._action_counter):
            egg = pick_easter_egg(self.root.tk.call("clock", "seconds"))
            self.status.configure(text=egg)

    def new_document(self):
        self.document_manager.new_temp_document()
        self.page_panel.refresh()
        self.layers_panel.refresh()
        self._track_action()

    def open_pdf(self):
        self.document_manager.open_pdf()
        self.page_panel.refresh()
        self.layers_panel.refresh()
        self._track_action()

    def save_pdf(self):
        self.document_manager.save_pdf()
        self._track_action()

    def save_as_pdf(self):
        self.document_manager.save_as_pdf()
        self._track_action()

    def print_pdf(self):
        if self.current_pdf:
            import subprocess
            try:
                subprocess.Popen(["start", "", self.current_pdf], shell=True)
            except Exception:
                messagebox.showinfo("Print", "PDF file opened. Use system print dialog.")

    def export_images(self):
        self.export_service.export_to_images()

    def export_docx(self):
        self.export_service.export_to_docx()

    def export_html(self):
        self.export_service.export_to_html()

    def insert_image(self):
        from tools.image_tool import add_image_tool
        add_image_tool(self)
        self._track_action()

    def set_tool(self, tool):
        self.active_tool = tool
        tool_map = {
            "text": "Text", "rect": "Rectangle", "ellipse": "Ellipse",
            "triangle": "Triangle", "line": "Line", "arrow": "Arrow",
            "highlight": "Highlight", "underline": "Underline",
            "strikethrough": "Strikethrough", "squiggly": "Squiggly",
            "note": "Sticky Note", "freehand": "Freehand",
            "link": "Link", "eraser": "Eraser",
        }
        name = tool_map.get(tool, tool)
        self.status.configure(text=f"Tool: {name} - Click on canvas")
        update_ribbon_state(self)

    def add_element_at_click(self, x, y, elem):
        self.undo_manager.save_state(self.elements)
        elem.page = self.current_page
        self.elements.append(elem)
        self.selected_element = len(self.elements) - 1
        self.canvas_manager.update_preview()
        self.layers_panel.refresh()
        self._track_action()

    def add_text_element(self):
        text = "Text"
        elem = TextElement(text=text, x=100, y=100, size=14,
                           page=self.current_page)
        self.add_element_at_click(100, 100, elem)

    def add_text_tool(self):
        from tools.text_tool import add_text_tool
        add_text_tool(self)
        self._track_action()

    def start_drawing(self):
        self.set_tool("rect")

    def undo(self):
        self.elements = self.undo_manager.undo(self.elements)
        self.selected_element = None
        self.canvas_manager.update_preview()
        self.page_panel.refresh()
        self.layers_panel.refresh()
        self.status.configure(text="Undo")

    def redo(self):
        self.elements = self.undo_manager.redo(self.elements)
        self.selected_element = None
        self.canvas_manager.update_preview()
        self.page_panel.refresh()
        self.layers_panel.refresh()
        self.status.configure(text="Redo")

    def cut_selected(self):
        self.copy_selected()
        self.delete_selected_element()

    def copy_selected(self):
        if self.selected_element is None:
            return
        import json
        elem = self.elements[self.selected_element]
        data = elem.to_json() if hasattr(elem, "to_json") else {}
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(data))
        self.status.configure(text="Copied")

    def paste_clipboard(self):
        try:
            data = self.root.clipboard_get()
            import json
            obj = json.loads(data)
            from models.elements import element_from_json
            elem = element_from_json(obj)
            if elem:
                elem.page = self.current_page
                self.add_element_at_click(0, 0, elem)
                self.status.configure(text="Pasted")
        except Exception:
            pass

    def select_all(self):
        page_elems = [i for i, e in enumerate(self.elements)
                      if getattr(e, "page", 0) == self.current_page]
        if page_elems:
            self.selected_element = page_elems[-1]
            self.canvas_manager.update_preview()
            self.status.configure(text=f"Selected {len(page_elems)} element(s)")

    def deselect_all(self):
        self.selected_element = None
        self.canvas_manager.update_preview()
        self.status.configure(text="Deselected")

    def delete_selected_element(self):
        if self.selected_element is not None:
            self.undo_manager.save_state(self.elements)
            self.elements.pop(self.selected_element)
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.page_panel.refresh()
            self.layers_panel.refresh()
            self.status.configure(text="Deleted")
            self._track_action()

    def edit_selected_element(self):
        if self.selected_element is None:
            return
        from ui.dialogs import edit_element_dialog
        edit_element_dialog(self)

    def set_font(self, font_name):
        self.formatting_manager.set_font_name(font_name)
        self._apply_formatting_to_selected()

    def set_font_size(self, size):
        self.formatting_manager.set_font_size(int(size))
        self._apply_formatting_to_selected()

    def toggle_bold(self):
        self.formatting_manager.toggle_bold()
        self._apply_formatting_to_selected()

    def toggle_italic(self):
        self.formatting_manager.toggle_italic()
        self._apply_formatting_to_selected()

    def toggle_underline(self):
        self.formatting_manager.toggle_underline()
        self._apply_formatting_to_selected()

    def set_alignment(self, align):
        self.formatting_manager.set_alignment(align)
        self._apply_formatting_to_selected()

    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.stroke_color)
        if color[1]:
            self.stroke_color = color[1]

    def pick_fill_color(self):
        color = colorchooser.askcolor(initialcolor=self.fill_color)
        if color[1]:
            self.fill_color = color[1]

    def _apply_formatting_to_selected(self):
        if self.selected_element is None:
            return
        elem = self.elements[self.selected_element]
        style = self.formatting_manager.text_style
        if hasattr(elem, "font_name"):
            elem.font_name = style.font_name
        if hasattr(elem, "size"):
            elem.size = style.font_size
        if hasattr(elem, "bold"):
            elem.bold = style.bold
        if hasattr(elem, "italic"):
            elem.italic = style.italic
        if hasattr(elem, "underline"):
            elem.underline = style.underline
        if hasattr(elem, "color"):
            elem.color = style.color
        if hasattr(elem, "alignment"):
            elem.alignment = style.alignment
        self.canvas_manager.update_preview()

    def set_zoom(self, level):
        self.zoom_level = max(25, min(400, int(level)))
        self.canvas_manager.update_preview()
        update_ribbon_state(self)

    def zoom_in(self):
        self.set_zoom(self.zoom_level + 10)

    def zoom_out(self):
        self.set_zoom(self.zoom_level - 10)

    def zoom_fit(self):
        if self.pdf_utils.doc and self.current_page < len(self.pdf_utils.doc):
            page = self.pdf_utils.doc[self.current_page]
            rect = page.rect
            canvas_w = self.canvas_preview.winfo_width()
            canvas_h = self.canvas_preview.winfo_height()
            if rect.width > 0 and rect.height > 0:
                zx = canvas_w / rect.width * 100
                zy = canvas_h / rect.height * 100
                self.set_zoom(min(zx, zy))

    def zoom_width(self):
        if self.pdf_utils.doc and self.current_page < len(self.pdf_utils.doc):
            page = self.pdf_utils.doc[self.current_page]
            rect = page.rect
            canvas_w = self.canvas_preview.winfo_width()
            if rect.width > 0:
                self.set_zoom(canvas_w / rect.width * 100)

    def toggle_grid(self):
        self.show_grid = not getattr(self, "show_grid", False)
        self.status.configure(text=f"Grid: {'ON' if self.show_grid else 'OFF'}")
        self.canvas_manager.update_preview()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.page_panel.refresh()
            self.layers_panel.refresh()
            self.status.configure(text=f"Page {self.current_page + 1}/{self.total_pages}")

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.page_panel.refresh()
            self.layers_panel.refresh()
            self.status.configure(text=f"Page {self.current_page + 1}/{self.total_pages}")

    def goto_page(self, page_num):
        if 0 <= page_num < self.total_pages:
            self.current_page = page_num
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.page_panel.refresh()
            self.layers_panel.refresh()

    def update_info_panel(self):
        self.layers_panel.refresh()

    def clear_elements(self):
        if self.elements:
            self.undo_manager.save_state(self.elements)
            self.elements.clear()
            self.selected_element = None
            self.canvas_manager.update_preview()
            self.page_panel.refresh()
            self.layers_panel.refresh()
            self.status.configure(text="All elements cleared")

    def show_stamp_dialog(self):
        result = stamp_dialog(self)
        if result:
            elem = StampElement(
                x=100, y=100, w=150, h=50,
                text=result.get("text", "APPROVED"),
                color=result.get("color", "#FF0000"),
                font_size=result.get("font_size", 24),
                page=self.current_page,
            )
            self.add_element_at_click(100, 100, elem)

    def show_signature_dialog(self):
        result = signature_dialog(self)
        if result:
            elem = SignatureElement(
                x=100, y=100, w=200, h=60,
                text=result.get("text", ""),
                image_data=result.get("image_data", ""),
                page=self.current_page,
            )
            self.add_element_at_click(100, 100, elem)

    def show_watermark_dialog(self):
        watermark_dialog(self)

    def show_protect_dialog(self):
        protect_dialog(self)

    def show_bookmarks_dialog(self):
        bookmarks_dialog(self)

    def show_split_dialog(self):
        split_dialog(self)

    def show_find_replace(self):
        find_replace_dialog(self)

    def show_header_footer_dialog(self):
        header_footer_dialog(self)

    def show_form_field_dialog(self):
        result = form_field_dialog(self)
        if result:
            elem = FormFieldElement(
                x=result.get("x", 100), y=result.get("y", 100),
                w=result.get("w", 200), h=result.get("h", 24),
                field_type=result.get("field_type", "text"),
                field_name=result.get("field_name", ""),
                value=result.get("value", ""),
                page=self.current_page,
            )
            self.add_element_at_click(100, 100, elem)

    def show_about(self):
        about_dialog(self)

    def insert_page(self):
        self.page_service.add_page(self.current_page)
        self.page_panel.refresh()

    def delete_page(self):
        self.page_service.delete_page(self.current_page)
        self.page_panel.refresh()

    def duplicate_page(self):
        self.page_service.duplicate_page(self.current_page)
        self.page_panel.refresh()

    def rotate_cw(self):
        self.page_service.rotate_page(self.current_page, 90)
        self.canvas_manager.update_preview()

    def rotate_ccw(self):
        self.page_service.rotate_page(self.current_page, -90)
        self.canvas_manager.update_preview()

    def crop_page(self):
        from ui.feature_dialogs import page_properties_dialog
        page_properties_dialog(self)

    def merge_pdfs(self):
        self.page_service.merge_pdfs([])

    def mark_redaction(self):
        self.set_tool("redact")
        self.status.configure(text="Draw rectangle over area to redact, then apply")

    def apply_redactions(self):
        self.redaction_service.apply_redactions()

    def flatten_pdf(self):
        self.undo_manager.save_state(self.elements)
        self.elements.clear()
        self.canvas_manager.update_preview()
        self.status.configure(text="PDF flattened")

    def ocr_current_page(self):
        self.ocr_manager.ocr_dialog()

    def ocr_all_pages(self):
        self.ocr_manager.ocr_dialog(all_pages=True)

    def ai_extract_text(self):
        text = self.ai_service.extract_text(self.current_page)
        if text:
            messagebox.showinfo("Extracted Text", text[:2000])
        else:
            messagebox.showinfo("Extracted Text", "No text found on this page")

    def ai_summarize(self):
        text = self.ai_service.extract_text(self.current_page)
        if text:
            summary = self.ai_service.summarize_text(text)
            messagebox.showinfo("Summary", summary)
        else:
            messagebox.showinfo("Summary", "No text to summarize")

    def run(self):
        self.root.mainloop()


def main():
    root = tk.Tk()
    app = PDFEditor(root)
    app.run()


if __name__ == "__main__":
    main()
