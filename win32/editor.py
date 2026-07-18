import os
import sys
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from PIL import Image, ImageTk

from win32.pdf_utils import PDFUtils
from services import (
    CanvasManager, InteractionManager, DocumentManager,
    FormattingManager, UndoRedoManager, OCRManager,
    PageService, WatermarkService, BookmarkService,
    SearchService, SecurityService, RedactionService,
    ExportService, AIService, FormService,
    LinkService, HeaderFooterService,
    CompareService, CompressService, SpellCheckService,
    TextToSpeechService, MeasurementService, PdfAService,
    BatesService, AutomationService, AccessibilityService,
    BackgroundService, ArticleService, PrintService,
    IndexService, BookmarkImportService, ClipboardService,
    SnapService,
)
from ui.ribbon import create_ribbon, update_ribbon_state
from ui.page_panel import PagePanel
from ui.layers_panel import LayersPanel
from ui.status_bar import create_status_bar, update_status
from ui.property_panel import PropertyPanel
from ui.shortcut_overlay import ShortcutOverlay
from ui.theme_manager import ThemeManager
from ui.find_toolbar import FindToolbar
from ui.zoom_widget import ZoomWidget
from ui.navigation_panel import NavigationPanel
from ui.toolbar_manager import ToolbarManager
from ui.context_menu import ContextMenuManager
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
from win32.i18n import get_i18n
from win32.easter_eggs import should_show_easter_egg, pick_easter_egg


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
        self.ocr_running = False

        self.colors = {
            "bg": "#1e1e2e",
            "bg_secondary": "#181825",
            "bg_surface": "#313244",
            "text": "#cdd6f4",
            "accent": "#89b4fa",
            "border": "#45475a",
            "selection": "#585b70",
        }

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

        self.compare_service = CompareService(self)
        self.compress_service = CompressService(self)
        self.spellcheck_service = SpellCheckService(self)
        self.tts_service = TextToSpeechService(self)
        self.measurement_service = MeasurementService(self)
        self.pdfa_service = PdfAService(self)
        self.bates_service = BatesService(self)
        self.automation_service = AutomationService(self)
        self.accessibility_service = AccessibilityService(self)
        self.background_service = BackgroundService(self)
        self.article_service = ArticleService(self)
        self.print_service = PrintService(self)
        self.index_service = IndexService(self)
        self.bookmark_import_service = BookmarkImportService(self)
        self.clipboard_service = ClipboardService(self)
        self.snap_service = SnapService(self)

        self._action_counter = 0

        # Theme manager (all classmethods, no instance needed)
        from ui.theme_manager import ThemeManager
        self.theme_manager = ThemeManager
        ThemeManager.apply_theme("Catppuccin Dark")

        # UI Components
        from ui.property_panel import PropertyPanel
        from ui.shortcut_overlay import ShortcutOverlay
        from ui.find_toolbar import FindToolbar
        from ui.zoom_widget import ZoomWidget
        from ui.navigation_panel import NavigationPanel
        from ui.toolbar_manager import ToolbarManager
        from ui.context_menu import ContextMenuManager

        self._build_ui()
        self._bind_shortcuts()

    def _apply_theme(self, theme_name):
        """Apply a UI theme"""
        ThemeManager.apply_theme(theme_name)

    def set_theme(self, theme_name):
        """Alias for _apply_theme used by ribbon"""
        self._apply_theme(theme_name)

    def _build_ui(self):
        menubar = tk.Menu(self.root, bg=self.colors["bg_secondary"], fg=self.colors["text"],
                          activebackground=self.colors["accent"], activeforeground="#000")
        self._build_menu(menubar)
        self.root.config(menu=menubar)

        self.shortcut_overlay = ShortcutOverlay(self, self.root)

        top_frame = tk.Frame(self.root, bg=self.colors["bg"])
        top_frame.pack(side=tk.TOP, fill=tk.X)
        self.ribbon = create_ribbon(self, top_frame)

        main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.left_panel = tk.Frame(main_frame, bg=self.colors["bg_secondary"], width=140)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)
        self.navigation_panel = NavigationPanel(self, self.left_panel)
        self.page_panel_frame = self.left_panel
        self.page_panel = self.navigation_panel

        canvas_frame = tk.Frame(main_frame, bg=self.colors["bg_surface"])
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_frame = canvas_frame

        self.find_toolbar = FindToolbar(self)

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

        right_frame = tk.Frame(main_frame, bg=self.colors["bg_secondary"], width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)

        self.layers_panel_frame = tk.Frame(right_frame, bg=self.colors["bg_secondary"])
        self.layers_panel_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.layers_panel = LayersPanel(self, self.layers_panel_frame)

        self.property_panel_frame = tk.Frame(right_frame, bg=self.colors["bg_secondary"])
        self.property_panel_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 0))
        self.property_panel = PropertyPanel(self, self.property_panel_frame)

        status_frame = tk.Frame(self.root, bg=self.colors["bg_secondary"], height=28)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status = create_status_bar(self, status_frame)
        if not hasattr(self, '_status_label'):
            self._status_label = getattr(self, 'status', None)
        self.status = self._status_label

        self.zoom_widget = ZoomWidget(self)
        self.zoom_widget.create_widget(status_frame)

        self.toolbar_manager = ToolbarManager(self)
        self.context_menu_manager = ContextMenuManager(self)

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
        file_menu.add_command(label="Export to SVG", command=self._export_svg)
        file_menu.add_separator()
        file_menu.add_command(label=t.get("print", "Print"), command=self.print_pdf, accelerator="Ctrl+P")
        file_menu.add_command(label="Print All Pages", command=self._print_all)
        file_menu.add_command(label="Print Current Page", command=self._print_current)
        file_menu.add_command(label="Print Booklet", command=self._print_booklet)
        file_menu.add_command(label="Print Poster", command=self._print_poster)
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
        edit_menu.add_command(label="Paste in Place", command=self._paste_in_place)
        edit_menu.add_command(label="Paste as Text", command=self._paste_as_text)
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
        insert_menu.add_separator()
        insert_menu.add_command(label="Barcode", command=self._add_barcode)
        insert_menu.add_command(label="Video", command=self._add_video)
        insert_menu.add_command(label="Audio", command=self._add_audio)
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
        annotate_menu.add_separator()
        annotate_menu.add_command(label="Add Callout", command=self._add_callout)
        annotate_menu.add_command(label="Add Text Box", command=self._add_textbox)
        annotate_menu.add_separator()
        annotate_menu.add_command(label="Measure Distance", command=self._measure_distance)
        annotate_menu.add_command(label="Measure Area", command=self._measure_area)
        annotate_menu.add_command(label="Measure Perimeter", command=self._measure_perimeter)
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
        page_menu.add_separator()
        page_menu.add_command(label="Add Bates Numbering", command=self._add_bates_numbering)
        page_menu.add_command(label="Set Background", command=self._set_background)
        page_menu.add_separator()
        page_menu.add_command(label="Import Bookmarks from HTML", command=self._import_bookmarks_html)
        page_menu.add_command(label="Export Bookmarks to HTML", command=self._export_bookmarks_html)
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
        tools_menu.add_separator()
        tools_menu.add_command(label="Compare Documents", command=self._compare_documents, accelerator="Ctrl+Shift+C")
        tools_menu.add_command(label="Compress PDF", command=self._compress_pdf)
        tools_menu.add_command(label="Optimize Images", command=self._optimize_images)
        tools_menu.add_command(label="PDF/A Compliance", command=self._pdfa_compliance)
        tools_menu.add_separator()
        tools_menu.add_command(label="Spell Check", command=self._spell_check, accelerator="F7")
        tools_menu.add_separator()
        tools_menu.add_command(label="Read Aloud", command=self._read_aloud, accelerator="F5")
        tools_menu.add_command(label="Read Selection", command=self._read_selection)
        tools_menu.add_command(label="Stop Reading", command=self._stop_reading)
        tools_menu.add_separator()
        tools_menu.add_command(label="Accessibility Check", command=self._accessibility_check)
        tools_menu.add_command(label="Action Wizard", command=self._action_wizard)
        tools_menu.add_separator()
        tools_menu.add_command(label="Full-Text Index", command=self._build_index)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        view_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["bg_secondary"], fg=self.colors["text"])
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl+=")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Fit Page", command=self.zoom_fit)
        view_menu.add_command(label="Fit Width", command=self.zoom_width)
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Grid", command=self.toggle_grid)
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Snap to Grid", command=self._toggle_snap)
        view_menu.add_command(label="Add Guide", command=self._add_guide)
        view_menu.add_command(label="Clear Guides", command=self._clear_guides)
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
        self.root.bind("<F5>", lambda e: self._read_aloud())
        self.root.bind("<F7>", lambda e: self._spell_check())
        self.root.bind("<Control-Shift-C>", lambda e: self._compare_documents())
        self.root.bind("<Control-Shift-F>", lambda e: self._find_in_all_pages())
        self.root.bind("<F1>", lambda e: self._show_shortcuts())
        self.root.bind("<Control-f>", lambda e: self._show_find_toolbar())

    def _on_mousewheel(self, event):
        if event.delta > 0:
            self.prev_page()
        else:
            self.next_page()

    def _track_action(self):
        self._action_counter += 1
        if should_show_easter_egg(self._action_counter):
            egg = pick_easter_egg()
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

    def add_image_element(self):
        from tools.image_tool import add_image_tool
        add_image_tool(self)

    def set_font_color(self, color):
        self.formatting_manager.set_color(color)
        if self.selected_element is not None and 0 <= self.selected_element < len(self.elements):
            elem = self.elements[self.selected_element]
            if hasattr(elem, 'color'):
                elem.color = color
                self.canvas_manager.update_preview()

    def apply_stamp(self, stamp_type):
        from models.elements import StampElement, PREDEFINED_STAMPS
        stamp_text = stamp_type.upper()
        for s in PREDEFINED_STAMPS:
            if s.lower() == stamp_type.lower():
                stamp_text = s
                break
        elem = StampElement(
            text=stamp_text, x=200, y=200, w=150, h=50,
            page=self.current_page, color="#FF0000"
        )
        self.add_element_at_click(200, 200, elem)

    def generate_barcode(self, bc_type):
        from models.elements import BarcodeElement
        elem = BarcodeElement(
            data="SAMPLE", barcode_type=bc_type,
            x=100, y=100, w=200, h=100,
            page=self.current_page
        )
        self.add_element_at_click(100, 100, elem)

    def start_drawing(self, shape_type="rect"):
        self.set_tool(shape_type)

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

    previous_page = prev_page

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

    def _compare_documents(self):
        if not self.current_pdf:
            messagebox.showwarning("Compare", "Open a PDF document first.")
            return
        path1 = self.current_pdf
        path2 = filedialog.askopenfilename(
            title="Select second PDF to compare",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not path2:
            return
        output = filedialog.asksaveasfilename(
            title="Save comparison result",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")]
        )
        if not output:
            return
        try:
            self.compare_service.compare_files(path1, path2, output)
            changes = self.compare_service.get_text_changes()
            self.status.configure(text=f"Comparison saved. {len(changes)} text difference(s) found.")
            messagebox.showinfo("Compare Documents", f"Comparison saved to:\n{output}\n{len(changes)} text difference(s) found.")
        except Exception as e:
            messagebox.showerror("Compare Error", str(e))

    def _compress_pdf(self):
        if not self.current_pdf:
            messagebox.showwarning("Compress", "Open a PDF document first.")
            return
        output = filedialog.asksaveasfilename(
            title="Save compressed PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output:
            return
        try:
            level = "medium"
            info = self.compress_service.get_compression_info(self.current_pdf)
            old_size = info.get("file_size", 0)
            self.compress_service.compress(self.current_pdf, output, level)
            new_size = os.path.getsize(output)
            savings = old_size - new_size
            self.status.configure(text=f"Compressed: {old_size} -> {new_size} bytes (saved {savings})")
            messagebox.showinfo("Compress PDF", f"Compressed successfully.\nSaved: {savings} bytes")
        except Exception as e:
            messagebox.showerror("Compress Error", str(e))

    def _optimize_images(self):
        if not self.current_pdf:
            messagebox.showwarning("Optimize", "Open a PDF document first.")
            return
        try:
            self.compress_service.optimize_images(self.current_pdf, quality=75)
            self.status.configure(text="Images optimized (quality=75)")
            messagebox.showinfo("Optimize Images", "Images optimized successfully.")
        except Exception as e:
            messagebox.showerror("Optimize Error", str(e))

    def _pdfa_compliance(self):
        if not self.current_pdf:
            messagebox.showwarning("PDF/A", "Open a PDF document first.")
            return
        result = self.pdfa_service.validate_pdfa(self.current_pdf)
        is_compliant = result.get("is_compliant", False)
        errors = result.get("errors", [])
        profile = result.get("profile", "unknown")
        if is_compliant:
            messagebox.showinfo("PDF/A Compliance", f"Document is PDF/A-{profile} compliant.\nNo issues found.")
        else:
            msg = f"Document is NOT PDF/A compliant.\nProfile: {profile}\n\nIssues:\n"
            for err in errors[:20]:
                msg += f"  - {err}\n"
            convert = messagebox.askyesno("PDF/A Compliance", msg + "\nConvert to PDF/A-1b?")
            if convert:
                output = filedialog.asksaveasfilename(
                    title="Save PDF/A document",
                    defaultextension=".pdf",
                    filetypes=[("PDF Files", "*.pdf")]
                )
                if output:
                    try:
                        self.pdfa_service.convert_to_pdfa(self.current_pdf, output, "1b")
                        self.status.configure(text=f"Converted to PDF/A-1b: {output}")
                        messagebox.showinfo("PDF/A", f"Converted successfully:\n{output}")
                    except Exception as e2:
                        messagebox.showerror("PDF/A Error", str(e2))

    def _spell_check(self):
        if not self.current_pdf:
            messagebox.showwarning("Spell Check", "Open a PDF document first.")
            return
        try:
            import pymupdf
            doc = pymupdf.open(self.current_pdf)
            text = doc[self.current_page].get_text("text")
            doc.close()
            if not text.strip():
                messagebox.showinfo("Spell Check", "No text found on current page.")
                return
            errors = self.spellcheck_service.check_text(text)
            if not errors:
                messagebox.showinfo("Spell Check", "No spelling errors found.")
                self.status.configure(text="Spell check passed - no errors")
                return
            msg = f"Found {len(errors)} spelling issue(s):\n\n"
            for err in errors[:20]:
                suggestions = ", ".join(err.get("suggestions", [])[:5])
                msg += f"  '{err['word']}' -> {suggestions}\n"
            messagebox.showinfo("Spell Check", msg)
            self.status.configure(text=f"Spell check: {len(errors)} issue(s) found")
        except Exception as e:
            messagebox.showerror("Spell Check Error", str(e))

    def _read_aloud(self):
        if not self.current_pdf:
            messagebox.showwarning("Read Aloud", "Open a PDF document first.")
            return
        try:
            self.tts_service.speak_page(self.current_page)
            self.status.configure(text="Reading page aloud...")
        except Exception as e:
            messagebox.showerror("Read Aloud Error", str(e))

    def _read_selection(self):
        if not self.current_pdf:
            messagebox.showwarning("Read Selection", "Open a PDF document first.")
            return
        try:
            import pymupdf
            doc = pymupdf.open(self.current_pdf)
            text = doc[self.current_page].get_text("text")
            doc.close()
            if text.strip():
                self.tts_service.speak(text)
                self.status.configure(text="Reading selection aloud...")
            else:
                self.status.configure(text="No text to read on current page")
        except Exception as e:
            messagebox.showerror("Read Selection Error", str(e))

    def _stop_reading(self):
        try:
            self.tts_service.stop()
            self.status.configure(text="Reading stopped")
        except Exception as e:
            messagebox.showerror("Stop Reading Error", str(e))

    def _accessibility_check(self):
        if not self.current_pdf:
            messagebox.showwarning("Accessibility", "Open a PDF document first.")
            return
        result = self.accessibility_service.check_accessibility(self.current_pdf)
        score = result.get("score", 0)
        issues = result.get("issues", [])
        msg = f"Accessibility Score: {score}/100\n\nIssues ({len(issues)}):\n"
        for issue in issues[:20]:
            msg += f"  [{issue.get('severity', 'low').upper()}] {issue.get('message', '')}\n"
        messagebox.showinfo("Accessibility Check", msg)
        self.status.configure(text=f"Accessibility score: {score}/100, {len(issues)} issue(s)")

    def _action_wizard(self):
        actions = self.automation_service.list_actions()
        if not actions:
            messagebox.showinfo("Action Wizard", "No saved actions. Create actions via JSON configuration.")
            return
        msg = "Available actions:\n\n"
        for i, name in enumerate(actions, 1):
            msg += f"  {i}. {name}\n"
        messagebox.showinfo("Action Wizard", msg)

    def _build_index(self):
        if not self.current_pdf:
            messagebox.showwarning("Full-Text Index", "Open a PDF document first.")
            return
        try:
            result = self.index_service.build_index(self.current_pdf)
            total_words = result.get("total_words", 0)
            total_pages = result.get("total_pages", 0)
            self.status.configure(text=f"Index built: {total_words} words across {total_pages} pages")
            messagebox.showinfo("Full-Text Index", f"Index built successfully.\n{total_words} words indexed across {total_pages} pages.")
        except Exception as e:
            messagebox.showerror("Index Error", str(e))

    def _add_callout(self):
        if not self.current_pdf:
            messagebox.showwarning("Callout", "Open a PDF document first.")
            return
        from models.elements import TextElement
        elem = TextElement(
            text="Callout", x=150, y=150, size=12,
            page=self.current_page, color="#FF6600"
        )
        self.add_element_at_click(150, 150, elem)
        self.status.configure(text="Callout added - double-click to edit text")

    def _add_textbox(self):
        if not self.current_pdf:
            messagebox.showwarning("Text Box", "Open a PDF document first.")
            return
        from models.elements import TextElement
        elem = TextElement(
            text="Text Box", x=100, y=100, size=12,
            page=self.current_page
        )
        self.add_element_at_click(100, 100, elem)
        self.status.configure(text="Text box added - double-click to edit text")

    def _measure_distance(self):
        if not self.current_pdf:
            messagebox.showwarning("Measure", "Open a PDF document first.")
            return
        self.set_tool("line")
        self.status.configure(text="Click two points to measure distance")

    def _measure_area(self):
        if not self.current_pdf:
            messagebox.showwarning("Measure", "Open a PDF document first.")
            return
        self.set_tool("rect")
        self.status.configure(text="Draw a rectangle to measure area")

    def _measure_perimeter(self):
        if not self.current_pdf:
            messagebox.showwarning("Measure", "Open a PDF document first.")
            return
        self.set_tool("freehand")
        self.status.configure(text="Draw a shape to measure perimeter")

    def _add_barcode(self):
        if not self.current_pdf:
            messagebox.showwarning("Barcode", "Open a PDF document first.")
            return
        from models.elements import TextElement
        elem = TextElement(
            text="||| || ||| || ||", x=100, y=100, size=14,
            page=self.current_page, font_name="Courier"
        )
        self.add_element_at_click(100, 100, elem)
        self.status.configure(text="Barcode placeholder added")

    def _add_video(self):
        if not self.current_pdf:
            messagebox.showwarning("Video", "Open a PDF document first.")
            return
        messagebox.showinfo("Video", "Video insertion: Select a video file to embed as a PDF annotation.")
        self.status.configure(text="Video embed not yet supported in this version")

    def _add_audio(self):
        if not self.current_pdf:
            messagebox.showwarning("Audio", "Open a PDF document first.")
            return
        messagebox.showinfo("Audio", "Audio insertion: Select an audio file to embed as a PDF annotation.")
        self.status.configure(text="Audio embed not yet supported in this version")

    def _paste_in_place(self):
        try:
            data = self.root.clipboard_get()
            import json
            obj = json.loads(data)
            from models.elements import element_from_json
            elem = element_from_json(obj)
            if elem:
                elem.page = self.current_page
                x = getattr(elem, "x", 0)
                y = getattr(elem, "y", 0)
                self.add_element_at_click(x, y, elem)
                self.status.configure(text="Pasted in place")
        except Exception:
            self.status.configure(text="Nothing to paste in place")

    def _paste_as_text(self):
        try:
            data = self.root.clipboard_get()
            from models.elements import TextElement
            elem = TextElement(
                text=data[:500], x=100, y=100, size=12,
                page=self.current_page
            )
            self.add_element_at_click(100, 100, elem)
            self.status.configure(text="Pasted as text element")
        except Exception:
            self.status.configure(text="No text to paste")

    def _add_bates_numbering(self):
        if not self.current_pdf:
            messagebox.showwarning("Bates", "Open a PDF document first.")
            return
        try:
            self.bates_service.add_bates_all_pages(
                prefix="DOC-", start_num=1,
                position="bottom-right", font_size=10
            )
            self.canvas_manager.update_preview()
            self.status.configure(text="Bates numbering added to all pages")
        except Exception as e:
            messagebox.showerror("Bates Error", str(e))

    def _set_background(self):
        if not self.current_pdf:
            messagebox.showwarning("Background", "Open a PDF document first.")
            return
        from tkinter import colorchooser
        color = colorchooser.askcolor(initialcolor="#FFFFFF", title="Select background color")
        if color[1]:
            try:
                self.background_service.set_solid_background(self.current_page, color[1])
                self.canvas_manager.update_preview()
                self.status.configure(text=f"Background set to {color[1]}")
            except Exception as e:
                messagebox.showerror("Background Error", str(e))

    def _import_bookmarks_html(self):
        if not self.current_pdf:
            messagebox.showwarning("Bookmarks", "Open a PDF document first.")
            return
        path = filedialog.askopenfilename(
            title="Select HTML file with bookmarks",
            filetypes=[("HTML Files", "*.html;*.htm")]
        )
        if not path:
            return
        try:
            bookmarks = self.bookmark_import_service.import_from_html(path)
            self.status.configure(text=f"Imported {len(bookmarks)} bookmark(s) from HTML")
            messagebox.showinfo("Bookmarks", f"Imported {len(bookmarks)} bookmark(s) from HTML.")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def _export_bookmarks_html(self):
        if not self.current_pdf:
            messagebox.showwarning("Bookmarks", "Open a PDF document first.")
            return
        output = filedialog.asksaveasfilename(
            title="Export bookmarks to HTML",
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html")]
        )
        if not output:
            return
        try:
            import pymupdf
            doc = pymupdf.open(self.current_pdf)
            toc = doc.get_toc(simple=True)
            doc.close()
            bookmarks = [{"title": t[1], "level": t[0], "page": t[2] if len(t) > 2 else 0} for t in toc]
            self.bookmark_import_service.export_to_html(bookmarks, output)
            self.status.configure(text=f"Exported {len(bookmarks)} bookmark(s) to HTML")
            messagebox.showinfo("Bookmarks", f"Exported {len(bookmarks)} bookmark(s) to:\n{output}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_svg(self):
        if not self.current_pdf:
            messagebox.showwarning("Export SVG", "Open a PDF document first.")
            return
        output = filedialog.asksaveasfilename(
            title="Export to SVG",
            defaultextension=".svg",
            filetypes=[("SVG Files", "*.svg")]
        )
        if not output:
            return
        try:
            import pymupdf
            doc = pymupdf.open(self.current_pdf)
            page = doc[self.current_page]
            svg = page.get_svg_image(text_as_path=False)
            with open(output, "w", encoding="utf-8") as f:
                f.write(svg)
            doc.close()
            self.status.configure(text=f"Exported page {self.current_page + 1} to SVG: {output}")
            messagebox.showinfo("Export SVG", f"Exported to:\n{output}")
        except Exception as e:
            messagebox.showerror("Export SVG Error", str(e))

    def _print_all(self):
        if not self.current_pdf:
            messagebox.showwarning("Print", "Open a PDF document first.")
            return
        try:
            self.print_service.print_all_pages()
            self.status.configure(text="Printing all pages...")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))

    def _print_current(self):
        if not self.current_pdf:
            messagebox.showwarning("Print", "Open a PDF document first.")
            return
        try:
            self.print_service.print_current_page()
            self.status.configure(text=f"Printing page {self.current_page + 1}...")
        except Exception as e:
            messagebox.showerror("Print Error", str(e))

    def _print_booklet(self):
        if not self.current_pdf:
            messagebox.showwarning("Print Booklet", "Open a PDF document first.")
            return
        output = filedialog.asksaveasfilename(
            title="Save booklet PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output:
            return
        try:
            self.print_service.print_booklet(self.current_pdf, output)
            self.status.configure(text=f"Booklet saved: {output}")
            messagebox.showinfo("Print Booklet", f"Booklet layout saved to:\n{output}")
        except Exception as e:
            messagebox.showerror("Booklet Error", str(e))

    def _print_poster(self):
        if not self.current_pdf:
            messagebox.showwarning("Print Poster", "Open a PDF document first.")
            return
        output = filedialog.asksaveasfilename(
            title="Save poster PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output:
            return
        try:
            self.print_service.print_poster(self.current_pdf, output, rows=2, cols=2)
            self.status.configure(text=f"Poster saved: {output}")
            messagebox.showinfo("Print Poster", f"Poster layout (2x2) saved to:\n{output}")
        except Exception as e:
            messagebox.showerror("Poster Error", str(e))

    def _toggle_snap(self):
        """Toggle snap to grid"""
        if hasattr(self, 'snap_service'):
            self.snap_service.toggle_snap(not getattr(self, '_snap_enabled', False))
            self._snap_enabled = not self._snap_enabled

    def _add_guide(self):
        """Add a guide line"""
        if hasattr(self, 'snap_service'):
            from tkinter import simpledialog
            orientation = simpledialog.askstring("Guide", "Orientation (h/v):", initialvalue="h")
            if orientation in ("h", "v"):
                position = simpledialog.askfloat("Guide", "Position (pixels):", initialvalue=400)
                if position:
                    self.snap_service.add_guide(orientation, position)

    def _clear_guides(self):
        """Clear all guides"""
        if hasattr(self, 'snap_service'):
            self.snap_service.clear_guides()

    def _find_in_all_pages(self):
        if not self.current_pdf:
            messagebox.showwarning("Find", "Open a PDF document first.")
            return
        from tkinter import simpledialog
        query = simpledialog.askstring("Find in All Pages", "Enter search text:")
        if not query:
            return
        try:
            results = self.index_service.search_index(query)
            if results:
                msg = f"Found '{query}' on {len(results)} page(s):\n\n"
                for r in results[:10]:
                    msg += f"  Page {r['page'] + 1} (score: {r['score']})\n"
                messagebox.showinfo("Find Results", msg)
            else:
                self.index_service.build_index(self.current_pdf)
                results = self.index_service.search_index(query)
                if results:
                    msg = f"Found '{query}' on {len(results)} page(s):\n\n"
                    for r in results[:10]:
                        msg += f"  Page {r['page'] + 1} (score: {r['score']})\n"
                    messagebox.showinfo("Find Results", msg)
                else:
                    messagebox.showinfo("Find Results", f"No results for '{query}'")
            self.status.configure(text=f"Search complete for '{query}'")
        except Exception as e:
            messagebox.showerror("Find Error", str(e))

    def _show_shortcuts(self):
        """Toggle keyboard shortcut overlay"""
        if hasattr(self, 'shortcut_overlay'):
            self.shortcut_overlay.toggle()

    def _show_find_toolbar(self):
        """Show the find toolbar"""
        if hasattr(self, 'find_toolbar'):
            self.find_toolbar.show()

    def run(self):
        self.root.mainloop()


def main():
    root = tk.Tk()
    app = PDFEditor(root)
    app.run()


if __name__ == "__main__":
    main()
