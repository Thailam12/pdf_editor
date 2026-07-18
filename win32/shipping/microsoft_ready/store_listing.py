"""Microsoft Store assets: descriptions, screenshots specs, features, and category optimization."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StoreAsset:
    asset_type: str = ""
    name: str = ""
    path: str = ""
    size_bytes: int = 0
    dimensions: str = ""
    description: str = ""


@dataclass
class StoreLocalization:
    language: str = "en-us"
    title: str = ""
    short_description: str = ""
    full_description: str = ""
    keywords: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    what_is_new: str = ""


class StoreListing:
    """Microsoft Store listing assets, descriptions, and optimization for maximum visibility."""

    APP_NAME = "PDFMind"
    DEVELOPER = "PDFMind Inc."
    CATEGORY = "Productivity"
    SUBCATEGORY = "Document Management"
    STORE_ID = ""

    def __init__(self):
        self._localizations: dict[str, StoreLocalization] = {}
        self._assets: list[StoreAsset] = []
        self._init_default_listing()

    def _init_default_listing(self):
        self._localizations["en-us"] = StoreLocalization(
            language="en-us",
            title="PDFMind - Intelligent PDF Editor & AI Assistant",
            short_description="Edit, annotate, merge, compress, and AI-analyze your PDFs with the most intelligent PDF editor on Windows.",
            full_description="""PDFMind is the most powerful and intelligent PDF editor designed exclusively for Windows. Built from the ground up with AI capabilities, PDFMind transforms how you work with PDF documents.

KEY FEATURES:

PDF Editing & Annotation
- Edit text directly in PDFs with full formatting control
- Add highlights, underlines, strikethroughs, and sticky notes
- Draw freehand with pressure-sensitive pen support
- Insert images, shapes, stamps, and watermarks
- Redact sensitive content permanently

AI-Powered Intelligence
- AI Summarize: Get instant summaries of lengthy documents
- AI Ask: Ask questions about your PDF content and get answers
- Smart Redaction: Automatically detect and redact PII, financial, and medical data
- AI Translation: Translate entire documents with context awareness
- Document Comparison: AI-powered difference detection

Cloud Integration
- Google Drive, Dropbox, Box, and WebDAV support
- Open, edit, and save directly to cloud storage
- Version history and collaborative sharing
- Offline editing with automatic sync

Professional Tools
- Merge and split PDFs with precision
- Compress PDFs to reduce file size by up to 90%
- OCR: Make scanned documents searchable and editable
- Digital signatures with certificate validation
- Form filling with auto-detection
- Advanced print management

Developer API
- Full REST API with OpenAPI 3.0 documentation
- Python and JavaScript SDKs
- MCP Server for AI agent integration
- Command-line interface (CLI)

Privacy & Security
- End-to-end encryption support
- Local AI processing (no data leaves your device)
- Digital signature verification
- WCAG 2.1 AA accessible
- GDPR compliant

Format Support
- Read and write PDF 1.0 through 2.0
- Export to DOCX, XLSX, PPTX, HTML, EPUB, SVG, Markdown
- Import from Word, Excel, PowerPoint, EPUB, DjVu, TIFF, SVG
- 50+ professional templates included

