import re
import hashlib
from collections import defaultdict

import pymupdf


WCAG_REQUIREMENTS = {
    "1.1.1": "Non-text Content",
    "1.3.1": "Info and Relationships",
    "1.3.2": "Meaningful Sequence",
    "1.4.1": "Use of Color",
    "1.4.3": "Contrast (Minimum)",
    "2.4.1": "Bypass Blocks",
    "2.4.2": "Page Titled",
    "2.4.4": "Link Purpose (In Context)",
    "3.1.1": "Language of Page",
    "3.1.2": "Language of Parts",
    "4.1.2": "Name, Role, Value",
}


class AdvancedAccessibilityService:
    def __init__(self, editor):
        self.editor = editor

    def validate_pdfua(self, path, standard="ua-1"):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"is_compliant": False, "errors": [f"Cannot open: {e}"], "score": 0}

        issues = []
        score = 100
        self._check_tag_tree(doc, issues, standard)
        self._check_metadata(doc, issues)
        self._check_reading_order(doc, issues)
        self._check_alt_text(doc, issues, standard)
        self._check_annotations(doc, issues)
        self._check_form_fields(doc, issues)
        self._check_language(doc, issues)
        self._check_headings(doc, issues)
        self._check_tables(doc, issues)
        self._check_color_contrast(doc, issues)
        self._check_navigation(doc, issues)
        self._check_links(doc, issues)

        for issue in issues:
            severity = issue.get("severity", "medium")
            if severity == "high":
                score -= 10
            elif severity == "medium":
                score -= 5
            else:
                score -= 2
        score = max(0, score)

        doc.close()
        return {
            "is_compliant": len([i for i in issues if i["severity"] == "high"]) == 0,
            "issues": issues,
            "score": score,
            "standard": standard,
            "total_issues": len(issues),
        }

    def _check_tag_tree(self, doc, issues, standard):
        has_tags = False
        try:
            xref_count = doc.xref_length()
            for i in range(1, xref_count):
                try:
                    obj = doc.xref_object(i)
                    if "/MarkInfo" in obj and "/Marked" in obj:
                        has_tags = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

        if not has_tags:
            issues.append({
                "severity": "high",
                "rule": "6.1.13",
                "element": "tag_tree",
                "message": "Document is not tagged (missing MarkInfo/Marked=true)",
                "wcag": "1.3.1",
                "fix": "Add structure tags to the document",
            })

    def _check_metadata(self, doc, issues):
        meta = doc.metadata
        if not meta:
            issues.append({
                "severity": "high",
                "rule": "6.7.1",
                "element": "metadata",
                "message": "Document metadata is completely missing",
                "wcag": "2.4.2",
                "fix": "Add document metadata including title and author",
            })
            return
        if not meta.get("title"):
            issues.append({
                "severity": "high",
                "rule": "6.7.1",
                "element": "metadata",
                "message": "Document title is missing from metadata",
                "wcag": "2.4.2",
                "fix": "Set a meaningful document title",
            })
        if not meta.get("author"):
            issues.append({
                "severity": "medium",
                "rule": "6.7.2",
                "element": "metadata",
                "message": "Author is missing from metadata",
                "fix": "Add author information to metadata",
            })

    def _check_reading_order(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                if not blocks:
                    continue
                y_positions = []
                for block in blocks:
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    y_positions.append(bbox[1])
                if y_positions and y_positions != sorted(y_positions):
                    issues.append({
                        "severity": "medium",
                        "rule": "6.1.7",
                        "element": f"page_{page_num + 1}",
                        "message": f"Page {page_num + 1}: Text blocks may not follow logical reading order",
                        "wcag": "1.3.2",
                        "fix": "Verify and correct the reading order of text blocks",
                    })
            except Exception:
                pass

    def _check_alt_text(self, doc, issues, standard):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                images = page.get_images(full=True)
                for img_ref in images:
                    xref = img_ref[0]
                    has_alt = False
                    try:
                        for i in range(1, doc.xref_length()):
                            obj = doc.xref_object(i)
                            if f"/Img" in str(obj) or f"/XObject" in str(obj):
                                if "/Alt" in obj or "/ActualText" in obj:
                                    has_alt = True
                                    break
                    except Exception:
                        pass
                    if not has_alt:
                        issues.append({
                            "severity": "high",
                            "rule": "6.1.5",
                            "element": f"image_xref_{xref}_page_{page_num + 1}",
                            "message": f"Image on page {page_num + 1} (xref {xref}) missing alternative text",
                            "wcag": "1.1.1",
                            "fix": "Add descriptive alternative text for this image",
                        })
            except Exception:
                pass

    def _check_annotations(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                annots = page.annots()
                if annots:
                    for annot in annots:
                        annot_type = annot.type
                        if annot_type and annot_type[0] == "Link":
                            contents = annot.info.get("content", "")
                            if not contents:
                                issues.append({
                                    "severity": "medium",
                                    "rule": "6.1.6",
                                    "element": f"annotation_page_{page_num + 1}",
                                    "message": f"Link annotation on page {page_num + 1} has no accessible name",
                                    "wcag": "2.4.4",
                                    "fix": "Add descriptive content/alt text to link annotation",
                                })
            except Exception:
                pass

    def _check_form_fields(self, doc, issues):
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        field_name = widget.field_name
                        if not field_name:
                            issues.append({
                                "severity": "high",
                                "rule": "6.1.2",
                                "element": f"form_field_page_{page_num + 1}",
                                "message": f"Form field on page {page_num + 1} has no accessible name",
                                "wcag": "4.1.2",
                                "fix": "Set a descriptive name for this form field",
                            })
                        field_label = widget.field_label_string if hasattr(widget, 'field_label_string') else ""
                        if not field_label and field_name:
                            issues.append({
                                "severity": "medium",
                                "rule": "6.1.2",
                                "element": f"form_field_{field_name}",
                                "message": f"Form field '{field_name}' missing associated label",
                                "fix": "Add a label element associated with this form field",
                            })
        except Exception:
            pass

    def _check_language(self, doc, issues):
        try:
            meta = doc.metadata
            if meta:
                lang = meta.get("language", "")
                if not lang:
                    issues.append({
                        "severity": "high",
                        "rule": "7.1.1",
                        "element": "document",
                        "message": "No language specified in document metadata",
                        "wcag": "3.1.1",
                        "fix": "Set the document language in metadata (e.g., 'en-US')",
                    })
        except Exception:
            pass

    def _check_headings(self, doc, issues):
        heading_levels = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                font_size = span.get("size", 12)
                                text = span.get("text", "").strip()
                                if text and font_size >= 16:
                                    heading_levels.append((page_num, font_size, text[:50]))
            except Exception:
                pass

        prev_level = 0
        for page_num, font_size, text in heading_levels:
            if font_size >= 24:
                level = 1
            elif font_size >= 18:
                level = 2
            else:
                level = 3
            if prev_level > 0 and level > prev_level + 1:
                issues.append({
                    "severity": "medium",
                    "rule": "6.1.8",
                    "element": f"heading_page_{page_num + 1}",
                    "message": f"Heading level skipped: H{prev_level} to H{level} on page {page_num + 1} ('{text}')",
                    "wcag": "1.3.1",
                    "fix": f"Adjust heading level from H{level} to H{prev_level + 1}",
                })
            prev_level = level

    def _check_tables(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                has_table_structure = False
                for block in text_dict.get("blocks", []):
                    lines = block.get("lines", [])
                    if len(lines) > 3:
                        cells_per_line = []
                        for line in lines:
                            spans = line.get("spans", [])
                            cells_per_line.append(len(spans))
                        if len(set(cells_per_line)) > 1 and max(cells_per_line) > 1:
                            if not has_table_structure:
                                issues.append({
                                    "severity": "medium",
                                    "rule": "6.1.9",
                                    "element": f"table_page_{page_num + 1}",
                                    "message": f"Possible table on page {page_num + 1} may lack proper table structure tags",
                                    "fix": "Ensure tables have proper TH, TD, and THEAD/TBODY tags",
                                })
                                has_table_structure = True
            except Exception:
                pass

    def _check_color_contrast(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                color = span.get("color", 0)
                                bg_color = span.get("bgcolor")
                                font_size = span.get("size", 12)
                                if isinstance(color, int):
                                    r = (color >> 16) & 0xFF
                                    g = (color >> 8) & 0xFF
                                    b = color & 0xFF
                                    if r > 200 and g > 200 and b > 200:
                                        issues.append({
                                            "severity": "low",
                                            "rule": "6.1.10",
                                            "element": f"color_page_{page_num + 1}",
                                            "message": f"Light text color on page {page_num + 1} may have insufficient contrast",
                                            "wcag": "1.4.3",
                                            "fix": "Ensure text has at least 4.5:1 contrast ratio (3:1 for large text)",
                                        })
            except Exception:
                pass

    def _check_navigation(self, doc, issues):
        has_bookmarks = False
        try:
            toc = doc.get_toc()
            if toc and len(toc) > 0:
                has_bookmarks = True
        except Exception:
            pass
        if not has_bookmarks and len(doc) > 5:
            issues.append({
                "severity": "medium",
                "rule": "6.1.12",
                "element": "navigation",
                "message": "Document has no bookmarks/table of contents for navigation",
                "wcag": "2.4.1",
                "fix": "Add bookmarks or a table of contents for navigation",
            })

    def _check_links(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                links = page.get_links()
                for link in links:
                    if link.get("kind") == pymupdf.LINK_URI:
                        uri = link.get("uri", "")
                        if uri.startswith("javascript:"):
                            issues.append({
                                "severity": "high",
                                "rule": "6.1.11",
                                "element": f"link_page_{page_num + 1}",
                                "message": f"JavaScript link on page {page_num + 1} is not accessible",
                                "fix": "Replace JavaScript link with standard URI or form action",
                            })
            except Exception:
                pass

    def generate_alt_text(self, doc, page_num, image_index=0):
        try:
            page = doc[page_num]
            images = page.get_images(full=True)
            if image_index >= len(images):
                return "Image"
            img_ref = images[image_index]
            xref = img_ref[0]
            width = img_ref[2] if len(img_ref) > 2 else 0
            height = img_ref[3] if len(img_ref) > 3 else 0
            page_rect = page.rect
            img_area = (width * height) / (page_rect.width * page_rect.height) if page_rect.width * page_rect.height > 0 else 0
            if img_area > 0.3:
                return "Full-page image"
            elif img_area > 0.1:
                return "Large image"
            else:
                return "Image"
        except Exception:
            return "Image"

    def auto_remediate(self, path, output_path=None):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e), "fixes": []}

        fixes = []
        if not doc.metadata or not doc.metadata.get("title"):
            doc.set_metadata({"title": "Untitled Document"})
            fixes.append("Added document title to metadata")

        meta = doc.metadata or {}
        if not meta.get("language"):
            merged = {**meta, "language": "en-US"}
            doc.set_metadata(merged)
            fixes.append("Added default language (en-US)")

        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                images = page.get_images(full=True)
                for img_ref in images:
                    xref = img_ref[0]
                    fixes.append(f"Image on page {page_num + 1} needs manual alt text (xref {xref})")
            except Exception:
                pass

        if output_path:
            try:
                doc.save(output_path, garbage=4, deflate=True)
                doc.close()
                return {"success": True, "output_path": output_path, "fixes": fixes}
            except Exception as e:
                doc.close()
                return {"success": False, "error": str(e), "fixes": fixes}
        else:
            doc.close()
            return {"success": True, "fixes": fixes}

    def generate_accessibility_report(self, path, standard="ua-1"):
        validation = self.validate_pdfua(path, standard)
        report_lines = [
            "=" * 60,
            "PDF/UA ACCESSIBILITY REPORT",
            "=" * 60,
            f"File: {path}",
            f"Standard: PDF/{standard.upper()}",
            f"Score: {validation['score']}/100",
            f"Status: {'PASS' if validation['is_compliant'] else 'FAIL'}",
            f"Total Issues: {validation['total_issues']}",
            "-" * 60,
        ]
        high_issues = [i for i in validation["issues"] if i["severity"] == "high"]
        med_issues = [i for i in validation["issues"] if i["severity"] == "medium"]
        low_issues = [i for i in validation["issues"] if i["severity"] == "low"]

        if high_issues:
            report_lines.append(f"\nHIGH SEVERITY ({len(high_issues)}):")
            for i, issue in enumerate(high_issues, 1):
                wcag_ref = f" [WCAG {issue['wcag']}]" if issue.get("wcag") else ""
                report_lines.append(f"  {i}. {issue['message']}{wcag_ref}")
                if issue.get("fix"):
                    report_lines.append(f"     Fix: {issue['fix']}")
        if med_issues:
            report_lines.append(f"\nMEDIUM SEVERITY ({len(med_issues)}):")
            for i, issue in enumerate(med_issues, 1):
                wcag_ref = f" [WCAG {issue['wcag']}]" if issue.get("wcag") else ""
                report_lines.append(f"  {i}. {issue['message']}{wcag_ref}")
                if issue.get("fix"):
                    report_lines.append(f"     Fix: {issue['fix']}")
        if low_issues:
            report_lines.append(f"\nLOW SEVERITY ({len(low_issues)}):")
            for i, issue in enumerate(low_issues, 1):
                report_lines.append(f"  {i}. {issue['message']}")

        if not validation["issues"]:
            report_lines.append("\nNo accessibility issues found.")
        report_lines.append("\n" + "=" * 60)
        return "\n".join(report_lines)

    def screen_reader_test(self, path):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e), "readable": False}

        content_order = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                page_content = []
                for block in text_dict.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            line_text = ""
                            for span in line.get("spans", []):
                                line_text += span.get("text", "")
                            if line_text.strip():
                                page_content.append(line_text.strip())
                content_order.append({
                    "page": page_num + 1,
                    "content": page_content,
                    "has_content": len(page_content) > 0,
                })
            except Exception:
                content_order.append({"page": page_num + 1, "content": [], "has_content": False})

        doc.close()
        total_pages = len(content_order)
        pages_with_content = len([p for p in content_order if p["has_content"]])
        return {
            "success": True,
            "readable": pages_with_content > 0,
            "total_pages": total_pages,
            "pages_with_content": pages_with_content,
            "pages_empty": total_pages - pages_with_content,
            "content_order": content_order,
        }

    def batch_validate(self, paths, standard="ua-1"):
        results = {}
        for path in paths:
            try:
                results[path] = self.validate_pdfua(path, standard)
            except Exception as e:
                results[path] = {"is_compliant": False, "error": str(e), "score": 0}
        return results
