"""
TUI Application for SpeedFlasher.
Complete interactive dashboard, wizard, partition inspector, settings,
directory explorer, and live build engine with animated twinkling starfield.
"""
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .theme import ALL_THEMES, THEME_COSMIC, Theme
from .stars import Starfield
from .terminal import (
    Terminal, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
    KEY_ENTER, KEY_TAB, KEY_SHIFT_TAB, KEY_ESC, KEY_BACKSPACE, KEY_SPACE
)
from .widgets import (
    draw_card, draw_header, draw_description_menu, draw_status_summary,
    draw_footer, draw_form_input, draw_form_toggle, draw_form_dropdown,
    draw_progress_bar, wrap_text
)

# Core SpeedFlasher engine imports
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from core.builder import FlashableBuilder, format_flashable_name, get_current_platform, get_host_zstd
from core.partitions import scan_partitions


class LogCapture:
    def __init__(self, log_queue: queue.Queue, original_stdout):
        self.log_queue = log_queue
        self.original_stdout = original_stdout

    def write(self, s: str):
        if s:
            for line in s.splitlines():
                if line.strip():
                    self.log_queue.put(line)

    def flush(self):
        pass


class SpeedFlasherApp:
    PAGE_MAIN = "main"
    PAGE_WIZARD = "wizard"
    PAGE_EXPLORER = "explorer"
    PAGE_INSPECT = "inspect"
    PAGE_SETTINGS = "settings"
    PAGE_BUILDING = "building"
    PAGE_COMPLETE = "complete"

    def __init__(self):
        self.term = Terminal()
        self.theme: Theme = THEME_COSMIC
        self.starfield = Starfield(density=0.8, compact=False, enabled=True)
        self.page = self.PAGE_MAIN
        self.running = True

        # Configuration state
        self.cfg = {
            "imgs_path": "",
            "device": "Infinix GT 20 Pro",
            "codename": "X6871",
            "version": "1.0",
            "maintainer": "Mehraann",
            "vbmeta": "skip",        # skip | disable | enable
            "zstd_level": 1,         # 0-22
            "zip_level": 1,          # 0-9
            "include_fastboot": True,
        }
        self.partitions: Dict[str, Dict[str, Any]] = {}
        self.auto_detected = False

        # Menu state (Clean terminal style, without emoji width offsets)
        self.menu_idx = 0
        self.menu_items = [
            ("Build Flashable Package",
             "Guided wizard to configure device, AVB 2.0, compression, and package all partitions into an installer.",
             "action_wizard"),
            ("Select Firmware Directory",
             "Interactive directory browser to select folder with .img or .img.zst partition images.",
             "action_browse"),
            ("Inspect Partitions",
             "Analyze partition layout, dynamic super groups, uncompressed sizes, and AVB status.",
             "action_inspect"),
            ("AVB 2.0 / VBMeta Mode",
             "Cycle through AVB 2.0 flags: Skip (preserve stock), Disable (disable verification), Enable.",
             "action_cycle_vbmeta"),
            ("Settings & Appearance",
             "Customize themes, animated stars background, and tool defaults.",
             "action_settings"),
            ("Quit SpeedFlasher",
             "Exit SpeedFlasher cleanly.",
             "action_exit"),
        ]

        # Clickable hitboxes for mouse support: list of (x1, y1, x2, y2, callback)
        self.click_regions: List[Tuple[int, int, int, int, Any]] = []

        # Wizard fields
        self.wizard_fields = [
            ("imgs_path", "Firmware Directory", "Folder containing .img or .img.zst files", "text"),
            ("device", "Device Name", "Marketing name (e.g. Infinix GT 20 Pro)", "text"),
            ("codename", "Device Codename", "Internal board codename (e.g. X6871)", "text"),
            ("version", "Firmware / ROM Version", "e.g. V14.0.1.0 or 1.0", "text"),
            ("maintainer", "Maintainer", "Package maintainer name", "text"),
            ("vbmeta", "AVB 2.0 Mode", "vbmeta flags (skip / disable / enable)", "select_vbmeta"),
            ("zstd_level", "ZSTD Compression", "Level 0-22 (0 = raw/uncompressed, 1 = fast)", "number"),
            ("zip_level", "ZIP Compression", "Level 0-9 (0 = stored, 1 = fast deflated)", "number"),
            ("include_fastboot", "Fastboot Installers", "Generate Windows, Linux & Termux scripts", "toggle"),
            ("build_btn", "START BUILD", "Begin partition conversion and packaging", "button"),
        ]
        self.wizard_idx = 0
        self.wizard_editing = False
        self.edit_buffer = ""

        # Settings fields
        self.settings_theme_list = list(ALL_THEMES.keys())
        self.settings_theme_idx = 0
        self.settings_idx = 0
        self.settings_fields = [
            ("theme", "Interface Theme", "Visual style for SpeedFlasher TUI", "theme_select"),
            ("compat", "Compatibility Mode", "Use standard ASCII characters for stars (*, +, .)", "toggle"),
            ("stars", "Show stars", "Display animated stars in the background", "toggle"),
            ("density", "Star Density", "Density of celestial stars (Low / Normal / High)", "density_select"),
        ]

        # Explorer state
        self.explorer_path = os.getcwd()
        self.explorer_entries: List[Tuple[str, bool, str]] = []
        self.explorer_idx = 0

        # Build worker state
        self.build_log_queue: queue.Queue = queue.Queue()
        self.build_logs: List[str] = []
        self.build_thread: Optional[threading.Thread] = None
        self.build_success = False
        self.build_error: Optional[str] = None
        self.build_result: Any = None
        self.build_start_time = 0.0
        self.build_stage_num = 1
        self.build_stage_text = "Initializing"

        # Check for images in current directory on startup
        self._check_default_firmware_dir()

    def _check_default_firmware_dir(self):
        cand_dirs = [os.getcwd(), os.path.join(os.getcwd(), "output")]
        for d in cand_dirs:
            if os.path.isdir(d):
                try:
                    parts = scan_partitions(d, zstd_bin=get_host_zstd())
                    if parts:
                        self.cfg["imgs_path"] = d
                        self.partitions = parts
                        self._detect_prop(d)
                        break
                except Exception:
                    pass

    def _detect_prop(self, path: str):
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".prop") or f == "build.prop":
                    try:
                        with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as pf:
                            for line in pf:
                                line = line.strip()
                                if "=" not in line or line.startswith("#"):
                                    continue
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip()
                                if k in ("ro.product.device", "ro.build.product", "ro.product.board") and not self.auto_detected:
                                    self.cfg["codename"] = v
                                elif k in ("ro.product.model", "ro.product.marketname") and not self.auto_detected:
                                    self.cfg["device"] = v
                                elif k in ("ro.build.display.id", "ro.build.version.incremental") and not self.auto_detected:
                                    self.cfg["version"] = v
                    except OSError:
                        pass
        self.auto_detected = True

    def run(self):
        self.term.enter_fullscreen()
        try:
            while self.running:
                self.term.update_size()
                self.term.clear(default_bg=None)
                self.click_regions.clear()

                # Animate stars
                self.starfield.tick(self.term.width, self.term.height)

                # Render active page
                if self.page == self.PAGE_MAIN:
                    self._render_main()
                elif self.page == self.PAGE_WIZARD:
                    self._render_wizard()
                elif self.page == self.PAGE_EXPLORER:
                    self._render_explorer()
                elif self.page == self.PAGE_INSPECT:
                    self._render_inspect()
                elif self.page == self.PAGE_SETTINGS:
                    self._render_settings()
                elif self.page == self.PAGE_BUILDING:
                    self._render_building()
                elif self.page == self.PAGE_COMPLETE:
                    self._render_complete()

                # Render starfield into non-occupied background space
                visible_stars = self.starfield.get_visible_stars(self.term.occupied_cells)
                for sx, sy, ch, var in visible_stars:
                    star_fg = self.theme.accent if ch == '✦' else (self.theme.highlight if var == 1 else self.theme.star)
                    self.term.put_char(sx, sy, ch, fg=star_fg, bg=None, occupied=False)

                # Flush frame to terminal
                self.term.flush()

                # Read non-blocking input
                key = self.term.read_key(timeout=0.035)
                if key is not None:
                    self._handle_input(key)

        except KeyboardInterrupt:
            pass
        finally:
            self.term.exit_fullscreen()

    # =========================================================================
    # Page Renderers
    # =========================================================================

    def _render_main(self):
        header_bottom = draw_header(self.term, self.theme, compact=(self.term.height < 28))

        w, h = self.term.width, self.term.height
        menu_w = 30
        desc_w = min(38, max(24, w - menu_w - 18))
        total_w = menu_w + 4 + desc_w

        menu_x = max(2, (w - total_w) // 2)
        menu_y = header_bottom + 1
        desc_x = menu_x + menu_w + 4

        # Register clickable regions for each menu item
        for idx in range(len(self.menu_items)):
            item_y = menu_y + idx * 2
            self.click_regions.append((menu_x, item_y, menu_x + menu_w, item_y, ("menu_click", idx)))

        # Draw left menu + right snug transparent floating description box
        draw_description_menu(
            self.term, menu_x, menu_y, self.menu_items, self.menu_idx,
            self.theme, desc_x, desc_w,
            ascii_mode=self.starfield.compact
        )

        # Draw centered status summary below menu
        status_y = menu_y + len(self.menu_items) * 2 + 1
        dev_val = f"{self.cfg['device']} [{self.cfg['codename']}]" if self.cfg['codename'] else self.cfg['device']
        fw_path = self.cfg['imgs_path'] or "None"
        if fw_path != "None" and len(fw_path) > 36:
            fw_path = "..." + fw_path[-33:]

        parts_val = f"{len(self.partitions)} partitions discovered" if self.partitions else "None (select folder)"

        summary_lines = [
            ("Target", dev_val),
            ("Firmware", fw_path),
            ("Status", parts_val),
        ]
        draw_status_summary(self.term, status_y, summary_lines, self.theme)

        # Footer hints
        draw_footer(self.term, "[↑/↓] Navigate   •   [Enter] Select   •   [q] Quit", self.theme)

    def _render_wizard(self):
        w, h = self.term.width, self.term.height
        card_w = min(78, w - 4)
        card_h = min(22, h - 4)
        card_x = max(2, (w - card_w) // 2)
        card_y = 2

        draw_card(self.term, card_x, card_y, card_w, card_h,
                  title="FLASHABLE PACKAGE BUILDER", theme=self.theme, active=True,
                  ascii_mode=self.starfield.compact, fill_bg=False)

        start_y = card_y + 2
        for idx, (key, label, subtext, f_type) in enumerate(self.wizard_fields):
            field_y = start_y + idx * 2
            if field_y >= card_y + card_h - 2:
                break
            focused = (idx == self.wizard_idx)
            val = self.cfg.get(key, "")

            # Clickable region for field
            self.click_regions.append((card_x + 2, field_y, card_x + card_w - 4, field_y + 2, ("wizard_click", idx)))

            if f_type in ("text", "number"):
                disp_val = str(self.edit_buffer if (focused and self.wizard_editing) else val)
                if not disp_val and key == "imgs_path":
                    disp_val = "<Press Enter to browse folders>"
                draw_form_input(
                    self.term, card_x + 3, field_y, card_w - 10,
                    label, subtext, disp_val, focused, self.theme,
                    ascii_mode=self.starfield.compact
                )
            elif f_type == "select_vbmeta":
                draw_form_dropdown(
                    self.term, card_x + 3, field_y, card_w - 10,
                    label, subtext, f"{val.upper()}", focused, self.theme,
                    ascii_mode=self.starfield.compact
                )
            elif f_type == "toggle":
                draw_form_toggle(
                    self.term, card_x + 3, field_y,
                    label, subtext, bool(val), focused, self.theme
                )
            elif f_type == "button":
                btn_str = f" [ {label} ] "
                bx = card_x + (card_w - len(btn_str)) // 2
                self.term.put_str(bx, field_y + 1, btn_str,
                                  fg=self.theme.accent if focused else self.theme.highlight,
                                  bg=self.theme.selection_bg if focused else None,
                                  bold=True, occupied=True)

        if self.wizard_editing:
            footer = "[Enter] Save   •   [Esc] Cancel edit"
        else:
            footer = "[↑/↓] Navigate   •   [Enter] Edit/Select   •   [Tab] Next   •   [Esc] Back"
        draw_footer(self.term, footer, self.theme)

    def _render_explorer(self):
        w, h = self.term.width, self.term.height
        card_w = min(84, w - 4)
        card_h = min(20, h - 4)
        card_x = max(2, (w - card_w) // 2)
        card_y = 2

        draw_card(self.term, card_x, card_y, card_w, card_h,
                  title="SELECT FIRMWARE DIRECTORY", theme=self.theme, active=True,
                  ascii_mode=self.starfield.compact, fill_bg=False)

        # Current directory path
        p_disp = self.explorer_path
        if len(p_disp) > card_w - 14:
            p_disp = "..." + p_disp[-(card_w - 17):]
        self.term.put_str(card_x + 3, card_y + 2, f"Path: {p_disp}", fg=self.theme.highlight, bg=None, bold=True, occupied=True)

        if not self.explorer_entries:
            self._load_explorer_entries()

        list_y = card_y + 4
        max_rows = card_h - 6
        start_idx = max(0, min(self.explorer_idx - max_rows // 2, max(0, len(self.explorer_entries) - max_rows)))

        for row in range(max_rows):
            entry_idx = start_idx + row
            if entry_idx >= len(self.explorer_entries):
                break
            name, is_dir, info = self.explorer_entries[entry_idx]
            is_sel = (entry_idx == self.explorer_idx)
            cy = list_y + row

            self.click_regions.append((card_x + 3, cy, card_x + card_w - 4, cy, ("explorer_click", entry_idx)))

            prefix = "> " if is_sel else "  "
            icon = "[DIR] " if is_dir else "[IMG] "
            row_fg = self.theme.accent if is_sel else (self.theme.fg if is_dir else self.theme.muted)
            row_bg = self.theme.selection_bg if is_sel else None

            line = f"{prefix}{icon}{name}"
            padded = line.ljust(card_w - 24)[:card_w - 24]
            self.term.put_str(card_x + 3, cy, padded, fg=row_fg, bg=row_bg, bold=is_sel, occupied=True)
            self.term.put_str(card_x + card_w - 20, cy, info[:16].rjust(16), fg=self.theme.muted, bg=row_bg, occupied=True)

        draw_footer(self.term, "[↑/↓] Navigate   •   [Enter] Open   •   [Space] Select Folder   •   [Esc] Cancel", self.theme)

    def _render_inspect(self):
        w, h = self.term.width, self.term.height
        card_w = min(88, w - 4)
        card_h = min(22, h - 4)
        card_x = max(2, (w - card_w) // 2)
        card_y = 2

        draw_card(self.term, card_x, card_y, card_w, card_h,
                  title="PARTITION INSPECTION", theme=self.theme, active=True,
                  ascii_mode=self.starfield.compact, fill_bg=False)

        if not self.partitions:
            self.term.put_str(card_x + 4, card_y + 4, "No partitions loaded yet.", fg=self.theme.warning, bg=None, bold=True, occupied=True)
            self.term.put_str(card_x + 4, card_y + 6, "Please select a firmware folder containing .img or .img.zst files.", fg=self.theme.muted, bg=None, occupied=True)
            draw_footer(self.term, "[Esc] Back to Menu", self.theme)
            return

        self.term.put_str(card_x + 4, card_y + 2, "PARTITION".ljust(22) + "TYPE".ljust(20) + "FORMAT".ljust(12) + "SIZE",
                          fg=self.theme.highlight, bg=None, bold=True, occupied=True)
        self.term.put_str(card_x + 4, card_y + 3, "─" * (card_w - 8), fg=self.theme.border, bg=None, occupied=True)

        rows = list(self.partitions.items())
        list_y = card_y + 4
        max_rows = card_h - 7

        total_sz = 0
        for i in range(min(max_rows, len(rows))):
            name, info = rows[i]
            ptype = info.get("type", "firmware").upper()
            fmt = ".img.zst" if info.get("is_zstd") else ".img"
            raw_sz = info.get("raw_size", 0)
            total_sz += raw_sz
            sz_str = f"{raw_sz / (1024*1024):.1f} MB" if raw_sz < 1024*1024*1024 else f"{raw_sz / (1024*1024*1024):.2f} GB"

            cy = list_y + i
            col_fg = self.theme.accent if "SUPER" in ptype else self.theme.fg
            self.term.put_str(card_x + 4, cy, name.ljust(22), fg=col_fg, bg=None, occupied=True)
            self.term.put_str(card_x + 26, cy, ptype.ljust(20), fg=self.theme.muted, bg=None, occupied=True)
            self.term.put_str(card_x + 46, cy, fmt.ljust(12), fg=self.theme.success, bg=None, occupied=True)
            self.term.put_str(card_x + 58, cy, sz_str, fg=self.theme.highlight, bg=None, occupied=True)

        tot_str = f"{total_sz / (1024*1024*1024):.2f} GB"
        sum_str = f"Total {len(rows)} partitions discovered ({tot_str} uncompressed)"
        self.term.put_str(card_x + 4, card_y + card_h - 2, sum_str, fg=self.theme.success, bg=None, bold=True, occupied=True)

        draw_footer(self.term, "[Esc] Back to Menu", self.theme)

    def _render_settings(self):
        """Settings page (Transparent cards)"""
        w, h = self.term.width, self.term.height
        card_w = min(80, w - 4)
        card_x = max(2, (w - card_w) // 2)
        card_y = 2

        header_text = "SETTINGS"
        hx = max(0, (w - len(header_text)) // 2)
        self.term.put_str(hx, 1, header_text, fg=self.theme.fg, bg=None, bold=True, occupied=True)

        # Card 1: INTERFACE
        intf_h = 13
        draw_card(self.term, card_x, card_y + 1, card_w, intf_h,
                  title="INTERFACE", theme=self.theme, active=False,
                  ascii_mode=self.starfield.compact, fill_bg=False)

        # Field 0: Interface Theme dropdown
        f0_sel = (self.settings_idx == 0)
        self.click_regions.append((card_x + 3, card_y + 2, card_x + card_w - 6, card_y + 4, ("settings_click", 0)))
        draw_form_dropdown(
            self.term, card_x + 3, card_y + 2, card_w - 10,
            "Interface Theme", "Visual style for SpeedFlasher TUI",
            f"{self.theme.name}", f0_sel, self.theme,
            ascii_mode=self.starfield.compact
        )

        # Field 1: Compatibility Mode toggle
        f1_sel = (self.settings_idx == 1)
        self.click_regions.append((card_x + 3, card_y + 6, card_x + card_w - 6, card_y + 8, ("settings_click", 1)))
        draw_form_toggle(
            self.term, card_x + 3, card_y + 6,
            "Compatibility Mode", "Use standard ASCII characters for stars (*, +, .)",
            self.starfield.compact, f1_sel, self.theme
        )

        # Field 2: Show stars toggle
        f2_sel = (self.settings_idx == 2)
        self.click_regions.append((card_x + 3, card_y + 9, card_x + card_w - 6, card_y + 11, ("settings_click", 2)))
        draw_form_toggle(
            self.term, card_x + 3, card_y + 9,
            "Show stars", "Display animated stars in the background",
            self.starfield.enabled, f2_sel, self.theme
        )

        # Card 2: SYSTEM
        def_y = card_y + intf_h + 2
        def_h = min(6, h - def_y - 2)
        if def_h >= 4:
            draw_card(self.term, card_x, def_y, card_w, def_h,
                      title="SYSTEM", theme=self.theme, active=False,
                      ascii_mode=self.starfield.compact, fill_bg=False)
            plat = get_current_platform()
            z_bin = get_host_zstd() or "internal"
            self.term.put_str(card_x + 4, def_y + 2, f"OS: {plat.__name__}   •   ZSTD: {os.path.basename(z_bin)}", fg=self.theme.muted, bg=None, occupied=True)

        draw_footer(self.term, "[↑/↓] Navigate   •   [Enter/Click] Toggle   •   [Tab] Next   •   [Esc] Back", self.theme)

    def _render_building(self):
        w, h = self.term.width, self.term.height
        card_w = min(84, w - 4)
        card_h = min(22, h - 4)
        card_x = max(2, (w - card_w) // 2)
        card_y = 2

        draw_card(self.term, card_x, card_y, card_w, card_h,
                  title="BUILDING FLASHABLE PACKAGE", theme=self.theme, active=True,
                  ascii_mode=self.starfield.compact, fill_bg=False)

        while not self.build_log_queue.empty():
            line = self.build_log_queue.get_nowait()
            self.build_logs.append(line)
            if "[1/5]" in line:
                self.build_stage_num = 1
                self.build_stage_text = "Partition Discovery"
            elif "[2/5]" in line:
                self.build_stage_num = 2
                self.build_stage_text = f"AVB 2.0 ({self.cfg['vbmeta'].upper()})"
            elif "[3/5]" in line:
                self.build_stage_num = 3
                self.build_stage_text = f"ZSTD Compression (L{self.cfg['zstd_level']})"
            elif "[4/5]" in line:
                self.build_stage_num = 4
                self.build_stage_text = "Recovery & Fastboot Generation"
            elif "[5/5]" in line:
                self.build_stage_num = 5
                self.build_stage_text = "Packaging Final ZIP"

        pct = (self.build_stage_num / 5.0) * 100.0
        draw_progress_bar(self.term, card_x + 4, card_y + 2, card_w - 8,
                          pct, label=f"Stage {self.build_stage_num}/5: {self.build_stage_text}", theme=self.theme)

        log_box_y = card_y + 4
        log_box_h = card_h - 6
        draw_card(self.term, card_x + 3, log_box_y, card_w - 6, log_box_h,
                  title="BUILD LOG", theme=self.theme, active=False, ascii_mode=self.starfield.compact, fill_bg=False)

        max_log_rows = log_box_h - 2
        recent_logs = self.build_logs[-max_log_rows:]
        for idx, line in enumerate(recent_logs):
            ly = log_box_y + 1 + idx
            line_disp = line.strip()[:card_w - 12]
            l_fg = self.theme.accent if "->" in line_disp else (self.theme.success if "ready" in line_disp.lower() else self.theme.fg)
            self.term.put_str(card_x + 5, ly, line_disp, fg=l_fg, bg=None, occupied=True)

        if self.build_thread and not self.build_thread.is_alive():
            if self.build_success:
                self.page = self.PAGE_COMPLETE
            else:
                self.term.put_str(card_x + 4, card_y + card_h - 2,
                                  f"Build Failed: {self.build_error or 'Unknown Error'}",
                                  fg=self.theme.error, bg=None, bold=True, occupied=True)
                draw_footer(self.term, "[Esc] Back to Menu", self.theme)
                return

        elapsed = time.monotonic() - self.build_start_time
        draw_footer(self.term, f"Elapsed: {elapsed:.1f}s   •   Processing partitions...", self.theme)

    def _render_complete(self):
        w, h = self.term.width, self.term.height
        card_w = min(82, w - 4)
        card_h = min(20, h - 4)
        card_x = max(2, (w - card_w) // 2)
        card_y = 2

        draw_card(self.term, card_x, card_y, card_w, card_h,
                  title="BUILD SUCCESSFUL", theme=self.theme, active=True,
                  ascii_mode=self.starfield.compact, fill_bg=False)

        res = self.build_result
        out_zip = getattr(res, "output_zip", "")
        sz = getattr(res, "size_mb", 0.0)

        self.term.put_str(card_x + 4, card_y + 2, "✔ Flashable Package Created Successfully!", fg=self.theme.success, bg=None, bold=True, occupied=True)

        lines = [
            f"Device        : {self.cfg['device']} ({self.cfg['codename']})",
            f"ROM Version   : {self.cfg['version']}",
            f"Maintainer    : {self.cfg['maintainer']}",
            f"Package Size  : {sz:.2f} MB",
            f"Output File   : {os.path.basename(out_zip)}",
            f"Full Path     : {out_zip}",
        ]
        for i, l in enumerate(lines):
            self.term.put_str(card_x + 4, card_y + 4 + i, l, fg=self.theme.fg, bg=None, occupied=True)

        inst_y = card_y + 11
        self.term.put_str(card_x + 4, inst_y, "Flash Instructions:", fg=self.theme.highlight, bg=None, bold=True, occupied=True)
        self.term.put_str(card_x + 6, inst_y + 1, "• Recovery: Flash directly via TWRP / OrangeFox Recovery.", fg=self.theme.muted, bg=None, occupied=True)
        self.term.put_str(card_x + 6, inst_y + 2, "• Windows : Extract and run flash_windows.bat in Fastboot mode.", fg=self.theme.muted, bg=None, occupied=True)
        self.term.put_str(card_x + 6, inst_y + 3, "• Linux/Termux: Extract and run flash_linux.sh or flash_termux.sh.", fg=self.theme.muted, bg=None, occupied=True)

        draw_footer(self.term, "[Enter] Return to Menu   •   [Esc] Exit", self.theme)

    # =========================================================================
    # Input & Navigation Handling (Zero Glitch / Rock-Solid)
    # =========================================================================

    def _handle_input(self, key: Union[str, Tuple[str, int, int]]):
        if self.page == self.PAGE_MAIN:
            self._input_main(key)
        elif self.page == self.PAGE_WIZARD:
            self._input_wizard(key)
        elif self.page == self.PAGE_EXPLORER:
            self._input_explorer(key)
        elif self.page == self.PAGE_INSPECT:
            self._input_inspect(key)
        elif self.page == self.PAGE_SETTINGS:
            self._input_settings(key)
        elif self.page == self.PAGE_BUILDING:
            self._input_building(key)
        elif self.page == self.PAGE_COMPLETE:
            self._input_complete(key)

    def _input_main(self, key: Union[str, Tuple[str, int, int]]):
        # Mouse click support
        if isinstance(key, tuple) and key[0] == 'MOUSE_CLICK':
            col, row = key[1], key[2]
            for x1, y1, x2, y2, payload in self.click_regions:
                if x1 <= col <= x2 and y1 <= row <= y2:
                    if payload[0] == "menu_click":
                        clicked_idx = payload[1]
                        if self.menu_idx == clicked_idx:
                            self._activate_menu_action()
                        else:
                            self.menu_idx = clicked_idx
                        return
            return

        # Up Navigation (Arrow, Vim k, WASD w)
        if key in (KEY_UP, "k", "K", "w", "W"):
            self.menu_idx = (self.menu_idx - 1) % len(self.menu_items)
            return

        # Down Navigation (Arrow, Vim j, WASD s)
        if key in (KEY_DOWN, "j", "J", "s", "S"):
            self.menu_idx = (self.menu_idx + 1) % len(self.menu_items)
            return

        # Action Execution
        if key in (KEY_ENTER, KEY_SPACE):
            self._activate_menu_action()
            return

        # Direct number shortcuts (1-6)
        if isinstance(key, str) and key.isdigit():
            num = int(key)
            if 1 <= num <= len(self.menu_items):
                self.menu_idx = num - 1
                self._activate_menu_action()
                return

        # Clean Quit
        if key in ("q", "Q"):
            self.running = False
            return

        # NOTE: KEY_ESC does NOTHING on the main screen to prevent any glitch from exiting the tool!

    def _activate_menu_action(self):
        _, _, action = self.menu_items[self.menu_idx]
        if action == "action_wizard":
            self.page = self.PAGE_WIZARD
        elif action == "action_browse":
            self.page = self.PAGE_EXPLORER
            self._load_explorer_entries()
        elif action == "action_inspect":
            self.page = self.PAGE_INSPECT
        elif action == "action_cycle_vbmeta":
            modes = ["skip", "disable", "enable"]
            cur = self.cfg["vbmeta"]
            next_idx = (modes.index(cur) + 1) % len(modes)
            self.cfg["vbmeta"] = modes[next_idx]
        elif action == "action_settings":
            self.page = self.PAGE_SETTINGS
        elif action == "action_exit":
            self.running = False

    def _input_wizard(self, key: Union[str, Tuple[str, int, int]]):
        if isinstance(key, tuple) and key[0] == 'MOUSE_CLICK':
            col, row = key[1], key[2]
            for x1, y1, x2, y2, payload in self.click_regions:
                if x1 <= col <= x2 and y1 <= row <= y2:
                    if payload[0] == "wizard_click":
                        self.wizard_idx = payload[1]
                        field_key, _, _, f_type = self.wizard_fields[self.wizard_idx]
                        if f_type == "button":
                            self._start_build()
                        elif f_type == "toggle":
                            self.cfg[field_key] = not self.cfg[field_key]
                        elif f_type == "select_vbmeta":
                            modes = ["skip", "disable", "enable"]
                            cur = self.cfg["vbmeta"]
                            self.cfg["vbmeta"] = modes[(modes.index(cur) + 1) % len(modes)]
                        elif f_type in ("text", "number"):
                            self.wizard_editing = True
                            self.edit_buffer = str(self.cfg.get(field_key, ""))
                        return
            return

        if self.wizard_editing:
            field_key, _, _, f_type = self.wizard_fields[self.wizard_idx]
            if key == KEY_ENTER:
                if f_type == "number":
                    try:
                        self.cfg[field_key] = int(self.edit_buffer)
                    except ValueError:
                        pass
                else:
                    self.cfg[field_key] = self.edit_buffer
                self.wizard_editing = False
                if field_key == "imgs_path" and os.path.isdir(self.cfg["imgs_path"]):
                    self.partitions = scan_partitions(self.cfg["imgs_path"], zstd_bin=get_host_zstd())
                    self._detect_prop(self.cfg["imgs_path"])
            elif key == KEY_ESC:
                self.wizard_editing = False
            elif key == KEY_BACKSPACE:
                self.edit_buffer = self.edit_buffer[:-1]
            elif isinstance(key, str) and len(key) == 1:
                self.edit_buffer += key
            return

        if key in (KEY_UP, "k", "K", "w", "W"):
            self.wizard_idx = (self.wizard_idx - 1) % len(self.wizard_fields)
        elif key in (KEY_DOWN, "j", "J", "s", "S", KEY_TAB):
            self.wizard_idx = (self.wizard_idx + 1) % len(self.wizard_fields)
        elif key == KEY_SHIFT_TAB:
            self.wizard_idx = (self.wizard_idx - 1) % len(self.wizard_fields)
        elif key in (KEY_ENTER, KEY_SPACE):
            field_key, _, _, f_type = self.wizard_fields[self.wizard_idx]
            if f_type in ("text", "number"):
                if field_key == "imgs_path" and not self.cfg["imgs_path"]:
                    self.page = self.PAGE_EXPLORER
                    self._load_explorer_entries()
                    return
                self.wizard_editing = True
                self.edit_buffer = str(self.cfg.get(field_key, ""))
            elif f_type == "select_vbmeta":
                modes = ["skip", "disable", "enable"]
                cur = self.cfg["vbmeta"]
                self.cfg["vbmeta"] = modes[(modes.index(cur) + 1) % len(modes)]
            elif f_type == "toggle":
                self.cfg[field_key] = not self.cfg[field_key]
            elif f_type == "button":
                self._start_build()
        elif key in (KEY_ESC, "b", "B"):
            self.page = self.PAGE_MAIN

    def _input_settings(self, key: Union[str, Tuple[str, int, int]]):
        if isinstance(key, tuple) and key[0] == 'MOUSE_CLICK':
            col, row = key[1], key[2]
            for x1, y1, x2, y2, payload in self.click_regions:
                if x1 <= col <= x2 and y1 <= row <= y2:
                    if payload[0] == "settings_click":
                        self.settings_idx = payload[1]
                        self._toggle_current_setting(step=1)
                        return
            return

        if key in (KEY_UP, "k", "K", "w", "W"):
            self.settings_idx = (self.settings_idx - 1) % len(self.settings_fields)
        elif key in (KEY_DOWN, "j", "J", "s", "S", KEY_TAB):
            self.settings_idx = (self.settings_idx + 1) % len(self.settings_fields)
        elif key == KEY_SHIFT_TAB:
            self.settings_idx = (self.settings_idx - 1) % len(self.settings_fields)
        elif key in (KEY_ENTER, KEY_SPACE, KEY_RIGHT):
            self._toggle_current_setting(step=1)
        elif key == KEY_LEFT:
            self._toggle_current_setting(step=-1)
        elif key in (KEY_ESC, "b", "B", "q", "Q"):
            self.page = self.PAGE_MAIN

    def _toggle_current_setting(self, step: int = 1):
        field_key, _, _, _ = self.settings_fields[self.settings_idx]
        if field_key == "theme":
            self.settings_theme_idx = (self.settings_theme_idx + step) % len(self.settings_theme_list)
            th_id = self.settings_theme_list[self.settings_theme_idx]
            self.theme = ALL_THEMES[th_id]
        elif field_key == "compat":
            self.starfield.compact = not self.starfield.compact
        elif field_key == "stars":
            self.starfield.enabled = not self.starfield.enabled
        elif field_key == "density":
            densities = [0.4, 0.8, 1.6]
            cur = self.starfield.density
            next_d = densities[(densities.index(cur) + step) % len(densities)] if cur in densities else 0.8
            self.starfield.density = next_d
            self.starfield.regenerate(self.term.width, self.term.height)

    def _load_explorer_entries(self):
        self.explorer_entries = []
        try:
            parent = os.path.dirname(self.explorer_path)
            if parent and parent != self.explorer_path:
                self.explorer_entries.append((".. (Parent Directory)", True, "Parent Dir"))

            entries = sorted(os.scandir(self.explorer_path), key=lambda e: (not e.is_dir(), e.name.lower()))
            for e in entries:
                if e.is_dir():
                    try:
                        imgs = [f for f in os.listdir(e.path) if f.endswith((".img", ".img.zst"))]
                        info = f"{len(imgs)} imgs" if imgs else "Folder"
                    except Exception:
                        info = "Folder"
                    self.explorer_entries.append((e.name, True, info))
                elif e.name.endswith((".img", ".img.zst")):
                    sz_mb = e.stat().st_size / (1024 * 1024)
                    self.explorer_entries.append((e.name, False, f"{sz_mb:.1f} MB"))
        except Exception as ex:
            self.explorer_entries.append((f"Error: {ex}", False, ""))
        self.explorer_idx = 0

    def _input_explorer(self, key: Union[str, Tuple[str, int, int]]):
        if isinstance(key, tuple) and key[0] == 'MOUSE_CLICK':
            col, row = key[1], key[2]
            for x1, y1, x2, y2, payload in self.click_regions:
                if x1 <= col <= x2 and y1 <= row <= y2:
                    if payload[0] == "explorer_click":
                        clicked_idx = payload[1]
                        if self.explorer_idx == clicked_idx:
                            self._activate_explorer_item()
                        else:
                            self.explorer_idx = clicked_idx
                        return
            return

        if key in (KEY_UP, "k", "K", "w", "W"):
            self.explorer_idx = max(0, self.explorer_idx - 1)
        elif key in (KEY_DOWN, "j", "J", "s", "S"):
            self.explorer_idx = min(len(self.explorer_entries) - 1, self.explorer_idx + 1)
        elif key == KEY_ENTER:
            self._activate_explorer_item()
        elif key == KEY_SPACE:
            self.cfg["imgs_path"] = self.explorer_path
            self.partitions = scan_partitions(self.explorer_path, zstd_bin=get_host_zstd())
            self._detect_prop(self.explorer_path)
            self.page = self.PAGE_WIZARD
        elif key in (KEY_ESC, "b", "B"):
            self.page = self.PAGE_WIZARD

    def _activate_explorer_item(self):
        if 0 <= self.explorer_idx < len(self.explorer_entries):
            name, is_dir, _ = self.explorer_entries[self.explorer_idx]
            if name.startswith(".."):
                self.explorer_path = os.path.dirname(self.explorer_path)
                self._load_explorer_entries()
            elif is_dir:
                self.explorer_path = os.path.join(self.explorer_path, name)
                self._load_explorer_entries()

    def _input_inspect(self, key: Union[str, Tuple[str, int, int]]):
        if key in (KEY_ESC, KEY_ENTER, KEY_SPACE, "b", "B", "q", "Q") or isinstance(key, tuple):
            self.page = self.PAGE_MAIN

    def _input_building(self, key: Union[str, Tuple[str, int, int]]):
        if key in (KEY_ESC, "b", "B") and not (self.build_thread and self.build_thread.is_alive()):
            self.page = self.PAGE_MAIN

    def _input_complete(self, key: Union[str, Tuple[str, int, int]]):
        if key in (KEY_ENTER, KEY_SPACE, KEY_ESC, "b", "B", "q", "Q") or isinstance(key, tuple):
            self.page = self.PAGE_MAIN

    # =========================================================================
    # Build Thread Execution
    # =========================================================================

    def _start_build(self):
        imgs_path = self.cfg["imgs_path"]
        if not imgs_path or not os.path.isdir(imgs_path):
            self.page = self.PAGE_EXPLORER
            self._load_explorer_entries()
            return

        if not self.partitions:
            self.partitions = scan_partitions(imgs_path, zstd_bin=get_host_zstd())

        if not self.partitions:
            return

        self.page = self.PAGE_BUILDING
        self.build_logs.clear()
        self.build_start_time = time.monotonic()
        self.build_success = False
        self.build_error = None
        self.build_stage_num = 1
        self.build_stage_text = "Starting Build"

        def worker():
            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            cap = LogCapture(self.build_log_queue, orig_stdout)
            sys.stdout = cap
            sys.stderr = cap
            try:
                out_dir = os.path.join(_PARENT_DIR, "output")
                os.makedirs(out_dir, exist_ok=True)
                out_name = format_flashable_name(self.cfg['device'], self.cfg['version'], self.cfg['codename'])
                output_zip = os.path.join(out_dir, out_name)

                res = FlashableBuilder.build(
                    imgs_dir=imgs_path,
                    partitions=self.partitions,
                    output_zip=output_zip,
                    device=self.cfg["device"],
                    firmware=self.cfg["version"],
                    codename=self.cfg["codename"],
                    maintainer=self.cfg["maintainer"],
                    vbmeta_option=self.cfg["vbmeta"],
                    zstd_level=self.cfg["zstd_level"],
                    zip_level=self.cfg["zip_level"],
                    include_fastboot=self.cfg["include_fastboot"]
                )
                self.build_result = res
                self.build_success = True
            except Exception as e:
                self.build_error = str(e)
                self.build_success = False
                self.build_log_queue.put(f"[ERROR] {e}")
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr

        self.build_thread = threading.Thread(target=worker, daemon=True)
        self.build_thread.start()


def launch_tui():
    app = SpeedFlasherApp()
    app.run()


if __name__ == "__main__":
    launch_tui()
