"""Contextual help: smart tooltips, feature discovery, what's new, and tips of the day."""

import logging
import random
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Tooltip:
    target_id: str = ""
    text: str = ""
    description: str = ""
    shortcut: str = ""
    category: str = "general"
    priority: int = 0
    max_shows: int = 5
    show_count: int = 0
    is_dismissed: bool = False


@dataclass
class FeatureDiscovery:
    feature_id: str = ""
    name: str = ""
    description: str = ""
    icon: str = ""
    category: str = ""
    is_new: bool = True
    tutorial_url: str = ""
    show_after: str = ""
    dismissed: bool = False


@dataclass
class WhatsNewEntry:
    version: str = ""
    date: str = ""
    title: str = ""
    description: str = ""
    category: str = ""
    is_read: bool = False


@dataclass
class TipOfDay:
    tip_id: int = 0
    title: str = ""
    content: str = ""
    category: str = "general"
    difficulty: str = "beginner"


class Tooltips:
    """Smart tooltips, feature discovery, what's new notifications, and tips of the day."""

    def __init__(self):
        self._tooltips: dict[str, Tooltip] = {}
        self._discoveries: dict[str, FeatureDiscovery] = {}
        self._tips: list[TipOfDay] = []
        self._whats_new: list[WhatsNewEntry] = []
        self._dismissed_ids: set[str] = set()
        self._current_tip_index = 0
        self._init_tooltips()
        self._init_tips()
        self._init_whats_new()
        self._init_discoveries()

    def _init_tooltips(self):
        defs = [
            ("toolbar_open", "Open PDF (Ctrl+O)", "Open a PDF file from your computer or cloud storage", "Ctrl+O", "file"),
            ("toolbar_save", "Save (Ctrl+S)", "Save the current document", "Ctrl+S", "file"),
            ("toolbar_print", "Print (Ctrl+P)", "Print the current document with advanced settings", "Ctrl+P", "file"),
            ("toolbar_undo", "Undo (Ctrl+Z)", "Undo the last action", "Ctrl+Z", "edit"),
            ("toolbar_redo", "Redo (Ctrl+Y)", "Redo the last undone action", "Ctrl+Y", "edit"),
            ("toolbar_select", "Select Tool (V)", "Select and move elements on the page", "V", "tools"),
            ("toolbar_text", "Text Tool (T)", "Add or edit text on the page", "T", "tools"),
            ("toolbar_highlight", "Highlight (H)", "Highlight text with color", "H", "annotate"),
            ("toolbar_underline", "Underline (U)", "Underline text", "U", "annotate"),
            ("toolbar_note", "Sticky Note (N)", "Add a sticky note comment", "N", "annotate"),
            ("toolbar_draw", "Draw (D)", "Freehand drawing on the page", "D", "tools"),
            ("toolbar_shapes", "Shapes (S)", "Add rectangles, circles, and lines", "S", "tools"),
            ("toolbar_image", "Image (I)", "Insert an image onto the page", "I", "tools"),
            ("toolbar_crop", "Crop (C)", "Crop the page to remove margins", "C", "tools"),
            ("toolbar_ai", "AI Assistant (Ctrl+AI)", "Access AI-powered features", "", "ai"),
            ("toolbar_merge", "Merge", "Combine multiple PDFs into one", "", "tools"),
            ("toolbar_split", "Split", "Split a PDF into separate files", "", "tools"),
            ("toolbar_compress", "Compress", "Reduce PDF file size", "", "tools"),
            ("toolbar_redact", "Redact (R)", "Permanently remove sensitive content", "R", "security"),
            ("toolbar_sign", "Digital Sign", "Add a digital signature", "", "security"),
            ("page_panel", "Page Thumbnails", "Drag pages to reorder. Right-click for page operations.", "", "navigation"),
            ("sidebar_tools", "Tool Panel", "Expand for detailed tool settings and properties.", "", "navigation"),
            ("zoom_control", "Zoom Control", "Zoom in/out. Use Ctrl+0 to fit page, Ctrl+= to zoom to 100%.", "", "view"),
            ("search_bar", "Search (Ctrl+F)", "Find text across all pages", "Ctrl+F", "tools"),
        ]
        for target_id, text, desc, shortcut, category in defs:
            self._tooltips[target_id] = Tooltip(
                target_id=target_id, text=text, description=desc,
                shortcut=shortcut, category=category,
            )

    def _init_tips(self):
        self._tips = [
            TipOfDay(1, "Quick Summarize", "Select text and press Ctrl+Shift+S to instantly summarize it with AI.", "ai"),
            TipOfDay(2, "Batch Export", "Hold Ctrl while selecting multiple files in Open to batch-export them.", "productivity"),
            TipOfDay(3, "Keyboard Shortcuts", "Press ? to see all keyboard shortcuts. Customize them in Settings > Shortcuts.", "general"),
            TipOfDay(4, "Smart Redaction", "Use AI > Smart Redact to automatically find and redact PII, financial, and medical data.", "ai"),
            TipOfDay(5, "Compare PDFs", "Open two PDFs side-by-side with View > Compare to see differences highlighted.", "tools"),
            TipOfDay(6, "Form Filling", "Click on form fields to fill them in. Tab moves to the next field.", "tools"),
            TipOfDay(7, "Cloud Sync", "Connect Google Drive or Dropbox for automatic cloud backup.", "integrations"),
            TipOfDay(8, "Page Templates", "Use File > New from Template to start with professional templates.", "productivity"),
            TipOfDay(9, "OCR Scanned PDFs", "Click Edit > OCR to make scanned documents searchable and editable.", "ai"),
            TipOfDay(10, "Dark Mode", "Toggle dark mode with Ctrl+Shift+D for comfortable reading.", "appearance"),
            TipOfDay(11, "Signature Templates", "Save frequently used signatures for quick access.", "security"),
            TipOfDay(12, "Watermark Wizard", "Add watermarks to all pages with Tools > Watermark. Supports text and images.", "tools"),
            TipOfDay(13, "Export to Word", "Convert PDFs back to editable Word documents with File > Export > DOCX.", "export"),
            TipOfDay(14, "Custom Themes", "Create your own theme in Settings > Appearance > Theme Editor.", "appearance"),
            TipOfDay(15, "API Access", "Use the REST API or CLI (pdfmind) for automation. See Developer > API Docs.", "developer"),
        ]

    def _init_whats_new(self):
        self._whats_new = [
            WhatsNewEntry("1.0.0", "2026-01-15", "Initial Release",
                          "PDFMind launches with intelligent PDF editing, AI assistant, and cloud integrations.", "release"),
            WhatsNewEntry("1.1.0", "2026-02-01", "AI Smart Redaction",
                          "AI-powered smart redaction automatically finds and removes PII, financial, and medical data.", "feature"),
            WhatsNewEntry("1.1.0", "2026-02-01", "Cloud Integration",
                          "Connect Google Drive, Dropbox, Box, and WebDAV for seamless cloud file access.", "feature"),
            WhatsNewEntry("1.1.0", "2026-02-01", "Template Gallery",
                          "50+ professional templates for business, legal, medical, and government documents.", "feature"),
            WhatsNewEntry("1.2.0", "2026-03-01", "MCP Server",
                          "PDFMind now works as an MCP server for AI agents like Claude and GPT.", "feature"),
            WhatsNewEntry("1.2.0", "2026-03-01", "Performance Boost",
                          "Lazy page loading and parallel rendering for 3x faster document opening.", "improvement"),
        ]

    def _init_discoveries(self):
        self._discoveries = {
            "ai_summarize": FeatureDiscovery(
                "ai_summarize", "AI Summarize", "Get instant summaries of long documents",
                "sparkles", "ai", is_new=True,
            ),
            "ai_redact": FeatureDiscovery(
                "ai_redact", "Smart Redaction", "Automatically find and redact sensitive data",
                "shield", "ai", is_new=True,
            ),
            "smart_merge": FeatureDiscovery(
                "smart_merge", "Smart Merge", "Intelligently merge PDFs with page matching",
                "layers", "tools", is_new=True,
            ),
            "batch_export": FeatureDiscovery(
                "batch_export", "Batch Export", "Export multiple PDFs in one operation",
                "export", "productivity",
            ),
        }

    def get_tooltip(self, target_id: str) -> Optional[Tooltip]:
        tooltip = self._tooltips.get(target_id)
        if tooltip and not tooltip.is_dismissed and tooltip.show_count < tooltip.max_shows:
            tooltip.show_count += 1
            return tooltip
        return None

    def dismiss_tooltip(self, target_id: str):
        if target_id in self._tooltips:
            self._tooltips[target_id].is_dismissed = True

    def get_tooltips_by_category(self, category: str) -> list[Tooltip]:
        return [t for t in self._tooltips.values() if t.category == category]

    def get_unseen_discoveries(self) -> list[FeatureDiscovery]:
        return [d for d in self._discoveries.values() if d.is_new and not d.dismissed]

    def dismiss_discovery(self, feature_id: str):
        if feature_id in self._discoveries:
            self._discoveries[feature_id].dismissed = True
            self._discoveries[feature_id].is_new = False

    def get_tip_of_the_day(self) -> TipOfDay:
        if not self._tips:
            return TipOfDay()
        tip = self._tips[self._current_tip_index % len(self._tips)]
        self._current_tip_index += 1
        return tip

    def get_random_tip(self) -> TipOfDay:
        return random.choice(self._tips) if self._tips else TipOfDay()

    def get_tips_by_category(self, category: str) -> list[TipOfDay]:
        return [t for t in self._tips if t.category == category]

    def get_whats_new(self, unread_only: bool = False) -> list[WhatsNewEntry]:
        entries = self._whats_new
        if unread_only:
            entries = [e for e in entries if not e.is_read]
        return entries

    def mark_whats_new_read(self, version: str = None):
        for entry in self._whats_new:
            if version is None or entry.version == version:
                entry.is_read = True

    def get_feature_tour(self) -> list[dict]:
        return [
            {"step": 1, "title": "Edit Text", "text": "Click any text to edit it directly on the page.", "target": "page_content"},
            {"step": 2, "title": "Annotate", "text": "Use the annotate toolbar to highlight, underline, or add notes.", "target": "toolbar_annotate"},
            {"step": 3, "title": "AI Power", "text": "Click AI for summarization, Q&A, and smart redaction.", "target": "toolbar_ai"},
            {"step": 4, "title": "Pages", "text": "Drag pages to reorder. Split, merge, or rotate from the page panel.", "target": "page_panel"},
            {"step": 5, "title": "Export", "text": "Export to any format: PDF, DOCX, images, HTML, and more.", "target": "toolbar_export"},
        ]
