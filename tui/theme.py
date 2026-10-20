"""
Color Themes for SpeedFlasher TUI.
Provides modern pastel color palettes with animated starfield support.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

RGB = Tuple[int, int, int]


@dataclass
class Theme:
    name: str
    id: str
    is_dark: bool
    bg: RGB
    card_bg: RGB
    fg: RGB
    accent: RGB
    highlight: RGB
    muted: RGB
    star: RGB
    border: RGB
    border_active: RGB
    success: RGB
    warning: RGB
    error: RGB
    selection_bg: RGB


# Cosmic Night (Default Theme)
THEME_COSMIC = Theme(
    name="Cosmic Night",
    id="cosmic",
    is_dark=True,
    bg=(2, 5, 23),                 # Deep night void
    card_bg=(14, 18, 38),           # Slate violet card
    fg=(224, 222, 244),             # Crisp soft white text
    accent=(255, 225, 246),         # Soft blossom pink/lavender
    highlight=(183, 168, 217),      # Glowing lavender highlight
    muted=(144, 140, 170),          # Subdued slate purple
    star=(160, 150, 195),           # Starlight purple-white
    border=(110, 100, 150),         # Clean visible border
    border_active=(196, 167, 231),  # Focused border
    success=(156, 207, 216),        # Soft cyan
    warning=(246, 193, 119),        # Warm gold
    error=(235, 111, 146),          # Crimson rose
    selection_bg=(35, 33, 60),      # Active row background
)

# System / Classic Dark
THEME_SYSTEM_DARK = Theme(
    name="System (Dark)",
    id="system_dark",
    is_dark=True,
    bg=(16, 16, 22),
    card_bg=(26, 26, 36),
    fg=(235, 235, 242),
    accent=(180, 205, 255),
    highlight=(120, 170, 255),
    muted=(125, 125, 145),
    star=(140, 160, 200),
    border=(80, 80, 110),
    border_active=(120, 170, 255),
    success=(110, 220, 160),
    warning=(255, 200, 100),
    error=(255, 110, 130),
    selection_bg=(40, 45, 65),
)

# Catppuccin Mocha
THEME_CATPPUCCIN = Theme(
    name="Catppuccin Mocha",
    id="catppuccin",
    is_dark=True,
    bg=(30, 30, 46),
    card_bg=(24, 24, 37),
    fg=(205, 214, 244),
    accent=(203, 166, 247),         # Mauve
    highlight=(180, 190, 254),      # Lavender
    muted=(108, 112, 134),          # Overlay0
    star=(147, 153, 178),           # Subtext0
    border=(90, 92, 120),
    border_active=(203, 166, 247),
    success=(166, 227, 161),
    warning=(249, 226, 175),
    error=(243, 139, 168),
    selection_bg=(49, 50, 68),
)

# Rosé Pine
THEME_ROSE_PINE = Theme(
    name="Rosé Pine",
    id="rose_pine",
    is_dark=True,
    bg=(25, 23, 36),
    card_bg=(31, 29, 46),
    fg=(224, 222, 244),
    accent=(235, 188, 186),
    highlight=(196, 167, 231),
    muted=(110, 106, 134),
    star=(144, 140, 170),
    border=(95, 90, 125),
    border_active=(196, 167, 231),
    success=(156, 207, 216),
    warning=(246, 193, 119),
    error=(235, 111, 146),
    selection_bg=(38, 35, 58),
)

# Gruvbox Dark
THEME_GRUVBOX = Theme(
    name="Gruvbox Dark",
    id="gruvbox",
    is_dark=True,
    bg=(40, 40, 40),
    card_bg=(50, 48, 47),
    fg=(235, 219, 178),
    accent=(254, 128, 25),
    highlight=(250, 189, 47),
    muted=(146, 131, 116),
    star=(213, 196, 161),
    border=(100, 95, 90),
    border_active=(250, 189, 47),
    success=(184, 187, 38),
    warning=(250, 189, 47),
    error=(251, 73, 52),
    selection_bg=(60, 56, 54),
)

ALL_THEMES: Dict[str, Theme] = {
    "cosmic": THEME_COSMIC,
    "system_dark": THEME_SYSTEM_DARK,
    "catppuccin": THEME_CATPPUCCIN,
    "rose_pine": THEME_ROSE_PINE,
    "gruvbox": THEME_GRUVBOX,
}


def rgb_to_ansi256(r: int, g: int, b: int) -> int:
    """Fallback mapping for terminals lacking 24-bit TrueColor."""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return round(((r - 8) / 247) * 23) + 232
    return 16 + (36 * round(r / 255 * 5)) + (6 * round(g / 255 * 5)) + round(b / 255 * 5)


def ansi_fg(rgb: RGB, truecolor: bool = True) -> str:
    r, g, b = rgb
    if truecolor:
        return f"\033[38;2;{r};{g};{b}m"
    return f"\033[38;5;{rgb_to_ansi256(r, g, b)}m"


def ansi_bg(rgb: RGB, truecolor: bool = True) -> str:
    r, g, b = rgb
    if truecolor:
        return f"\033[48;2;{r};{g};{b}m"
    return f"\033[48;5;{rgb_to_ansi256(r, g, b)}m"


ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_ITALIC = "\033[3m"
ANSI_UNDERLINE = "\033[4m"
