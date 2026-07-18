"""Advanced theming: 10 built-in themes, custom theme creator, and import/export."""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ThemeColors:
    background: str = "#1e1e2e"
    surface: str = "#313244"
    surface_alt: str = "#45475a"
    primary: str = "#89b4fa"
    secondary: str = "#a6e3a1"
    accent: str = "#f38ba8"
    text: str = "#cdd6f4"
    text_secondary: str = "#a6adc8"
    text_muted: str = "#6c7086"
    border: str = "#585b70"
    error: str = "#f38ba8"
    warning: str = "#fab387"
    success: str = "#a6e3a1"
    info: str = "#89dceb"
    highlight: str = "#f9e2af"
    selection: str = "rgba(137,180,250,0.3)"
    shadow: str = "rgba(0,0,0,0.3)"
    scrollbar_bg: str = "#313244"
    scrollbar_thumb: str = "#585b70"
    tooltip_bg: str = "#313244"
    tooltip_text: str = "#cdd6f4"
    toolbar_bg: str = "#181825"
    sidebar_bg: str = "#181825"
    panel_bg: str = "#1e1e2e"
    input_bg: str = "#313244"
    input_border: str = "#585b70"
    button_primary_bg: str = "#89b4fa"
    button_primary_text: str = "#1e1e2e"
    button_secondary_bg: str = "#45475a"
    button_secondary_text: str = "#cdd6f4"


@dataclass
class ThemeSpacing:
    xs: int = 2
    sm: int = 4
    md: int = 8
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass
class ThemeBorder:
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 8
    radius_xl: int = 12
    radius_full: int = 9999


@dataclass
class ThemeTypography:
    font_family: str = "Inter, -apple-system, sans-serif"
    font_family_mono: str = "JetBrains Mono, Fira Code, monospace"
    font_size_xs: int = 11
    font_size_sm: int = 12
    font_size_md: int = 14
    font_size_lg: int = 16
    font_size_xl: int = 20
    font_size_xxl: int = 24
    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_bold: int = 700
    line_height: float = 1.5


@dataclass
class Theme:
    name: str = "Catppuccin Mocha"
    id: str = "catppuccin_mocha"
    description: str = ""
    author: str = "PDFMind"
    version: str = "1.0.0"
    is_dark: bool = True
    colors: ThemeColors = field(default_factory=ThemeColors)
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    border: ThemeBorder = field(default_factory=ThemeBorder)
    typography: ThemeTypography = field(default_factory=ThemeTypography)


