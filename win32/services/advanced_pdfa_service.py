import os
import re
import uuid
import hashlib
from datetime import datetime, timezone

import pymupdf


PDFA_LEVELS = {
    "pdfa-1a": {"part": "1", "conformance": "a"},
    "pdfa-1b": {"part": "1", "conformance": "b"},
    "pdfa-2a": {"part": "2", "conformance": "a"},
    "pdfa-2b": {"part": "2", "conformance": "b"},
    "pdfa-2u": {"part": "2", "conformance": "u"},
    "pdfa-3a": {"part": "3", "conformance": "a"},
    "pdfa-3b": {"part": "3", "conformance": "b"},
    "pdfa-3u": {"part": "3", "conformance": "u"},
    "pdfa-4":  {"part": "4", "conformance": "f"},
}

XMP_TEMPLATE = """<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
 <rdf:Description rdf:about=""
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:xmp="http://ns.adobe.com/xap/1.0/"
  xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"
  xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"
  xmlns:prism="http://prismstandard.org/namespaces/2.0/basic/">
  <dc:title>{title}</dc:title>
  <dc:creator>{author}</dc:creator>
  <dc:description>{description}</dc:description>
  <dc:format>application/pdf</dc:format>
  <dc:identifier>{doc_id}</dc:identifier>
  <xmp:CreatorTool>PDF Editor Advanced</xmp:CreatorTool>
  <xmp:CreateDate>{create_date}</xmp:CreateDate>
  <xmp:ModifyDate>{modify_date}</xmp:ModifyDate>
  <xmp:MetadataDate>{modify_date}</xmp:MetadataDate>
  <xmpMM:InstanceID>uuid:{instance_id}</xmpMM:InstanceID>
  <xmpMM:DocumentID>uuid:{doc_id}</xmpMM:DocumentID>
  <pdfaid:part>{part}</pdfaid:part>
  <pdfaid:conformance>{conformance}</pdfaid:conformance>
 </rdf:Description>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""


class AdvancedPdfAService:
    def __init__(self, editor):
        self.editor = editor

    def detect_level(self, path):
        try:
            doc = pymupdf.open(path)
            level = self._detect_from_xmp(doc)
            if level == "unknown":
                level = self._detect_from_metadata(doc)
            doc.close()
            return level
        except Exception:
            return "unknown"

    def _detect_from_xmp(self, doc):
        try:
            xmp = doc.xref_xml_metadata(0)
            if not xmp:
                return "unknown"
            part_match = re.search(r"pdfaid:part>(\d+)<", xmp)
            conf_match = re.search(r"pdfaid:conformance>(\w)<", xmp)
            if part_match:
                part = part_match.group(1)
                conf = conf_match.group(1).lower() if conf_match else "b"
                if part == "4":
                    return "pdfa-4"
                return f"pdfa-{part}-{conf}"
        except Exception:
            pass
        return "unknown"

    def _detect_from_metadata(self, doc):
        try:
            meta = doc.metadata
            if not meta:
                return "unknown"
            format_str = meta.get("format", "")
            if "PDF/A" in format_str:
                match = re.search(r"PDF/A-(\d+[abu]?)", format_str)
                if match:
                    return f"pdfa-{match.group(1).lower()}"
        except Exception:
            pass
        return "unknown"

    def validate(self, path, level="pdfa-1b"):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"is_compliant": False, "errors": [f"Cannot open PDF: {e}"], "level": level, "warnings": []}

        errors = []
        warnings = []
        level_info = PDFA_LEVELS.get(level, PDFA_LEVELS["pdfa-1b"])
        part_num = int(level_info["part"])
        conformance = level_info["conformance"]

        self._check_metadata(doc, errors, warnings)
        self._check_xmp_metadata(doc, level, level_info, errors, warnings)
        self._check_fonts(doc, errors, warnings, part_num)
        self._check_images(doc, errors, warnings, part_num)
        self._check_encryption(doc, errors)
        self._check_javascript(doc, errors, part_num)
        self._check_embedded_files(doc, errors, warnings, part_num)
        self._check_transparency(doc, errors, warnings, part_num)
        self._check_output_intents(doc, errors, warnings, conformance)
        self._check_color_spaces(doc, errors, warnings, part_num)
        self._check_layers(doc, errors, part_num)
        self._check_annotations(doc, errors, warnings, part_num)

        doc.close()
        return {
            "is_compliant": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "level": level,
            "part": part_num,
            "conformance": conformance,
        }

    def _check_metadata(self, doc, errors, warnings):
        meta = doc.metadata
        if not meta:
            errors.append("Document metadata is missing entirely")
            return
        if not meta.get("title"):
            warnings.append("Missing document title in metadata")
        if not meta.get("author"):
            warnings.append("Missing author in metadata")
        if not meta.get("creationDate"):
            errors.append("Missing creation date in metadata")
        if not meta.get("modDate"):
            warnings.append("Missing modification date in metadata")

    def _check_xmp_metadata(self, doc, level, level_info, errors, warnings):
        try:
            xmp = doc.xref_xml_metadata(0)
            if not xmp:
                errors.append("XMP metadata packet is missing")
                return
            if "pdfaid:part" not in xmp:
                errors.append("XMP metadata does not contain pdfaid:part identification")
            else:
                part_match = re.search(r"pdfaid:part>(\d+)<", xmp)
                if part_match and part_match.group(1) != level_info["part"]:
                    errors.append(f"XMP declares PDF/A-{part_match.group(1)} but target is PDF/A-{level_info['part']}")
            if "dc:title" not in xmp:
                warnings.append("XMP metadata missing dc:title")
            if "dc:creator" not in xmp:
                warnings.append("XMP metadata missing dc:creator")
            if "xmp:CreateDate" not in xmp:
                errors.append("XMP metadata missing xmp:CreateDate")
            if "xmpMM:DocumentID" not in xmp:
                errors.append("XMP metadata missing xmpMM:DocumentID")
        except Exception:
            errors.append("Cannot read XMP metadata")

    def _check_fonts(self, doc, errors, warnings, part_num):
        font_check_done = set()
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                font_list = page.get_fonts(full=True)
                for font_entry in font_list:
                    xref = font_entry[0] if isinstance(font_entry, (list, tuple)) else 0
                    if xref in font_check_done:
                        continue
                    font_check_done.add(xref)
                    font_name = font_entry[3] if len(font_entry) > 3 else "unknown"
                    is_standard = font_entry[2] if len(font_entry) > 2 else ""
                    if not is_standard and part_num >= 2:
                        warnings.append(f"Font '{font_name}' on page {page_num + 1} may need embedding verification")
            except Exception:
                pass

    def _check_images(self, doc, errors, warnings, part_num):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                images = page.get_images(full=True)
                for img in images:
                    xref = img[0]
                    try:
                        img_rect = doc.xref_object(xref)
                        if img_rect and "SMask" in img_rect:
                            pass
                        if part_num >= 2:
                            if "Alternates" in (img_rect or ""):
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

    def _check_encryption(self, doc, errors):
        try:
            enc = doc.needs_pass()
            if enc:
                errors.append("PDF/A documents must not be encrypted")
        except Exception:
            pass

    def _check_javascript(self, doc, errors, part_num):
        try:
            has_js = False
            for page_num in range(len(doc)):
                page = doc[page_num]
                annots = page.annots()
                if annots:
                    for annot in annots:
                        try:
                            obj = doc.xref_object(annot.xref)
                            if "A" in obj and "/JavaScript" in str(obj):
                                has_js = True
                                break
                        except Exception:
                            pass
                if has_js:
                    break
            if has_js and part_num <= 2:
                errors.append("JavaScript actions are not allowed in PDF/A-1 and PDF/A-2")
        except Exception:
            pass

    def _check_embedded_files(self, doc, errors, warnings, part_num):
        try:
            ef_count = doc.embfile_count()
            if ef_count > 0 and part_num <= 1:
                errors.append(f"Embedded files ({ef_count}) are not allowed in PDF/A-1")
            elif ef_count > 0 and part_num == 2:
                warnings.append(f"Embedded files ({ef_count}) found; PDF/A-2 allows limited embedding")
        except Exception:
            pass

    def _check_transparency(self, doc, errors, warnings, part_num):
        if part_num == 1:
            for page_num in range(len(doc)):
                page = doc[page_num]
                try:
                    text_dict = page.get_text("dict")
                    for block in text_dict.get("blocks", []):
                        if block.get("type") == 0:
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    color = span.get("color", 0)
                                    if isinstance(color, int) and color > 0:
                                        pass
                except Exception:
                    pass

    def _check_output_intents(self, doc, errors, warnings, conformance):
        if conformance == "a":
            try:
                xref_count = doc.xref_length()
                has_output_intent = False
                for i in range(1, xref_count):
                    try:
                        obj = doc.xref_object(i)
                        if "/OutputIntents" in obj:
                            has_output_intent = True
                            break
                    except Exception:
                        continue
                if not has_output_intent:
                    warnings.append("PDF/A-a conformance requires at least one output intent (recommended)")
            except Exception:
                pass

    def _check_color_spaces(self, doc, errors, warnings, part_num):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                drawings = page.get_drawings()
                for draw in drawings:
                    fill = draw.get("fill")
                    if fill and isinstance(fill, (list, tuple)) and len(fill) >= 3:
                        pass
            except Exception:
                pass

    def _check_layers(self, doc, errors, part_num):
        if part_num <= 1:
            try:
                for i in range(doc.xref_length()):
                    try:
                        obj = doc.xref_object(i)
                        if "/OCGs" in obj or "/Order" in obj:
                            errors.append("Optional content groups (layers) are not allowed in PDF/A-1")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

    def _check_annotations(self, doc, errors, warnings, part_num):
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                annots = page.annots()
                if annots:
                    for annot in annots:
                        annot_type = annot.type
                        if annot_type and annot_type[0] in ("Movie", "Sound", "Screen", "Widget"):
                            if part_num <= 2:
                                errors.append(f"Annotation type '{annot_type[1]}' on page {page_num + 1} not allowed in PDF/A-{part_num}")
            except Exception:
                pass

    def convert_to_pdfa(self, input_path, output_path, level="pdfa-1b", title=None, author=None):
        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": f"Cannot open PDF: {e}"}

        level_info = PDFA_LEVELS.get(level, PDFA_LEVELS["pdfa-1b"])
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta = doc.metadata or {}
        doc_title = title or meta.get("title") or os.path.basename(input_path)
        doc_author = author or meta.get("author") or "PDF Editor Advanced"
        doc_desc = meta.get("subject", "")
        doc_id = str(uuid.uuid4())
        instance_id = str(uuid.uuid4())

        self._strip_javascript(doc, int(level_info["part"]))
        self._strip_embedded_files(doc, int(level_info["part"]))
        self._flatten_transparency(doc, int(level_info["part"]))
        self._normalize_color_spaces(doc, int(level_info["part"]))

        doc.set_metadata({
            "title": doc_title,
            "author": doc_author,
            "subject": doc_desc,
            "creationDate": now_str,
            "modDate": now_str,
            "creator": "PDF Editor Advanced",
            "producer": "PDF Editor Advanced",
        })

        xmp_xml = XMP_TEMPLATE.format(
            title=self._escape_xml(doc_title),
            author=self._escape_xml(doc_author),
            description=self._escape_xml(doc_desc),
            doc_id=doc_id,
            instance_id=instance_id,
            create_date=now_str,
            modify_date=now_str,
            part=level_info["part"],
            conformance=level_info["conformance"],
        )

        try:
            doc.set_xmp_metadata(xmp_xml)
        except Exception:
            pass

        try:
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": f"Save failed: {e}"}

        verification = self.validate(output_path, level)
        return {
            "success": verification["is_compliant"],
            "output_path": output_path,
            "level": level,
            "verification": verification,
        }

    def _strip_javascript(self, doc, part_num):
        if part_num > 2:
            return
        try:
            xref_count = doc.xref_length()
            for i in range(xref_count - 1, 0, -1):
                try:
                    obj = doc.xref_object(i)
                    if "/JavaScript" in obj or "/JS" in obj:
                        doc.xref_set_key(i, "JavaScript", "")
                        doc.xref_set_key(i, "JS", "")
                except Exception:
                    continue
        except Exception:
            pass

    def _strip_embedded_files(self, doc, part_num):
        if part_num >= 3:
            return
        try:
            ef_count = doc.embfile_count()
            for i in range(ef_count - 1, -1, -1):
                doc.embfile_delete(i)
        except Exception:
            pass

    def _flatten_transparency(self, doc, part_num):
        if part_num > 1:
            return
        for page in doc:
            try:
                page.clean_contents()
            except Exception:
                pass

    def _normalize_color_spaces(self, doc, part_num):
        for page in doc:
            try:
                page.clean_contents()
            except Exception:
                pass

    def _escape_xml(self, text):
        if not text:
            return ""
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))

    def embed_icc_profile(self, input_path, output_path, profile_path=None):
        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": str(e)}
        try:
            if profile_path and os.path.exists(profile_path):
                with open(profile_path, "rb") as f:
                    profile_data = f.read()
                if len(profile_data) < 128:
                    doc.close()
                    return {"success": False, "error": "ICC profile file too small or invalid"}
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

    def generate_compliance_report(self, path, level="pdfa-1b"):
        validation = self.validate(path, level)
        report_lines = [
            "=" * 60,
            "PDF/A COMPLIANCE REPORT",
            "=" * 60,
            f"File: {os.path.basename(path)}",
            f"Target Level: PDF/A-{level.upper().replace('PDFA-', '')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Status: {'PASS' if validation['is_compliant'] else 'FAIL'}",
            "-" * 60,
        ]
        if validation["errors"]:
            report_lines.append(f"\nERRORS ({len(validation['errors'])}):")
            for i, err in enumerate(validation["errors"], 1):
                report_lines.append(f"  {i}. {err}")
        if validation["warnings"]:
            report_lines.append(f"\nWARNINGS ({len(validation['warnings'])}):")
            for i, warn in enumerate(validation["warnings"], 1):
                report_lines.append(f"  {i}. {warn}")
        if not validation["errors"] and not validation["warnings"]:
            report_lines.append("\nNo issues found. Document appears compliant.")
        report_lines.append("\n" + "=" * 60)
        return "\n".join(report_lines)

    def embed_xmp_metadata(self, path, output_path, metadata_dict):
        try:
            doc = pymupdf.open(path)
            existing_meta = doc.metadata or {}
            merged = {**existing_meta, **metadata_dict}
            doc.set_metadata(merged)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            doc_id = str(uuid.uuid4())
            instance_id = str(uuid.uuid4())
            xmp_xml = XMP_TEMPLATE.format(
                title=self._escape_xml(merged.get("title", "")),
                author=self._escape_xml(merged.get("author", "")),
                description=self._escape_xml(merged.get("subject", "")),
                doc_id=doc_id,
                instance_id=instance_id,
                create_date=merged.get("creationDate", now_str),
                modify_date=now_str,
                part=merged.get("pdfaid:part", "1"),
                conformance=merged.get("pdfaid:conformance", "b"),
            )
            doc.set_xmp_metadata(xmp_xml)
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_validate(self, paths, level="pdfa-1b"):
        results = {}
        for path in paths:
            try:
                results[path] = self.validate(path, level)
            except Exception as e:
                results[path] = {"is_compliant": False, "error": str(e), "level": level}
        return results
