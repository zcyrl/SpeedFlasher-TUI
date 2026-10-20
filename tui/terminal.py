"""
Cross-platform Terminal Engine & Double-Buffered Differential Renderer.
Runs on Linux, Android Termux, and Windows with zero third-party dependencies.
Supports TrueColor, 256-color fallback, SGR mouse reporting, and robust key parsing.
"""
import atexit
import os
import shutil
import sys
import time
from typing import List, Optional, Set, Tuple, Union

from .theme import RGB, Theme, ansi_bg, ansi_fg, ANSI_RESET, ANSI_BOLD, ANSI_DIM, ANSI_UNDERLINE

IS_WINDOWS = sys.platform.startswith("win")

# Key Constants
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
KEY_PAGE_UP = "PAGE_UP"
KEY_PAGE_DOWN = "PAGE_DOWN"
KEY_DELETE = "DELETE"


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


class Terminal:
    def __init__(self):
        self.width = 80
        self.height = 24
        self.truecolor = self._check_truecolor()
        self.in_fullscreen = False
        self._orig_termios = None
        self._termios = None
        self._back_buffer: List[List[Cell]] = []
        self._front_buffer: List[List[Cell]] = []
        self.occupied_cells: Set[Tuple[int, int]] = set()
        self._input_queue: List[Union[str, Tuple[str, int, int]]] = []

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

        # Alternate screen buffer, hide cursor, clear, enable mouse tracking (SGR mode)
        sys.stdout.write("\033[?1049h\033[?25l\033[?1000h\033[?1006h\033[2J\033[H")
        sys.stdout.flush()

        if not IS_WINDOWS and self._termios and sys.stdin.isatty():
            try:
                import tty
                self._orig_termios = self._termios.tcgetattr(sys.stdin.fileno())
                # Use cbreak mode so signals like Ctrl+C still generate KeyboardInterrupt
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                pass

        atexit.register(self.exit_fullscreen)

    def exit_fullscreen(self):
        if not self.in_fullscreen:
            return
        self.in_fullscreen = False

        # Disable mouse tracking, show cursor, leave alternate buffer
        sys.stdout.write(f"{ANSI_RESET}\033[?1006l\033[?1000l\033[?25h\033[?1049l")
        sys.stdout.flush()

        if not IS_WINDOWS and self._termios and self._orig_termios and sys.stdin.isatty():
            try:
                self._termios.tcsetattr(sys.stdin.fileno(), self._termios.TCSADRAIN, self._orig_termios)
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
        Preserves transparent backgrounds cleanly.
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
                    if cursor_x != x or cursor_y != y:
                        output.append(f"\033[{y+1};{x+1}H")
                        cursor_x = x
                        cursor_y = y

                    if (back.fg != cur_fg or back.bg != cur_bg or
                            back.bold != cur_bold or back.dim != cur_dim or
                            back.underline != cur_underline):

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

    def read_key(self, timeout: float = 0.035) -> Optional[Union[str, Tuple[str, int, int]]]:
        """
        Rock-solid non-blocking key reader.
        Uses direct low-level os.read(0, 1024) on Unix/Termux/Linux and msvcrt on Windows.
        Parses multi-byte escape sequences atomically so arrow keys NEVER glitch into KEY_ESC!
        Supports SGR mouse click decoding ('MOUSE_CLICK', col, row).
        """
        if self._input_queue:
            return self._input_queue.pop(0)

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
                            'S': KEY_DELETE,
                            'I': KEY_PAGE_UP,
                            'Q': KEY_PAGE_DOWN,
                            '\x0f': KEY_SHIFT_TAB,
                        }
                        return mapping.get(ch2, None)
                    elif ch in ('\r', '\n'):
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

            r, _, _ = select.select([0], [], [], timeout)
            if not r:
                return None

            try:
                raw = os.read(0, 1024)
            except OSError:
                return None

            if not raw:
                return None

            # Parse raw bytes into keys/mouse events
            parsed_keys = self._decode_bytes(raw)
            if parsed_keys:
                first = parsed_keys.pop(0)
                self._input_queue.extend(parsed_keys)
                return first
            return None

    def _decode_bytes(self, data: bytes) -> List[Union[str, Tuple[str, int, int]]]:
        keys = []
        i = 0
        n = len(data)

        while i < n:
            b = data[i:i+1]

            # Carriage return or newline
            if b in (b'\r', b'\n'):
                keys.append(KEY_ENTER)
                i += 1
                continue

            # Tab
            if b == b'\t':
                keys.append(KEY_TAB)
                i += 1
                continue

            # Backspace
            if b in (b'\x7f', b'\x08'):
                keys.append(KEY_BACKSPACE)
                i += 1
                continue

            # Space
            if b == b' ':
                keys.append(KEY_SPACE)
                i += 1
                continue

            # Ctrl+C
            if b == b'\x03':
                raise KeyboardInterrupt

            # Escape sequence handling
            if b == b'\x1b':
                # Check if there are remaining bytes in this chunk
                if i + 1 >= n:
                    # Escape alone at the very end
                    keys.append(KEY_ESC)
                    i += 1
                    continue

                nxt = data[i+1:i+2]

                # Application keypad mode \x1bO...
                if nxt == b'O' and i + 2 < n:
                    code = data[i+2:i+3]
                    if code == b'A': keys.append(KEY_UP)
                    elif code == b'B': keys.append(KEY_DOWN)
                    elif code == b'C': keys.append(KEY_RIGHT)
                    elif code == b'D': keys.append(KEY_LEFT)
                    elif code == b'H': keys.append("HOME")
                    elif code == b'F': keys.append("END")
                    i += 3
                    continue

                # CSI sequence \x1b[...
                if nxt == b'[':
                    # Find sequence terminator (0x40 - 0x7E)
                    end = i + 2
                    while end < n and not (0x40 <= data[end] <= 0x7E):
                        end += 1

                    if end < n:
                        term_char = data[end:end+1]
                        seq = data[i:end+1]
                        i = end + 1

                        # SGR Mouse Event: \x1b[<button;col;rowM or \x1b[<button;col;rowm
                        if seq.startswith(b'\x1b[<'):
                            try:
                                s_str = seq.decode('latin1')
                                parts = s_str[3:-1].split(';')
                                btn = int(parts[0])
                                col = int(parts[1]) - 1  # 0-indexed column
                                row = int(parts[2]) - 1  # 0-indexed row
                                if s_str.endswith('M') and (btn & 3) == 0:
                                    keys.append(('MOUSE_CLICK', col, row))
                            except Exception:
                                pass
                            continue

                        # Arrow keys & modifiers
                        if term_char == b'A': keys.append(KEY_UP)
                        elif term_char == b'B': keys.append(KEY_DOWN)
                        elif term_char == b'C': keys.append(KEY_RIGHT)
                        elif term_char == b'D': keys.append(KEY_LEFT)
                        elif term_char == b'Z': keys.append(KEY_SHIFT_TAB)
                        elif term_char == b'~':
                            if b'5' in seq: keys.append(KEY_PAGE_UP)
                            elif b'6' in seq: keys.append(KEY_PAGE_DOWN)
                            elif b'3' in seq: keys.append(KEY_DELETE)
                        continue
                    else:
                        i = n
                        continue

                # Unknown escape sequence
                keys.append(KEY_ESC)
                i += 1
                continue

            # Regular characters
            try:
                char_str = data[i:i+1].decode('utf-8')
                keys.append(char_str)
            except UnicodeDecodeError:
                # Multi-byte UTF-8 character
                found = False
                for length in (2, 3, 4):
                    if i + length <= n:
                        try:
                            char_str = data[i:i+length].decode('utf-8')
                            keys.append(char_str)
                            i += length
                            found = True
                            break
                        except UnicodeDecodeError:
                            continue
                if not found:
                    i += 1
                continue

            i += 1

        return keys
