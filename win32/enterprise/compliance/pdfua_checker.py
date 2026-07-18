import re
from datetime import datetime, timezone

import pymupdf


UA_CHECKS = {
    "tag_structure": {"description": "Document must have a tagged structure", "severity": "critical", "wcag": "1.3.1"},
    "document_title": {"description": "Document must have a title in metadata", "severity": "critical", "wcag": "2.4.2"},
    "language": {"description": "Document must specify its language", "severity": "critical", "wcag": "3.1.1"},
    "alt_text": {"description": "Images must have alternative text", "severity": "high", "wcag": "1.1.1"},
    "reading_order": {"description": "Content must follow logical reading order", "severity": "high", "wcag": "1.3.2"},
    "form_labels": {"description": "Form fields must have accessible labels", "severity": "high", "wcag": "4.1.2"},
    "navigation": {"description": "Document must have navigation aids", "severity": "medium", "wcag": "2.4.1"},
    "heading_hierarchy": {"description": "Headings must follow proper hierarchy", "severity": "medium", "wcag": "1.3.1"},
    "link_purpose": {"description": "Links must have descriptive text", "severity": "medium", "wcag": "2.4.4"},
    "table_structure": {"description": "Tables must have proper header structure", "severity": "medium", "wcag": "1.3.1"},
    "color_contrast": {"description": "Text must meet minimum contrast ratio", "severity": "medium", "wcag": "1.4.3"},
    "annotation_accessibility": {"description": "Annotations must be accessible", "severity": "medium", "wcag": "1.3.1"},
    "meaningful_sequences": {"description": "Reading order must be meaningful", "severity": "high", "wcag": "1.3.2"},
}


