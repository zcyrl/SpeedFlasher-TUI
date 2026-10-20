"""
Animated blinking stars background engine for SpeedFlasher TUI.
Faithfully recreates Antumbra TUI's celestial starfield animation.
"""
import random
import time
from typing import List, Set, Tuple

STAR_CHARS = ['✦', '✧', '·', ' ']
STAR_CHARS_COMPACT = ['*', '+', '.', ' ']


class Star:
    __slots__ = ('x', 'y', 'char_idx', 'next_twinkle', 'color_variant')

    def __init__(self, x: int, y: int, char_idx: int, next_twinkle: float, color_variant: int = 0):
        self.x = x
        self.y = y
        self.char_idx = char_idx
        self.next_twinkle = next_twinkle
        self.color_variant = color_variant


class Starfield:
    def __init__(self, density: float = 0.8, compact: bool = False, enabled: bool = True):
        self.density = density
        self.compact = compact
        self.enabled = enabled
        self.stars: List[Star] = []
        self.last_width = 0
        self.last_height = 0

    def regenerate(self, width: int, height: int):
        self.last_width = width
        self.last_height = height
        self.stars.clear()

        if width <= 0 or height <= 0 or not self.enabled:
            return

        total_cells = width * height
        num_stars = max(5, int((total_cells / 100.0) * self.density))
        chars = STAR_CHARS_COMPACT if self.compact else STAR_CHARS
        char_len = len(chars)
        now = time.monotonic()

        for _ in range(num_stars):
            x = random.randint(0, max(0, width - 1))
            y = random.randint(0, max(0, height - 1))
            char_idx = random.randint(0, char_len - 1)
            delay = random.uniform(0.05, 0.6)
            color_variant = random.randint(0, 2)
            self.stars.append(Star(x, y, char_idx, now + delay, color_variant))

    def tick(self, width: int, height: int):
        if not self.enabled:
            return

        if width != self.last_width or height != self.last_height:
            self.regenerate(width, height)
            return

        now = time.monotonic()
        chars = STAR_CHARS_COMPACT if self.compact else STAR_CHARS
        char_len = len(chars)

        for star in self.stars:
            if now >= star.next_twinkle:
                if random.random() < 0.7:
                    star.char_idx = (star.char_idx + 1) % char_len
                else:
                    star.char_idx = random.randint(0, char_len - 1)

                delay = random.uniform(0.15, 0.42)
                star.next_twinkle = now + delay

    def get_visible_stars(self, occupied_cells: Set[Tuple[int, int]]) -> List[Tuple[int, int, str, int]]:
        """
        Returns a list of (x, y, character, color_variant) for active stars
        that are not obscured by UI cards or text.
        """
        if not self.enabled:
            return []

        chars = STAR_CHARS_COMPACT if self.compact else STAR_CHARS
        result = []
        for star in self.stars:
            ch = chars[star.char_idx]
            if ch != ' ' and (star.x, star.y) not in occupied_cells:
                result.append((star.x, star.y, ch, star.color_variant))
        return result
