"""All features free and open-source under MIT license. No pricing tiers."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PricingFeature:
    name: str = ""
    description: str = ""
    included: bool = True


class PricingTier:
    """All features are free and open-source under the MIT license."""

    def __init__(self):
        self._features = self._create_features()

    def _create_features(self) -> list[PricingFeature]:
        return [
            PricingFeature("PDF Viewing", "Open and read PDFs"),
            PricingFeature("Basic Annotations", "Highlights, notes, shapes"),
            PricingFeature("Text Editing", "Edit text directly in PDFs"),
            PricingFeature("AI Summarize", "AI-powered document summaries"),
            PricingFeature("AI Q&A", "Ask questions about documents"),
            PricingFeature("Smart Redaction", "Auto-detect and redact PII"),
            PricingFeature("OCR", "Make scanned PDFs searchable"),
            PricingFeature("Merge/Split", "Combine or split PDFs"),
            PricingFeature("Compression", "Reduce PDF file size"),
            PricingFeature("Digital Signatures", "Sign PDFs digitally"),
            PricingFeature("Cloud Integration", "Google Drive, Dropbox, etc."),
            PricingFeature("Export Formats", "DOCX, XLSX, PPTX, EPUB"),
            PricingFeature("Templates", "Professional document templates"),
            PricingFeature("API Access", "REST API and webhooks"),
            PricingFeature("CLI Tools", "Command-line interface"),
            PricingFeature("Custom Themes", "Create and import themes"),
            PricingFeature("SSO/SAML", "Enterprise authentication"),
            PricingFeature("Admin Dashboard", "Team management"),
            PricingFeature("Audit Logging", "Track all actions"),
            PricingFeature("Support", "Community support"),
        ]

    def get_all_features(self) -> list[PricingFeature]:
        return list(self._features)

    def get_feature_matrix(self) -> list[PricingFeature]:
        return list(self._features)

    def get_pricing_page_data(self) -> dict:
        return {
            "message": "All features are free and open-source under the MIT license.",
            "license": "MIT",
            "feature_count": len(self._features),
            "features": [{"name": f.name, "description": f.description, "included": f.included} for f in self._features],
        }
