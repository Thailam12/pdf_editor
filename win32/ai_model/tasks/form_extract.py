"""PDFMind 100M — Form Field Extraction.

Extracts form field information from PDFs:
- Detects field labels, types, and values
- Maps field relationships (grouped fields, dependent fields)
- Validates form completeness
"""

from typing import Dict, List, Optional


class FormExtractor:
    FIELD_TYPES = [
        "text", "number", "date", "email", "phone", "address",
        "checkbox", "radio", "dropdown", "signature", "file_upload",
        "currency", "percentage", "ssn", "url",
    ]

    def __init__(self, model=None, tokenizer=None, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def extract(self, text: str, use_model: bool = False) -> Dict:
        if use_model and self.model is not None:
            return self._model_extract(text)
        return self._rule_extract(text)

    def extract_from_pages(self, pages: List[str]) -> Dict:
        all_fields = []
        for i, page in enumerate(pages):
            result = self.extract(page)
            for field in result.get("fields", []):
                field["page"] = i + 1
                all_fields.append(field)
        return {
            "fields": all_fields,
            "total_fields": len(all_fields),
            "filled_fields": sum(1 for f in all_fields if f.get("value")),
            "empty_fields": sum(1 for f in all_fields if not f.get("value")),
        }

    def validate_form(self, fields: List[Dict]) -> Dict:
        issues = []
        required_empty = [f for f in fields if f.get("required") and not f.get("value")]
        if required_empty:
            issues.append(f"{len(required_empty)} required fields are empty")

        for field in fields:
            if field.get("value") and field.get("type"):
                if not self._validate_field_type(field):
                    issues.append(f"Field '{field.get('label')}' has invalid {field['type']} value")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "completion_rate": sum(1 for f in fields if f.get("value")) / max(len(fields), 1),
        }

    def auto_fill(self, fields: List[Dict], data: Dict) -> List[Dict]:
        for field in fields:
            label_lower = field.get("label", "").lower()
            for key, value in data.items():
                if key.lower() in label_lower or label_lower in key.lower():
                    field["value"] = str(value)
                    field["auto_filled"] = True
                    break
        return fields

    def _rule_extract(self, text: str) -> Dict:
        import re
        fields = []
        lines = text.split("\n")

        label_patterns = [
            r"^([A-Za-z\s]+):\s*(.*)$",
            r"^([A-Za-z\s]+)\s*[_\-.]\s*(.*)$",
            r"^([A-Za-z\s]+)\s*$",
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in label_patterns:
                match = re.match(pattern, line)
                if match:
                    label = match.group(1).strip()
                    value = match.group(2).strip() if match.lastindex >= 2 else ""
                    if len(label) > 2 and len(label) < 60:
                        field_type = self._infer_type(label, value)
                        fields.append({
                            "label": label,
                            "type": field_type,
                            "value": value,
                            "required": self._is_likely_required(label),
                            "page": 1,
                        })
                    break

        return {
            "fields": fields,
            "total_fields": len(fields),
            "filled_fields": sum(1 for f in fields if f.get("value")),
            "empty_fields": sum(1 for f in fields if not f.get("value")),
        }

    def _model_extract(self, text: str) -> Dict:
        import torch
        prompt = (
            "Extract all form fields from this document. "
            "For each field, provide: LABEL | TYPE | VALUE | REQUIRED\n\n"
            f"Document:\n{text[:3000]}\n\n"
            "Form Fields:"
        )
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=512, temperature=0.1)
        response = self.tokenizer.decode(output[0].tolist(), skip_special=True)

        fields = []
        for line in response.split("\n"):
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    fields.append({
                        "label": parts[0],
                        "type": parts[1] if len(parts) > 1 else "text",
                        "value": parts[2] if len(parts) > 2 else "",
                        "required": parts[3].lower() == "yes" if len(parts) > 3 else False,
                        "page": 1,
                    })

        return {
            "fields": fields,
            "total_fields": len(fields),
            "filled_fields": sum(1 for f in fields if f.get("value")),
            "empty_fields": sum(1 for f in fields if not f.get("value")),
        }

    def _infer_type(self, label: str, value: str) -> str:
        label_lower = label.lower()
        if any(w in label_lower for w in ["email", "e-mail"]):
            return "email"
        if any(w in label_lower for w in ["phone", "tel", "fax"]):
            return "phone"
        if any(w in label_lower for w in ["date", "born", "birth"]):
            return "date"
        if any(w in label_lower for w in ["amount", "price", "cost", "total", "$"]):
            return "currency"
        if any(w in label_lower for w in ["ssn", "social security"]):
            return "ssn"
        if any(w in label_lower for w in ["address", "street", "city", "zip"]):
            return "address"
        if any(w in label_lower for w in ["percent", "%"]):
            return "percentage"
        if any(w in label_lower for w in ["number", "no.", "#"]):
            return "number"
        if any(w in label_lower for w in ["check", "yes", "no"]):
            return "checkbox"
        return "text"

    def _is_likely_required(self, label: str) -> bool:
        return "*" in label or "required" in label.lower()

    def _validate_field_type(self, field: Dict) -> bool:
        value = str(field.get("value", ""))
        ftype = field.get("type", "text")
        if ftype == "email":
            return "@" in value
        if ftype == "phone":
            return any(c.isdigit() for c in value)
        if ftype == "number" or ftype == "currency":
            return value.replace(".", "").replace("-", "").replace("$", "").isdigit() or not value
        return True
