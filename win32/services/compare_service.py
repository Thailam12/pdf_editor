import os
import pymupdf
from PIL import Image, ImageChops, ImageDraw


class CompareService:
    def __init__(self, editor):
        self.editor = editor
        self._text_changes = []
        self._page_diffs = {}

    def compare_files(self, path1, path2, output_path):
        """Compare two PDFs visually and produce a diff image highlighting changes."""
        try:
            doc1 = pymupdf.open(path1)
            doc2 = pymupdf.open(path2)
            max_pages = max(len(doc1), len(doc2))
            diff_images = []
            self._text_changes = []
            self._page_diffs = {}
            for i in range(max_pages):
                img1 = self._render_page(doc1, i)
                img2 = self._render_page(doc2, i)
                diff = self._compute_pixel_diff(img1, img2)
                diff_images.append(diff)
                self._page_diffs[i] = diff
                self._extract_text_changes(doc1, doc2, i)
            if diff_images:
                total_w = max(img.width for img in diff_images)
                total_h = sum(img.height for img in diff_images)
                combined = Image.new("RGB", (total_w, total_h), (255, 255, 255))
                y_offset = 0
                for img in diff_images:
                    combined.paste(img, (0, y_offset))
                    y_offset += img.height
                combined.save(output_path)
            doc1.close()
            doc2.close()
            return output_path
        except Exception as e:
            raise RuntimeError(f"Compare failed: {e}")

    def get_text_changes(self):
        """Return list of text differences found during last comparison."""
        return list(self._text_changes)

    def get_page_diff(self, page_num):
        """Return PIL Image diff for a specific page number."""
        return self._page_diffs.get(page_num)

    def _render_page(self, doc, page_num):
        """Render a page to PIL Image."""
        if page_num < len(doc):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return Image.new("RGB", (800, 600), (255, 255, 255))

    def _compute_pixel_diff(self, img1, img2):
        """Compute pixel-level diff between two images, highlighting differences in red."""
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)
        diff = ImageChops.difference(img1, img2)
        if diff.getbbox():
            gray = diff.convert("L")
            threshold = 30
            mask = gray.point(lambda p: 255 if p > threshold else 0)
            result = img1.copy()
            red_overlay = Image.new("RGB", img1.size, (255, 0, 0))
            result.paste(red_overlay, mask=mask)
            draw = ImageDraw.Draw(result)
            bbox = mask.getbbox()
            if bbox:
                draw.rectangle(bbox, outline=(255, 0, 0), width=2)
            return result
        return img1.copy()

    def _extract_text_changes(self, doc1, doc2, page_num):
        """Extract and record text differences for a given page."""
        text1 = ""
        text2 = ""
        if page_num < len(doc1):
            text1 = doc1[page_num].get_text("text")
        if page_num < len(doc2):
            text2 = doc2[page_num].get_text("text")
        words1 = text1.split()
        words2 = text2.split()
        for word in words2:
            if word not in words1:
                self._text_changes.append({
                    "page": page_num,
                    "type": "added",
                    "word": word
                })
        for word in words1:
            if word not in words2:
                self._text_changes.append({
                    "page": page_num,
                    "type": "removed",
                    "word": word
                })
