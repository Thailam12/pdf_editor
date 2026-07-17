from tkinter import messagebox
from models.elements import FormFieldElement


class FormService:
    def __init__(self, editor):
        self.editor = editor

    def detect_form_fields(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return []
            page = doc[page_num]
            widgets = page.widgets()
            fields = []
            if widgets:
                for widget in widgets:
                    field_name = widget.field_name or ""
                    field_type = widget.field_type_string or "text"
                    field_value = widget.field_value or ""
                    rect = widget.rect
                    fields.append({
                        "name": field_name,
                        "type": field_type,
                        "value": str(field_value),
                        "x": rect.x0, "y": rect.y0,
                        "w": rect.width, "h": rect.height,
                    })
                    elem = FormFieldElement(
                        x=rect.x0, y=rect.y0,
                        w=rect.width, h=rect.height,
                        field_type=field_type,
                        field_name=field_name,
                        value=str(field_value),
                        page=page_num
                    )
                    existing = [
                        e for e in self.editor.elements
                        if getattr(e, 'type_name', '') == 'formfield'
                        and getattr(e, 'field_name', '') == field_name
                        and getattr(e, 'page', 0) == page_num
                    ]
                    if not existing:
                        self.editor.elements.append(elem)
            if fields:
                self.editor.canvas_manager.update_preview()
                self.editor.update_info_panel()
            return fields
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể phát hiện trường: {str(e)}")
            return []

    def add_text_field(self, x, y, w, h, name, value=""):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = FormFieldElement(
                x=x, y=y, w=w, h=h,
                field_type="text",
                field_name=name or f"text_{len([e for e in self.editor.elements if getattr(e, 'type_name', '') == 'formfield'])}",
                value=value,
                page=self.editor.current_page
            )
            self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm trường văn bản '{elem.field_name}'")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm trường: {str(e)}")

    def add_checkbox(self, x, y, name, checked=False):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = FormFieldElement(
                x=x, y=y, w=14, h=14,
                field_type="checkbox",
                field_name=name or f"check_{len([e for e in self.editor.elements if getattr(e, 'type_name', '') == 'formfield'])}",
                value=str(checked),
                page=self.editor.current_page
            )
            self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm checkbox '{elem.field_name}'")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm checkbox: {str(e)}")

    def add_dropdown(self, x, y, w, options, name):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = FormFieldElement(
                x=x, y=y, w=w, h=24,
                field_type="dropdown",
                field_name=name or f"dropdown_{len([e for e in self.editor.elements if getattr(e, 'type_name', '') == 'formfield'])}",
                value=options[0] if options else "",
                page=self.editor.current_page
            )
            self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm dropdown '{elem.field_name}'")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm dropdown: {str(e)}")

    def fill_form_field(self, name, value):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            found = False
            for e in self.editor.elements:
                if getattr(e, 'type_name', '') == 'formfield' and getattr(e, 'field_name', '') == name:
                    e.value = value
                    found = True
            if found:
                self.editor.canvas_manager.update_preview()
                self.editor.update_info_panel()
                self.editor.status.configure(text=f"Đã điền trường '{name}'")
            else:
                messagebox.showinfo("Thông báo", f"Không tìm thấy trường '{name}'")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể điền trường: {str(e)}")

    def get_form_data(self):
        try:
            form_data = []
            for e in self.editor.elements:
                if getattr(e, 'type_name', '') == 'formfield':
                    form_data.append({
                        "name": getattr(e, 'field_name', ''),
                        "type": getattr(e, 'field_type', 'text'),
                        "value": getattr(e, 'value', ''),
                        "page": getattr(e, 'page', 0),
                    })
            doc = self.editor.pdf_utils.doc
            if doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    widgets = page.widgets()
                    if widgets:
                        for widget in widgets:
                            form_data.append({
                                "name": widget.field_name or "",
                                "type": widget.field_type_string or "text",
                                "value": str(widget.field_value or ""),
                                "page": page_num,
                            })
            return form_data
        except Exception as e:
            return []
