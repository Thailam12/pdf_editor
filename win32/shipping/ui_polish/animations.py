"""UI animations: page transitions, zoom, panel slides, tool hovers, and loading spinners."""

import math
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnimationKeyframe:
    time_pct: float = 0.0
    properties: dict = field(default_factory=dict)
    easing: str = "linear"


@dataclass
class AnimationDefinition:
    name: str = ""
    duration_ms: int = 300
    keyframes: list[AnimationKeyframe] = field(default_factory=list)
    loop: bool = False
    auto_reverse: bool = False
    delay_ms: int = 0


@dataclass
class AnimationState:
    animation_name: str = ""
    current_time_ms: float = 0
    is_playing: bool = False
    is_paused: bool = False
    progress: float = 0.0
    current_properties: dict = field(default_factory=dict)


class UIAnimations:
    """Animation engine for PDFMind UI providing transitions, zoom, and visual effects."""

    EASING_FUNCTIONS = {
        "linear": lambda t: t,
        "ease_in": lambda t: t * t,
        "ease_out": lambda t: t * (2 - t),
        "ease_in_out": lambda t: t * t * (3 - 2 * t),
        "ease_in_cubic": lambda t: t ** 3,
        "ease_out_cubic": lambda t: 1 - (1 - t) ** 3,
        "ease_in_out_cubic": lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
        "bounce_out": lambda t: 7.5625 * t ** 2 if t < 0.5 else 1 - (1.5 - t) ** 2 * 2.25 if t < 0.75 else 1 - (1 - t) ** 2 * 4.9375 if t < 0.9375 else 1 + (2 - t) ** 2 * 6.25,
        "elastic_out": lambda t: 0.05 * math.sin(10 * (t - 0.075) * math.pi / 0.075) * (1 - t) ** 2 if t > 0.075 else 1,
    }

    def __init__(self):
        self._animations: dict[str, AnimationDefinition] = {}
        self._active_states: dict[str, AnimationState] = {}
        self._presets: dict[str, AnimationDefinition] = {}
        self._create_presets()

    def _create_presets(self):
        self._presets["page_transition_slide_left"] = AnimationDefinition(
            name="page_transition_slide_left", duration_ms=350,
            keyframes=[
                AnimationKeyframe(0.0, {"translateX": "100%", "opacity": 0}),
                AnimationKeyframe(1.0, {"translateX": "0%", "opacity": 1}),
            ],
            easing="ease_out_cubic",
        )
        self._presets["page_transition_slide_right"] = AnimationDefinition(
            name="page_transition_slide_right", duration_ms=350,
            keyframes=[
                AnimationKeyframe(0.0, {"translateX": "-100%", "opacity": 0}),
                AnimationKeyframe(1.0, {"translateX": "0%", "opacity": 1}),
            ],
            easing="ease_out_cubic",
        )
        self._presets["page_transition_fade"] = AnimationDefinition(
            name="page_transition_fade", duration_ms=300,
            keyframes=[
                AnimationKeyframe(0.0, {"opacity": 0}),
                AnimationKeyframe(1.0, {"opacity": 1}),
            ],
            easing="ease_in_out",
        )
        self._presets["page_transition_crossfade"] = AnimationDefinition(
            name="page_transition_crossfade", duration_ms=400,
            keyframes=[
                AnimationKeyframe(0.0, {"opacity": 0, "scale": 0.95}),
                AnimationKeyframe(0.5, {"opacity": 0.5, "scale": 0.98}),
                AnimationKeyframe(1.0, {"opacity": 1, "scale": 1.0}),
            ],
            easing="ease_in_out",
        )
        self._presets["zoom_in"] = AnimationDefinition(
            name="zoom_in", duration_ms=250,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 1.0, "transformOrigin": "center"}),
                AnimationKeyframe(1.0, {"scale": 1.5}),
            ],
            easing="ease_out",
        )
        self._presets["zoom_out"] = AnimationDefinition(
            name="zoom_out", duration_ms=250,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 1.5}),
                AnimationKeyframe(1.0, {"scale": 1.0}),
            ],
            easing="ease_out",
        )
        self._presets["zoom_smooth"] = AnimationDefinition(
            name="zoom_smooth", duration_ms=300,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 1.0}),
                AnimationKeyframe(0.5, {"scale": 1.02}),
                AnimationKeyframe(1.0, {"scale": 1.0}),
            ],
            easing="ease_in_out",
        )
        self._presets["panel_slide_in_left"] = AnimationDefinition(
            name="panel_slide_in_left", duration_ms=300,
            keyframes=[
                AnimationKeyframe(0.0, {"translateX": "-100%", "opacity": 0}),
                AnimationKeyframe(1.0, {"translateX": "0%", "opacity": 1}),
            ],
            easing="ease_out_cubic",
        )
        self._presets["panel_slide_out_left"] = AnimationDefinition(
            name="panel_slide_out_left", duration_ms=250,
            keyframes=[
                AnimationKeyframe(0.0, {"translateX": "0%", "opacity": 1}),
                AnimationKeyframe(1.0, {"translateX": "-100%", "opacity": 0}),
            ],
            easing="ease_in_cubic",
        )
        self._presets["panel_slide_in_right"] = AnimationDefinition(
            name="panel_slide_in_right", duration_ms=300,
            keyframes=[
                AnimationKeyframe(0.0, {"translateX": "100%", "opacity": 0}),
                AnimationKeyframe(1.0, {"translateX": "0%", "opacity": 1}),
            ],
            easing="ease_out_cubic",
        )
        self._presets["panel_slide_in_bottom"] = AnimationDefinition(
            name="panel_slide_in_bottom", duration_ms=300,
            keyframes=[
                AnimationKeyframe(0.0, {"translateY": "100%", "opacity": 0}),
                AnimationKeyframe(1.0, {"translateY": "0%", "opacity": 1}),
            ],
            easing="ease_out_cubic",
        )
        self._presets["panel_fade_out"] = AnimationDefinition(
            name="panel_fade_out", duration_ms=200,
            keyframes=[
                AnimationKeyframe(0.0, {"opacity": 1}),
                AnimationKeyframe(1.0, {"opacity": 0}),
            ],
            easing="ease_in",
        )
        self._presets["tool_hover_scale"] = AnimationDefinition(
            name="tool_hover_scale", duration_ms=150,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 1.0}),
                AnimationKeyframe(1.0, {"scale": 1.15}),
            ],
            easing="ease_out",
        )
        self._presets["tool_hover_glow"] = AnimationDefinition(
            name="tool_hover_glow", duration_ms=200,
            keyframes=[
                AnimationKeyframe(0.0, {"boxShadow": "0 0 0 rgba(79,140,255,0)"}),
                AnimationKeyframe(1.0, {"boxShadow": "0 0 12px rgba(79,140,255,0.5)"}),
            ],
            easing="ease_out",
        )
        self._presets["tool_press"] = AnimationDefinition(
            name="tool_press", duration_ms=100,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 1.15}),
                AnimationKeyframe(1.0, {"scale": 0.95}),
            ],
            easing="ease_out",
        )
        for speed, ms in [("fast", 400), ("normal", 800), ("slow", 1200)]:
            self._presets[f"spinner_{speed}"] = AnimationDefinition(
                name=f"spinner_{speed}", duration_ms=ms,
                keyframes=[
                    AnimationKeyframe(0.0, {"rotation": "0deg"}),
                    AnimationKeyframe(1.0, {"rotation": "360deg"}),
                ],
                loop=True, easing="linear",
            )
        self._presets["spinner_pulse"] = AnimationDefinition(
            name="spinner_pulse", duration_ms=1000,
            keyframes=[
                AnimationKeyframe(0.0, {"opacity": 0.4, "scale": 0.8}),
                AnimationKeyframe(0.5, {"opacity": 1.0, "scale": 1.0}),
                AnimationKeyframe(1.0, {"opacity": 0.4, "scale": 0.8}),
            ],
            loop=True, easing="ease_in_out",
        )
        self._presets["spinner_dots"] = AnimationDefinition(
            name="spinner_dots", duration_ms=1500,
            keyframes=[
                AnimationKeyframe(0.0, {"dots": 1}),
                AnimationKeyframe(0.33, {"dots": 2}),
                AnimationKeyframe(0.66, {"dots": 3}),
                AnimationKeyframe(1.0, {"dots": 1}),
            ],
            loop=True, easing="linear",
        )
        self._presets["ripple"] = AnimationDefinition(
            name="ripple", duration_ms=500,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 0, "opacity": 0.6}),
                AnimationKeyframe(1.0, {"scale": 2.5, "opacity": 0}),
            ],
            easing="ease_out",
        )
        self._presets["shake"] = AnimationDefinition(
            name="shake", duration_ms=400,
            keyframes=[
                AnimationKeyframe(0.0, {"translateX": 0}),
                AnimationKeyframe(0.25, {"translateX": -5}),
                AnimationKeyframe(0.5, {"translateX": 5}),
                AnimationKeyframe(0.75, {"translateX": -3}),
                AnimationKeyframe(1.0, {"translateX": 0}),
            ],
            easing="linear",
        )
        self._presets["scale_in"] = AnimationDefinition(
            name="scale_in", duration_ms=200,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 0.8, "opacity": 0}),
                AnimationKeyframe(1.0, {"scale": 1.0, "opacity": 1}),
            ],
            easing="ease_out",
        )
        self._presets["scale_out"] = AnimationDefinition(
            name="scale_out", duration_ms=150,
            keyframes=[
                AnimationKeyframe(0.0, {"scale": 1.0, "opacity": 1}),
                AnimationKeyframe(1.0, {"scale": 0.8, "opacity": 0}),
            ],
            easing="ease_in",
        )

    def register_animation(self, definition: AnimationDefinition):
        self._animations[definition.name] = definition

    def get_preset(self, name: str) -> Optional[AnimationDefinition]:
        return self._presets.get(name) or self._animations.get(name)

    def get_all_preset_names(self) -> list[str]:
        return sorted(self._presets.keys())

    def interpolate(self, definition: AnimationDefinition, time_ms: float) -> dict:
        if not definition.keyframes:
            return {}
        duration = definition.duration_ms or 1
        t = max(0.0, min(1.0, time_ms / duration))
        easing_fn = self.EASING_FUNCTIONS.get(definition.easing, self.EASING_FUNCTIONS["linear"])
        eased_t = easing_fn(t)
        prev_kf = definition.keyframes[0]
        next_kf = definition.keyframes[-1]
        for i, kf in enumerate(definition.keyframes):
            if kf.time_pct >= eased_t:
                next_kf = kf
                prev_kf = definition.keyframes[max(0, i - 1)] if i > 0 else kf
                break
        span = next_kf.time_pct - prev_kf.time_pct
        local_t = (eased_t - prev_kf.time_pct) / span if span > 0 else 0
        properties = {}
        all_keys = set(prev_kf.properties.keys()) | set(next_kf.properties.keys())
        for key in all_keys:
            v1 = prev_kf.properties.get(key, 0)
            v2 = next_kf.properties.get(key, 0)
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                properties[key] = v1 + (v2 - v1) * local_t
            else:
                properties[key] = v2 if local_t > 0.5 else v1
        return properties

    def create_animation_css(self, name: str) -> str:
        definition = self.get_preset(name)
        if not definition:
            return ""
        keyframe_css = []
        for kf in definition.keyframes:
            props_str = "; ".join(f"{k}: {v}" for k, v in kf.properties.items())
            keyframe_css.append(f"  {kf.time_pct * 100:.0f}% {{ {props_str} }}")
        keyframes_block = "\n".join(keyframe_css)
        loop = "infinite" if definition.loop else "1"
        return (
            f"@keyframes {name} {{\n{keyframes_block}\n}}\n"
            f".anim-{name} {{ animation: {name} {definition.duration_ms}ms "
            f"{definition.easing} {loop} {'alternate' if definition.auto_reverse else 'normal'}; }}"
        )

    def create_all_css(self) -> str:
        css_parts = [self.create_animation_css(name) for name in self._presets]
        return "\n\n".join(filter(None, css_parts))

    def create_loading_spinner(self, style: str = "dots", size_px: int = 24, color: str = "#4F8CFF") -> dict:
        spinners = {
            "dots": {
                "type": "css",
                "animation": "spinner_dots",
                "html": f'<div class="spinner spinner-dots" style="width:{size_px}px;height:{size_px}px;color:{color}"><span></span><span></span><span></span></div>',
            },
            "ring": {
                "type": "css",
                "animation": "spinner_normal",
                "html": f'<div class="spinner spinner-ring" style="width:{size_px}px;height:{size_px}px;border-color:{color}"></div>',
            },
            "pulse": {
                "type": "css",
                "animation": "spinner_pulse",
                "html": f'<div class="spinner spinner-pulse" style="width:{size_px}px;height:{size_px}px;background:{color}"></div>',
            },
            "bars": {
                "type": "svg",
                "html": f'<svg width="{size_px}" height="{size_px}" viewBox="0 0 24 24"><rect x="4" y="2" width="4" height="20" fill="{color}" opacity="0.3"><animate attributeName="height" values="20;8;20" dur="1s" repeatCount="indefinite"/><animate attributeName="y" values="2;8;2" dur="1s" repeatCount="indefinite"/></rect><rect x="10" y="2" width="4" height="20" fill="{color}" opacity="0.5"><animate attributeName="height" values="8;20;8" dur="1s" repeatCount="indefinite"/><animate attributeName="y" values="8;2;8" dur="1s" repeatCount="indefinite"/></rect><rect x="16" y="2" width="4" height="20" fill="{color}" opacity="0.3"><animate attributeName="height" values="20;8;20" dur="1s" repeatCount="indefinite"/><animate attributeName="y" values="2;8;2" dur="1s" repeatCount="indefinite"/></rect></svg>',
            },
        }
        return spinners.get(style, spinners["dots"])
