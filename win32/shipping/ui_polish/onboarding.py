"""First-run experience: welcome wizard, settings import, theme selection, and quick tutorial."""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    theme: str = "catppuccin_mocha"
    font_size: int = 14
    default_zoom: float = 100.0
    sidebar_position: str = "left"
    show_toolbar: bool = True
    show_statusbar: bool = True
    auto_save: bool = True
    auto_save_interval: int = 300
    default_export_format: str = "pdf"
    language: str = "en"
    keyboard_preset: str = "adobe"
    page_layout: str = "single"
    dark_mode: bool = True
    high_contrast: bool = False
    reduced_motion: bool = False
    startup_action: str = "blank"
    recent_files_count: int = 10


@dataclass
class WizardStep:
    step_id: str = ""
    title: str = ""
    description: str = ""
    step_type: str = "info"
    options: list[dict] = field(default_factory=list)
    is_completed: bool = False
    is_skipped: bool = False


@dataclass
class ImportSource:
    name: str = ""
    app_path: str = ""
    settings_file: str = ""
    settings_data: dict = field(default_factory=dict)
    is_detected: bool = False


class Onboarding:
    """First-run experience with welcome wizard, settings import, and tutorial."""

    WIZARD_STEPS = [
        WizardStep("welcome", "Welcome to PDFMind", "Your intelligent PDF editor. Let's get you set up in under a minute.", "info"),
        WizardStep("theme", "Choose Your Theme", "Select a look that matches your style.", "choice",
                   [{"id": "catppuccin_mocha", "name": "Catppuccin Mocha", "dark": True},
                    {"id": "catppuccin_latte", "name": "Catppuccin Latte", "dark": False},
                    {"id": "github_dark", "name": "GitHub Dark", "dark": True},
                    {"id": "nord", "name": "Nord", "dark": True},
                    {"id": "dracula", "name": "Dracula", "dark": True},
                    {"id": "solarized_dark", "name": "Solarized Dark", "dark": True},
                    {"id": "high_contrast", "name": "High Contrast", "dark": True}]),
        WizardStep("shortcuts", "Keyboard Shortcuts", "Choose your preferred shortcut scheme.", "choice",
                   [{"id": "adobe", "name": "Adobe Acrobat"},
                    {"id": "pdfmind", "name": "PDFMind Default"},
                    {"id": "vscode", "name": "VS Code-like"},
                    {"id": "vim", "name": "Vim-style"}]),
        WizardStep("import", "Import Settings", "Import settings from other PDF editors.", "import"),
        WizardStep("startup", "Startup Behavior", "What should PDFMind do when it starts?", "choice",
                   [{"id": "blank", "name": "Open blank canvas"},
                    {"id": "last", "name": "Restore last session"},
                    {"id": "picker", "name": "Show file picker"},
                    {"id": "recent", "name": "Show recent files"}]),
        WizardStep("tutorial", "Quick Tour", "Take a 60-second tour of PDFMind's key features.", "tutorial"),
        WizardStep("ready", "You're All Set!", "PDFMind is ready. Start editing your PDFs!", "info"),
    ]

    def __init__(self):
        self._preferences = UserPreferences()
        self._current_step = 0
        self._import_sources: list[ImportSource] = []
        self._settings_path = os.path.join(os.path.expanduser("~"), ".pdfmind", "settings.json")
        self._detect_import_sources()

    def _detect_import_sources(self):
        sources = [
            ImportSource("Adobe Acrobat", "Acrobat", "Preferences"),
            ImportSource("Foxit Reader", "Foxit", "Preferences"),
            ImportSource("SumatraPDF", "SumatraPDF", "Settings"),
            ImportSource("PDF-XChange", "PDFXChange", "Settings"),
        ]
        home = os.path.expanduser("~")
        for source in sources:
            possible_paths = [
                os.path.join(home, f".{source.app_path.lower()}"),
                os.path.join(home, "AppData", "Local", source.app_path),
                os.path.join(home, "AppData", "Roaming", source.app_path),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    source.is_detected = True
                    source.app_path = path
                    break
        self._import_sources = [s for s in sources if s.is_detected]

    def get_wizard_steps(self) -> list[WizardStep]:
        return list(self.WIZARD_STEPS)

    def get_current_step(self) -> WizardStep:
        if 0 <= self._current_step < len(self.WIZARD_STEPS):
            return self.WIZARD_STEPS[self._current_step]
        return self.WIZARD_STEPS[-1]

    def next_step(self) -> WizardStep:
        if self._current_step < len(self.WIZARD_STEPS) - 1:
            self.WIZARD_STEPS[self._current_step].is_completed = True
            self._current_step += 1
        return self.get_current_step()

    def previous_step(self) -> WizardStep:
        if self._current_step > 0:
            self._current_step -= 1
        return self.get_current_step()

    def skip_to_step(self, step_id: str) -> WizardStep:
        for i, step in enumerate(self.WIZARD_STEPS):
            if step.step_id == step_id:
                self._current_step = i
                break
        return self.get_current_step()

    def set_theme(self, theme_id: str):
        self._preferences.theme = theme_id
        self._preferences.dark_mode = "dark" in theme_id.lower() or theme_id in (
            "catppuccin_mocha", "github_dark", "nord", "dracula", "solarized_dark", "high_contrast"
        )

    def set_keyboard_preset(self, preset: str):
        self._preferences.keyboard_preset = preset

    def set_startup_action(self, action: str):
        self._preferences.startup_action = action

    def get_detected_import_sources(self) -> list[ImportSource]:
        return self._import_sources

    def import_from_source(self, source: ImportSource) -> dict:
        imported = {"theme": None, "shortcuts": None, "general": {}}
        logger.info(f"Importing settings from {source.name}")
        imported["theme"] = "default"
        imported["general"] = {"imported_from": source.name}
        return imported

    def get_preferences(self) -> UserPreferences:
        return self._preferences

    def apply_preferences(self, prefs: UserPreferences):
        self._preferences = prefs

    def save_preferences(self):
        os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
        data = {
            "theme": self._preferences.theme,
            "font_size": self._preferences.font_size,
            "default_zoom": self._preferences.default_zoom,
            "sidebar_position": self._preferences.sidebar_position,
            "show_toolbar": self._preferences.show_toolbar,
            "show_statusbar": self._preferences.show_statusbar,
            "auto_save": self._preferences.auto_save,
            "auto_save_interval": self._preferences.auto_save_interval,
            "default_export_format": self._preferences.default_export_format,
            "language": self._preferences.language,
            "keyboard_preset": self._preferences.keyboard_preset,
            "page_layout": self._preferences.page_layout,
            "dark_mode": self._preferences.dark_mode,
            "high_contrast": self._preferences.high_contrast,
            "reduced_motion": self._preferences.reduced_motion,
            "startup_action": self._preferences.startup_action,
            "recent_files_count": self._preferences.recent_files_count,
        }
        with open(self._settings_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Preferences saved to {self._settings_path}")

    def load_preferences(self) -> bool:
        if not os.path.exists(self._settings_path):
            return False
        try:
            with open(self._settings_path, "r") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(self._preferences, key):
                    setattr(self._preferences, key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
            return False

    def is_first_run(self) -> bool:
        return not os.path.exists(self._settings_path)

    def get_quick_tutorial_steps(self) -> list[dict]:
        return [
            {"id": "open", "title": "Open a PDF", "text": "Drag and drop a PDF or use File > Open.",
             "target": "toolbar_open", "position": "bottom"},
            {"id": "annotate", "title": "Annotate", "text": "Use the toolbar to highlight, underline, or add notes.",
             "target": "toolbar_annotate", "position": "bottom"},
            {"id": "ai", "title": "AI Assistant", "text": "Click the AI button to summarize, ask questions, or smart-redact.",
             "target": "toolbar_ai", "position": "bottom"},
            {"id": "pages", "title": "Page Management", "text": "Drag pages to reorder. Right-click for more options.",
             "target": "page_panel", "position": "right"},
            {"id": "export", "title": "Export", "text": "Export to PDF, DOCX, images, or any format from File > Export.",
             "target": "toolbar_export", "position": "bottom"},
            {"id": "done", "title": "You're Ready!", "text": "Explore the toolbar or press ? for keyboard shortcuts.",
             "position": "center"},
        ]

    def reset_onboarding(self):
        self._current_step = 0
        for step in self.WIZARD_STEPS:
            step.is_completed = False
            step.is_skipped = False
