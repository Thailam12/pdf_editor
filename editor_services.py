import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from new_file_template import create_blank_pdf

class CanvasInteractionManager:
    def __init__(self, editor):
        self.editor = editor

    def get_resize_handle_at(self, x, y):
        canvas = self.editor.canvas_preview
        items = canvas.find_overlapping(x - 8, y - 8, x + 8, y + 8)
        for item in items:
            for tag in canvas.gettags(item):
                if tag.startswith("handle_"):
                    return tag
        return None

    def _find_element_id_at(self, x, y):
        canvas = self.editor.canvas_preview
        def element_id_from_tag(tag):
            try:
                parts = tag.split("_")
                if len(parts) >= 2: return int(parts[1])
            except: pass
            return None

        items = canvas.find_overlapping(x - 5, y - 5, x + 5, y + 5)
        for item in reversed(items):
            for tag in canvas.gettags(item):
                if any(tag.startswith(p) for p in ["text_", "img_", "shape_", "sel_", "handle_"]):
                    eid = element_id_from_tag(tag)
                    if eid is not None: return eid

        scale = self.editor.zoom_level / 100
        for i, (etype, params) in reversed(list(enumerate(self.editor.elements))):
            if params.get("page", 0) != self.editor.current_page: continue
            if etype == "line":
                xmin, xmax = min(params['x1'], params['x2']), max(params['x1'], params['x2'])
                ymin, ymax = min(params['y1'], params['y2']), max(params['y1'], params['y2'])
            else:
                xmin, ymin = params.get('x', 0), params.get('y', 0)
                xmax, ymax = xmin + params.get('w', 50), ymin + params.get('h', 20)
            if xmin - 5 <= x/scale <= xmax + 5 and ymin - 5 <= y/scale <= ymax + 5:
                return i
        return None

    def on_canvas_click(self, event):
        editor = self.editor
        editor.dragging = editor.resizing = False
        handle = self.get_resize_handle_at(event.x, event.y)
        if handle:
            editor.selected_element = int(handle.split("_", 2)[1])
            editor.resizing, editor.resize_handle, editor.resize_start = True, handle, (event.x, event.y)
            editor.resize_orig_params = dict(editor.elements[editor.selected_element][1])
            editor.update_preview(); return
        
        eid = self._find_element_id_at(event.x, event.y)
        if eid is None: editor.selected_element = None
        else:
            editor.selected_element = eid
            etype, params = editor.elements[eid]
            editor.dragging, editor.drag_orig_params = True, dict(params)
            scale = editor.zoom_level / 100
            if etype == "line": editor.drag_offset = (event.x/scale - params['x1'], event.y/scale - params['y1'])
            else: editor.drag_offset = (event.x/scale - params.get('x', 0), event.y/scale - params.get('y', 0))
        editor.update_preview()

    def on_canvas_drag(self, event):
        editor = self.editor
        if editor.selected_element is None: return
        scale = editor.zoom_level / 100
        etype, params = editor.elements[editor.selected_element]
        if editor.resizing:
            dx, dy = (event.x - editor.resize_start[0])/scale, (event.y - editor.resize_start[1])/scale
            corner = editor.resize_handle.rsplit("_", 1)[-1]
            if etype == "text": params['size'] = max(8, int(editor.resize_orig_params.get('size', 12) + (dx+dy)/2*0.6))
            elif etype in ["image", "rect", "ellipse", "triangle"]:
                if "e" in corner: params['w'] = max(10, editor.resize_orig_params.get('w', 50) + dx)
                if "s" in corner: params['h'] = max(10, editor.resize_orig_params.get('h', 50) + dy)
                if "w" in corner:
                    dw = editor.resize_orig_params.get('w', 50) - dx
                    if dw > 10: params['x'], params['w'] = editor.resize_orig_params.get('x', 0) + dx, dw
                if "n" in corner:
                    dh = editor.resize_orig_params.get('h', 50) - dy
                    if dh > 10: params['y'], params['h'] = editor.resize_orig_params.get('y', 0) + dy, dh
        elif editor.dragging:
            nx, ny = event.x/scale - editor.drag_offset[0], event.y/scale - editor.drag_offset[1]
            if etype == "line":
                dx, dy = nx - editor.drag_orig_params['x1'], ny - editor.drag_orig_params['y1']
                params['x1'], params['y1'] = nx, ny
                params['x2'], params['y2'] = editor.drag_orig_params['x2'] + dx, editor.drag_orig_params['y2'] + dy
            else: params['x'], params['y'] = max(0, nx), max(0, ny)
        editor.update_preview()

    def on_canvas_release(self, event):
        if self.editor.dragging or self.editor.resizing:
            self.editor.undo_redo_manager.save_state(self.editor.elements)
            self.editor.dragging = self.editor.resizing = False

    def on_canvas_motion(self, event):
        editor = self.editor
        if self.get_resize_handle_at(event.x, event.y): editor.canvas_preview.configure(cursor="arrow")
        elif self._find_element_id_at(event.x, event.y) is not None: editor.canvas_preview.configure(cursor="hand2")
        else: editor.canvas_preview.configure(cursor="cross")

    def show_context_menu(self, event):
        editor = self.editor
        eid = self._find_element_id_at(event.x, event.y)
        if eid is not None: editor.selected_element = eid; editor.update_preview()
        menu = tk.Menu(editor.root, tearoff=0)
        if editor.selected_element is not None:
            menu.add_command(label="Sửa", command=editor.edit_selected_element)
            menu.add_command(label="Xóa", command=editor.delete_selected_element)
            menu.add_separator()
        menu.add_command(label="Hủy", command=lambda: None)
        menu.tk_popup(event.x_root, event.y_root)

