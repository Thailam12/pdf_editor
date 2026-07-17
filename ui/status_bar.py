import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None

BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
BTN_BG = "#45475a"
ACTIVE_BG = "#585b70"
SECTION_BG = "#313244"


def create_status_bar(editor, parent):
    status_frame = tk.Frame(parent, bg=BG, bd=0, highlightthickness=0, height=28)
    status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    status_frame.pack_propagate(False)

    left_frame = tk.Frame(status_frame, bg=BG, bd=0)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

    center_frame = tk.Frame(status_frame, bg=BG, bd=0)
    center_frame.pack(side=tk.LEFT, fill=tk.Y, padx=16)

    right_frame = tk.Frame(status_frame, bg=BG, bd=0)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8))

    status_label = tk.Label(left_frame, text="Ready",
                            bg=BG, fg=FG, font=("Segoe UI", 9),
                            anchor="w", padx=4)
    status_label.pack(side=tk.LEFT, fill=tk.Y)
    editor._status_label = status_label

    page_frame = tk.Frame(center_frame, bg=BG, bd=0)
    page_frame.pack(side=tk.LEFT, fill=tk.Y)

    prev_btn = tk.Button(page_frame, text="\u25c0", bg=BTN_BG, fg=FG,
                         font=("Segoe UI", 9), relief="flat", bd=0,
                         padx=6, pady=1, cursor="hand2",
                         command=editor.previous_page)
    prev_btn.pack(side=tk.LEFT, padx=2)

    page_info_label = tk.Label(page_frame, text="Page 1 / 1",
                               bg=BG, fg=FG, font=("Segoe UI", 9),
                               padx=8)
    page_info_label.pack(side=tk.LEFT)
    editor._status_page_info = page_info_label

    next_btn = tk.Button(page_frame, text="\u25b6", bg=BTN_BG, fg=FG,
                         font=("Segoe UI", 9), relief="flat", bd=0,
                         padx=6, pady=1, cursor="hand2",
                         command=editor.next_page)
    next_btn.pack(side=tk.LEFT, padx=2)

    sep1 = tk.Frame(right_frame, bg="#585b70", width=1)
    sep1.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)

    zoom_label = tk.Label(right_frame, text="100%",
                          bg=BG, fg=FG, font=("Segoe UI", 9),
                          padx=6)
    zoom_label.pack(side=tk.LEFT)
    editor._status_zoom = zoom_label

    zoom_in_btn = tk.Button(right_frame, text="+", bg=BTN_BG, fg=FG,
                            font=("Segoe UI", 8), relief="flat", bd=0,
                            padx=4, pady=0, cursor="hand2",
                            command=lambda: editor.set_zoom(editor.zoom_level + 10))
    zoom_in_btn.pack(side=tk.LEFT, padx=1)

    zoom_out_btn = tk.Button(right_frame, text="-", bg=BTN_BG, fg=FG,
                             font=("Segoe UI", 8), relief="flat", bd=0,
                             padx=4, pady=0, cursor="hand2",
                             command=lambda: editor.set_zoom(editor.zoom_level - 10))
    zoom_out_btn.pack(side=tk.LEFT, padx=1)

    sep2 = tk.Frame(right_frame, bg="#585b70", width=1)
    sep2.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)

    cursor_label = tk.Label(right_frame, text="X: 0  Y: 0",
                            bg=BG, fg="#a6adc8", font=("Segoe UI", 8),
                            padx=6)
    cursor_label.pack(side=tk.LEFT)
    editor._status_cursor = cursor_label

    sep3 = tk.Frame(right_frame, bg="#585b70", width=1)
    sep3.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=4)

    elem_label = tk.Label(right_frame, text="0 elements",
                          bg=BG, fg="#a6adc8", font=("Segoe UI", 8),
                          padx=6)
    elem_label.pack(side=tk.LEFT)
    editor._status_elem_count = elem_label

    def update_cursor(event):
        x = int(event.x)
        y = int(event.y)
        editor._status_cursor.configure(text=f"X: {x}  Y: {y}")

    if hasattr(editor, 'canvas_preview'):
        editor.canvas_preview.bind("<Motion>", update_cursor)

    return status_frame


def update_status(editor):
    status_label = getattr(editor, "_status_label", None)
    if status_label:
        if editor.ocr_running:
            status_label.configure(text="OCR processing...")
        elif editor.current_pdf:
            status_label.configure(text=f"Loaded: {editor.current_pdf}")
        else:
            status_label.configure(text="Ready")

    page_info = getattr(editor, "_status_page_info", None)
    if page_info:
        if editor.total_pages > 0:
            page_info.configure(text=f"Page {editor.current_page + 1} / {editor.total_pages}")
        else:
            page_info.configure(text="No pages")

    zoom_label = getattr(editor, "_status_zoom", None)
    if zoom_label:
        zoom_label.configure(text=f"{editor.zoom_level}%")

    elem_label = getattr(editor, "_status_elem_count", None)
    if elem_label:
        total = len(editor.elements)
        page_elems = sum(1 for e in editor.elements if getattr(e, "page", 0) == editor.current_page)
        elem_label.configure(text=f"{page_elems} / {total} elements")
