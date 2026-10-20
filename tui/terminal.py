"""
Cross-platform Terminal Engine & Double-Buffered Differential Renderer.
Runs on Linux, Android Termux, and Windows with zero third-party dependencies.
"""
import atexit
import os
import shutil
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

from .theme import RGB, Theme, ansi_bg, ansi_fg, ANSI_RESET, ANSI_BOLD, ANSI_DIM, ANSI_UNDERLINE

IS_WINDOWS = sys.platform.startswith("win")

# Keys
KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_LEFT = "LEFT"
KEY_RIGHT = "RIGHT"
KEY_ENTER = "ENTER"
KEY_TAB = "TAB"
KEY_SHIFT_TAB = "SHIFT_TAB"
KEY_ESC = "ESC"
KEY_BACKSPACE = "BACKSPACE"
KEY_SPACE = "SPACE"


class Cell:
    __slots__ = ('char', 'fg', 'bg', 'bold', 'dim', 'underline')

    def __init__(self, char: str = ' ', fg: Optional[RGB] = None, bg: Optional[RGB] = None,
                 bold: bool = False, dim: bool = False, underline: bool = False):
        self.char = char
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.dim = dim
        self.underline = underline

    def equals(self, other: 'Cell') -> bool:
        return (self.char == other.char and
                self.fg == other.fg and
                self.bg == other.bg and
                self.bold == other.bold and
                self.dim == other.dim and
                self.underline == other.underline)

    def clone(self) -> 'Cell':
        return Cell(self.char, self.fg, self.bg, self.bold, self.dim, self.underline)


