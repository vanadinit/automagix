import shutil
from time import time

from tqdm import tqdm
import signal


class Cursor:
    @staticmethod
    def _print(code: str):
        print(code, end='', flush=True)

    @staticmethod
    def save():
        Cursor._print("\033[s")

    @staticmethod
    def restore():
        Cursor._print("\033[u")

    @staticmethod
    def move_up(lines: int = 1):
        Cursor._print(f"\033[{lines}A")

    @staticmethod
    def move_right(lines: int = 1):
        Cursor._print(f"\033[{lines}C")

    @staticmethod
    def move_to(row: int, col: int):
        Cursor._print(f"\033[{row};{col}f")

    @staticmethod
    def clear_line():
        Cursor._print("\033[2K")

    @staticmethod
    def set_scroll_region(top: int, bottom: int):
        # ANSI standard is 1-based.
        # Original code used 0, which most terminals treat as 1.
        Cursor._print(f"\033[{top};{bottom}r")

    @staticmethod
    def reset_scroll_region():
        Cursor._print("\033[r")


class TqdmProgressBar:
    def __init__(self):
        self.start_time = 0
        self.last_percentage = 0
        self.last_color = None
        self.cursor_col = 0
        self._orig_sigwinch_handler = None

    def _update_scroll_region(self):
        cols, lines = shutil.get_terminal_size()
        scroll_region_bottom = max(1, lines - 2)

        # Scroll down a bit to avoid visual glitch when the screen area shrinks by one row
        print("\n\n", end='', flush=True)

        Cursor.save()

        # Set scroll region (this will place the cursor in the top left usually)
        # Note: Original code used 0;...r. ANSI standard is 1-based.
        # Most terminals treat 0 as 1. We stick to the original logic to be safe.
        Cursor.set_scroll_region(0, scroll_region_bottom)

        Cursor.restore()
        Cursor.move_up(2)
        Cursor.move_right(self.cursor_col)

        self.draw(percentage=self.last_percentage, color=self.last_color)

    def _on_resize(self, signum, frame):
        self._update_scroll_region()

    def setup(self):
        self.start_time = time()
        self._update_scroll_region()

        if hasattr(signal, "SIGWINCH"):
            self._orig_sigwinch_handler = signal.signal(signal.SIGWINCH, self._on_resize)

    def draw(self, percentage: int | None, color: str = None, cursor_col: int | None = None):
        if cursor_col is not None:
            self.cursor_col = cursor_col
        if percentage is None:
            return

        self.last_percentage = percentage
        self.last_color = color

        cols, lines = shutil.get_terminal_size()

        Cursor.save()

        # Move cursor position to last row
        Cursor.move_to(lines, 0)

        # Clear progress bar line
        Cursor.clear_line()

        # Calculate stats for tqdm
        elapsed = time() - self.start_time

        # tqdm.format_meter generates the progress bar string
        # We subtract 1 from cols to avoid accidental wrapping at the very last character
        bar_str = tqdm.format_meter(
            n=percentage,
            total=100,
            elapsed=elapsed,
            ncols=cols - 1,
            unit='pct',
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
            colour=color
        )

        print(bar_str, end='', flush=True)

        # Also clear the line above the bar (the separator line) to keep it clean
        # Move cursor up one line
        Cursor.move_to(lines - 1, 0)
        Cursor.clear_line()

        Cursor.restore()

    def block(self, percentage: int | None, cursor_col: int | None = None):
        self.draw(percentage, color='yellow', cursor_col=cursor_col)

    def destroy(self):
        if hasattr(signal, "SIGWINCH") and self._orig_sigwinch_handler is not None:
            signal.signal(signal.SIGWINCH, self._orig_sigwinch_handler)

        cols, lines = shutil.get_terminal_size()

        # Scroll-Region aufheben
        Cursor.reset_scroll_region()

        # Untere Zeilen leeren
        Cursor.move_to(lines - 1, 1)
        Cursor.clear_line()
        Cursor.move_to(lines, 1)
        Cursor.clear_line()

        # Cursor sauber am Ende platzieren
        Cursor.move_to(lines, 1)
        print()
