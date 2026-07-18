import os
import pymupdf
from models.elements import ShapeElement


class BackgroundService:
    def __init__(self, editor):
        self.editor = editor
        self._backgrounds = {}

    def set_solid_background(self, page_num, color):
        """Set a solid color background for a page."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            page = doc[page_num]
            rect = page.rect
            bg = ShapeElement(
                shape_type="rect",
                x=0, y=0, w=rect.width, h=rect.height,
                color=color, filled=True, fill_color=color,
                page=page_num
            )
            bg.name = f"Background: solid {color}"
            self._backgrounds[page_num] = {
                "type": "solid", "color": color
            }
            self.editor.elements.insert(0, bg)
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot set solid background: {e}")

    def set_gradient_background(self, page_num, color1, color2, direction="vertical"):
        """Set a gradient background (approximated with overlapping shapes)."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            page = doc[page_num]
            rect = page.rect
            num_bands = 20
            if direction == "vertical":
                band_h = rect.height / num_bands
                for i in range(num_bands):
                    ratio = i / max(num_bands - 1, 1)
                    r = int(color1[1:3], 16) * (1 - ratio) + int(color2[1:3], 16) * ratio
                    g = int(color1[3:5], 16) * (1 - ratio) + int(color2[3:5], 16) * ratio
                    b = int(color1[5:7], 16) * (1 - ratio) + int(color2[5:7], 16) * ratio
                    band_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                    bg = ShapeElement(
                        shape_type="rect",
                        x=0, y=i * band_h, w=rect.width, h=band_h + 1,
                        color=band_color, filled=True, fill_color=band_color,
                        page=page_num
                    )
                    self.editor.elements.insert(0, bg)
            else:
                band_w = rect.width / num_bands
                for i in range(num_bands):
                    ratio = i / max(num_bands - 1, 1)
                    r = int(color1[1:3], 16) * (1 - ratio) + int(color2[1:3], 16) * ratio
                    g = int(color1[3:5], 16) * (1 - ratio) + int(color2[3:5], 16) * ratio
                    b = int(color1[5:7], 16) * (1 - ratio) + int(color2[5:7], 16) * ratio
                    band_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                    bg = ShapeElement(
                        shape_type="rect",
                        x=i * band_w, y=0, w=band_w + 1, h=rect.height,
                        color=band_color, filled=True, fill_color=band_color,
                        page=page_num
                    )
                    self.editor.elements.insert(0, bg)
            self._backgrounds[page_num] = {
                "type": "gradient", "color1": color1,
                "color2": color2, "direction": direction
            }
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot set gradient background: {e}")

    def set_image_background(self, page_num, image_path):
        """Set an image as the page background."""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            self.editor.undo_manager.save_state(self.editor.elements)
            from models.elements import ImageElement
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            from PIL import Image
            img = Image.open(image_path)
            img_w, img_h = img.size
            page = doc[page_num]
            rect = page.rect
            scale = min(rect.width / img_w, rect.height / img_h)
            w = img_w * scale
            h = img_h * scale
            x = (rect.width - w) / 2
            y = (rect.height - h) / 2
            bg = ImageElement(
                path=image_path, x=x, y=y, w=w, h=h, page=page_num
            )
            bg.name = "Image Background"
            self._backgrounds[page_num] = {
                "type": "image", "path": image_path
            }
            self.editor.elements.insert(0, bg)
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot set image background: {e}")

    def remove_background(self, page_num):
        """Remove the background from a specific page."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            bg_names = {"Background:", "Image Background"}
            self.editor.elements = [
                e for e in self.editor.elements
                if not (getattr(e, 'page', -1) == page_num and
                        any(getattr(e, 'name', '').startswith(n) for n in bg_names))
            ]
            self._backgrounds.pop(page_num, None)
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot remove background: {e}")

    def apply_to_all_pages(self, color):
        """Apply a solid color background to all pages."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            for page_num in range(len(doc)):
                self.set_solid_background(page_num, color)
        except Exception as e:
            raise RuntimeError(f"Cannot apply background to all pages: {e}")

    def get_background_info(self, page_num):
        """Return background info dict for a given page."""
        return self._backgrounds.get(page_num, {"type": "none"})
