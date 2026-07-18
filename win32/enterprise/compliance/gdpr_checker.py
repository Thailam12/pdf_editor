import re
import os
import json
import hashlib
from datetime import datetime, timezone

import pymupdf


PERSONAL_DATA_PATTERNS = {
    "email": {"description": "Email addresses (personal data)", "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure", "portability"]},
    "phone": {"description": "Phone numbers", "regex": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure"]},
    "ip_address": {"description": "IP addresses", "regex": r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure"]},
    "name": {"description": "Personal names", "regex": r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure", "rectification"]},
    "address": {"description": "Physical addresses", "regex": r"\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)[,\s]+[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure", "rectification"]},
    "date_of_birth": {"description": "Dates of birth", "regex": r"\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure"]},
    "ssn": {"description": "National identification numbers", "regex": r"\b\d{3}-\d{2}-\d{4}\b", "article": "Art. 4(5)", "data_subject_rights": ["access", "erasure"]},
    "credit_card": {"description": "Payment card numbers", "regex": r"\b(?:\d{4}[-.\s]?){3}\d{4}\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure"]},
    "passport": {"description": "Passport numbers", "regex": r"\b[A-Z]\d{8}\b", "article": "Art. 4(1)", "data_subject_rights": ["access", "erasure"]},
    "consent_ref": {"description": "Consent references", "regex": r"\b(?:consent|agreement|opt-in)[:\s#]*[A-Z0-9-]{4,20}\b", "article": "Art. 7", "data_subject_rights": ["access"]},
}


