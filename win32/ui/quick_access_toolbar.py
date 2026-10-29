"""Quick-Access Toolbar (QAT).

A compact strip above the ribbon with default commands (Save, Undo, Redo,
Print) and a "+" button that opens a customization dialog exposing the
full feature catalog (80+ commands). Layout persists to
~/.pdf_editor_qat.json.
"""
import os
import json
import tkinter as tk
from tkinter import messagebox

try:
    import customtkinter as ctk
except Exception:
    ctk = None


BG = "#181825"
BTN_BG = "#181825"
BTN_FG = "#cdd6f4"
HOVER_BG = "#45475a"
ACTIVE_BG = "#585b70"
SEPARATOR_BG = "#45475a"
DIALOG_BG = "#1e1e2e"

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".pdf_editor_qat.json")

DEFAULT_ITEMS = ["save", "undo", "redo", "print"]


class _Feature:
    __slots__ = ("fid", "category", "label", "icon", "accel", "resolver")

    def __init__(self, fid, category, label, icon, resolver, accel=""):
        self.fid = fid
        self.category = category
        self.label = label
        self.icon = icon
        self.accel = accel
        # resolver(editor) -> callable or None when the command is unavailable
        self.resolver = resolver


def _m(name, accel=""):
    """Resolve a plain editor method by name."""
    def _resolve(editor):
        fn = getattr(editor, name, None)
        return fn if callable(fn) else None
    return _resolve, accel


def _tool(tool_name):
    """Resolve a set_tool(...) command."""
    def _resolve(editor):
        if hasattr(editor, "set_tool"):
            return lambda: editor.set_tool(tool_name)
        return None
    return _resolve, ""


