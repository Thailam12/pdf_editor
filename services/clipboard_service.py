import copy
import io
import base64
import pymupdf
from PIL import Image


class ClipboardService:
    def __init__(self, editor):
        self.editor = editor
        self._internal_buffer = {}
        self._text_buffer = ""
        self._image_buffer = None
        self._page_buffer = None

    def copy_element(self, element):
        """Copy an element to the clipboard (internal buffer + system clipboard)."""
        try:
            self._internal_buffer = {
                "type": "element",
                "data": copy.deepcopy(element)
            }
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                if hasattr(element, 'text') and element.text:
                    root.clipboard_clear()
                    root.clipboard_append(str(element.text))
                root.destroy()
            except Exception:
                pass
        except Exception as e:
            raise RuntimeError(f"Cannot copy element: {e}")

    def paste_element(self):
        """Paste an element from the internal buffer. Returns element or None."""
        try:
            if self._internal_buffer.get("type") == "element":
                elem = self._internal_buffer.get("data")
                if elem:
                    return copy.deepcopy(elem)
            return None
        except Exception:
            return None

    def copy_text(self, text):
        """Copy plain text to the clipboard."""
        try:
            self._text_buffer = text
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(text)
                root.destroy()
            except Exception:
                pass
        except Exception as e:
            raise RuntimeError(f"Cannot copy text: {e}")

    def paste_text(self):
        """Paste text from the system clipboard or internal buffer."""
        try:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                text = root.clipboard_get()
                root.destroy()
                if text:
                    return text
            except Exception:
                pass
            return self._text_buffer
        except Exception:
            return self._text_buffer or ""

    def copy_image(self, pil_image):
        """Copy a PIL Image to the clipboard."""
        try:
            self._image_buffer = pil_image.copy()
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                import win32clipboard
                output = io.BytesIO()
                pil_image.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]
                output.close()
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
            except ImportError:
                pass
            except Exception:
                pass
            root.destroy() if 'root' in dir() else None
        except Exception as e:
            raise RuntimeError(f"Cannot copy image: {e}")

    def paste_image(self):
        """Paste an image from the system clipboard. Returns PIL Image or None."""
        try:
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                    output = io.BytesIO(data)
                    win32clipboard.CloseClipboard()
                    output.seek(0)
                    img = Image.open(output)
                    return img
                except Exception:
                    win32clipboard.CloseClipboard()
            except ImportError:
                pass
            except Exception:
                pass
            return self._image_buffer
        except Exception:
            return self._image_buffer

    def copy_page(self, page_num):
        """Copy a page to the internal buffer as serialized data."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return None
            page = doc[page_num]
            text = page.get_text("text")
            images = []
            for img in page.get_images(full=True):
                try:
                    base_img = doc.extract_image(img[0])
                    if base_img:
                        images.append({
                            "xref": img[0],
                            "ext": base_img["ext"],
                            "width": base_img.get("width", 0),
                            "height": base_img.get("height", 0)
                        })
                except Exception:
                    continue
            elements = [
                e.to_json() for e in self.editor.elements
                if getattr(e, 'page', 0) == page_num
            ]
            self._page_buffer = {
                "text": text,
                "images": images,
                "elements": elements,
                "page_num": page_num
            }
            return self._page_buffer
        except Exception as e:
            raise RuntimeError(f"Cannot copy page: {e}")

    def paste_page(self, data):
        """Paste page data as a new page. Returns the new page number."""
        try:
            if not data or not isinstance(data, dict):
                return None
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return None
            new_page_num = len(doc)
            page = doc.new_page(width=595, height=842)
            if data.get("text"):
                rect = page.rect
                page.insert_textbox(
                    rect, data["text"],
                    fontsize=10, fontname="helv"
                )
            if data.get("elements"):
                from models.elements import element_from_json
                for elem_data in data["elements"]:
                    elem = element_from_json(elem_data)
                    if elem:
                        elem.page = new_page_num
                        self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            return new_page_num
        except Exception as e:
            raise RuntimeError(f"Cannot paste page: {e}")
