"""
Antumbra-styled UI Widgets for SpeedFlasher TUI.
Provides transparent cards, floating description boxes, form inputs, toggles,
dropdowns, progress indicators, and banners matching Antumbra's exact visual design.
"""
from typing import Any, List, Optional, Tuple
from .theme import Theme
from .terminal import Terminal

# Border glyph styles
BORDER_ROUNDED = {
    'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯',
    'h': '─', 'v': '│'
}
BORDER_SHARP = {
    'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
    'h': '─', 'v': '│'
}
BORDER_ASCII = {
    'tl': '+', 'tr': '+', 'bl': '+', 'br': '+',
    'h': '-', 'v': '|'
}

LOGO_FULL = [
    " ███████╗██████╗ ███████╗███████╗██████╗ ███████╗██╗      █████╗ ███████╗██╗  ██╗███████╗██████╗ ",
    " ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗",
    " ███████╗██████╔╝█████╗  █████╗  ██║  ██║█████╗  ██║     ███████║███████╗███████║█████╗  ██████╔╝",
    " ╚════██║██╔═══╝ ██╔══╝  ██╔══╝  ██║  ██║██╔══╝  ██║     ██╔══██║╚════██║██╔══██║██╔══╝  ██╔══██╗",
    " ██████╔╝██║     ███████╗███████╗██████╔╝██║     ███████╗██║  ██║███████║██║  ██║███████╗██║  ██║",
    " ╚═════╝ ╚═╝     ╚══════╝╚══════╝╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
]

LOGO_MEDIUM = [
    "  ___ ___ ___ ___ ___  ___ _      _   ___ _  _ ___ ___ ",
    " / __| _ \\ __| __|   \\| __| |    /_\\ / __| || | __| _ \\",
    " \\__ \\  _/ _|| _|| |) | _|| |__ / _ \\\\__ \\ __ | _||   /",
    " |___/_| |___|___|___/|_| |____/_/ \\_\\___/_||_|___|_|_\\"
]

LOGO_COMPACT = [
    "✦ SPEEDFLASHER TUI ✦"
]


def wrap_text(text: str, max_width: int) -> List[str]:
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        cur = []
        cur_len = 0
        for w in words:
            w_len = len(w)
            sep = 1 if cur else 0
            if cur_len + w_len + sep <= max_width:
                cur.append(w)
                cur_len += w_len + sep
            else:
                if cur:
                    lines.append(" ".join(cur))
                cur = [w]
                cur_len = w_len
        if cur:
            lines.append(" ".join(cur))
    return lines


def draw_card(term: Terminal, x: int, y: int, w: int, h: int,
              title: str = "", theme: Optional[Theme] = None,
              active: bool = False, ascii_mode: bool = False,
              fill_bg: bool = False):
    """
    Renders a clean, transparent, unbroken bordered card.
    Default fill_bg=False guarantees terminal transparency / blur is preserved.
    """
    if w < 4 or h < 2:
        return
    b = BORDER_ASCII if ascii_mode else BORDER_ROUNDED
    border_color = (theme.border_active if active else theme.border) if theme else None
    bg_color = (theme.card_bg if fill_bg else None) if theme else None
    title_color = (theme.accent if active else theme.fg) if theme else None

    # Top border
    if title:
        title_str = f" {title} "
        rem = max(0, w - 2 - len(title_str))
        top_str = b['tl'] + b['h'] + title_str + (b['h'] * max(0, rem - 1)) + b['tr']
    else:
        top_str = b['tl'] + (b['h'] * max(0, w - 2)) + b['tr']

    term.put_str(x, y, top_str[:w], fg=border_color, bg=bg_color, occupied=True)
    if title:
        term.put_str(x + 2, y, title_str, fg=title_color, bg=bg_color, bold=True, occupied=True)

    # Middle rows (transparent inside, only borders occupy cells)
    for row in range(1, h - 1):
        cy = y + row
        term.put_char(x, cy, b['v'], fg=border_color, bg=bg_color, occupied=True)
        if fill_bg and w > 2:
            term.put_str(x + 1, cy, " " * (w - 2), fg=None, bg=bg_color, occupied=False)
        term.put_char(x + w - 1, cy, b['v'], fg=border_color, bg=bg_color, occupied=True)

    # Bottom border
    bot_str = b['bl'] + (b['h'] * max(0, w - 2)) + b['br']
    term.put_str(x, y + h - 1, bot_str[:w], fg=border_color, bg=bg_color, occupied=True)
    term.mark_occupied_rect(x, y, w, h)