class PdfUAChecker:
    def __init__(self):
        self._last_check = None

    def check(self, path, standard="ua-1"):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"compliant": False, "issues": [{"code": "OPEN_FAILED", "message": str(e), "severity": "critical"}], "score": 0}

        issues = []
        score = 100
        self._check_tag_tree(doc, issues)
        self._check_metadata(doc, issues)
        self._check_language(doc, issues)
        self._check_images_alt_text(doc, issues, standard)
        self._check_reading_order(doc, issues)
        self._check_form_fields(doc, issues)
        self._check_headings(doc, issues)
        self._check_tables(doc, issues)
        self._check_links(doc, issues)
        self._check_color_contrast(doc, issues)
        self._check_annotations(doc, issues)
        self._check_navigation(doc, issues)
        self._check_meaningful_sequences(doc, issues)

        for issue in issues:
            sev = issue.get("severity", "medium")
            if sev == "critical":
                score -= 15
            elif sev == "high":
                score -= 10
            elif sev == "medium":
                score -= 5
            else:
                score -= 2
        score = max(0, min(100, score))

        doc.close()
        result = {
            "compliant": len([i for i in issues if i["severity"] in ("critical", "high")]) == 0,
            "standard": standard,
            "score": score,
            "issues": issues,
            "issue_count": len(issues),
            "critical_count": len([i for i in issues if i["severity"] == "critical"]),
            "high_count": len([i for i in issues if i["severity"] == "high"]),
            "medium_count": len([i for i in issues if i["severity"] == "medium"]),
            "low_count": len([i for i in issues if i["severity"] == "low"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._last_check = result
        return result

    def _add_issue(self, issues, check_id, message, extra=None):
        check_info = UA_CHECKS.get(check_id, {})
        issue = {
            "code": check_id,
            "message": message,
            "severity": check_info.get("severity", "medium"),
            "wcag": check_info.get("wcag", ""),
            "description": check_info.get("description", ""),
            "remediation": self._get_remediation(check_id),
        }
        if extra:
            issue.update(extra)
        issues.append(issue)

    def _get_remediation(self, check_id):
        remediations = {
            "tag_structure": "Use a PDF authoring tool that generates tagged PDF, or run the auto-tag utility",
            "document_title": "Set the document title in Properties > Description > Title",
            "language": "Set the document language in Properties > Advanced > Language",
            "alt_text": "Add alt text to each image via the Tags panel or accessibility checker",
            "reading_order": "Use the Content panel or Reading Order tool to reorder content",
            "form_labels": "Associate each form field with a label using the tooltip or /TU entry",
            "navigation": "Add bookmarks or a table of contents for document navigation",
            "heading_hierarchy": "Ensure heading levels descend logically (H1 → H2 → H3, no skips)",
            "link_purpose": "Add descriptive text to link annotations or use meaningful link text",
            "table_structure": "Tag tables with <Table>, <TR>, <TH>, and <TD> elements",
            "color_contrast": "Ensure text has at least 4.5:1 contrast ratio against background",
            "annotation_accessibility": "Add content/description to all annotation objects",
            "meaningful_sequences": "Verify that the tag tree order matches the visual reading order",
        }
        return remediations.get(check_id, "Consult WCAG 2.1 guidelines for remediation steps")

    def _check_tag_tree(self, doc, issues):
        has_mark_info = False
        try:
            for i in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(i)
                    if "/MarkInfo" in obj:
                        has_mark_info = True
                        if "/Marked" in obj and "/true" in obj.lower():
                            return
                        break
                except Exception:
                    continue
        except Exception:
            pass
        if not has_mark_info:
            self._add_issue(issues, "tag_structure", "Document is not tagged (missing MarkInfo)")
        else:
            self._add_issue(issues, "tag_structure", "MarkInfo present but /Marked is not set to true")

    def _check_metadata(self, doc, issues):
        meta = doc.metadata
        if not meta:
            self._add_issue(issues, "document_title", "Document metadata is completely missing")
            return
        if not meta.get("title"):
            self._add_issue(issues, "document_title", "Document title is missing from metadata")
        if not meta.get("author"):
            issues.append({
                "code": "author_missing",
                "message": "Author missing from metadata",
                "severity": "low",
                "remediation": "Add author information to document properties",
            })

    def _check_language(self, doc, issues):
        try:
            meta = doc.metadata or {}
            lang = meta.get("language", "")
            if not lang:
                self._add_issue(issues, "language", "No document language specified in metadata")
        except Exception:
            self._add_issue(issues, "language", "Cannot determine document language")

    def _check_images_alt_text(self, doc, issues, standard):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                images = page.get_images(full=True)
                for img_ref in images:
                    xref = img_ref[0]
                    has_alt = False
                    try:
                        for i in range(1, min(doc.xref_length(), 5000)):
                            try:
                                obj = doc.xref_object(i)
                                if "/Alt" in obj and str(xref) in obj:
                                    has_alt = True
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass
                    if not has_alt:
                        self._add_issue(issues, "alt_text",
                                        f"Image on page {page_num + 1} (xref {xref}) missing alt text",
                                        extra={"page": page_num + 1, "xref": xref})
            except Exception:
                pass

    def _check_reading_order(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                if len(blocks) < 2:
                    continue
                prev_y = -1
                out_of_order = False
                for block in sorted(blocks, key=lambda b: b.get("bbox", (0, 0, 0, 0))[1]):
                    y = block.get("bbox", (0, 0, 0, 0))[1]
                    if y < prev_y - 10:
                        out_of_order = True
                        break
                    prev_y = y
                if out_of_order:
                    self._add_issue(issues, "reading_order",
                                    f"Page {page_num + 1}: Content blocks may have incorrect reading order",
                                    extra={"page": page_num + 1})
            except Exception:
                pass

    def _check_form_fields(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        name = widget.field_name
                        if not name:
                            self._add_issue(issues, "form_labels",
                                            f"Form field on page {page_num + 1} has no accessible name",
                                            extra={"page": page_num + 1})
            except Exception:
                pass

    def _check_headings(self, doc, issues):
        heading_levels = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = span.get("size", 12)
                            text = span.get("text", "").strip()
                            if text and size >= 16:
                                level = 1 if size >= 24 else (2 if size >= 18 else 3)
                                heading_levels.append((page_num, level, text[:40]))
            except Exception:
                pass

        prev_level = 0
        for pg, level, text in heading_levels:
            if prev_level > 0 and level > prev_level + 1:
                self._add_issue(issues, "heading_hierarchy",
                                f"Heading level skipped: H{prev_level} → H{level} on page {pg + 1}",
                                extra={"page": pg + 1, "from_level": prev_level, "to_level": level})
            prev_level = level

    def _check_tables(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    lines = block.get("lines", [])
                    if len(lines) < 2:
                        continue
                    cell_counts = [len(line.get("spans", [])) for line in lines]
                    if len(set(cell_counts)) > 1 and max(cell_counts) > 2:
                        self._add_issue(issues, "table_structure",
                                        f"Possible table on page {page_num + 1} may lack proper tagging",
                                        extra={"page": page_num + 1})
                        break
            except Exception:
                pass

    def _check_links(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                links = page.get_links()
                for link in links:
                    if link.get("kind") == pymupdf.LINK_URI:
                        uri = link.get("uri", "")
                        if uri.startswith("javascript:"):
                            self._add_issue(issues, "link_purpose",
                                            f"JavaScript link on page {page_num + 1}",
                                            extra={"page": page_num + 1})
            except Exception:
                pass

    def _check_color_contrast(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            color = span.get("color", 0)
                            if isinstance(color, int):
                                r = (color >> 16) & 0xFF
                                g = (color >> 8) & 0xFF
                                b = color & 0xFF
                                brightness = (0.299 * r + 0.587 * g + 0.114 * b)
                                if brightness > 220:
                                    self._add_issue(issues, "color_contrast",
                                                    f"Potentially low-contrast text on page {page_num + 1}",
                                                    extra={"page": page_num + 1, "brightness": brightness})
            except Exception:
                pass

    def _check_annotations(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                annots = page.annots()
                if annots:
                    for annot in annots:
                        info = annot.info
                        content = info.get("content", "") if info else ""
                        if not content and annot.type and annot.type[0] in ("FreeText", "Text", "Line"):
                            self._add_issue(issues, "annotation_accessibility",
                                            f"Annotation on page {page_num + 1} lacks accessible description",
                                            extra={"page": page_num + 1})
            except Exception:
                pass

    def _check_navigation(self, doc, issues):
        try:
            toc = doc.get_toc()
            if not toc or len(toc) == 0:
                if len(doc) > 5:
                    self._add_issue(issues, "navigation",
                                    "Document has no bookmarks/table of contents")
        except Exception:
            pass

    def _check_meaningful_sequences(self, doc, issues):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                if len(blocks) < 2:
                    continue
                bboxes = [b.get("bbox", (0, 0, 0, 0)) for b in blocks]
                visual_order = sorted(range(len(bboxes)), key=lambda i: (bboxes[i][1], bboxes[i][0]))
                reverse_count = 0
                for i in range(1, len(visual_order)):
                    if bboxes[visual_order[i]][1] < bboxes[visual_order[i - 1]][1] - 5:
                        reverse_count += 1
                if reverse_count > 0:
                    self._add_issue(issues, "meaningful_sequences",
                                    f"Page {page_num + 1}: {reverse_count} sequence reversal(s) detected",
                                    extra={"page": page_num + 1})
            except Exception:
                pass

    def generate_report(self, path, standard="ua-1"):
        check = self.check(path, standard)
        lines = [
            "=" * 60,
            "PDF/UA COMPLIANCE REPORT",
            "=" * 60,
            f"Document: {path}",
            f"Standard: PDF/{standard.upper()}",
            f"Score: {check['score']}/100",
            f"Result: {'COMPLIANT' if check['compliant'] else 'NON-COMPLIANT'}",
            f"Issues: {check['issue_count']} "
            f"(Critical: {check['critical_count']}, High: {check['high_count']}, "
            f"Medium: {check['medium_count']}, Low: {check['low_count']})",
            f"Generated: {check['timestamp']}",
            "-" * 60,
        ]
        for severity in ("critical", "high", "medium", "low"):
            sev_issues = [i for i in check["issues"] if i["severity"] == severity]
            if sev_issues:
                lines.append(f"\n{severity.upper()} ISSUES ({len(sev_issues)}):")
                for idx, issue in enumerate(sev_issues, 1):
                    wcag = f" [WCAG {issue['wcag']}]" if issue.get("wcag") else ""
                    lines.append(f"  {idx}. [{issue['code']}] {issue['message']}{wcag}")
                    if issue.get("remediation"):
                        lines.append(f"     Remediation: {issue['remediation']}")
        if not check["issues"]:
            lines.append("\nNo issues found. Document appears to be PDF/UA compliant.")
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
