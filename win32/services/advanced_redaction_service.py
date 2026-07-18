import re
import os
import json
import hashlib
from datetime import datetime

import pymupdf


PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ssn_nodash": re.compile(r"\b\d{9}\b"),
    "phone_us": re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "phone_intl": re.compile(r"\+\d{1,3}[-.\s]?\d{4,14}"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-.\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "date_of_birth": re.compile(r"\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b"),
    "zip_code": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
    "ein": re.compile(r"\b\d{2}-\d{7}\b"),
    "passport_us": re.compile(r"\b[A-Z]\d{8}\b"),
    "drivers_license": re.compile(r"\b[A-Z]\d{7,12}\b"),
    "name_pattern": re.compile(r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"),
    "address_us": re.compile(r"\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\b"),
    "routing_number": re.compile(r"\b(?:0[1-9]|[12]\d|3[0-2])\d{7}\b"),
    "bank_account": re.compile(r"\b\d{8,17}\b"),
    "npi": re.compile(r"\b\d{10}\b"),
}

PHI_PATTERNS = {
    "medical_record_number": re.compile(r"\b(?:MRN|MR#|MED REC)[-\s:#]*\d{5,12}\b", re.IGNORECASE),
    "health_plan_id": re.compile(r"\b(?:HP|HIP|Plan)[-\s:#]*\d{6,12}\b", re.IGNORECASE),
    "account_number_health": re.compile(r"\b(?:Acct|Account)[-\s:#]*\d{6,14}\b", re.IGNORECASE),
    "license_number_health": re.compile(r"\b(?:Lic|License)[-\s:#]*[A-Z0-9]{6,12}\b", re.IGNORECASE),
    "diagnosis_code": re.compile(r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b"),
    "procedure_code": re.compile(r"\b\d{4,5}\b"),
    "drug_code": re.compile(r"\b(?:NDC)[-\s:]*\d{10,11}\b", re.IGNORECASE),
    "device_serial": re.compile(r"\b(?:S/N|Serial)[-\s:#]*[A-Z0-9]{6,16}\b", re.IGNORECASE),
}

FINANCIAL_PATTERNS = {
    "credit_card_visa": re.compile(r"\b4\d{3}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b"),
    "credit_card_mastercard": re.compile(r"\b5[1-5]\d{2}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b"),
    "credit_card_amex": re.compile(r"\b3[47]\d{2}[-.\s]?\d{6}[-.\s]?\d{5}\b"),
    "credit_card_discover": re.compile(r"\b6(?:011|5\d{2})[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b"),
    "routing_number_aba": re.compile(r"\b(?:0[1-9]|[12]\d|3[0-2])\d{7}\b"),
    "swift_code": re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b"),
    "bitcoin_address": re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),
    "tax_id_ein": re.compile(r"\b\d{2}-\d{7}\b"),
    "tax_id_ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

PATTERN_LIBRARY = {**PII_PATTERNS, **PHI_PATTERNS, **FINANCIAL_PATTERNS}

CATEGORY_LABELS = {
    "ssn": "Social Security Number",
    "phone_us": "US Phone Number",
    "email": "Email Address",
    "credit_card": "Credit Card Number",
    "diagnosis_code": "Diagnosis Code",
    "routing_number": "Routing Number",
}


class AdvancedRedactionService:
    def __init__(self, editor):
        self.editor = editor
        self._audit_log = []
        self._custom_patterns = {}
        self._preview_mode = True

    def scan_document(self, path, categories=None):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e), "findings": []}

        findings = []
        active_patterns = self._get_active_patterns(categories)

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            for page_num_text in range(1, len(doc) + 1):
                pass
            for pattern_name, pattern in active_patterns.items():
                for match in pattern.finditer(text):
                    category_label = CATEGORY_LABELS.get(pattern_name, pattern_name)
                    findings.append({
                        "page": page_num,
                        "pattern": pattern_name,
                        "category": category_label,
                        "match": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": self._estimate_confidence(pattern_name, match.group()),
                    })

        doc.close()
        findings.sort(key=lambda f: (f["page"], f["start"]))
        return {
            "success": True,
            "total_findings": len(findings),
            "findings": findings,
            "by_category": self._group_by_category(findings),
            "by_page": self._group_by_page(findings),
        }

    def _get_active_patterns(self, categories=None):
        if categories is None:
            return PATTERN_LIBRARY
        active = {}
        category_map = {
            "pii": PII_PATTERNS,
            "phi": PHI_PATTERNS,
            "financial": FINANCIAL_PATTERNS,
        }
        for cat in categories:
            if cat.lower() in category_map:
                active.update(category_map[cat.lower()])
            elif cat.lower() in PATTERN_LIBRARY:
                active[cat.lower()] = PATTERN_LIBRARY[cat.lower()]
        return active

    def _estimate_confidence(self, pattern_name, text):
        length = len(text.replace("-", "").replace(" ", "").replace(".", ""))
        if pattern_name == "ssn":
            return 0.95 if len(text.replace("-", "")) == 9 else 0.5
        if pattern_name in ("phone_us", "phone_intl"):
            return 0.85
        if pattern_name == "email":
            return 0.98
        if "credit_card" in pattern_name:
            return 0.9 if self._luhn_check(text.replace("-", "").replace(" ", "")) else 0.4
        return 0.7

    def _luhn_check(self, num_str):
        try:
            digits = [int(d) for d in num_str if d.isdigit()]
            if len(digits) < 13:
                return False
            checksum = 0
            for i, d in enumerate(reversed(digits)):
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                checksum += d
            return checksum % 10 == 0
        except Exception:
            return False

    def _group_by_category(self, findings):
        groups = {}
        for f in findings:
            cat = f["category"]
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(f)
        return groups

    def _group_by_page(self, findings):
        groups = {}
        for f in findings:
            pg = f["page"]
            if pg not in groups:
                groups[pg] = []
            groups[pg].append(f)
        return groups

    def redact_findings(self, path, output_path, findings, fill_color=(0, 0, 0), custom_pattern=None):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        redacted_count = 0
        for finding in findings:
            page_num = finding["page"]
            if page_num >= len(doc):
                continue
            page = doc[page_num]
            text_dict = page.get_text("dict")
            search_text = finding["match"]

            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if search_text in span_text:
                            span_rect = span.get("bbox")
                            if span_rect:
                                local_start = span_text.index(search_text)
                                char_width = (span_rect[2] - span_rect[0]) / max(len(span_text), 1)
                                x0 = span_rect[0] + local_start * char_width
                                x1 = x0 + len(search_text) * char_width
                                rect = pymupdf.Rect(x0, span_rect[1], x1, span_rect[3])
                                page.add_redact_annot(rect, fill=fill_color)
                                redacted_count += 1

        for page in doc:
            try:
                page.apply_redactions()
            except Exception:
                pass

        try:
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        self._log_audit("redact", path, output_path, redacted_count)
        return {"success": True, "output_path": output_path, "redacted_count": redacted_count}

    def redact_regex(self, path, output_path, regex_pattern, fill_color=(0, 0, 0)):
        try:
            pattern = re.compile(regex_pattern)
        except re.error as e:
            return {"success": False, "error": f"Invalid regex: {e}"}

        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        redacted_count = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            text_dict = page.get_text("dict")
            for match in pattern.finditer(text):
                search_text = match.group()
                for block in text_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            if search_text in span_text:
                                span_rect = span.get("bbox")
                                if span_rect:
                                    local_start = span_text.index(search_text)
                                    char_width = (span_rect[2] - span_rect[0]) / max(len(span_text), 1)
                                    x0 = span_rect[0] + local_start * char_width
                                    x1 = x0 + len(search_text) * char_width
                                    rect = pymupdf.Rect(x0, span_rect[1], x1, span_rect[3])
                                    page.add_redact_annot(rect, fill=fill_color)
                                    redacted_count += 1

        for page in doc:
            try:
                page.apply_redactions()
            except Exception:
                pass

        try:
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        return {"success": True, "output_path": output_path, "redacted_count": redacted_count}

    def add_custom_pattern(self, name, regex_str):
        try:
            pattern = re.compile(regex_str)
            self._custom_patterns[name] = pattern
            return True
        except re.error:
            return False

    def get_pattern_library(self):
        library = {}
        for name, pattern in PATTERN_LIBRARY.items():
            library[name] = {
                "pattern": pattern.pattern,
                "category": "pii" if name in PII_PATTERNS else ("phi" if name in PHI_PATTERNS else "financial"),
                "label": CATEGORY_LABELS.get(name, name),
            }
        for name, pattern in self._custom_patterns.items():
            library[name] = {
                "pattern": pattern.pattern,
                "category": "custom",
                "label": name,
            }
        return library

    def scrub_metadata(self, path, output_path, remove_xmp=True, remove_exif=True, remove_properties=True):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        scrubbed = []
        if remove_properties:
            original_meta = doc.metadata or {}
            safe_meta = {}
            for key in ("title", "author", "subject", "creator", "producer"):
                if key in original_meta:
                    safe_meta[key] = original_meta[key]
            safe_meta["creator"] = "PDF Editor"
            safe_meta["producer"] = "PDF Editor"
            doc.set_metadata(safe_meta)
            scrubbed.append("Document properties")

        if remove_xmp:
            try:
                doc.set_xmp_metadata("")
                scrubbed.append("XMP metadata")
            except Exception:
                pass

        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                annots = page.annots()
                if annots:
                    for annot in annots:
                        try:
                            info = annot.info
                            if info:
                                annot.set_info(content="", title="", subject="")
                                annot.update()
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                page.set_metadata({})
            except Exception:
                pass

        try:
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        self._log_audit("scrub_metadata", path, output_path, len(scrubbed))
        return {"success": True, "output_path": output_path, "items_scrubbed": scrubbed}

    def verify_redaction(self, path, original_findings=None):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e), "leaked": []}

        leaked = []
        if original_findings:
            for finding in original_findings:
                page_num = finding["page"]
                if page_num >= len(doc):
                    continue
                page = doc[page_num]
                text = page.get_text("text")
                if finding["match"] in text:
                    leaked.append(finding)

        full_text = ""
        for page in doc:
            full_text += page.get_text("text")

        remaining_pii = {}
        for pattern_name, pattern in PII_PATTERNS.items():
            matches = pattern.findall(full_text)
            if matches:
                remaining_pii[pattern_name] = matches

        doc.close()
        return {
            "success": True,
            "leaked_from_original": leaked,
            "remaining_pii": remaining_pii,
            "is_clean": len(leaked) == 0 and len(remaining_pii) == 0,
        }

    def preview_redaction(self, path, findings):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        preview_data = []
        for finding in findings:
            page_num = finding["page"]
            if page_num >= len(doc):
                continue
            page = doc[page_num]
            text_dict = page.get_text("dict")
            search_text = finding["match"]
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if search_text in span_text:
                            bbox = span.get("bbox")
                            if bbox:
                                preview_data.append({
                                    "page": page_num,
                                    "text": search_text,
                                    "bbox": bbox,
                                    "pattern": finding["pattern"],
                                    "category": finding["category"],
                                })

        doc.close()
        return {"success": True, "preview": preview_data, "total": len(preview_data)}

    def _log_audit(self, action, input_path, output_path, count):
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "input": input_path,
            "output": output_path,
            "count": count,
        })

    def get_audit_log(self):
        return list(self._audit_log)

    def export_audit_log(self, output_path):
        try:
            with open(output_path, "w") as f:
                json.dump(self._audit_log, f, indent=2)
            return True
        except Exception:
            return False
