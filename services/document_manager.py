import os
import json
import tempfile
from tkinter import filedialog, messagebox
from new_file_template import create_blank_pdf


def _elements_path(pdf_path):
    return pdf_path + ".elements.json"


def _save_elements_sidecar(pdf_path, elements):
    if not pdf_path:
        return
    from models.elements import elements_to_json_list
    data = elements_to_json_list(elements)
    try:
        with open(_elements_path(pdf_path), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_elements_sidecar(pdf_path):
    if not pdf_path:
        return []
    from models.elements import elements_from_json_list
    path = _elements_path(pdf_path)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return elements_from_json_list(data)
    except Exception:
        return []


class DocumentManager:
    def __init__(self, editor):
        self.editor = editor

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return
        self.editor.pdf_utils.load_pdf(path)
        self.editor.current_pdf = path
        self.editor.is_temp_document = False
        self.editor.elements.clear()
        self.editor.element_images.clear()
        self.editor.total_pages = len(self.editor.pdf_utils.doc)
        self.editor.current_page = 0
        self.editor.selected_element = None
        saved = _load_elements_sidecar(path)
        if saved:
            self.editor.elements.extend(saved)
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.editor.undo_manager.clear()
        if saved:
            self.editor.status.configure(text=f"Đã mở: {os.path.basename(path)} ({len(saved)} phần tử)")
        else:
            self.editor.status.configure(text=f"Đã mở: {os.path.basename(path)}")

    def _should_prompt_save_as(self):
        return bool(getattr(self.editor, "is_temp_document", False))

    def save_pdf(self):
        if not self.editor.current_pdf:
            messagebox.showwarning("Cảnh báo", "Chưa có file PDF để lưu!")
            return
        self.editor.pdf_utils.save_edited_pdf(
            self.editor.current_pdf, self.editor.current_pdf, self.editor.elements
        )
        _save_elements_sidecar(self.editor.current_pdf, self.editor.elements)
        self.editor.status.configure(text="Đã lưu PDF")

    def save_as_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")]
        )
        if not path:
            return
        self.editor.pdf_utils.save_edited_pdf(
            self.editor.current_pdf, path, self.editor.elements
        )
        self.editor.current_pdf = path
        self.editor.is_temp_document = False
        _save_elements_sidecar(path, self.editor.elements)
        self.editor.status.configure(text=f"Đã lưu: {os.path.basename(path)}")

    def new_temp_document(self):
        path = os.path.join(
            tempfile.gettempdir(),
            f"temp_{next(tempfile._get_candidate_names())}.pdf",
        )
        create_blank_pdf(path)
        self.editor.pdf_utils.load_pdf(path)
        self.editor.current_pdf = path
        self.editor.is_temp_document = True
        self.editor.elements.clear()
        self.editor.element_images.clear()
        self.editor.total_pages = 1
        self.editor.current_page = 0
        self.editor.selected_element = None
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