PDFMind is the last PDF tool you'll ever need. From casual reading to professional document management, PDFMind handles it all with elegance and intelligence.""",
            keywords=[
                "pdf editor", "pdf annotator", "pdf editor windows", "ai pdf",
                "pdf merge", "pdf compress", "pdf ocr", "pdf editor free",
                "document editor", "pdf to word", "pdf annotation",
                "pdf signer", "pdf redaction", "intelligent pdf",
                "pdf tools", "pdf maker", "pdf converter", "pdf reader",
            ],
            features=[
                "Direct text editing in PDFs",
                "AI-powered summarization and Q&A",
                "Smart automatic PII redaction",
                "Cloud storage integration",
                "Digital signatures and encryption",
                "OCR for scanned documents",
                "50+ professional templates",
                "REST API and CLI tools",
                "WCAG 2.1 AA accessible",
                "Privacy-first local AI processing",
            ],
            what_is_new="New: AI Smart Redaction, Cloud Integration, MCP Server for AI agents, 3x faster rendering with lazy page loading.",
        )

    def get_listing(self, language: str = "en-us") -> StoreLocalization:
        return self._localizations.get(language, self._localizations["en-us"])

    def get_all_localizations(self) -> list[StoreLocalization]:
        return list(self._localizations.values())

    def add_localization(self, localization: StoreLocalization):
        self._localizations[localization.language] = localization

    def get_required_assets(self) -> list[StoreAsset]:
        return [
            StoreAsset("logo", "Store Logo", "assets/store_logo.png", dimensions="300x300"),
            StoreAsset("logo_large", "Large Logo", "assets/store_logo_large.png", dimensions="150x150"),
            StoreAsset("screenshot_1", "Screenshot - Main Editor", "assets/screenshot_editor.png", dimensions="1920x1080"),
            StoreAsset("screenshot_2", "Screenshot - AI Features", "assets/screenshot_ai.png", dimensions="1920x1080"),
            StoreAsset("screenshot_3", "Screenshot - Dark Theme", "assets/screenshot_dark.png", dimensions="1920x1080"),
            StoreAsset("screenshot_4", "Screenshot - Templates", "assets/screenshot_templates.png", dimensions="1920x1080"),
            StoreAsset("screenshot_5", "Screenshot - Cloud Integration", "assets/screenshot_cloud.png", dimensions="1920x1080"),
            StoreAsset("promo", "Promotional Image", "assets/promo.png", dimensions="1180x540"),
            StoreAsset("hero", "Hero Image", "assets/hero.png", dimensions="1920x1080"),
        ]

    def get_screenshot_descriptions(self) -> list[dict]:
        return [
            {"file": "screenshot_1.png", "caption": "PDFMind's clean, intuitive editor with direct text editing"},
            {"file": "screenshot_2.png", "caption": "AI-powered features: summarize, ask questions, and smart redaction"},
            {"file": "screenshot_3.png", "caption": "Beautiful dark theme with 10+ built-in themes"},
            {"file": "screenshot_4.png", "caption": "50+ professional templates for business, legal, and more"},
            {"file": "screenshot_5.png", "caption": "Seamless cloud integration with Google Drive, Dropbox, and more"},
        ]

    def get_store_page_url(self) -> str:
        return f"https://apps.microsoft.com/store/detail/{self.STORE_ID}" if self.STORE_ID else ""

    def get_seo_keywords(self) -> list[str]:
        return [
            "best pdf editor windows 11", "free pdf editor", "ai pdf editor",
            "pdf annotator", "pdf editor ai", "pdf merge tool", "pdf compressor",
            "pdf ocr windows", "pdf signer", "pdf redaction tool",
            "intelligent pdf", "smart pdf editor", "pdf editor pro",
            "document editor windows", "pdf tools 2024", "microsoft store pdf",
        ]

    def get_competitive_keywords(self) -> list[str]:
        return [
            "adobe acrobat alternative", "foxit alternative", "pdf element alternative",
            "nitro pdf alternative", "pdf xchange alternative",
            "best pdf editor 2024", "cheaper than adobe",
        ]

    def get_category_suggestions(self) -> list[dict]:
        return [
            {"category": "Productivity", "subcategory": "Document Management", "match_score": 95},
            {"category": "Business", "subcategory": "Office Suites", "match_score": 85},
            {"category": "Developer tools", "subcategory": "Utilities", "match_score": 70},
        ]

    def generate_store_description_markdown(self) -> str:
        loc = self.get_listing()
        features = "\n".join(f"- {f}" for f in loc.features)
        return f"""# {loc.title}

{loc.short_description}

## Features
{features}

## What's New
{loc.what_is_new}

## System Requirements
- Windows 10 (1809+) or Windows 11
- 4 GB RAM minimum, 8 GB recommended
- 500 MB available disk space
- .NET 6+ runtime (included)

## Privacy
PDFMind processes all AI features locally on your device. No document data is sent to external servers.

## Support
- Website: https://pdfmind.app
- Email: support@pdfmind.app
- Documentation: https://docs.pdfmind.app
- GitHub: https://github.com/pdfmind/pdfmind
"""
