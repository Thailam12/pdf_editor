import os
import re
import uuid
from datetime import datetime, timezone

import pymupdf


PDFA_PROFILES = {
    "pdfa-1a": {"part": "1", "conformance": "a", "level": "PDF/A-1a"},
    "pdfa-1b": {"part": "1", "conformance": "b", "level": "PDF/A-1b"},
    "pdfa-2a": {"part": "2", "conformance": "a", "level": "PDF/A-2a"},
    "pdfa-2b": {"part": "2", "conformance": "b", "level": "PDF/A-2b"},
    "pdfa-2u": {"part": "2", "conformance": "u", "level": "PDF/A-2u"},
    "pdfa-3a": {"part": "3", "conformance": "a", "level": "PDF/A-3a"},
    "pdfa-3b": {"part": "3", "conformance": "b", "level": "PDF/A-3b"},
    "pdfa-3u": {"part": "3", "conformance": "u", "level": "PDF/A-3u"},
    "pdfa-4":  {"part": "4", "conformance": "f", "level": "PDF/A-4"},
}

SPEC_REFERENCES = {
    "6.1.2": "ISO 19005-1:2005 §6.1.2 - Stream encodings",
    "6.1.3": "ISO 19005-1:2005 §6.1.3 - Encryption prohibition",
    "6.1.4": "ISO 19005-1:2005 §6.1.4 - Transparency groups",
    "6.1.5": "ISO 19005-1:2005 §6.1.5 - Annotation characteristics",
    "6.1.6": "ISO 19005-1:2005 §6.1.6 - Sound and movie annotations",
    "6.1.7": "ISO 19005-1:2005 §6.1.7 - JavaScript prohibition",
    "6.1.8": "ISO 19005-1:2005 §6.1.8 - Optional content",
    "6.1.9": "ISO 19005-1:2005 §6.1.9 - Embedded files",
    "6.1.10": "ISO 19005-1:2005 §6.1.10 - General RGB colors",
    "6.1.11": "ISO 19005-1:2005 §6.1.11 - LZW prohibition",
    "6.1.12": "ISO 19005-2:2011 §6.1.12 - PDF version requirements",
    "6.1.13": "ISO 19005-2:2011 §6.1.13 - XMP metadata requirements",
    "6.7.1": "ISO 19005-1:2005 §6.7.1 - Metadata requirements",
    "6.7.3": "ISO 19005-1:2005 §6.7.3 - XMP metadata packet",
    "6.7.4": "ISO 19005-1:2005 §6.7.4 - Document info dictionary",
    "6.7.5": "ISO 19005-1:2005 §6.7.5 - Output intents",
    "6.7.6": "ISO 19005-1:2005 §6.7.6 - ICC profile requirements",
    "6.2.1": "ISO 19005-1:2005 §6.2.1 - Font requirements",
    "6.2.2": "ISO 19005-1:2005 §6.2.2 - Font descriptor requirements",
}