def draw_floating_description_box(term: Terminal, x: int, y: int, w: int,
                                  text: str, theme: Theme, ascii_mode: bool = False):
    """
    Renders the exact Antumbra floating description box:
    - Completely transparent background (bg=None) letting terminal blur/wallpaper show.
    - Complete, unbroken rounded box with NO cuts or title gaps: ╭──────╮, │ text │, ╰──────╯
    - Snug height matching wrapped text.
    - Text styled in theme.info/highlight.
    """
    b = BORDER_ASCII if ascii_mode else BORDER_ROUNDED
    border_color = theme.border
    text_color = theme.highlight

    inner_w = max(10, w - 4)
    lines = wrap_text(text, inner_w)
    box_h = len(lines) + 2

    # Top border (unbroken)
    top_str = b['tl'] + (b['h'] * (w - 2)) + b['tr']
    term.put_str(x, y, top_str[:w], fg=border_color, bg=None, occupied=True)

    # Middle text rows
    for i, line in enumerate(lines):
        cy = y + 1 + i
        term.put_char(x, cy, b['v'], fg=border_color, bg=None, occupied=True)
        padded_text = f" {line.ljust(inner_w)} "
        term.put_str(x + 1, cy, padded_text[:w - 2], fg=text_color, bg=None, dim=False, occupied=True)
        term.put_char(x + w - 1, cy, b['v'], fg=border_color, bg=None, occupied=True)

    # Bottom border (unbroken)
    bot_str = b['bl'] + (b['h'] * (w - 2)) + b['br']
    term.put_str(x, y + box_h - 1, bot_str[:w], fg=border_color, bg=None, occupied=True)
    term.mark_occupied_rect(x, y, w, box_h)
    return box_h


