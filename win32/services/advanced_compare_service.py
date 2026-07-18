import os
import hashlib
import difflib
from datetime import datetime

import pymupdf


class AdvancedCompareService:
    def __init__(self, editor):
        self.editor = editor

    def compare_documents(self, path_a, path_b, mode="visual"):
        try:
            doc_a = pymupdf.open(path_a)
            doc_b = pymupdf.open(path_b)
        except Exception as e:
            return {"success": False, "error": str(e)}

        if mode == "visual":
            result = self._visual_diff(doc_a, doc_b)
        elif mode == "text":
            result = self._text_diff(doc_a, doc_b)
        elif mode == "structure":
            result = self._structure_diff(doc_a, doc_b)
        elif mode == "image":
            result = self._image_diff(doc_a, doc_b)
        else:
            result = self._visual_diff(doc_a, doc_b)

        doc_a.close()
        doc_b.close()
        result["success"] = True
        result["mode"] = mode
        result["timestamp"] = datetime.now().isoformat()
        return result

    def _visual_diff(self, doc_a, doc_b):
        max_pages = max(len(doc_a), len(doc_b))
        min_pages = min(len(doc_a), len(doc_b))
        page_diffs = []
        identical_count = 0

        for page_idx in range(max_pages):
            page_info = {"page": page_idx + 1, "changes": []}
            if page_idx >= len(doc_a):
                page_info["changes"].append({"type": "added", "description": "Page exists only in document B"})
                page_diffs.append(page_info)
                continue
            if page_idx >= len(doc_b):
                page_info["changes"].append({"type": "deleted", "description": "Page exists only in document A"})
                page_diffs.append(page_info)
                continue

            pix_a = doc_a[page_idx].get_pixmap(matrix=pymupdf.Matrix(2, 2))
            pix_b = doc_b[page_idx].get_pixmap(matrix=pymupdf.Matrix(2, 2))

            if pix_a.width == pix_b.width and pix_a.height == pix_b.height:
                samples_a = pix_a.samples
                samples_b = pix_b.samples
                if samples_a == samples_b:
                    identical_count += 1
                    continue

                diff_pixels = 0
                total_pixels = pix_a.width * pix_a.height
                stride_a = pix_a.stride
                stride_b = pix_b.stride
                for y in range(pix_a.height):
                    for x in range(pix_a.width):
                        off_a = y * stride_a + x * 3
                        off_b = y * stride_b + x * 3
                        if off_a + 2 < len(samples_a) and off_b + 2 < len(samples_b):
                            if (samples_a[off_a] != samples_b[off_b] or
                                    samples_a[off_a + 1] != samples_b[off_b + 1] or
                                    samples_a[off_a + 2] != samples_b[off_b + 2]):
                                diff_pixels += 1

                if diff_pixels > 0:
                    pct_changed = (diff_pixels / total_pixels) * 100
                    page_info["changes"].append({
                        "type": "modified",
                        "description": f"{pct_changed:.1f}% of pixels differ",
                        "diff_pixels": diff_pixels,
                        "total_pixels": total_pixels,
                    })
                else:
                    identical_count += 1
            else:
                page_info["changes"].append({
                    "type": "modified",
                    "description": f"Page dimensions differ: A={pix_a.width}x{pix_a.height} B={pix_b.width}x{pix_b.height}",
                })
            if page_info["changes"]:
                page_diffs.append(page_info)

        return {
            "total_pages_a": len(doc_a),
            "total_pages_b": len(doc_b),
            "identical_pages": identical_count,
            "pages_with_changes": len(page_diffs),
            "page_diffs": page_diffs,
            "summary": f"{identical_count}/{max_pages} pages identical",
        }

    def _text_diff(self, doc_a, doc_b):
        texts_a = []
        texts_b = []
        for page in doc_a:
            texts_a.append(page.get_text("text"))
        for page in doc_b:
            texts_b.append(page.get_text("text"))

        full_text_a = "\n".join(texts_a)
        full_text_b = "\n".join(texts_b)

        lines_a = full_text_a.splitlines(keepends=True)
        lines_b = full_text_b.splitlines(keepends=True)
        differ = difflib.unified_diff(lines_a, lines_b, fromfile="Document A", tofile="Document B", lineterm="")
        diff_lines = list(differ)

        added = [l for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
        deleted = [l for l in diff_lines if l.startswith("-") and not l.startswith("---")]
        modified = [l for l in diff_lines if l.startswith("@")]

        page_diffs = []
        max_pages = max(len(doc_a), len(doc_b))
        for pg in range(max_pages):
            text_a = texts_a[pg] if pg < len(texts_a) else ""
            text_b = texts_b[pg] if pg < len(texts_b) else ""
            if text_a == text_b:
                continue
            sm = difflib.SequenceMatcher(None, text_a.splitlines(), text_b.splitlines())
            ops = sm.get_opcodes()
            changes = []
            for tag, i1, i2, j1, j2 in ops:
                if tag != "equal":
                    changes.append({
                        "type": tag,
                        "from_lines": (i1 + 1, i2),
                        "to_lines": (j1 + 1, j2),
                    })
            if changes:
                page_diffs.append({"page": pg + 1, "changes": changes})

        return {
            "total_lines_added": len(added),
            "total_lines_deleted": len(deleted),
            "total_hunks": len(modified),
            "page_diffs": page_diffs,
            "diff_text": "\n".join(diff_lines),
            "summary": f"{len(added)} lines added, {len(deleted)} lines deleted",
        }

    def _structure_diff(self, doc_a, doc_b):
        struct_a = self._extract_structure(doc_a)
        struct_b = self._extract_structure(doc_b)

        diffs = []
        key_a = set(struct_a.keys())
        key_b = set(struct_b.keys())

        for key in key_a | key_b:
            val_a = struct_a.get(key)
            val_b = struct_b.get(key)
            if val_a != val_b:
                diffs.append({
                    "property": key,
                    "value_a": val_a,
                    "value_b": val_b,
                })

        bookmark_diffs = self._compare_bookmarks(
            doc_a.get_toc() if hasattr(doc_a, 'get_toc') else [],
            doc_b.get_toc() if hasattr(doc_b, 'get_toc') else [],
        )

        return {
            "metadata_diffs": diffs,
            "bookmark_diffs": bookmark_diffs,
            "pages_a": len(doc_a),
            "pages_b": len(doc_b),
            "summary": f"{len(diffs)} metadata differences, {len(bookmark_diffs)} bookmark differences",
        }

    def _extract_structure(self, doc):
        structure = {}
        try:
            meta = doc.metadata or {}
            structure["title"] = meta.get("title", "")
            structure["author"] = meta.get("author", "")
            structure["page_count"] = len(doc)
            structure["encrypted"] = doc.needs_pass()
            structure["has_toc"] = len(doc.get_toc()) > 0 if hasattr(doc, 'get_toc') else False
            for pg in range(len(doc)):
                page = doc[pg]
                structure[f"page_{pg}_width"] = page.rect.width
                structure[f"page_{pg}_height"] = page.rect.height
                try:
                    images = page.get_images()
                    structure[f"page_{pg}_images"] = len(images)
                except Exception:
                    structure[f"page_{pg}_images"] = 0
                try:
                    links = page.get_links()
                    structure[f"page_{pg}_links"] = len(links)
                except Exception:
                    structure[f"page_{pg}_links"] = 0
        except Exception:
            pass
        return structure

    def _compare_bookmarks(self, toc_a, toc_b):
        diffs = []
        titles_a = set(t[1] for t in toc_a)
        titles_b = set(t[1] for t in toc_b)
        for title in titles_a - titles_b:
            diffs.append({"type": "removed", "title": title})
        for title in titles_b - titles_a:
            diffs.append({"type": "added", "title": title})
        for t_a in toc_a:
            for t_b in toc_b:
                if t_a[1] == t_b[1] and t_a[2] != t_b[2]:
                    diffs.append({"type": "moved", "title": t_a[1], "page_a": t_a[2], "page_b": t_b[2]})
        return diffs

    def _image_diff(self, doc_a, doc_b):
        max_pages = max(len(doc_a), len(doc_b))
        image_diffs = []

        for pg in range(max_pages):
            if pg >= len(doc_a) or pg >= len(doc_b):
                image_diffs.append({"page": pg + 1, "status": "missing_in_one"})
                continue
            images_a = doc_a[pg].get_images(full=True)
            images_b = doc_b[pg].get_images(full=True)

            hashes_a = set()
            hashes_b = set()
            for img in images_a:
                try:
                    xref = img[0]
                    img_data = doc_a.extract_image(xref)
                    if img_data and "image" in img_data:
                        h = hashlib.md5(img_data["image"]).hexdigest()
                        hashes_a.add(h)
                except Exception:
                    pass
            for img in images_b:
                try:
                    xref = img[0]
                    img_data = doc_b.extract_image(xref)
                    if img_data and "image" in img_data:
                        h = hashlib.md5(img_data["image"]).hexdigest()
                        hashes_b.add(h)
                except Exception:
                    pass

            added_imgs = hashes_b - hashes_a
            removed_imgs = hashes_a - hashes_b
            if added_imgs or removed_imgs:
                image_diffs.append({
                    "page": pg + 1,
                    "images_added": len(added_imgs),
                    "images_removed": len(removed_imgs),
                    "total_a": len(hashes_a),
                    "total_b": len(hashes_b),
                })

        return {
            "pages_with_image_changes": len(image_diffs),
            "image_diffs": image_diffs,
            "summary": f"{len(image_diffs)} pages have image differences",
        }

    def side_by_side_report(self, path_a, path_b):
        result = self.compare_documents(path_a, path_b, mode="text")
        report = [
            "=" * 70,
            "SIDE-BY-SIDE COMPARISON REPORT",
            "=" * 70,
            f"Document A: {os.path.basename(path_a)}",
            f"Document B: {os.path.basename(path_b)}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 70,
            f"Summary: {result.get('summary', 'N/A')}",
            "",
        ]
        for pdiff in result.get("page_diffs", []):
            report.append(f"--- Page {pdiff['page']} ---")
            for change in pdiff.get("changes", []):
                report.append(f"  {change['type']}: lines {change.get('from_lines', 'N/A')} -> {change.get('to_lines', 'N/A')}")
        report.append("=" * 70)
        return "\n".join(report)

    def generate_diff_pdf(self, path_a, path_b, output_path):
        try:
            result = self.compare_documents(path_a, path_b, mode="text")
            doc = pymupdf.open()
            page = doc.new_page(width=595, height=842)
            writer = pymupdf.TextWriter(page.rect)
            font = pymupdf.Font("courier")
            y = 30
            lines = result.get("diff_text", "").split("\n")
            for line in lines[:200]:
                if y > 800:
                    page = doc.new_page(width=595, height=842)
                    y = 30
                text = line[:100]
                if text.startswith("+"):
                    color = (0, 0.5, 0)
                elif text.startswith("-"):
                    color = (0.8, 0, 0)
                elif text.startswith("@"):
                    color = (0, 0, 0.8)
                else:
                    color = (0.3, 0.3, 0.3)
                try:
                    writer.append(pymupdf.Point(20, y), text, font=font, fontsize=8)
                except Exception:
                    pass
                y += 12
            writer.write_text(page)
            doc.save(output_path)
            doc.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