class PdfAValidator:
    def __init__(self):
        self._last_validation = None

    def validate(self, path, target_level="pdfa-1b"):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"valid": False, "errors": [{"code": "OPEN_FAILED", "message": str(e), "severity": "critical"}], "level": target_level}

        profile = PDFA_PROFILES.get(target_level, PDFA_PROFILES["pdfa-1b"])
        errors = []
        warnings = []
        self._check_metadata(doc, errors, warnings, profile)
        self._check_xmp(doc, errors, warnings, profile)
        self._check_encryption(doc, errors)
        self._check_javascript(doc, errors, profile)
        self._check_embedded_files(doc, errors, warnings, profile)
        self._check_fonts(doc, errors, warnings, profile)
        self._check_images(doc, errors, warnings, profile)
        self._check_color_spaces(doc, errors, warnings, profile)
        self._check_layers(doc, errors, profile)
        self._check_annotations(doc, errors, warnings, profile)
        self._check_output_intents(doc, errors, warnings, profile)
        self._check_streams(doc, errors, profile)

        doc.close()
        result = {
            "valid": len(errors) == 0,
            "level": target_level,
            "profile": profile["level"],
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._last_validation = result
        return result

    def _add_error(self, errors, code, message, severity="error"):
        errors.append({
            "code": code,
            "message": message,
            "severity": severity,
            "spec_ref": SPEC_REFERENCES.get(code, ""),
            "fix_suggestion": self._get_fix_suggestion(code),
        })

    def _get_fix_suggestion(self, code):
        suggestions = {
            "6.1.3": "Remove all encryption from the document before converting to PDF/A",
            "6.1.7": "Remove all JavaScript actions from the document",
            "6.1.8": "Flatten all transparency groups and layers",
            "6.1.9": "Remove embedded files for PDF/A-1 compliance",
            "6.7.1": "Add required metadata fields: title, author, creation date",
            "6.7.3": "Ensure XMP metadata packet is properly formatted with pdfaid identification",
            "6.7.4": "Remove or minimize document info dictionary entries to match XMP",
            "6.7.5": "Add at least one output intent for color management",
            "6.1.13": "Add MarkInfo with /Marked true for tagged PDF/A",
            "6.2.1": "Ensure all fonts are embedded or use standard PDF fonts",
        }
        return suggestions.get(code, "Consult the PDF/A specification for this requirement")

    def _check_metadata(self, doc, errors, warnings, profile):
        meta = doc.metadata
        if not meta:
            self._add_error(errors, "6.7.1", "Document metadata dictionary is completely missing")
            return
        if not meta.get("title"):
            warnings.append({"code": "META_TITLE", "message": "Document title missing from metadata", "severity": "warning"})
        if not meta.get("author"):
            warnings.append({"code": "META_AUTHOR", "message": "Author missing from metadata", "severity": "warning"})
        if not meta.get("creationDate"):
            self._add_error(errors, "6.7.1", "Creation date is required in document metadata")
        if not meta.get("modDate"):
            warnings.append({"code": "META_MODDATE", "message": "Modification date missing from metadata", "severity": "warning"})
        prod = meta.get("producer", "")
        if not prod:
            warnings.append({"code": "META_PRODUCER", "message": "Producer field missing from metadata", "severity": "warning"})

    def _check_xmp(self, doc, errors, warnings, profile):
        try:
            xmp = doc.xref_xml_metadata(0)
            if not xmp:
                self._add_error(errors, "6.7.3", "XMP metadata packet is missing")
                return
            if "pdfaid:part" not in xmp:
                self._add_error(errors, "6.7.3", "XMP metadata does not contain PDF/A identification (pdfaid:part)")
            else:
                part_match = re.search(r"pdfaid:part>(\d+)<", xmp)
                conf_match = re.search(r"pdfaid:conformance>(\w)<", xmp)
                if part_match:
                    actual_part = part_match.group(1)
                    target_part = profile["part"]
                    if actual_part != target_part:
                        self._add_error(errors, "6.7.3", f"XMP declares PDF/A-{actual_part} but target is PDF/A-{target_part}")
            if "dc:title" not in xmp:
                warnings.append({"code": "XMP_TITLE", "message": "XMP missing dc:title element", "severity": "warning"})
            if "xmp:CreateDate" not in xmp:
                self._add_error(errors, "6.1.13", "XMP metadata missing xmp:CreateDate")
            if "xmpMM:DocumentID" not in xmp:
                self._add_error(errors, "6.1.13", "XMP metadata missing xmpMM:DocumentID")
            if "dc:format" not in xmp:
                warnings.append({"code": "XMP_FORMAT", "message": "XMP missing dc:format element", "severity": "warning"})
        except Exception as e:
            self._add_error(errors, "6.7.3", f"Cannot read XMP metadata: {e}")

    def _check_encryption(self, doc, errors):
        try:
            if doc.needs_pass():
                self._add_error(errors, "6.1.3", "Encrypted documents are not allowed in PDF/A", severity="critical")
        except Exception:
            pass

    def _check_javascript(self, doc, errors, profile):
        part_num = int(profile["part"])
        if part_num > 2:
            return
        try:
            for i in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(i)
                    if "/JavaScript" in obj or "/JS " in obj:
                        self._add_error(errors, "6.1.7", "JavaScript actions are prohibited in PDF/A-1 and PDF/A-2")
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def _check_embedded_files(self, doc, errors, warnings, profile):
        part_num = int(profile["part"])
        try:
            ef_count = doc.embfile_count()
            if ef_count > 0 and part_num <= 1:
                self._add_error(errors, "6.1.9", f"Embedded files ({ef_count}) are prohibited in PDF/A-1")
            elif ef_count > 0 and part_num == 2:
                warnings.append({"code": "EF_LIMITED", "message": f"PDF/A-2 allows limited embedded files; found {ef_count}", "severity": "warning"})
        except Exception:
            pass

    def _check_fonts(self, doc, errors, warnings, profile):
        checked = set()
        for page in doc:
            try:
                fonts = page.get_fonts(full=True)
                for font in fonts:
                    xref = font[0] if isinstance(font, (list, tuple)) else 0
                    if xref in checked:
                        continue
                    checked.add(xref)
                    font_name = font[3] if len(font) > 3 else "unknown"
                    font_type = font[2] if len(font) > 2 else ""
                    if "Type1" not in str(font_type) and not font_type:
                        warnings.append({
                            "code": "FONT_EMBED",
                            "message": f"Font '{font_name}' embedding status should be verified",
                            "severity": "warning",
                        })
            except Exception:
                pass

    def _check_images(self, doc, errors, warnings, profile):
        part_num = int(profile["part"])
        for page in doc:
            try:
                images = page.get_images(full=True)
                for img in images:
                    xref = img[0]
                    try:
                        img_data = doc.extract_image(xref)
                        if img_data:
                            ext = img_data.get("ext", "")
                            if ext == "jpx" and part_num == 1:
                                self._add_error(errors, "6.1.2", "JPEG2000 images are not allowed in PDF/A-1")
                            if ext == "jbig2" and part_num <= 2:
                                self._add_error(errors, "6.1.2", "JBIG2 images are not allowed in PDF/A-1 and PDF/A-2")
                    except Exception:
                        pass
            except Exception:
                pass

    def _check_color_spaces(self, doc, errors, warnings, profile):
        part_num = int(profile["part"])
        if part_num == 1:
            for page in doc:
                try:
                    text_dict = page.get_text("dict")
                    for block in text_dict.get("blocks", []):
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                color = span.get("color", 0)
                                if isinstance(color, tuple) and len(color) >= 4:
                                    if color[3] < 1.0:
                                        warnings.append({
                                            "code": "CS_TRANSPARENCY",
                                            "message": f"Transparent text color on page {page.number + 1}",
                                            "severity": "warning",
                                        })
                except Exception:
                    pass

    def _check_layers(self, doc, errors, profile):
        part_num = int(profile["part"])
        if part_num > 1:
            return
        try:
            for i in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(i)
                    if "/OCGs" in obj:
                        self._add_error(errors, "6.1.8", "Optional content groups (layers) are prohibited in PDF/A-1")
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def _check_annotations(self, doc, errors, warnings, profile):
        prohibited_types = {"Movie", "Sound", "Screen"}
        part_num = int(profile["part"])
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                annots = page.annots()
                if annots:
                    for annot in annots:
                        atype = annot.type
                        if atype and atype[0] in prohibited_types:
                            self._add_error(errors, "6.1.6", f"Annotation type '{atype[1]}' on page {page_num + 1} is prohibited")
            except Exception:
                pass

    def _check_output_intents(self, doc, errors, warnings, profile):
        conf = profile["conformance"]
        if conf in ("a", "b", "u"):
            try:
                has_oi = False
                for i in range(1, doc.xref_length()):
                    try:
                        obj = doc.xref_object(i)
                        if "/OutputIntents" in obj:
                            has_oi = True
                            break
                    except Exception:
                        continue
                if not has_oi:
                    warnings.append({
                        "code": "OI_MISSING",
                        "message": "No output intents found; recommended for color management",
                        "severity": "warning",
                    })
            except Exception:
                pass

    def _check_streams(self, doc, errors, profile):
        part_num = int(profile["part"])
        if part_num > 1:
            return
        try:
            for i in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(i)
                    if "/Filter" in obj and "/LZWDecode" in obj:
                        self._add_error(errors, "6.1.11", "LZW compression is prohibited in PDF/A-1")
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def validate_batch(self, paths, level="pdfa-1b"):
        results = {}
        for path in paths:
            try:
                results[path] = self.validate(path, level)
            except Exception as e:
                results[path] = {"valid": False, "errors": [{"code": "BATCH_ERROR", "message": str(e)}], "level": level}
        return results

    def generate_certificate(self, path, level="pdfa-1b"):
        validation = self.validate(path, level)
        cert_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        certificate = {
            "certificate_id": cert_id,
            "document": os.path.basename(path),
            "document_path": path,
            "target_level": level,
            "result": "PASS" if validation["valid"] else "FAIL",
            "error_count": validation["error_count"],
            "warning_count": validation["warning_count"],
            "validated_at": now,
            "validator": "PDF Editor Enterprise - PdfAValidator v1.0",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        }
        return certificate