class Terminal:
    def __init__(self):
        self.width = 80
        self.height = 24
        self.truecolor = self._check_truecolor()
        self.in_fullscreen = False
        self._orig_termios = None
        self._back_buffer: List[List[Cell]] = []
        self._front_buffer: List[List[Cell]] = []
        self.occupied_cells: Set[Tuple[int, int]] = set()

        self._init_platform()
        self.update_size()

    def _check_truecolor(self) -> bool:
        ct = os.environ.get("COLORTERM", "").lower()
        if ct in ("truecolor", "24bit"):
            return True
        term = os.environ.get("TERM", "").lower()
        if any(t in term for t in ("kitty", "alacritty", "foot", "wezterm", "xterm-kitty")):
            return True
        if IS_WINDOWS and ("WT_SESSION" in os.environ or "ConEmuPID" in os.environ):
            return True
        return True

    def _init_platform(self):
        if IS_WINDOWS:
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # Enable virtual terminal processing (VT100 ANSI)
                h_out = kernel32.GetStdHandle(-11)
                mode = ctypes.c_ulong()
                kernel32.GetConsoleMode(h_out, ctypes.byref(mode))
                kernel32.SetConsoleMode(h_out, mode.value | 0x0004 | 0x0008)
            except Exception:
                pass
        else:
            try:
                import termios
                self._termios = termios
            except ImportError:
                self._termios = None

    def enter_fullscreen(self):
        if self.in_fullscreen:
            return
        self.in_fullscreen = True

        # Alternate screen buffer, hide cursor, clear
        sys.stdout.write("\033[?1049h\033[?25l\033[2J\033[H")
        sys.stdout.flush()

        if not IS_WINDOWS and self._termios and sys.stdin.isatty():
            try:
                import tty
                self._orig_termios = self._termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                pass

        atexit.register(self.exit_fullscreen)

    def exit_fullscreen(self):
        if not self.in_fullscreen:
            return
        self.in_fullscreen = False

        # Reset colors, show cursor, leave alternate buffer
        sys.stdout.write(f"{ANSI_RESET}\033[?25h\033[?1049l")
        sys.stdout.flush()

        if not IS_WINDOWS and self._termios and self._orig_termios and sys.stdin.isatty():
            try:
                self._termios.tcsetattr(sys.stdin, self._termios.TCSADRAIN, self._orig_termios)
            except Exception:
                pass

    def update_size(self) -> bool:
        try:
            sz = shutil.get_terminal_size((80, 24))
            w, h = sz.columns, sz.lines
        except Exception:
            w, h = 80, 24

        changed = (w != self.width or h != self.height)
        if changed or not self._back_buffer:
            self.width = max(20, w)
            self.height = max(10, h)
            self._back_buffer = [[Cell() for _ in range(self.width)] for _ in range(self.height)]
            self._front_buffer = [[Cell(char='\x00') for _ in range(self.width)] for _ in range(self.height)]
            # Clear terminal on resize
            if self.in_fullscreen:
                sys.stdout.write("\033[2J")
                sys.stdout.flush()
        return changed

    def clear(self, default_bg: Optional[RGB] = None):
        self.occupied_cells.clear()
        for y in range(self.height):
            for x in range(self.width):
                c = self._back_buffer[y][x]
                c.char = ' '
                c.fg = None
                c.bg = default_bg
                c.bold = False
                c.dim = False
                c.underline = False

    def put_char(self, x: int, y: int, char: str, fg: Optional[RGB] = None, bg: Optional[RGB] = None,
                 bold: bool = False, dim: bool = False, underline: bool = False, occupied: bool = True):
        if 0 <= y < self.height and 0 <= x < self.width:
            c = self._back_buffer[y][x]
            c.char = char
            c.fg = fg
            c.bg = bg
            c.bold = bold
            c.dim = dim
            c.underline = underline
            if occupied and char != ' ':
                self.occupied_cells.add((x, y))

    def put_str(self, x: int, y: int, text: str, fg: Optional[RGB] = None, bg: Optional[RGB] = None,
                bold: bool = False, dim: bool = False, underline: bool = False, occupied: bool = True,
                max_width: Optional[int] = None):
        if not (0 <= y < self.height):
            return
        limit = len(text)
        if max_width is not None:
            limit = min(limit, max_width)

        for i in range(limit):
            col = x + i
            if col >= self.width:
                break
            if col >= 0:
                self.put_char(col, y, text[i], fg, bg, bold, dim, underline, occupied=occupied)

    def mark_occupied_rect(self, x: int, y: int, w: int, h: int):
        for cy in range(max(0, y), min(self.height, y + h)):
            for cx in range(max(0, x), min(self.width, x + w)):
                self.occupied_cells.add((cx, cy))

    def flush(self):
        """
        Differential screen update: outputs minimal ANSI cursor moves and styles
        for only the terminal cells that changed.
        """
        output = []
        cur_fg = None
        cur_bg = None
        cur_bold = False
        cur_dim = False
        cur_underline = False
        cursor_x = -1
        cursor_y = -1

        for y in range(self.height):
            for x in range(self.width):
                back = self._back_buffer[y][x]
                front = self._front_buffer[y][x]

                if not back.equals(front):
                    # Move cursor if not immediately adjacent
                    if cursor_x != x or cursor_y != y:
                        output.append(f"\033[{y+1};{x+1}H")
                        cursor_x = x
                        cursor_y = y

                    # Style changes
                    style_changed = False
                    if back.fg != cur_fg or back.bg != cur_bg or back.bold != cur_bold or back.dim != cur_dim or back.underline != cur_underline:
                        style_seq = [ANSI_RESET]
                        if back.fg:
                            style_seq.append(ansi_fg(back.fg, self.truecolor))
                        if back.bg:
                            style_seq.append(ansi_bg(back.bg, self.truecolor))
                        if back.bold:
                            style_seq.append(ANSI_BOLD)
                        if back.dim:
                            style_seq.append(ANSI_DIM)
                        if back.underline:
                            style_seq.append(ANSI_UNDERLINE)

                        output.append("".join(style_seq))
                        cur_fg = back.fg
                        cur_bg = back.bg
                        cur_bold = back.bold
                        cur_dim = back.dim
                        cur_underline = back.underline

                    output.append(back.char)
                    # Update front buffer copy
                    front.char = back.char
                    front.fg = back.fg
                    front.bg = back.bg
                    front.bold = back.bold
                    front.dim = back.dim
                    front.underline = back.underline

                    cursor_x += 1

        if output:
            output.append(ANSI_RESET)
            sys.stdout.write("".join(output))
            sys.stdout.flush()

    def read_key(self, timeout: float = 0.03) -> Optional[str]:
        """
        Non-blocking key reader for Windows and Unix/Termux.
        Returns KEY_* constants or individual characters.
        """
        if IS_WINDOWS:
            import msvcrt
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ('\x00', '\xe0'):
                        ch2 = msvcrt.getwch()
                        mapping = {
                            'H': KEY_UP,
                            'P': KEY_DOWN,
                            'K': KEY_LEFT,
                            'M': KEY_RIGHT,
                            'S': 'DELETE',
                            '\x0f': KEY_SHIFT_TAB,
                        }
                        return mapping.get(ch2, None)
                    elif ch == '\r' or ch == '\n':
                        return KEY_ENTER
                    elif ch == '\t':
                        return KEY_TAB
                    elif ch == '\x1b':
                        return KEY_ESC
                    elif ch in ('\x08', '\x7f'):
                        return KEY_BACKSPACE
                    elif ch == ' ':
                        return KEY_SPACE
                    return ch
                time.sleep(0.005)
            return None
        else:
            import select
            if not sys.stdin.isatty():
                time.sleep(timeout)
                return None

            r, _, _ = select.select([sys.stdin], [], [], timeout)
            if not r:
                return None

            try:
                ch = sys.stdin.read(1)
            except Exception:
                return None

            if ch == '\x1b':
                # Check for escape sequence
                r2, _, _ = select.select([sys.stdin], [], [], 0.02)
                if not r2:
                    return KEY_ESC
                seq = sys.stdin.read(1)
                if seq == '[':
                    r3, _, _ = select.select([sys.stdin], [], [], 0.02)
                    if not r3:
                        return KEY_ESC
                    code = sys.stdin.read(1)
                    if code == 'A':
                        return KEY_UP
                    elif code == 'B':
                        return KEY_DOWN
                    elif code == 'C':
                        return KEY_RIGHT
                    elif code == 'D':
                        return KEY_LEFT
                    elif code == 'Z':
                        return KEY_SHIFT_TAB
                    elif code in ('1', '2', '3', '4', '5', '6', '7', '8'):
                        # Multi-byte sequences like delete or page up
                        select.select([sys.stdin], [], [], 0.01)
                        sys.stdin.read(1)
                        return None
                    return None
                elif seq == 'O':
                    # Cursor keys in application keypad mode
                    code = sys.stdin.read(1)
                    if code == 'A':
                        return KEY_UP
                    elif code == 'B':
                        return KEY_DOWN
                    elif code == 'C':
                        return KEY_RIGHT
                    elif code == 'D':
                        return KEY_LEFT
                return KEY_ESC
            elif ch in ('\r', '\n'):
                return KEY_ENTER
            elif ch == '\t':
                return KEY_TAB
            elif ch in ('\x7f', '\x08'):
                return KEY_BACKSPACE
            elif ch == ' ':
                return KEY_SPACE
            elif ch == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            return ch
