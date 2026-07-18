"""Interactive tutorial: step-by-step guided tours with UI highlighting and overlay instructions."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TutorialStep:
    step_id: str = ""
    title: str = ""
    description: str = ""
    target_element: str = ""
    highlight_style: str = "glow"
    overlay_position: str = "bottom"
    action_required: str = ""
    action_target: str = ""
    media_url: str = ""
    tooltip_text: str = ""


@dataclass
class TutorialTour:
    tour_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    steps: list[TutorialStep] = field(default_factory=list)
    estimated_time_sec: int = 60
    difficulty: str = "beginner"
    is_completed: bool = False
    progress: float = 0.0


@dataclass
class TutorialProgress:
    user_id: str = "default"
    completed_tours: list[str] = field(default_factory=list)
    current_tour: str = ""
    current_step: int = 0
    total_time_spent_sec: int = 0
    achievements: list[dict] = field(default_factory=list)


class InteractiveTutorial:
    """Guided tours with element highlighting, overlay instructions, and completion tracking."""

    def __init__(self):
        self._tours: dict[str, TutorialTour] = {}
        self._progress = TutorialProgress()
        self._register_tours()

    def _register_tours(self):
        getting_started = TutorialTour(
            tour_id="getting_started", name="Getting Started",
            description="Learn the basics of PDFMind in 2 minutes",
            category="basics", estimated_time_sec=120, difficulty="beginner",
            steps=[
                TutorialStep("gs_open", "Open a PDF", "Click the Open button or drag a PDF into the window.",
                             "toolbar_open", "glow", "bottom", "click", "toolbar_open"),
                TutorialStep("gs_navigate", "Navigate Pages", "Use the page thumbnails on the left to navigate.",
                             "page_panel", "border", "right", "click", "page_panel"),
                TutorialStep("gs_zoom", "Zoom In/Out", "Use Ctrl+scroll or the zoom controls to zoom.",
                             "zoom_control", "glow", "top", "scroll", "page_content"),
                TutorialStep("gs_edit_text", "Edit Text", "Click any text block to edit it directly.",
                             "page_content", "border", "bottom", "click", "text_block"),
                TutorialStep("gs_annotate", "Annotate", "Select the Highlight tool and drag over text.",
                             "toolbar_highlight", "glow", "bottom", "click", "toolbar_highlight"),
                TutorialStep("gs_save", "Save", "Press Ctrl+S to save your changes.",
                             "toolbar_save", "glow", "bottom", "keypress", "Ctrl+S"),
            ],
        )
        ai_features = TutorialTour(
            tour_id="ai_features", name="AI Features",
            description="Discover PDFMind's AI-powered capabilities",
            category="ai", estimated_time_sec=180, difficulty="intermediate",
            steps=[
                TutorialStep("ai_summarize", "AI Summarize", "Click AI > Summarize to get a document summary.",
                             "toolbar_ai", "glow", "bottom", "click", "toolbar_ai"),
                TutorialStep("ai_ask", "Ask Questions", "Use AI > Ask to question the document content.",
                             "ai_ask_input", "border", "top", "type", "ai_ask_input"),
                TutorialStep("ai_redact", "Smart Redaction", "AI > Smart Redact automatically finds PII.",
                             "toolbar_ai", "glow", "bottom", "click", "ai_redact_menu"),
                TutorialStep("ai_translate", "Translation", "Use AI > Translate to translate the document.",
                             "toolbar_ai", "glow", "bottom", "click", "ai_translate_menu"),
            ],
        )
        annotation = TutorialTour(
            tour_id="annotation", name="Annotation Mastery",
            description="Master all annotation tools in PDFMind",
            category="tools", estimated_time_sec=150, difficulty="beginner",
            steps=[
                TutorialStep("ann_highlight", "Highlighting", "Select the Highlight tool and drag over text to highlight.",
                             "toolbar_highlight", "glow", "bottom", "click", "toolbar_highlight"),
                TutorialStep("ann_underline", "Underlining", "Use the Underline tool to underline important text.",
                             "toolbar_underline", "glow", "bottom", "click", "toolbar_underline"),
                TutorialStep("ann_note", "Sticky Notes", "Click the Note tool then click anywhere to add a note.",
                             "toolbar_note", "glow", "bottom", "click", "toolbar_note"),
                TutorialStep("ann_shapes", "Shapes", "Add rectangles, arrows, and circles with the Shapes tool.",
                             "toolbar_shapes", "glow", "bottom", "click", "toolbar_shapes"),
                TutorialStep("ann_draw", "Freehand Draw", "Use the Draw tool to freehand draw on the page.",
                             "toolbar_draw", "glow", "bottom", "click", "toolbar_draw"),
                TutorialStep("ann_stamps", "Stamps", "Add pre-built stamps like Approved, Draft, or Confidential.",
                             "toolbar_stamp", "glow", "bottom", "click", "toolbar_stamp"),
            ],
        )
        security = TutorialTour(
            tour_id="security", name="Security & Signing",
            description="Learn about PDFMind's security features",
            category="security", estimated_time_sec=120, difficulty="intermediate",
            steps=[
                TutorialStep("sec_redact", "Redaction", "Use the Redact tool to permanently remove sensitive content.",
                             "toolbar_redact", "glow", "bottom", "click", "toolbar_redact"),
                TutorialStep("sec_encrypt", "Encryption", "Go to File > Encrypt to password-protect your PDF.",
                             "menu_file", "border", "bottom", "click", "menu_encrypt"),
                TutorialStep("sec_sign", "Digital Signatures", "Add a digital signature with Tools > Sign.",
                             "toolbar_sign", "glow", "bottom", "click", "toolbar_sign"),
            ],
        )
        for tour in [getting_started, ai_features, annotation, security]:
            self._tours[tour.tour_id] = tour

    def register_tour(self, tour: TutorialTour):
        self._tours[tour.tour_id] = tour

    def get_all_tours(self) -> list[TutorialTour]:
        return list(self._tours.values())

    def get_tour(self, tour_id: str) -> Optional[TutorialTour]:
        return self._tours.get(tour_id)

    def get_tours_by_category(self, category: str) -> list[TutorialTour]:
        return [t for t in self._tours.values() if t.category == category]

    def start_tour(self, tour_id: str) -> Optional[TutorialStep]:
        tour = self._tours.get(tour_id)
        if not tour:
            return None
        self._progress.current_tour = tour_id
        self._progress.current_step = 0
        if tour.steps:
            return tour.steps[0]
        return None

    def next_step(self) -> Optional[TutorialStep]:
        tour = self._tours.get(self._progress.current_tour)
        if not tour:
            return None
        self._progress.current_step += 1
        if self._progress.current_step >= len(tour.steps):
            self._complete_tour(tour)
            return None
        return tour.steps[self._progress.current_step]

    def previous_step(self) -> Optional[TutorialStep]:
        tour = self._tours.get(self._progress.current_tour)
        if not tour:
            return None
        if self._progress.current_step > 0:
            self._progress.current_step -= 1
        return tour.steps[self._progress.current_step]

    def go_to_step(self, step_index: int) -> Optional[TutorialStep]:
        tour = self._tours.get(self._progress.current_tour)
        if not tour or step_index < 0 or step_index >= len(tour.steps):
            return None
        self._progress.current_step = step_index
        return tour.steps[step_index]

    def _complete_tour(self, tour: TutorialTour):
        tour.is_completed = True
        tour.progress = 1.0
        if tour.tour_id not in self._progress.completed_tours:
            self._progress.completed_tours.append(tour.tour_id)
        self._progress.current_tour = ""
        self._progress.current_step = 0
        self._check_achievements()
        logger.info(f"Completed tour: {tour.name}")

    def _check_achievements(self):
        completed = len(self._progress.completed_tours)
        achievement_defs = [
            (1, "First Steps", "Completed your first tutorial"),
            (3, "Tour Guide", "Completed 3 tutorials"),
            (5, "PDFMaster", "Completed all tutorials"),
        ]
        for count, name, desc in achievement_defs:
            if completed >= count:
                existing = [a["id"] for a in self._progress.achievements]
                if name not in existing:
                    self._progress.achievements.append({
                        "id": name, "description": desc,
                        "unlocked_at": "now",
                    })

    def get_progress(self) -> TutorialProgress:
        total = sum(len(t.steps) for t in self._tours.values())
        completed = sum(len(t.steps) for t in self._tours.values() if t.is_completed)
        self._progress.total_time_spent_sec = 0
        return self._progress

    def get_completion_percentage(self) -> float:
        total = len(self._tours)
        if total == 0:
            return 0.0
        completed = sum(1 for t in self._tours.values() if t.is_completed)
        return (completed / total) * 100

    def skip_tour(self):
        self._progress.current_tour = ""
        self._progress.current_step = 0

    def reset_progress(self):
        self._progress = TutorialProgress()
        for tour in self._tours.values():
            tour.is_completed = False
            tour.progress = 0.0

    def get_step_overlay(self, step: TutorialStep) -> dict:
        return {
            "target": step.target_element,
            "highlight": step.highlight_style,
            "position": step.overlay_position,
            "title": step.title,
            "description": step.description,
            "action": step.action_required,
            "step_id": step.step_id,
            "has_action": bool(step.action_required),
        }

    def get_step_position_styles(self, step: TutorialStep) -> dict:
        positions = {
            "top": {"arrow_direction": "down", "margin_bottom": "8px"},
            "bottom": {"arrow_direction": "up", "margin_top": "8px"},
            "left": {"arrow_direction": "right", "margin_right": "8px"},
            "right": {"arrow_direction": "left", "margin_left": "8px"},
            "center": {"arrow_direction": "none", "margin": "0 auto"},
        }
        return positions.get(step.overlay_position, positions["bottom"])
