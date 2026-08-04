import os
import shutil
import signal
from abc import abstractmethod, ABCMeta
from time import time


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


class MetaProgressBar(ABCMeta):
    """Meta class for progress bars."""

    @abstractmethod
    def setup(self):
        raise NotImplementedError

    @abstractmethod
    def draw(self, percentage: int | None, color: str | None = None, cursor_col: int | None = None):
        raise NotImplementedError

    @abstractmethod
    def block(self, percentage: int | None, cursor_col: int | None = None):
        raise NotImplementedError

    @abstractmethod
    def destroy(self):
        raise NotImplementedError


class BasicProgressBar(metaclass=MetaProgressBar):
    # inspired by: https://github.com/pollev/python_progress_bar/blob/master/python_progress_bar/progress_bar.py
    def __init__(self, rate_bar: bool = True):
        self.progress_clocked = False
        self.current_nr_lines = 0
        self.start_time = 0
        self.rate_bar = rate_bar

    @staticmethod
    def _get_current_nr_lines() -> int:
        stream = os.popen('tput lines')
        output = stream.read()
        return int(output)

    @staticmethod
    def _get_current_nr_cols() -> int:
        stream = os.popen('tput cols')
        output = stream.read()
        return int(output)

    @staticmethod
    def __format_interval(t: float | int) -> str:
        h_m, s = divmod(int(t), 60)
        h, m = divmod(h_m, 60)
        if h:
            return f"{h:d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"

    def __prepare_r_bar(self, n: int) -> str:
        elapsed = time() - self.start_time
        elapsed_str = self.__format_interval(elapsed)

        # Percentage/second rate (or second/percentage if slow)
        rate = n / elapsed
        inv_rate = 1 / rate if rate else None
        rate_noinv_fmt = f"{f'{rate:5.2f}' if rate else '?'}pct/s"
        rate_inv_fmt = f"{f'{inv_rate:5.2f}' if inv_rate else '?'}s/pct"
        rate_fmt = rate_inv_fmt if inv_rate and inv_rate > 1 else rate_noinv_fmt

        # Remaining time
        remaining = (100 - n) / rate if rate else 0
        remaining_str = self.__format_interval(remaining) if rate else "?"

        r_bar = f"[{elapsed_str}<{remaining_str}, {rate_fmt}]"
        return r_bar

    def _print_bar_text(self, percentage: int, color: str | None):
        colorstr = '\033[30m\033[43m' if color == 'yellow' else '\033[30m\033[42m'
        cols = self._get_current_nr_cols()
        if self.rate_bar:
            r_bar = self.__prepare_r_bar(n=percentage)
            bar_size = cols - 21 - len(r_bar)
        else:
            r_bar = ""
            bar_size = cols - 20

        complete_size = round((bar_size * percentage) / 100)
        remainder_size = bar_size - complete_size
        progress_bar = f"[{colorstr}{'#' * complete_size}\033[39m\033[49m{'.' * remainder_size}]"
        percentage_str = ' 100' if percentage == 100 else f"{percentage:4.1f}"

        print(f" Progress {percentage_str}% {progress_bar} {r_bar}\r", end='')

    def _clear_progress_bar(self):
        lines = self._get_current_nr_lines()
        Cursor.save()
        Cursor.move_to(row=lines, col=0)
        Cursor.clear_line()
        Cursor.restore()

    def setup(self):
        self.start_time = time()

        self.current_nr_lines = self._get_current_nr_lines()
        lines = self.current_nr_lines - 1

        print('\n', end='')
        Cursor.save()
        Cursor.set_scroll_region(top=0, bottom=lines)
        Cursor.restore()
        Cursor.move_up()

        self.draw(0)

    def draw(self, percentage: int | None, color: str | None = None, cursor_col: int | None = None):
        if percentage is None:
            return
        lines = self._get_current_nr_lines()
        if lines != self.current_nr_lines:
            self.setup()

        Cursor.save()
        Cursor.move_to(row=lines, col=0)
        Cursor.clear_line()
        self.progress_clocked = False
        self._print_bar_text(percentage=percentage, color=color)

        Cursor.restore()

    def block(self, percentage: int | None, cursor_col: int | None = None):
        self.draw(percentage=percentage, color='yellow')

    def destroy(self):
        lines = self._get_current_nr_lines()
        Cursor.save()
        Cursor.set_scroll_region(top=0, bottom=lines)
        Cursor.restore()
        Cursor.move_up()
        self._clear_progress_bar()

        print('\n\n', end='')


class TqdmProgressBar(metaclass=MetaProgressBar):
    def __init__(self):
        from tqdm import tqdm
        self.tqdm = tqdm
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
        bar_str = self.tqdm.format_meter(
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