class DocumentManager:
    def __init__(self, editor): self.editor = editor
    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path: return
        self.editor.pdf_utils.load_pdf(path); self.editor.current_pdf, self.editor.is_temp_document = path, False
        self.editor.elements.clear(); self.editor.total_pages = len(self.editor.pdf_utils.doc)
        self.editor.current_page = 0; self.editor.update_preview(); self.editor.update_info_panel()
    def save_pdf(self):
        if self.editor.current_pdf: self.editor.pdf_utils.save_edited_pdf(self.editor.current_pdf, self.editor.current_pdf, self.editor.elements)
    def save_as_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if path: self.editor.pdf_utils.save_edited_pdf(self.editor.current_pdf, path, self.editor.elements); self.editor.current_pdf, self.editor.is_temp_document = path, False
    def new_temp_document(self):
        path = os.path.join(tempfile.gettempdir(), f"temp_{next(tempfile._get_candidate_names())}.pdf")
        create_blank_pdf(path); self.editor.pdf_utils.load_pdf(path); self.editor.current_pdf, self.editor.is_temp_document = path, True
        self.editor.elements.clear(); self.editor.total_pages = 1; self.editor.current_page = 0; self.editor.update_preview()

class OCRManager:
    def __init__(self, editor): self.editor = editor
    def ocr_dialog(self, all_pages=False):
        dialog = tk.Toplevel(self.editor.root); tk.Label(dialog, text="Language:").pack()
        v = tk.StringVar(value="en"); ttk.Combobox(dialog, textvariable=v, values=["en", "vi", "ch"]).pack()
        tk.Button(dialog, text="Start", command=lambda: [dialog.destroy(), self._start_ocr(all_pages, v.get())]).pack()
    def _start_ocr(self, all_pages, lang):
        import threading
        threading.Thread(target=self._worker, args=(all_pages, lang), daemon=True).start()
    def _worker(self, all_pages, lang):
        from ocr_utils import OCRBox, boxes_to_editor_text_elements; import pymupdf; from PIL import Image
        e = self.editor; pages = range(len(e.pdf_utils.doc)) if all_pages else [e.current_page]
        for p in pages:
            page = e.pdf_utils.doc[p]; pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            boxes = e._ocr_image_to_boxes(img, lang=lang)
            els = boxes_to_editor_text_elements([OCRBox(b.text, b.x1_px, b.y1_px, b.x2_px, b.y2_px) for b in boxes], p, pix.width, pix.height, float(page.rect.width), float(page.rect.height))
            e.root.after(0, lambda: [e.elements.extend(els), e.update_preview()])