# ---------------------------------------------------------------------------
# Feature catalog: (id, category, label, icon, resolver, accelerator)
# ---------------------------------------------------------------------------
_CATALOG = [
    # --- File ---
    _Feature("new", "File", "New Document", "\U0001f4c4", *_m("new_document", "Ctrl+N")),
    _Feature("open", "File", "Open PDF", "\U0001f4c2", *_m("open_pdf", "Ctrl+O")),
    _Feature("save", "File", "Save", "\U0001f4be", *_m("save_pdf", "Ctrl+S")),
    _Feature("save_as", "File", "Save As", "\U0001f4ab", *_m("save_as_pdf", "Ctrl+Shift+S")),
    _Feature("print", "File", "Print", "\U0001f5a8", *_m("print_pdf", "Ctrl+P")),
    _Feature("print_all", "File", "Print All Pages", "\U0001f5a7", *_m("_print_all")),
    _Feature("print_current", "File", "Print Current Page", "\U0001f5a6", *_m("_print_current")),
    _Feature("print_booklet", "File", "Print Booklet", "\U0001f4d6", *_m("_print_booklet")),
    _Feature("print_poster", "File", "Print Poster", "\U0001f5bc", *_m("_print_poster")),
    _Feature("export_images", "File", "Export to Images", "\U0001f5bc", *_m("export_images")),
    _Feature("export_docx", "File", "Export to DOCX", "\U0001f4c5", *_m("export_docx")),
    _Feature("export_html", "File", "Export to HTML", "\U0001f310", *_m("export_html")),
    _Feature("export_svg", "File", "Export to SVG", "\U0001f58c", *_m("_export_svg")),
    # --- Edit ---
    _Feature("undo", "Edit", "Undo", "\u21b6", *_m("undo", "Ctrl+Z")),
    _Feature("redo", "Edit", "Redo", "\u21b7", *_m("redo", "Ctrl+Y")),
    _Feature("cut", "Edit", "Cut", "\u2702", *_m("cut_selected", "Ctrl+X")),
    _Feature("copy", "Edit", "Copy", "\U0001f4cb", *_m("copy_selected", "Ctrl+C")),
    _Feature("paste", "Edit", "Paste", "\U0001f4ea", *_m("paste_clipboard", "Ctrl+V")),
    _Feature("paste_place", "Edit", "Paste in Place", "\U0001f4cc", *_m("_paste_in_place")),
    _Feature("paste_text", "Edit", "Paste as Text", "\U0001f177", *_m("_paste_as_text")),
    _Feature("select_all", "Edit", "Select All", "\U0001f5c1", *_m("select_all", "Ctrl+A")),
    _Feature("deselect", "Edit", "Deselect", "\u274c", *_m("deselect_all", "Esc")),
    _Feature("delete", "Edit", "Delete Selected", "\U0001f5d1", *_m("delete_selected_element", "Del")),
    _Feature("edit_element", "Edit", "Edit Selected", "\u270e", *_m("edit_selected_element")),
    _Feature("find_replace", "Edit", "Find & Replace", "\U0001f50d", *_m("show_find_replace", "Ctrl+H")),
    _Feature("clear_all", "Edit", "Clear All Elements", "\U0001f9f9", *_m("clear_elements")),
    # --- Insert ---
    _Feature("tool_text", "Insert", "Text Tool", "\U0001f520", *_tool("text")),
    _Feature("tool_image", "Insert", "Image Tool", "\U0001f5bc", *_tool("image")),
    _Feature("insert_image", "Insert", "Insert Image", "\U0001faba", *_m("insert_image")),
    _Feature("tool_rect", "Insert", "Rectangle", "\u25a1", *_tool("rect")),
    _Feature("tool_ellipse", "Insert", "Ellipse", "\u25cb", *_tool("ellipse")),
    _Feature("tool_triangle", "Insert", "Triangle", "\u25b3", *_tool("triangle")),
    _Feature("tool_line", "Insert", "Line", "\u2571", *_tool("line")),
    _Feature("tool_arrow", "Insert", "Arrow", "\u27a4", *_tool("arrow")),
    _Feature("tool_freehand", "Insert", "Freehand Draw", "\u270d", *_tool("freehand")),
    _Feature("stamp", "Insert", "Stamp", "\U0001f41d", *_m("show_stamp_dialog")),
    _Feature("signature", "Insert", "Signature", "\u2712", *_m("show_signature_dialog")),
    _Feature("watermark", "Insert", "Watermark", "\U0001f4a7", *_m("show_watermark_dialog")),
    _Feature("header_footer", "Insert", "Header/Footer", "\U0001f4c4", *_m("show_header_footer_dialog")),
    _Feature("form_field", "Insert", "Form Field", "\U0001f9fe", *_m("show_form_field_dialog")),
    _Feature("tool_link", "Insert", "Link", "\U0001f517", *_tool("link")),
    _Feature("barcode", "Insert", "Barcode", "\U0001f4f0", *_m("_add_barcode")),
    _Feature("video", "Insert", "Video", "\U0001f3a5", *_m("_add_video")),
    _Feature("audio", "Insert", "Audio", "\U0001f3b5", *_m("_add_audio")),
    _Feature("callout", "Insert", "Callout", "\U0001f4ac", *_m("_add_callout")),
    _Feature("textbox", "Insert", "Text Box", "\U0001f582", *_m("_add_textbox")),
    # --- Annotate ---
    _Feature("tool_highlight", "Annotate", "Highlight", "\U0001f58e", *_tool("highlight")),
    _Feature("tool_underline", "Annotate", "Underline", "\u0336", *_tool("underline")),
    _Feature("tool_strike", "Annotate", "Strikethrough", "\u0335", *_tool("strikethrough")),
    _Feature("tool_squiggly", "Annotate", "Squiggly", "\u2060", *_tool("squiggly")),
    _Feature("tool_note", "Annotate", "Sticky Note", "\U0001f4dd", *_tool("note")),
    _Feature("redact", "Annotate", "Redact", "\u2593", *_m("mark_redaction")),
    _Feature("apply_redact", "Annotate", "Apply Redactions", "\u26a0", *_m("apply_redactions")),
    _Feature("measure_dist", "Annotate", "Measure Distance", "\U0001f4cf", *_m("_measure_distance")),
    _Feature("measure_area", "Annotate", "Measure Area", "\u259d", *_m("_measure_area")),
    _Feature("measure_perim", "Annotate", "Measure Perimeter", "\u2599", *_m("_measure_perimeter")),
    # --- Page ---
    _Feature("page_insert", "Page", "Insert Page", "\U0001f4be", *_m("insert_page")),
    _Feature("page_delete", "Page", "Delete Page", "\U0001f5d1", *_m("delete_page")),
    _Feature("page_duplicate", "Page", "Duplicate Page", "\U0001f4d8", *_m("duplicate_page")),
    _Feature("rotate_cw", "Page", "Rotate Clockwise", "\u21bb", *_m("rotate_cw")),
    _Feature("rotate_ccw", "Page", "Rotate Counter-CW", "\u21ba", *_m("rotate_ccw")),
    _Feature("crop", "Page", "Crop Page", "\u2702", *_m("crop_page")),
    _Feature("merge", "Page", "Merge PDFs", "\U0001f4d6", *_m("merge_pdfs")),
    _Feature("split", "Page", "Split PDF", "\U0001f4d4", *_m("show_split_dialog")),
    _Feature("bates", "Page", "Bates Numbering", "\U0001f522", *_m("_add_bates_numbering")),
    _Feature("background", "Page", "Set Background", "\U0001f3a8", *_m("_set_background")),
    _Feature("bm_import", "Page", "Import Bookmarks (HTML)", "\U0001f4e5", *_m("_import_bookmarks_html")),
    _Feature("bm_export", "Page", "Export Bookmarks (HTML)", "\U0001f4e4", *_m("_export_bookmarks_html")),
    # --- Tools ---
    _Feature("bookmarks", "Tools", "Bookmarks", "\U0001f516", *_m("show_bookmarks_dialog")),
    _Feature("ocr_page", "Tools", "OCR Current Page", "\U0001f9dd", *_m("ocr_current_page")),
    _Feature("ocr_all", "Tools", "OCR All Pages", "\U0001f4da", *_m("ocr_all_pages")),
    _Feature("protect", "Tools", "Password Protect", "\U0001f512", *_m("show_protect_dialog")),
    _Feature("flatten", "Tools", "Flatten PDF", "\U0001f98a", *_m("flatten_pdf")),
    _Feature("ai_extract", "Tools", "AI: Extract Text", "\u2728", *_m("ai_extract_text")),
    _Feature("ai_summarize", "Tools", "AI: Summarize", "\U0001f9e0", *_m("ai_summarize")),
    _Feature("compare", "Tools", "Compare Documents", "\U0001f500", *_m("_compare_documents", "Ctrl+Shift+C")),
    _Feature("compress", "Tools", "Compress PDF", "\U0001f4e6", *_m("_compress_pdf")),
    _Feature("opt_images", "Tools", "Optimize Images", "\U0001f387", *_m("_optimize_images")),
    _Feature("pdfa", "Tools", "PDF/A Compliance", "\U0001f3c5", *_m("_pdfa_compliance")),
    _Feature("spellcheck", "Tools", "Spell Check", "\u2714", *_m("_spell_check", "F7")),
    _Feature("read_aloud", "Tools", "Read Aloud", "\U0001f50a", *_m("_read_aloud", "F5")),
    _Feature("read_sel", "Tools", "Read Selection", "\U0001f5e3", *_m("_read_selection")),
    _Feature("stop_reading", "Tools", "Stop Reading", "\U0001f4a4", *_m("_stop_reading")),
    _Feature("a11y", "Tools", "Accessibility Check", "\u267f", *_m("_accessibility_check")),
    _Feature("wizard", "Tools", "Action Wizard", "\U0001f9d9", *_m("_action_wizard")),
    _Feature("index", "Tools", "Full-Text Index", "\U0001f4cf", *_m("_build_index")),
    _Feature("find_all", "Tools", "Find in All Pages", "\U0001f50e", *_m("_find_in_all_pages", "Ctrl+Shift+F")),
    # --- View ---
    _Feature("prev_page", "View", "Previous Page", "\u23ee", *_m("prev_page", "\u2190")),
    _Feature("next_page", "View", "Next Page", "\u23ed", *_m("next_page", "\u2192")),
    _Feature("goto_page", "View", "Go to Page", "\U0001f170", *_m("goto_page")),
    _Feature("zoom_in", "View", "Zoom In", "\U0001f536", *_m("zoom_in", "Ctrl++")),
    _Feature("zoom_out", "View", "Zoom Out", "\U0001f53a", *_m("zoom_out", "Ctrl+-")),
    _Feature("zoom_fit", "View", "Fit Page", "\u26f5", *_m("zoom_fit")),
    _Feature("zoom_width", "View", "Fit Width", "\u2194", *_m("zoom_width")),
    _Feature("grid", "View", "Toggle Grid", "\u25a6", *_m("toggle_grid")),
    _Feature("snap", "View", "Toggle Snap to Grid", "\U0001f9f2", *_m("_toggle_snap")),
    _Feature("guide", "View", "Add Guide", "\U0001f4cf", *_m("_add_guide")),
    _Feature("clear_guides", "View", "Clear Guides", "\U0001f9f9", *_m("_clear_guides")),
    _Feature("font_color", "View", "Font Color", "\U0001f534", *_m("pick_color")),
    _Feature("fill_color", "View", "Fill Color", "\U0001f7e1", *_m("pick_fill_color")),
    _Feature("shortcuts", "Help", "Keyboard Shortcuts", "\u2328", *_m("_show_shortcuts", "F1")),
    _Feature("about", "Help", "About", "\u2139", *_m("show_about")),
]

