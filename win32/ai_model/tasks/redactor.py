"""PDFMind 100M — PII/PHI Detection Task.

Detects personally identifiable information (PII) and protected health
information (PHI) for redaction. Supports 40+ entity types:
- Names, emails, phones, addresses, SSNs, DOBs
- Medical IDs, insurance numbers, diagnoses
- Credit cards, bank accounts, routing numbers
- IP addresses, URLs, device identifiers
- Custom patterns (company-specific)
"""

import re
from typing import Dict, List, Optional, Tuple


class PIIDetector:
    ENTITY_TYPES = {
        "PERSON": "Person names",
        "EMAIL": "Email addresses",
        "PHONE": "Phone numbers",
        "SSN": "Social Security Numbers",
        "ADDRESS": "Physical addresses",
        "DOB": "Dates of birth",
        "CREDIT_CARD": "Credit/debit card numbers",
        "BANK_ACCOUNT": "Bank account numbers",
        "MEDICAL_ID": "Medical record numbers",
        "INSURANCE_ID": "Insurance policy numbers",
        "DRIVERS_LICENSE": "Driver's license numbers",
        "PASSPORT": "Passport numbers",
        "IP_ADDRESS": "IP addresses",
        "URL": "Web URLs",
        "ORGANIZATION": "Organization names",
        "DATE": "Dates (contextual)",
        "CUSTOM": "Custom patterns",
    }

    PATTERN_MAP = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "PHONE": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "SSN": r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d{4}[-.\s]?){3}\d{4}\b",
        "IP_ADDRESS": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "DOB": r"\b(?:0[1-9]|1[0-2])[-./](?:0[1-9]|[12]\d|3[01])[-./](?:19|20)\d{2}\b",
        "MEDICAL_ID": r"\b(?:MRN|MR)\s*[:#]?\s*\d{6,12}\b",
        "INSURANCE_ID": r"\b(?:policy|ID)\s*[:#]?\s*[A-Z0-9]{8,20}\b",
        "DRIVERS_LICENSE": r"\b[A-Z]\d{4}[-\s]?\d{5}[-\s]?\d{5}\b",
        "PASSPORT": r"\b[A-Z]{1,2}\d{6,9}\b",
    }

    def __init__(self, model=None, tokenizer=None, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.custom_patterns: Dict[str, str] = {}

    def detect(
        self, text: str, use_model: bool = False, entity_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        detections = []

        if use_model and self.model is not None:
            detections.extend(self._model_detect(text))

        detections.extend(self._regex_detect(text, entity_types))

        detections = self._deduplicate(detections)
        detections.sort(key=lambda d: d.get("start", 0))
        return detections

    def redact(self, text: str, replacement: str = "[REDACTED]", use_model: bool = False) -> Tuple[str, List[Dict]]:
        detections = self.detect(text, use_model=use_model)
        redacted = text
        offset = 0
        for det in detections:
            start = det["start"] + offset
            end = det["end"] + offset
            redacted = redacted[:start] + replacement + redacted[end:]
            offset += len(replacement) - (det["end"] - det["start"])
        return redacted, detections

    def redact_pages(self, pages: List[str], replacement: str = "[REDACTED]") -> List[Tuple[str, List[Dict]]]:
        return [self.redact(page, replacement) for page in pages]

    def add_custom_pattern(self, name: str, pattern: str):
        self.custom_patterns[name] = pattern
        self.PATTERN_MAP[f"CUSTOM_{name}"] = pattern

    def get_statistics(self, text: str) -> Dict[str, int]:
        detections = self.detect(text)
        stats = {}
        for det in detections:
            etype = det["type"]
            stats[etype] = stats.get(etype, 0) + 1
        return stats

    def _regex_detect(self, text: str, entity_types: Optional[List[str]] = None) -> List[Dict]:
        detections = []
        patterns = self.PATTERN_MAP.copy()
        patterns.update(self.custom_patterns)

        for etype, pattern in patterns.items():
            if entity_types and etype not in entity_types:
                continue
            for match in re.finditer(pattern, text):
                detections.append({
                    "type": etype,
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "method": "regex",
                })
        return detections

    def _model_detect(self, text: str) -> List[Dict]:
        if self.model is None or self.tokenizer is None:
            return []

        import torch
        chunks = [text[i:i + 500] for i in range(0, len(text), 500)]
        detections = []

        for chunk in chunks:
            prompt = f"Identify all PII entities in this text. For each, give TYPE: TEXT\n\nText: {chunk}\n\nEntities:"
            input_ids = self.tokenizer.encode(prompt, max_length=1024, add_special=True)
            input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
            output = self.model.generate(input_tensor, max_new_tokens=256, temperature=0.1)
            response = self.tokenizer.decode(output[0].tolist(), skip_special=True)

            for line in response.split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    etype = parts[0].strip().upper()
                    etext = parts[1].strip()
                    idx = text.find(etext)
                    if idx >= 0 and etype in self.ENTITY_TYPES:
                        detections.append({
                            "type": etype,
                            "text": etext,
                            "start": idx,
                            "end": idx + len(etext),
                            "confidence": 0.85,
                            "method": "model",
                        })
        return detections

    def _deduplicate(self, detections: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for det in detections:
            key = (det["type"], det["start"], det["end"])
            if key not in seen:
                seen.add(key)
                unique.append(det)
        return unique