class ElementManager:
    def __init__(self, editor): self.editor = editor
    def delete_selected(self):
        if self.editor.selected_element is not None:
            self.editor.undo_redo_manager.save_state(self.editor.elements)
            del self.editor.elements[self.editor.selected_element]; self.editor.selected_element = None; self.editor.update_preview()
        def edit_selected(self):
            editor = self.editor
            if editor.selected_element is None or editor.selected_element >= len(editor.elements):
                return
            elem = editor.elements[editor.selected_element]
            etype, params = elem
            if params.get('page', 0) != editor.current_page:
                editor.selected_element = None
                return
            
            editor.undo_redo_manager.save_state(editor.elements)
            dialog = tk.Toplevel(editor.root)
            dialog.transient(editor.root)
            dialog.grab_set()
            dialog.title(f"Sửa {etype}")
            dialog.geometry("420x550")
        
            row = 0
            def add_label(text):
                nonlocal row
                tk.Label(dialog, text=text, anchor="w").grid(row=row, column=0, sticky="w", padx=12, pady=6)
                row += 1

            def add_entry(var, width=16):
                entry = tk.Entry(dialog, textvariable=var, width=width)
                entry.grid(row=row-1, column=1, sticky="e", padx=12)
                return entry

            add_label("Loại phần tử:")
            tk.Label(dialog, text=etype.title(), anchor="w").grid(row=row-1, column=1, sticky="e", padx=12)

            vars = {}
            if etype == "text":
                vars['text'] = tk.StringVar(value=params.get('text', ''))
                add_label("Nội dung:"); tk.Entry(dialog, textvariable=vars['text'], width=35).grid(row=row-1, column=1, sticky="e", padx=12)
                vars['x'] = tk.DoubleVar(value=params.get('x', 0) / 72); add_label("X (inch):"); add_entry(vars['x'])
                vars['y'] = tk.DoubleVar(value=params.get('y', 0) / 72); add_label("Y (inch):"); add_entry(vars['y'])
                vars['size'] = tk.IntVar(value=params.get('size', 12)); add_label("Kích thước:"); add_entry(vars['size'])
                vars['font_name'] = tk.StringVar(value=params.get('font_name', 'Arial')); add_label("Font:")
                ttk.Combobox(dialog, textvariable=vars['font_name'], values=["Arial", "Times New Roman", "Courier", "Calibri"], width=14, state="readonly").grid(row=row-1, column=1, sticky="e", padx=12)
                vars['color'] = tk.StringVar(value=params.get('color', '#000000')); add_label("Màu:")
                c_btn = tk.Button(dialog, text="Chọn màu", bg=vars['color'].get(), fg="white", command=lambda: pick_color(vars['color'], c_btn))
                c_btn.grid(row=row-1, column=1, sticky="e", padx=12)
            elif etype == "image":
                vars['path'] = tk.StringVar(value=params.get('path', ''))
                add_label("Đường dẫn:"); tk.Entry(dialog, textvariable=vars['path'], width=35).grid(row=row-1, column=1, sticky="e", padx=12)
                vars['x'] = tk.DoubleVar(value=params.get('x', 0) / 72); add_label("X (inch):"); add_entry(vars['x'])
                vars['y'] = tk.DoubleVar(value=params.get('y', 0) / 72); add_label("Y (inch):"); add_entry(vars['y'])
                vars['w'] = tk.DoubleVar(value=params.get('w', 100) / 72); add_label("Rộng (inch):"); add_entry(vars['w'])
                vars['h'] = tk.DoubleVar(value=params.get('h', 100) / 72); add_label("Cao (inch):"); add_entry(vars['h'])
            elif etype in ["rect", "ellipse", "triangle"]:
                vars['x'] = tk.DoubleVar(value=params.get('x', 0) / 72); add_label("X (inch):"); add_entry(vars['x'])
                vars['y'] = tk.DoubleVar(value=params.get('y', 0) / 72); add_label("Y (inch):"); add_entry(vars['y'])
                vars['w'] = tk.DoubleVar(value=params.get('w', 100) / 72); add_label("Rộng (inch):"); add_entry(vars['w'])
                vars['h'] = tk.DoubleVar(value=params.get('h', 100) / 72); add_label("Cao (inch):"); add_entry(vars['h'])
                vars['color'] = tk.StringVar(value=params.get('color', 'red')); add_label("Màu:")
                c_btn = tk.Button(dialog, text="Chọn màu", bg=vars['color'].get(), fg="white", command=lambda: pick_color(vars['color'], c_btn))
                c_btn.grid(row=row-1, column=1, sticky="e", padx=12)

            def pick_color(v, b):
                from tkinter import colorchooser
                c = colorchooser.askcolor(initialcolor=v.get())[1]
                if c: v.set(c); b.configure(bg=c)

            def apply():
                for k, v in vars.items():
                    if k in ['x', 'y', 'w', 'h']: params[k] = v.get() * 72
                    else: params[k] = v.get()
                editor.update_preview(); dialog.destroy()

            tk.Button(dialog, text="Lưu thay đổi", command=apply, bg="#007bff", fg="white", width=20).grid(row=row, column=0, columnspan=2, pady=20)