FEATURES = {f.fid: f for f in _CATALOG}
CATEGORIES = ["File", "Edit", "Insert", "Annotate", "Page", "Tools", "View", "Help"]


def _tool_icon(parent, **kw):
    if ctk is not None:
        return ctk.CTkButton(parent, **kw)
    return tk.Button(parent, **kw)


class QuickAccessToolbar:
    """Compact customizable command strip packed at the very top of the window."""

    def __init__(self, editor, parent):
        self.editor = editor
        self.items = self._load_items()
        self._btn_widgets = {}

        self.frame = tk.Frame(parent, bg=BG, height=30)
        self.frame.pack(side=tk.TOP, fill=tk.X)
        self.frame.pack_propagate(False)
        self._build()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_items(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            saved = [fid for fid in data.get("items", []) if fid in FEATURES]
            if saved:
                return saved
        except Exception:
            pass
        return list(DEFAULT_ITEMS)

    def _save_items(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump({"items": self.items}, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Toolbar building
    # ------------------------------------------------------------------
    def _build(self):
        for child in self.frame.winfo_children():
            child.destroy()
        self._btn_widgets = {}

        left = tk.Frame(self.frame, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        for fid in self.items:
            feat = FEATURES.get(fid)
            if feat is None:
                continue
            self._add_button(left, feat)

        right = tk.Frame(self.frame, bg=BG)
        right.pack(side=tk.RIGHT)
        self._add_customize_button(right)

    def _add_button(self, parent, feat):
        text = feat.icon
        tip = f"{feat.label}  ({feat.accel})" if feat.accel else feat.label

        def command(f=feat):
            fn = f.resolver(self.editor)
            if fn is not None:
                fn()
            else:
                self.editor.set_status(f"{f.label}: not available")

        btn = tk.Button(
            parent, text=text, command=command,
            bg=BTN_BG, fg=BTN_FG, activebackground=ACTIVE_BG,
            relief=tk.FLAT, bd=0, width=3,
            font=("Segoe UI Symbol", 11),
            highlightthickness=0, cursor="hand2",
        )
        btn.pack(side=tk.LEFT, padx=1, pady=3)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=HOVER_BG))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BTN_BG))
        _bind_tooltip(btn, tip)
        self._btn_widgets[feat.fid] = btn

    def _add_customize_button(self, parent):
        btn = tk.Button(
            parent, text="\u2795", command=self.open_customize_dialog,
            bg=BTN_BG, fg="#89b4fa", activebackground=ACTIVE_BG,
            relief=tk.FLAT, bd=0, width=3,
            font=("Segoe UI Symbol", 11),
            highlightthickness=0, cursor="hand2",
        )
        btn.pack(side=tk.RIGHT, padx=(1, 4), pady=3)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=HOVER_BG))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BTN_BG))
        _bind_tooltip(btn, "Customize Quick-Access Toolbar (add more tools)")

        # small dropdown on right-click for quick actions
        menu = tk.Menu(btn, tearoff=0, bg="#313244", fg="#cdd6f4",
                       activebackground="#585b70")
        menu.add_command(label="Customize\u2026", command=self.open_customize_dialog)
        menu.add_command(label="Reset to Default", command=self.reset_defaults)
        btn.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_items(self, item_ids):
        self.items = [fid for fid in item_ids if fid in FEATURES]
        self._save_items()
        self._build()

    def reset_defaults(self):
        self.set_items(list(DEFAULT_ITEMS))
        self.editor.set_status("Quick-Access Toolbar reset to defaults")

    def open_customize_dialog(self):
        CustomizeDialog(self)