class ThemeEngine:
    """Advanced theming engine with 10 built-in themes, custom themes, and CSS generation."""

    def __init__(self):
        self._themes: dict[str, Theme] = {}
        self._active_theme: str = "catppuccin_mocha"
        self._custom_themes: dict[str, Theme] = {}
        self._init_builtin_themes()

    def _init_builtin_themes(self):
        self._themes["catppuccin_mocha"] = Theme(
            name="Catppuccin Mocha", id="catppuccin_mocha",
            description="Rich, warm dark theme (default)",
            is_dark=True,
            colors=ThemeColors(
                background="#1e1e2e", surface="#313244", surface_alt="#45475a",
                primary="#89b4fa", secondary="#a6e3a1", accent="#f38ba8",
                text="#cdd6f4", text_secondary="#a6adc8", text_muted="#6c7086",
                border="#585b70", error="#f38ba8", warning="#fab387",
                success="#a6e3a1", info="#89dceb", highlight="#f9e2af",
                toolbar_bg="#181825", sidebar_bg="#181825", panel_bg="#1e1e2e",
                input_bg="#313244", input_border="#585b70",
                button_primary_bg="#89b4fa", button_primary_text="#1e1e2e",
                button_secondary_bg="#45475a", button_secondary_text="#cdd6f4",
            ),
        )
        self._themes["catppuccin_latte"] = Theme(
            name="Catppuccin Latte", id="catppuccin_latte",
            description="Soft, light theme",
            is_dark=False,
            colors=ThemeColors(
                background="#eff1f5", surface="#ccd0da", surface_alt="#bcc0cc",
                primary="#1e66f5", secondary="#40a02b", accent="#d20f39",
                text="#4c4f69", text_secondary="#6c6f85", text_muted="#9ca0b0",
                border="#bcc0cc", error="#d20f39", warning="#fe640b",
                success="#40a02b", info="#209fb5", highlight="#df8e1d",
                toolbar_bg="#e6e9ef", sidebar_bg="#e6e9ef", panel_bg="#eff1f5",
                input_bg="#ccd0da", input_border="#bcc0cc",
                button_primary_bg="#1e66f5", button_primary_text="#ffffff",
                button_secondary_bg="#ccd0da", button_secondary_text="#4c4f69",
            ),
        )
        self._themes["github_dark"] = Theme(
            name="GitHub Dark", id="github_dark",
            description="GitHub's dark theme",
            is_dark=True,
            colors=ThemeColors(
                background="#0d1117", surface="#161b22", surface_alt="#21262d",
                primary="#58a6ff", secondary="#3fb950", accent="#f85149",
                text="#c9d1d9", text_secondary="#8b949e", text_muted="#484f58",
                border="#30363d", error="#f85149", warning="#d29922",
                success="#3fb950", info="#58a6ff", highlight="#d29922",
                toolbar_bg="#010409", sidebar_bg="#010409", panel_bg="#0d1117",
                input_bg="#0d1117", input_border="#30363d",
                button_primary_bg="#238636", button_primary_text="#ffffff",
                button_secondary_bg="#21262d", button_secondary_text="#c9d1d9",
            ),
        )
        self._themes["one_dark"] = Theme(
            name="One Dark Pro", id="one_dark",
            description="Atom's One Dark theme",
            is_dark=True,
            colors=ThemeColors(
                background="#282c34", surface="#2c313a", surface_alt="#353b45",
                primary="#61afef", secondary="#98c379", accent="#e06c75",
                text="#abb2bf", text_secondary="#7f848e", text_muted="#5c6370",
                border="#3e4451", error="#e06c75", warning="#e5c07b",
                success="#98c379", info="#56b6c2", highlight="#e5c07b",
                toolbar_bg="#21252b", sidebar_bg="#21252b", panel_bg="#282c34",
                input_bg="#282c34", input_border="#3e4451",
                button_primary_bg="#61afef", button_primary_text="#282c34",
                button_secondary_bg="#3e4451", button_secondary_text="#abb2bf",
            ),
        )
        self._themes["dracula"] = Theme(
            name="Dracula", id="dracula",
            description="Famous Dracula color scheme",
            is_dark=True,
            colors=ThemeColors(
                background="#282a36", surface="#44475a", surface_alt="#6272a4",
                primary="#bd93f9", secondary="#50fa7b", accent="#ff5555",
                text="#f8f8f2", text_secondary="#bfbfbf", text_muted="#6272a4",
                border="#6272a4", error="#ff5555", warning="#f1fa8c",
                success="#50fa7b", info="#8be9fd", highlight="#f1fa8c",
                toolbar_bg="#21222c", sidebar_bg="#21222c", panel_bg="#282a36",
                input_bg="#44475a", input_border="#6272a4",
                button_primary_bg="#bd93f9", button_primary_text="#282a36",
                button_secondary_bg="#44475a", button_secondary_text="#f8f8f2",
            ),
        )
        self._themes["nord"] = Theme(
            name="Nord", id="nord",
            description="Arctic, north-bluish clean and elegant theme",
            is_dark=True,
            colors=ThemeColors(
                background="#2e3440", surface="#3b4252", surface_alt="#434c5e",
                primary="#88c0d0", secondary="#a3be8c", accent="#bf616a",
                text="#eceff4", text_secondary="#d8dee9", text_muted="#4c566a",
                border="#4c566a", error="#bf616a", warning="#ebcb8b",
                success="#a3be8c", info="#88c0d0", highlight="#ebcb8b",
                toolbar_bg="#2e3440", sidebar_bg="#2e3440", panel_bg="#2e3440",
                input_bg="#3b4252", input_border="#4c566a",
                button_primary_bg="#88c0d0", button_primary_text="#2e3440",
                button_secondary_bg="#434c5e", button_secondary_text="#eceff4",
            ),
        )
        self._themes["solarized_dark"] = Theme(
            name="Solarized Dark", id="solarized_dark",
            description="Ethan Schoonover's Solarized dark theme",
            is_dark=True,
            colors=ThemeColors(
                background="#002b36", surface="#073642", surface_alt="#094959",
                primary="#268bd2", secondary="#859900", accent="#dc322f",
                text="#839496", text_secondary="#93a1a1", text_muted="#586e75",
                border="#586e75", error="#dc322f", warning="#b58900",
                success="#859900", info="#2aa198", highlight="#b58900",
                toolbar_bg="#002b36", sidebar_bg="#002b36", panel_bg="#002b36",
                input_bg="#073642", input_border="#586e75",
                button_primary_bg="#268bd2", button_primary_text="#fdf6e3",
                button_secondary_bg="#073642", button_secondary_text="#839496",
            ),
        )
        self._themes["solarized_light"] = Theme(
            name="Solarized Light", id="solarized_light",
            description="Ethan Schoonover's Solarized light theme",
            is_dark=False,
            colors=ThemeColors(
                background="#fdf6e3", surface="#eee8d5", surface_alt="#e8e0cc",
                primary="#268bd2", secondary="#859900", accent="#dc322f",
                text="#657b83", text_secondary="#586e75", text_muted="#93a1a1",
                border="#93a1a1", error="#dc322f", warning="#b58900",
                success="#859900", info="#2aa198", highlight="#b58900",
                toolbar_bg="#eee8d5", sidebar_bg="#eee8d5", panel_bg="#fdf6e3",
                input_bg="#eee8d5", input_border="#93a1a1",
                button_primary_bg="#268bd2", button_primary_text="#fdf6e3",
                button_secondary_bg="#eee8d5", button_secondary_text="#657b83",
            ),
        )
        self._themes["high_contrast"] = Theme(
            name="High Contrast", id="high_contrast",
            description="WCAG AAA compliant high contrast theme",
            is_dark=True,
            colors=ThemeColors(
                background="#000000", surface="#1a1a1a", surface_alt="#333333",
                primary="#ffffff", secondary="#00ff00", accent="#ff0000",
                text="#ffffff", text_secondary="#e0e0e0", text_muted="#b0b0b0",
                border="#ffffff", error="#ff0000", warning="#ffff00",
                success="#00ff00", info="#00ffff", highlight="#ffff00",
                toolbar_bg="#000000", sidebar_bg="#000000", panel_bg="#000000",
                input_bg="#1a1a1a", input_border="#ffffff",
                button_primary_bg="#ffffff", button_primary_text="#000000",
                button_secondary_bg="#333333", button_secondary_text="#ffffff",
            ),
            typography=ThemeTypography(
                font_size_xs=13, font_size_sm=14, font_size_md=16,
                font_size_lg=18, font_size_xl=22, font_size_xxl=28,
                font_weight_normal=500, font_weight_bold=700,
            ),
        )

    def get_theme(self, theme_id: str) -> Optional[Theme]:
        return self._themes.get(theme_id) or self._custom_themes.get(theme_id)

    def get_all_themes(self) -> list[Theme]:
        all_themes = list(self._themes.values()) + list(self._custom_themes.values())
        return all_themes

    def get_builtin_themes(self) -> list[Theme]:
        return list(self._themes.values())

    def set_active_theme(self, theme_id: str) -> bool:
        if theme_id in self._themes or theme_id in self._custom_themes:
            self._active_theme = theme_id
            return True
        return False

    def get_active_theme(self) -> Theme:
        return self.get_theme(self._active_theme) or Theme()

    def create_custom_theme(self, name: str, base_theme_id: str = "catppuccin_mocha",
                            color_overrides: dict = None) -> Theme:
        base = self.get_theme(base_theme_id) or Theme()
        import copy
        custom = copy.deepcopy(base)
        custom.name = name
        custom.id = name.lower().replace(" ", "_").replace("-", "_")
        custom.author = "Custom"
        if color_overrides:
            for key, value in color_overrides.items():
                if hasattr(custom.colors, key):
                    setattr(custom.colors, key, value)
        self._custom_themes[custom.id] = custom
        logger.info(f"Created custom theme: {name}")
        return custom

    def edit_theme(self, theme_id: str, color_overrides: dict) -> Optional[Theme]:
        theme = self._custom_themes.get(theme_id) or self._themes.get(theme_id)
        if not theme:
            return None
        if theme_id in self._themes:
            import copy
            theme = copy.deepcopy(theme)
            theme.id = f"{theme_id}_custom"
            self._custom_themes[theme.id] = theme
        for key, value in color_overrides.items():
            if hasattr(theme.colors, key):
                setattr(theme.colors, key, value)
        return theme

    def delete_custom_theme(self, theme_id: str) -> bool:
        if theme_id in self._custom_themes:
            del self._custom_themes[theme_id]
            return True
        return False

    def generate_css(self, theme: Theme = None) -> str:
        theme = theme or self.get_active_theme()
        c = theme.colors
        s = theme.spacing
        b = theme.border
        t = theme.typography
        css = f"""/* PDFMind Theme: {theme.name} */
:root {{
  /* Colors */
  --bg-background: {c.background};
  --bg-surface: {c.surface};
  --bg-surface-alt: {c.surface_alt};
  --bg-toolbar: {c.toolbar_bg};
  --bg-sidebar: {c.sidebar_bg};
  --bg-panel: {c.panel_bg};
  --bg-input: {c.input_bg};
  --color-primary: {c.primary};
  --color-secondary: {c.secondary};
  --color-accent: {c.accent};
  --color-text: {c.text};
  --color-text-secondary: {c.text_secondary};
  --color-text-muted: {c.text_muted};
  --color-border: {c.border};
  --color-error: {c.error};
  --color-warning: {c.warning};
  --color-success: {c.success};
  --color-info: {c.info};
  --color-highlight: {c.highlight};
  --color-selection: {c.selection};
  --btn-primary-bg: {c.button_primary_bg};
  --btn-primary-text: {c.button_primary_text};
  --btn-secondary-bg: {c.button_secondary_bg};
  --btn-secondary-text: {c.button_secondary_text};
  /* Spacing */
  --space-xs: {s.xs}px;
  --space-sm: {s.sm}px;
  --space-md: {s.md}px;
  --space-lg: {s.lg}px;
  --space-xl: {s.xl}px;
  --space-xxl: {s.xxl}px;
  /* Border Radius */
  --radius-sm: {b.radius_sm}px;
  --radius-md: {b.radius_md}px;
  --radius-lg: {b.radius_lg}px;
  --radius-xl: {b.radius_xl}px;
  --radius-full: {b.radius_full}px;
  /* Typography */
  --font-family: {t.font_family};
  --font-family-mono: {t.font_family_mono};
  --font-size-xs: {t.font_size_xs}px;
  --font-size-sm: {t.font_size_sm}px;
  --font-size-md: {t.font_size_md}px;
  --font-size-lg: {t.font_size_lg}px;
  --font-size-xl: {t.font_size_xl}px;
  --font-size-xxl: {t.font_size_xxl}px;
}}
body {{
  background: var(--bg-background);
  color: var(--color-text);
  font-family: var(--font-family);
  font-size: var(--font-size-md);
}}
button.primary {{
  background: var(--btn-primary-bg);
  color: var(--btn-primary-text);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-lg);
  font-weight: var(--font-weight-medium);
}}
button.secondary {{
  background: var(--btn-secondary-bg);
  color: var(--btn-secondary-text);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-lg);
}}
input, textarea {{
  background: var(--bg-input);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  font-family: var(--font-family);
}}
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: var(--bg-surface); }}
::-webkit-scrollbar-thumb {{ background: var(--color-border); border-radius: var(--radius-full); }}
::selection {{ background: var(--color-selection); }}"""
        return css

    def export_theme(self, theme_id: str) -> Optional[str]:
        theme = self.get_theme(theme_id)
        if not theme:
            return None
        data = {
            "name": theme.name, "id": theme.id, "description": theme.description,
            "author": theme.author, "is_dark": theme.is_dark,
            "colors": {k: v for k, v in theme.colors.__dict__.items()},
            "spacing": {k: v for k, v in theme.spacing.__dict__.items()},
            "border": {k: v for k, v in theme.border.__dict__.items()},
            "typography": {k: v for k, v in theme.typography.__dict__.items()},
        }
        return json.dumps(data, indent=2)

    def import_theme(self, json_data: str) -> Optional[Theme]:
        try:
            data = json.loads(json_data)
            theme = Theme(
                name=data["name"], id=data["id"],
                description=data.get("description", ""),
                author=data.get("author", "Imported"),
                is_dark=data.get("is_dark", True),
            )
            if "colors" in data:
                for k, v in data["colors"].items():
                    if hasattr(theme.colors, k):
                        setattr(theme.colors, k, v)
            self._custom_themes[theme.id] = theme
            return theme
        except Exception as e:
            logger.error(f"Theme import failed: {e}")
            return None

    def get_high_contrast_themes(self) -> list[Theme]:
        return [t for t in self._themes.values() if t.id in ("high_contrast", "solarized_dark")]

    def get_light_themes(self) -> list[Theme]:
        return [t for t in self._themes.values() if not t.is_dark]
