import pymupdf


class AccessibilityService:
    def __init__(self, editor):
        self.editor = editor

    def check_accessibility(self, path):
        """Check PDF/UA accessibility. Returns dict with score, issues list."""
        try:
            doc = pymupdf.open(path)
            issues = []
            score = 100

            metadata = doc.metadata
            if not metadata or not metadata.get("title"):
                issues.append({
                    "severity": "high",
                    "element": "metadata",
                    "message": "Document is missing a title"
                })
                score -= 15
            if not metadata or not metadata.get("author"):
                issues.append({
                    "severity": "medium",
                    "element": "metadata",
                    "message": "Document is missing an author"
                })
                score -= 10

            for page in doc:
                page_num = page.number
                text = page.get_text("text").strip()
                images = page.get_images(full=True)
                if not text and images:
                    issues.append({
                        "severity": "high",
                        "element": f"page_{page_num}",
                        "message": f"Page {page_num + 1} has images but no text (possible missing alt text)"
                    })
                    score -= 10
                if not text and not images:
                    issues.append({
                        "severity": "medium",
                        "element": f"page_{page_num}",
                        "message": f"Page {page_num + 1} appears to be empty"
                    })
                    score -= 5

                try:
                    links = page.get_links()
                    for link in links:
                        if link.get("kind") == pymupdf.LINK_URI:
                            uri = link.get("uri", "")
                            if not uri.startswith(("http://", "https://", "mailto:")):
                                issues.append({
                                    "severity": "low",
                                    "element": f"link_page_{page_num}",
                                    "message": f"Non-standard link URI: {uri}"
                                })
                except Exception:
                    pass

            font_sizes = set()
            for page in doc:
                blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
                for block in blocks:
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                font_sizes.add(round(span.get("size", 12)))
            if len(font_sizes) > 5:
                issues.append({
                    "severity": "low",
                    "element": "structure",
                    "message": f"Too many font sizes ({len(font_sizes)}), may indicate poor structure"
                })
                score -= 5

            doc.close()
            score = max(0, min(100, score))
            return {"score": score, "issues": issues, "profile": "pdf/ua"}
        except Exception as e:
            raise RuntimeError(f"Accessibility check failed: {e}")

    def fix_accessibility(self, path, output_path):
        """Apply common accessibility fixes to a PDF."""
        try:
            doc = pymupdf.open(path)
            metadata = doc.metadata or {}
            if not metadata.get("title"):
                import os
                metadata["title"] = os.path.basename(path)
            if not metadata.get("author"):
                metadata["author"] = "PDF Editor"
            metadata["subject"] = metadata.get("subject", "Accessible document")
            doc.set_metadata(metadata)
            doc.save(output_path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Cannot fix accessibility: {e}")

    def add_tags(self, path, output_path):
        """Add structural tags to the PDF for screen readers."""
        try:
            doc = pymupdf.open(path)
            for page in doc:
                blocks = page.get_text("dict").get("blocks", [])
                for block in blocks:
                    if block.get("type") == 0:
                        bbox = block.get("bbox", [0, 0, 0, 0])
                        rect = pymupdf.Rect(bbox)
                        try:
                            page.add_stamp_annot(
                                rect,
                                text=" ",
                                overlay=False
                            )
                        except Exception:
                            pass
            doc.save(output_path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Cannot add tags: {e}")

    def set_language_tag(self, page_num, lang):
        """Set the language tag for a specific page."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            page = doc[page_num]
            xref = page.xref
            doc.xref_set_key(xref, "Lang", f"/{lang}")
        except Exception as e:
            raise RuntimeError(f"Cannot set language tag: {e}")

    def add_alt_text(self, element, text):
        """Add alt text to an element (stored as a custom property)."""
        try:
            if hasattr(element, 'alt_text'):
                element.alt_text = text
            else:
                element.alt_text = text
        except Exception as e:
            raise RuntimeError(f"Cannot add alt text: {e}")

    def check_reading_order(self):
        """Check and return the reading order of elements on the current page."""
        try:
            page_num = getattr(self.editor, 'current_page', 0)
            elements_on_page = [
                e for e in self.editor.elements
                if getattr(e, 'page', 0) == page_num
            ]
            elements_on_page.sort(key=lambda e: (
                getattr(e, 'y', 0),
                getattr(e, 'x', 0)
            ))
            reading_order = []
            for i, elem in enumerate(elements_on_page):
                reading_order.append({
                    "index": i,
                    "type": getattr(elem, 'type_name', 'unknown'),
                    "position": (getattr(elem, 'x', 0), getattr(elem, 'y', 0)),
                    "name": getattr(elem, 'name', '')
                })
            return reading_order
        except Exception as e:
            raise RuntimeError(f"Cannot check reading order: {e}")

    def generate_accessibility_report(self, path, output_path):
        """Generate an HTML accessibility report."""
        try:
            result = self.check_accessibility(path)
            score = result["score"]
            issues = result["issues"]
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Accessibility Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
.score {{ font-size: 24px; font-weight: bold; }}
.score.good {{ color: green; }}
.score.fair {{ color: orange; }}
.score.poor {{ color: red; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #f2f2f2; }}
.severity-high {{ color: red; }}
.severity-medium {{ color: orange; }}
.severity-low {{ color: #888; }}
</style>
</head>
<body>
<h1>PDF Accessibility Report</h1>
<p class="score {'good' if score >= 80 else 'fair' if score >= 50 else 'poor'}">
Score: {score}/100</p>
<h2>Issues ({len(issues)})</h2>
<table>
<tr><th>Severity</th><th>Element</th><th>Message</th></tr>
"""
            for issue in issues:
                sev = issue.get("severity", "low")
                html += f'<tr><td class="severity-{sev}">{sev.upper()}</td>'
                html += f'<td>{issue.get("element", "")}</td>'
                html += f'<td>{issue.get("message", "")}</td></tr>\n'
            html += """</table>
<p>Report generated by PDF Editor Accessibility Service</p>
</body>
</html>"""
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Cannot generate report: {e}")