class CustomizeDialog:
    """Two-pane picker: available commands (grouped by category) and the
    active QAT order with move/remove controls. Falls back to plain tk widgets."""

    MAX_HINT = 24  # soft recommendation; toolbar wraps beyond that

    def __init__(self, qat):
        self.qat = qat
        self.editor = qat.editor
        self._checkvars = {}
        self._ordered_ids = list(qat.items)
        self.order_list = None
        root = qat.frame

        self.win = tk.Toplevel(root)
        self.win.title("Customize Quick-Access Toolbar")
        self.win.configure(bg=DIALOG_BG)
        self.win.geometry("720x480")
        self.win.transient(root.winfo_toplevel())
        self.win.grab_set()

        body = tk.Frame(self.win, bg=DIALOG_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left: available features grouped by category ---
        left = tk.LabelFrame(body, text="All Features", bg=DIALOG_BG, fg=BTN_FG,
                             font=("Segoe UI", 9, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._checkvars = {}
        container = tk.Frame(left, bg=DIALOG_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        canvas = tk.Canvas(container, bg=DIALOG_BG, highlightthickness=0)
        scroll = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=DIALOG_BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(inner_id, width=e.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        active = set(self._ordered_ids)
        for category in CATEGORIES:
            tk.Label(inner, text=category, bg=DIALOG_BG, fg="#89b4fa",
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 0))
            for feat in _CATALOG:
                if feat.category != category:
                    continue
                var = tk.BooleanVar(value=feat.fid in active)
                cb = tk.Checkbutton(
                    inner, text=f"{feat.icon}  {feat.label}", variable=var,
                    bg=DIALOG_BG, fg=BTN_FG, selectcolor="#313244",
                    activebackground=DIALOG_BG, activeforeground=BTN_FG,
                    highlightthickness=0, anchor="w", font=("Segoe UI", 9),
                    command=self._refresh_order,
                )
                cb.pack(fill=tk.X)
                self._checkvars[feat.fid] = var

        # --- Right: current QAT order ---
        right = tk.Frame(body, bg=DIALOG_BG, width=250)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        tk.Label(right, text="Toolbar Order", bg=DIALOG_BG, fg=BTN_FG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.order_list = tk.Listbox(
            right, bg="#313244", fg=BTN_FG, selectbackground="#585b70",
            highlightthickness=0, font=("Segoe UI", 9), exportselection=False,
        )
        self.order_list.pack(fill=tk.BOTH, expand=True, pady=4)
        self._refresh_order()

        btns = tk.Frame(right, bg=DIALOG_BG)
        btns.pack(fill=tk.X)
        for text, cmd in (
            ("\u2b06 Move Up", lambda: self._move(-1)),
            ("\u2b07 Move Down", lambda: self._move(1)),
            ("\u2716 Remove", self._remove_selected),
        ):
            tk.Button(btns, text=text, command=cmd, bg="#45475a", fg=BTN_FG,
                      relief=tk.FLAT, bd=0, font=("Segoe UI", 9)).pack(fill=tk.X, pady=1)

        # --- Bottom actions ---
        bottom = tk.Frame(self.win, bg=DIALOG_BG)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(bottom, text="Reset Default (Save/Undo/Redo/Print)",
                  command=self._reset, bg="#45475a", fg=BTN_FG, relief=tk.FLAT,
                  bd=0, padx=8, pady=3).pack(side=tk.LEFT)
        tk.Button(bottom, text="OK", command=self._apply, bg="#89b4fa", fg="#1e1e2e",
                  relief=tk.FLAT, bd=0, padx=16, pady=3,
                  font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Button(bottom, text="Cancel", command=self.win.destroy, bg="#45475a",
                  fg=BTN_FG, relief=tk.FLAT, bd=0, padx=16, pady=3).pack(side=tk.RIGHT)

        self.win.bind("<Destroy>", self._cleanup)

    def _cleanup(self, _e):
        try:
            self.qat.frame.winfo_toplevel().unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _selected_ids(self):
        """Ordered ids currently in the order list."""
        return list(self._ordered_ids)

    def _refresh_order(self, ordered=None):
        if ordered is None:
            ordered = list(self._ordered_ids)
        # include newly checked items at the end; drop unchecked
        checked = {fid for fid, var in self._checkvars.items() if var.get()}
        ordered = [fid for fid in ordered if fid in checked]
        ordered += [fid for fid in FEATURES if fid in checked and fid not in ordered]
        self._ordered_ids = ordered
        if self.order_list is None:
            return
        self.order_list.delete(0, tk.END)
        for fid in ordered:
            feat = FEATURES[fid]
            self.order_list.insert(tk.END, f"{feat.icon} {feat.label}")
        if ordered:
            self.order_list.selection_set(0)

    def _move(self, direction):
        sel = self.order_list.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + direction
        if 0 <= j < len(self._ordered_ids):
            ids = self._ordered_ids
            ids[i], ids[j] = ids[j], ids[i]
            self._refresh_order(ids)
            self.order_list.selection_set(j)

    def _remove_selected(self):
        sel = self.order_list.curselection()
        if not sel:
            return
        fid = self._ordered_ids[sel[0]]
        self._checkvars[fid].set(False)
        self._refresh_order()

    def _reset(self):
        for fid, var in self._checkvars.items():
            var.set(fid in DEFAULT_ITEMS)
        self._refresh_order(list(DEFAULT_ITEMS))

    def _apply(self):
        self._refresh_order()
        ids = self._ordered_ids
        if not ids:
            messagebox.showwarning("Quick-Access Toolbar",
                                   "Add at least one command.",
                                   parent=self.win)
            return
        self.qat.set_items(ids)
        self.win.destroy()
        self.editor.set_status(f"Quick-Access Toolbar updated ({len(ids)} commands)")


class _Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None

    def show(self, _e=None):
        if self.tip_window or not self.text:
            return
        x, y = self.widget.winfo_rootx(), self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 8), padx=6, pady=2).pack()

    def hide(self, _e=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


def _bind_tooltip(widget, text):
    tip = _Tooltip(widget, text)
    widget.bind("<Enter>", tip.show)
    widget.bind("<Leave>", tip.hide)