class GDPRChecker:
    def __init__(self):
        self._scan_history = []

    def scan_personal_data(self, path):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e), "findings": []}

        findings = []
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            full_text += text + "\n"
            for cat_name, cat_info in PERSONAL_DATA_PATTERNS.items():
                pattern = re.compile(cat_info["regex"], re.IGNORECASE)
                for match in pattern.finditer(text):
                    findings.append({
                        "category": cat_name,
                        "description": cat_info["description"],
                        "match": match.group(),
                        "page": page_num,
                        "position": {"start": match.start(), "end": match.end()},
                        "gdpr_article": cat_info["article"],
                        "data_subject_rights": cat_info["data_subject_rights"],
                        "is_special_category": cat_name in ("ssn", "passport"),
                    })

        doc.close()
        total_chars = len(full_text)
        self._scan_history.append({
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "findings_count": len(findings),
        })
        return {
            "success": True,
            "total_findings": len(findings),
            "findings": findings,
            "by_category": self._group_by_category(findings),
            "by_article": self._group_by_article(findings),
            "special_category_count": len([f for f in findings if f["is_special_category"]]),
            "total_characters_scanned": total_chars,
            "scan_time": datetime.now(timezone.utc).isoformat(),
        }

    def _group_by_category(self, findings):
        groups = {}
        for f in findings:
            cat = f["category"]
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(f)
        return groups

    def _group_by_article(self, findings):
        groups = {}
        for f in findings:
            art = f["gdpr_article"]
            if art not in groups:
                groups[art] = []
            groups[art].append(f)
        return groups

    def check_consent_references(self, path):
        try:
            doc = pymupdf.open(path)
            consent_found = False
            consent_details = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                pattern = re.compile(r"\b(?:consent|agreement|opt-in|permission|authorized)[:\s]*(.{0,100})", re.IGNORECASE)
                for match in pattern.finditer(text):
                    consent_found = True
                    consent_details.append({
                        "page": page_num,
                        "context": match.group()[:150],
                        "position": match.start(),
                    })
            doc.close()
            return {
                "consent_references_found": consent_found,
                "consent_details": consent_details,
                "status": "PASS" if consent_found else "WARNING",
                "message": "Consent references found" if consent_found else "No consent references found in document",
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def check_data_minimization(self, path):
        try:
            doc = pymupdf.open(path)
            issues = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                word_count = len(text.split())
                if word_count > 5000:
                    issues.append({
                        "page": page_num + 1,
                        "issue": f"Page has {word_count} words - review for data minimization (Art. 5(1)(c))",
                        "severity": "low",
                    })
                for cat_name, cat_info in PERSONAL_DATA_PATTERNS.items():
                    pattern = re.compile(cat_info["regex"], re.IGNORECASE)
                    matches = pattern.findall(text)
                    if len(matches) > 5:
                        issues.append({
                            "page": page_num + 1,
                            "issue": f"Multiple {cat_info['description']} instances ({len(matches)}) - review necessity",
                            "category": cat_name,
                            "severity": "medium",
                        })
            doc.close()
            return {
                "issues": issues,
                "status": "PASS" if not issues else "REVIEW_NEEDED",
                "message": "No data minimization concerns" if not issues else f"Found {len(issues)} minimization concerns",
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def support_right_to_erasure(self, path, output_path, target_data):
        try:
            doc = pymupdf.open(path)
            erasured_count = 0
            for data_item in target_data:
                pattern_str = re.escape(data_item)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text("text")
                    if re.search(pattern_str, text, re.IGNORECASE):
                        text_dict = page.get_text("dict")
                        for block in text_dict.get("blocks", []):
                            if block.get("type") != 0:
                                continue
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    span_text = span.get("text", "")
                                    if re.search(pattern_str, span_text, re.IGNORECASE):
                                        bbox = span.get("bbox")
                                        if bbox:
                                            rect = pymupdf.Rect(bbox)
                                            page.add_redact_annot(rect, fill=(0, 0, 0))
                                            erasured_count += 1

            for page in doc:
                try:
                    page.apply_redactions()
                except Exception:
                    pass

            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
            return {
                "success": True,
                "output_path": output_path,
                "items_erased": erasured_count,
                "data_items_processed": len(target_data),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_privacy_impact(self, path):
        scan = self.scan_personal_data(path)
        consent = self.check_consent_references(path)
        minimization = self.check_data_minimization(path)

        risk_score = 0
        risk_factors = []
        if scan.get("special_category_count", 0) > 0:
            risk_score += 30
            risk_factors.append(f"Special category data found: {scan['special_category_count']} instances")
        if scan.get("total_findings", 0) > 20:
            risk_score += 20
            risk_factors.append(f"High volume of personal data: {scan['total_findings']} instances")
        elif scan.get("total_findings", 0) > 5:
            risk_score += 10
            risk_factors.append(f"Moderate personal data: {scan['total_findings']} instances")
        if consent.get("status") == "WARNING":
            risk_score += 15
            risk_factors.append("No consent references found")
        if minimization.get("status") == "REVIEW_NEEDED":
            risk_score += 10
            risk_factors.append("Data minimization concerns identified")

        if risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "personal_data_scan": scan,
            "consent_check": consent,
            "minimization_check": minimization,
            "recommendations": self._generate_recommendations(risk_level, scan, consent, minimization),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_recommendations(self, risk_level, scan, consent, minimization):
        recs = []
        if scan.get("special_category_count", 0) > 0:
            recs.append({
                "priority": "HIGH",
                "article": "Art. 9",
                "action": "Review processing of special category data (health, biometric, etc.)",
                "detail": "Special category data requires explicit consent or other Art. 9(2) exemption",
            })
        if scan.get("total_findings", 0) > 0:
            recs.append({
                "priority": "MEDIUM",
                "article": "Art. 13-14",
                "action": "Ensure data subjects are informed about processing",
                "detail": "Provide privacy notice covering all personal data categories found",
            })
        if consent.get("status") == "WARNING":
            recs.append({
                "priority": "HIGH",
                "article": "Art. 7",
                "action": "Verify and document consent for personal data processing",
                "detail": "No consent references found; ensure valid consent basis exists",
            })
        if minimization.get("status") == "REVIEW_NEEDED":
            recs.append({
                "priority": "MEDIUM",
                "article": "Art. 5(1)(c)",
                "action": "Review data minimization - remove unnecessary personal data",
                "detail": "Excess personal data found that may not be necessary for stated purpose",
            })
        recs.append({
            "priority": "LOW",
            "article": "Art. 30",
            "action": "Record this processing activity in your ROPA",
            "detail": "Maintain Record of Processing Activities as required by Art. 30",
        })
        return recs

    def generate_report(self, path):
        impact = self.check_privacy_impact(path)
        lines = [
            "=" * 60,
            "GDPR PRIVACY IMPACT ASSESSMENT",
            "=" * 60,
            f"Document: {path}",
            f"Generated: {impact['timestamp']}",
            f"Risk Level: {impact['risk_level']} (Score: {impact['risk_score']}/100)",
            "-" * 60,
        ]
        if impact["risk_factors"]:
            lines.append("\nRISK FACTORS:")
            for factor in impact["risk_factors"]:
                lines.append(f"  - {factor}")
        scan = impact["personal_data_scan"]
        lines.append(f"\nPERSONAL DATA: {scan.get('total_findings', 0)} instances found")
        for cat, items in scan.get("by_category", {}).items():
            lines.append(f"  {cat}: {len(items)} instances")
        lines.append(f"\nCONSENT: {impact['consent_check']['status']}")
        lines.append(f"DATA MINIMIZATION: {impact['minimization_check']['status']}")
        if impact["recommendations"]:
            lines.append("\nRECOMMENDATIONS:")
            for idx, rec in enumerate(impact["recommendations"], 1):
                lines.append(f"  {idx}. [{rec['priority']}] {rec['action']}")
                lines.append(f"     {rec['detail']}")
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def get_scan_history(self):
        return list(self._scan_history)
