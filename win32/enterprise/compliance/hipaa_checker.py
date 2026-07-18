import re
import os
import json
from datetime import datetime, timezone

import pymupdf


PHI_CATEGORIES = {
    "names": {"description": "Patient names", "regex": r"\b(?:Mr\.|Mrs\.|Ms\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", "hipaa_ref": "164.514(b)"},
    "ssn": {"description": "Social Security Numbers", "regex": r"\b\d{3}-\d{2}-\d{4}\b", "hipaa_ref": "164.514(b)(2)"},
    "dates": {"description": "Dates of birth/admission/discharge", "regex": r"\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b", "hipaa_ref": "164.514(b)(2)"},
    "phone": {"description": "Phone numbers", "regex": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "hipaa_ref": "164.514(b)(2)"},
    "fax": {"description": "Fax numbers", "regex": r"\b(?:fax| Fax)[:\s]*(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "hipaa_ref": "164.514(b)(2)"},
    "email": {"description": "Email addresses", "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "hipaa_ref": "164.514(b)(2)"},
    "address": {"description": "Street addresses", "regex": r"\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\.?\s*(?:,\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?", "hipaa_ref": "164.514(b)(2)"},
    "mrn": {"description": "Medical Record Numbers", "regex": r"\b(?:MRN|MR#|MED REC|Patient ID)[:\s#]*\d{5,15}\b", "hipaa_ref": "164.514(b)(2)"},
    "npi": {"description": "National Provider Identifier", "regex": r"\b(?:NPI)[:\s#]*\d{10}\b", "hipaa_ref": "164.514(b)(2)"},
    "health_plan_id": {"description": "Health Plan Beneficiary Numbers", "regex": r"\b(?:Health Plan|HP|Beneficiary)[:\s#]*\d{6,15}\b", "hipaa_ref": "164.514(b)(2)"},
    "account_number": {"description": "Account Numbers", "regex": r"\b(?:Account|Acct)[:\s#]*\d{6,15}\b", "hipaa_ref": "164.514(b)(2)"},
    "license": {"description": "License Numbers", "regex": r"\b(?:License|Lic)[:\s#]*[A-Z0-9]{6,15}\b", "hipaa_ref": "164.514(b)(2)"},
    "diagnosis": {"description": "Diagnosis Codes (ICD)", "regex": r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b", "hipaa_ref": "164.514(b)(2)"},
    "procedure": {"description": "Procedure Codes (CPT)", "regex": r"\b(?:CPT)[:\s#]*\d{5}\b", "hipaa_ref": "164.514(b)(2)"},
    "device_serial": {"description": "Device Identifiers and Serial Numbers", "regex": r"\b(?:S/N|Serial|Device ID)[:\s#]*[A-Z0-9]{6,20}\b", "hipaa_ref": "164.514(b)(2)"},
    "url": {"description": "URLs (potential PHI in links)", "regex": r"https?://[^\s<>\"']+patient[^\s<>\"']*", "hipaa_ref": "164.514(b)(2)"},
}


class HIPAAChecker:
    def __init__(self):
        self._scan_history = []

    def scan_document(self, path):
        try:
            doc = pymupdf.open(path)
        except Exception as e:
            return {"success": False, "error": str(e), "findings": []}

        findings = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            for cat_name, cat_info in PHI_CATEGORIES.items():
                pattern = re.compile(cat_info["regex"], re.IGNORECASE)
                for match in pattern.finditer(text):
                    findings.append({
                        "category": cat_name,
                        "description": cat_info["description"],
                        "match": match.group(),
                        "page": page_num,
                        "position": {"start": match.start(), "end": match.end()},
                        "hipaa_ref": cat_info["hipaa_ref"],
                        "severity": "high" if cat_name in ("ssn", "mrn", "names") else "medium",
                    })

        doc.close()
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

    def check_encryption(self, path):
        try:
            doc = pymupdf.open(path)
            encrypted = doc.needs_pass()
            doc.close()
            return {
                "encrypted": encrypted,
                "status": "PASS" if encrypted else "WARNING",
                "message": "Document is encrypted" if encrypted else "Document is NOT encrypted - encryption recommended for PHI",
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def check_access_controls(self, path):
        try:
            doc = pymupdf.open(path)
            permissions = doc.get_permissions()
            doc.close()
            issues = []
            if permissions & (1 << 2):
                issues.append("Print permission is allowed - consider restricting for PHI documents")
            if permissions & (1 << 3):
                issues.append("Copy/extract permission is allowed - consider restricting for PHI documents")
            if permissions & (1 << 4):
                issues.append("Modify permission is allowed - consider restricting for PHI documents")
            return {
                "has_restrictions": not (permissions & 0xFFFF == 0xFFFF),
                "issues": issues,
                "status": "PASS" if not issues else "WARNING",
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def check_audit_metadata(self, path):
        try:
            doc = pymupdf.open(path)
            meta = doc.metadata or {}
            doc.close()
            issues = []
            if not meta.get("author"):
                issues.append("Missing author - required for audit trail")
            if not meta.get("creationDate"):
                issues.append("Missing creation date - required for audit trail")
            if not meta.get("modDate"):
                issues.append("Missing modification date - required for audit trail")
            return {
                "has_audit_fields": len(issues) == 0,
                "issues": issues,
                "status": "PASS" if not issues else "WARNING",
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def generate_compliance_report(self, path):
        phi_scan = self.scan_document(path)
        encryption = self.check_encryption(path)
        access = self.check_access_controls(path)
        audit = self.check_audit_metadata(path)
        critical_findings = [f for f in phi_scan.get("findings", []) if f["severity"] == "high"]

        overall_status = "COMPLIANT"
        if critical_findings:
            overall_status = "NON-COMPLIANT - UNREDACTED PHI"
        elif phi_scan.get("total_findings", 0) > 0:
            overall_status = "REVIEW REQUIRED"
        elif encryption.get("status") == "WARNING":
            overall_status = "REVIEW REQUIRED"

        report = {
            "document": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "phi_scan": {
                "total_findings": phi_scan.get("total_findings", 0),
                "high_severity": len(critical_findings),
                "categories_found": list(phi_scan.get("by_category", {}).keys()),
            },
            "encryption": encryption,
            "access_controls": access,
            "audit_metadata": audit,
            "recommendations": self._generate_recommendations(phi_scan, encryption, access, audit),
        }
        return report

    def _generate_recommendations(self, phi_scan, encryption, access, audit):
        recs = []
        if phi_scan.get("total_findings", 0) > 0:
            recs.append({
                "priority": "HIGH",
                "action": "Redact all unredacted PHI before sharing or storing the document",
                "details": f"Found {phi_scan['total_findings']} potential PHI instances",
            })
        if encryption.get("status") == "WARNING":
            recs.append({
                "priority": "HIGH",
                "action": "Apply encryption to the document",
                "details": "Document containing PHI should be encrypted at rest and in transit",
            })
        if access.get("issues"):
            recs.append({
                "priority": "MEDIUM",
                "action": "Restrict print/copy/modify permissions",
                "details": "Limit document permissions to prevent unauthorized access to PHI",
            })
        if audit.get("issues"):
            recs.append({
                "priority": "LOW",
                "action": "Add audit metadata (author, dates)",
                "details": "Complete metadata supports HIPAA audit trail requirements",
            })
        return recs

    def get_scan_history(self):
        return list(self._scan_history)
