from models.elements import HeaderFooterElement


class BatesService:
    def __init__(self, editor):
        self.editor = editor
        self._bates_entries = []
        self._counter = 0

    def add_bates_number(self, page_num, prefix="", start_num=1, position="bottom-right",
                         font_size=10, color="#000000"):
        """Add a Bates number to a specific page."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            bates_text = f"{prefix}{start_num:06d}"
            x, y = self._get_position_coords(doc[page_num], position, font_size)
            elem = HeaderFooterElement(
                text=bates_text, x=x, y=y,
                size=font_size, color=color,
                font_name="Courier",
                position=position,
                page=page_num
            )
            elem.name = f"Bates: {bates_text}"
            self.editor.elements.append(elem)
            self._bates_entries.append({
                "page": page_num, "text": bates_text,
                "position": position
            })
            self._counter = start_num + 1
            self.editor.canvas_manager.update_preview()
            return elem
        except Exception as e:
            raise RuntimeError(f"Cannot add Bates number: {e}")

    def add_bates_all_pages(self, prefix="", start_num=1, position="bottom-right",
                            font_size=10, color="#000000"):
        """Add sequential Bates numbers to all pages."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            num = start_num
            for page_num in range(len(doc)):
                bates_text = f"{prefix}{num:06d}"
                x, y = self._get_position_coords(doc[page_num], position, font_size)
                elem = HeaderFooterElement(
                    text=bates_text, x=x, y=y,
                    size=font_size, color=color,
                    font_name="Courier",
                    position=position,
                    page=page_num
                )
                elem.name = f"Bates: {bates_text}"
                self.editor.elements.append(elem)
                self._bates_entries.append({
                    "page": page_num, "text": bates_text,
                    "position": position
                })
                num += 1
            self._counter = num
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot add Bates numbers: {e}")

    def get_bates_info(self):
        """Return list of all Bates number entries."""
        return list(self._bates_entries)

    def remove_bates_numbers(self):
        """Remove all Bates number elements from the document."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.elements = [
                e for e in self.editor.elements
                if not (isinstance(e, HeaderFooterElement) and
                        e.name and e.name.startswith("Bates:"))
            ]
            self._bates_entries.clear()
            self._counter = 0
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            raise RuntimeError(f"Cannot remove Bates numbers: {e}")

    def _get_position_coords(self, page, position, font_size):
        """Calculate x, y coordinates for the given position string."""
        rect = page.rect
        margin = 30
        if "top" in position:
            y = margin
        elif "bottom" in position:
            y = rect.height - margin - font_size
        else:
            y = rect.height - margin - font_size
        if "left" in position:
            x = margin
        elif "right" in position:
            x = rect.width - margin - 120
        else:
            x = rect.width / 2 - 60
        return x, y