def draw_header(term: Terminal, theme: Theme, compact: bool = False) -> int:
    """
    Renders the Antumbra title banner and attribution subtitle:
    'By Mehraann (patched UI by Softbrick)'
    """
    w = term.width
    if w >= 102 and not compact:
        logo = LOGO_FULL
    elif w >= 60:
        logo = LOGO_MEDIUM
    else:
        logo = LOGO_COMPACT

    start_y = 1
    for i, line in enumerate(logo):
        lx = max(0, (w - len(line)) // 2)
        term.put_str(lx, start_y + i, line, fg=theme.accent, bg=None, bold=True, occupied=True)

    # Attribution Subtitle
    sub_y = start_y + len(logo) + 1
    sub_text = "By Mehraann (patched UI by Softbrick)"
    sub_x = max(0, (w - len(sub_text)) // 2)
    term.put_str(sub_x, sub_y, sub_text, fg=theme.highlight, bg=None, bold=False, dim=False, occupied=True)

    return sub_y + 2


def draw_description_menu(term: Terminal, x: int, y: int, items: List[Tuple[str, str, Any]],
                          selected: int, theme: Theme, desc_x: int, desc_w: int,
                          ascii_mode: bool = False):
    """
    Renders Antumbra description menu:
    - Left: Clean bullet items with `> * ` cursor
    - Right: Snug, completely transparent floating description box vertically following the selected item
    """
    y_spacing = 2
    for idx, (label, _, _) in enumerate(items):
        item_y = y + idx * y_spacing
        is_sel = (idx == selected)

        prefix = "> * " if is_sel else "  * "
        prefix_color = theme.accent if is_sel else theme.muted
        label_color = theme.accent if is_sel else theme.fg
        bold = is_sel

        term.put_str(x, item_y, prefix, fg=prefix_color, bg=None, bold=bold, occupied=True)
        term.put_str(x + 4, item_y, label, fg=label_color, bg=None, bold=bold, occupied=True)

    # Right floating description box (transparent, unbroken, vertically following selected item)
    if 0 <= selected < len(items):
        _, desc_text, _ = items[selected]
        # Align vertically with selected item
        target_y = y + selected * y_spacing
        draw_floating_description_box(
            term, desc_x, target_y, desc_w, desc_text, theme, ascii_mode=ascii_mode
        )


def draw_status_summary(term: Terminal, y: int, lines: List[Tuple[str, str]], theme: Theme):
    """
    Centered status summary matching Antumbra Screenshot 1:
          Target: Infinix GT 20 Pro [X6871]
          Firmware: None
          Status: None (select folder)
    """
    w = term.width
    max_label_len = max((len(lbl) for lbl, _ in lines), default=10)
    for i, (label, val) in enumerate(lines):
        line_str = f"{label.rjust(max_label_len)}: {val}"
        lx = max(0, (w - len(line_str)) // 2)
        lbl_part = f"{label.rjust(max_label_len)}: "
        term.put_str(lx, y + i, lbl_part, fg=theme.muted, bg=None, occupied=True)

        is_active = (val != "None" and not val.startswith("None"))
        val_color = theme.success if is_active else theme.muted
        term.put_str(lx + len(lbl_part), y + i, val, fg=val_color, bg=None, bold=is_active, occupied=True)


def draw_footer(term: Terminal, hints: str, theme: Theme):
    """
    Footer bar at the bottom:
    [↑/↓] Navigate   •   [Enter] Select   •   [q] Quit
    """
    y = term.height - 1
    term.put_str(0, y, " " * term.width, fg=None, bg=None, occupied=False)
    lx = max(0, (term.width - len(hints)) // 2)

    parts = hints.split("•")
    cur_x = lx
    for i, part in enumerate(parts):
        part_clean = part.strip()
        if "[" in part_clean and "]" in part_clean:
            k_start = part_clean.find("[")
            k_end = part_clean.find("]") + 1
            key_hint = part_clean[k_start:k_end]
            label = part_clean[k_end:].strip()

            term.put_str(cur_x, y, key_hint, fg=theme.highlight, bg=None, bold=True, occupied=True)
            cur_x += len(key_hint)
            term.put_str(cur_x, y, f" {label}", fg=theme.muted, bg=None, occupied=True)
            cur_x += len(label) + 1
        else:
            term.put_str(cur_x, y, part_clean, fg=theme.muted, bg=None, occupied=True)
            cur_x += len(part_clean)

        if i < len(parts) - 1:
            term.put_str(cur_x, y, "   •   ", fg=theme.border, bg=None, occupied=True)
            cur_x += 7


def draw_form_input(term: Terminal, x: int, y: int, w: int, label: str,
                    subtext: str, value: str, focused: bool, theme: Theme,
                    ascii_mode: bool = False):
    """
    Transparent form input field matching Screenshot 2.
    """
    prefix = "> " if focused else "  "
    term.put_str(x, y, prefix, fg=theme.accent if focused else theme.muted, bg=None, bold=focused, occupied=True)
    term.put_str(x + 2, y, label, fg=theme.accent if focused else theme.fg, bg=None, bold=focused, occupied=True)
    if subtext:
        term.put_str(x + 2 + len(label), y, f" - {subtext}", fg=theme.muted, bg=None, dim=True, occupied=True)

    b = BORDER_ASCII if ascii_mode else BORDER_ROUNDED
    b_color = theme.border_active if focused else theme.border

    box_w = max(10, w)
    top = b['tl'] + (b['h'] * (box_w - 2)) + b['tr']
    bot = b['bl'] + (b['h'] * (box_w - 2)) + b['br']
    term.put_str(x + 2, y + 1, top, fg=b_color, bg=None, occupied=True)

    term.put_char(x + 2, y + 2, b['v'], fg=b_color, bg=None, occupied=True)
    inner_w = box_w - 4
    val_disp = value
    if len(val_disp) > inner_w:
        val_disp = "..." + val_disp[-(inner_w - 3):]
    val_padded = val_disp.ljust(inner_w)
    term.put_str(x + 4, y + 2, val_padded, fg=theme.fg, bg=None, occupied=True)
    term.put_char(x + 2 + box_w - 1, y + 2, b['v'], fg=b_color, bg=None, occupied=True)

    term.put_str(x + 2, y + 3, bot, fg=b_color, bg=None, occupied=True)
    term.mark_occupied_rect(x + 2, y + 1, box_w, 3)


def draw_form_toggle(term: Terminal, x: int, y: int, label: str,
                     subtext: str, checked: bool, focused: bool, theme: Theme):
    """
    Transparent toggle matching Screenshot 2.
    """
    prefix = "> " if focused else "  "
    term.put_str(x, y, prefix, fg=theme.accent if focused else theme.muted, bg=None, bold=focused, occupied=True)
    term.put_str(x + 2, y, label, fg=theme.accent if focused else theme.fg, bg=None, bold=focused, occupied=True)
    if subtext:
        term.put_str(x + 2 + len(label), y, f" - {subtext}", fg=theme.muted, bg=None, dim=True, occupied=True)

    chk_str = "[✓]" if checked else "[ ]"
    term.put_str(x + 2, y + 1, chk_str, fg=theme.success if checked else theme.muted, bg=None, bold=focused, occupied=True)


def draw_form_dropdown(term: Terminal, x: int, y: int, w: int, label: str,
                       subtext: str, value_text: str, focused: bool, theme: Theme,
                       ascii_mode: bool = False):
    """
    Transparent dropdown control matching Screenshot 2.
    """
    prefix = "> " if focused else "  "
    term.put_str(x, y, prefix, fg=theme.accent if focused else theme.muted, bg=None, bold=focused, occupied=True)
    term.put_str(x + 2, y, label, fg=theme.accent if focused else theme.fg, bg=None, bold=focused, occupied=True)
    if subtext:
        term.put_str(x + 2 + len(label), y, f" - {subtext}", fg=theme.muted, bg=None, dim=True, occupied=True)

    b = BORDER_ASCII if ascii_mode else BORDER_ROUNDED
    b_color = theme.border_active if focused else theme.border

    box_w = max(10, w)
    top = b['tl'] + (b['h'] * (box_w - 2)) + b['tr']
    bot = b['bl'] + (b['h'] * (box_w - 2)) + b['br']
    term.put_str(x + 2, y + 1, top, fg=b_color, bg=None, occupied=True)

    term.put_char(x + 2, y + 2, b['v'], fg=b_color, bg=None, occupied=True)
    inner_w = box_w - 4
    arrow = "▼" if not ascii_mode else "v"
    content = f"{value_text} {arrow}"
    padded = content.ljust(inner_w)
    term.put_str(x + 4, y + 2, padded, fg=theme.highlight if focused else theme.fg, bg=None, bold=focused, occupied=True)
    term.put_char(x + 2 + box_w - 1, y + 2, b['v'], fg=b_color, bg=None, occupied=True)

    term.put_str(x + 2, y + 3, bot, fg=b_color, bg=None, occupied=True)
    term.mark_occupied_rect(x + 2, y + 1, box_w, 3)


def draw_progress_bar(term: Terminal, x: int, y: int, w: int,
                      percent: float, label: str = "", theme: Optional[Theme] = None):
    bar_w = max(10, w - len(label) - 8)
    filled_w = int(bar_w * max(0.0, min(1.0, percent / 100.0)))
    empty_w = bar_w - filled_w

    fill_char = "█"
    empty_char = "░"
    bar_str = (fill_char * filled_w) + (empty_char * empty_w)

    pct_str = f" {int(percent)}%"
    term.put_str(x, y, f"{label} [", fg=theme.fg if theme else None, bg=None, occupied=True)
    bar_x = x + len(label) + 2
    term.put_str(bar_x, y, bar_str, fg=theme.accent if theme else None, bg=None, occupied=True)
    term.put_str(bar_x + bar_w, y, f"]{pct_str}", fg=theme.highlight if theme else None, bg=None, bold=True, occupied=True)
