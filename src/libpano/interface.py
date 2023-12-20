"""Interface for the database."""

import curses

from .db import RawDB
from .log import LogMixin

ACCEPT_KEYS = ["Y", "y"]
REJECT_KEYS = ["N", "n", "\n", "\r", "\x1b"]  # \x1b is the escape key


class TUI(LogMixin):
    """Text User Interface for the database."""

    def __init__(self, db: RawDB):
        """Initialize the TUI."""
        super().__init__()
        self.db = db
        self.selected_index = 0
        self.first_displayed_index = 0
        return

    def start(self):
        """Start the TUI."""
        curses.wrapper(self.main)
        return

    def main(self, stdscr: curses.window):
        """Start the main loop for the TUI."""
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        stdscr.nodelay(True)
        stdscr.timeout(500)

        while True:
            self.db.post_process()

            stdscr.clear()
            self.display(stdscr)

            key = get_char(stdscr)

            if key == "q":
                break

            if key == "k":
                self.selected_index = max(0, self.selected_index - 1)
            elif key == "j":
                self.selected_index = min(
                    len(self.db.data.index) - 1, self.selected_index + 1
                )
            elif key == "<":
                self.selected_index = 0
            elif key == ">":
                self.selected_index = len(self.db.data.index) - 1
            elif key == "\x04":  # Ctrl-D
                scr_height, _ = stdscr.getmaxyx()
                self.selected_index = min(
                    len(self.db.data.index) - 1,
                    self.selected_index + scr_height // 2,
                )
            elif key == "\x15":  # Ctrl-U
                scr_height, _ = stdscr.getmaxyx()
                self.selected_index = max(0, self.selected_index - scr_height // 2)
            elif key == "o":
                self.open(stdscr)
            elif key == "c":
                self.convert(stdscr)
            elif key == "x":
                self.discard(stdscr)
            elif key == " ":
                self.toggle(self.selected_index)
            elif key == "s":
                self.save(stdscr)
            elif key == "r":
                self.reset(stdscr)
            elif key:
                self.logger.debug(f"Key: {key} not bound")

            stdscr.refresh()
        return

    def display(self, stdscr):
        """Display the database items."""
        scr_height, width = stdscr.getmaxyx()
        list_height = scr_height - 1
        if self.selected_index < self.first_displayed_index:
            self.first_displayed_index = max(0, self.selected_index - list_height // 3)
        elif self.selected_index >= self.first_displayed_index + list_height - 1:
            self.first_displayed_index = min(
                len(self.db.data.index) - list_height,
                self.selected_index - list_height + 1 + list_height // 3,
            )

        for idx, item in enumerate(
            self.db.data.index[self.first_displayed_index :],
            start=self.first_displayed_index,
        ):
            if idx - self.first_displayed_index >= list_height:
                break

            jpeg_flag = "J" if self.db.data.at[item, "HasJpeg"] else " "
            pano_flag = "P" if self.db.data.at[item, "HasPano"] else " "
            xmp_flag = "X" if self.db.data.at[item, "HasXmp"] else " "

            color = curses.color_pair(0)
            if self.db.data.at[item, "Next"]:
                color = curses.color_pair(1)
            elif self.db.data.at[item, "Prev"]:
                color = curses.color_pair(2)

            if idx == self.selected_index:
                stdscr.addstr(
                    idx - self.first_displayed_index,
                    0,
                    f"{jpeg_flag}{pano_flag}{xmp_flag}>{item}",
                    curses.A_REVERSE | color,
                )
            else:
                stdscr.addstr(
                    idx - self.first_displayed_index,
                    0,
                    f"{jpeg_flag}{pano_flag}{xmp_flag} {item}",
                    color,
                )

        queue = ""
        if self.db.queue:
            queue = f"Queue: {'  '.join(self.db.queue)}"

        stdscr.addstr(
            scr_height - 1,
            0,
            f"o:open  c:convert  s:save  r:reset  {queue}".ljust(width - 1)[
                : width - 1
            ],
            curses.A_BOLD,
        )

        return

    @property
    def selected(self) -> str:
        """Return the selected item."""
        return str(self.db.data.index[self.selected_index])

    def link(self, n: int):
        """Link the nth item to the next item."""
        if n < len(self.db.data.index) - 1:
            this = self.db.data.index[n]
            nxt = self.db.data.index[n + 1]

            self.db.data.at[this, "Next"] = nxt
            self.db.data.at[nxt, "Prev"] = this

            self.logger.info(f"Linked {this} to {nxt}")
        return

    def unlink(self, n: int):
        """Unlink the nth item with the next item."""
        this = self.db.data.index[n]
        nxt = self.db.data.at[this, "Next"]

        if nxt:
            self.db.data.at[nxt, "Prev"] = ""

        self.db.data.at[this, "Next"] = ""

        self.logger.info(f"Unlinked {this}")
        return

    def toggle(self, n: int):
        """Toggle the nth item link to the next item."""
        if n < len(self.db.data.index):
            this = self.db.data.index[n]
            if self.db.data.at[this, "Next"]:
                self.unlink(n)
            else:
                self.link(n)
        return

    def discard(self, stdscr):
        """Prompt the user to confirm discarding the selected photo."""
        update_footer(stdscr, "Discard photo? y/N: ")
        while True:
            key = get_char(stdscr)
            if key in ACCEPT_KEYS:
                self.logger.info(f"Discarding photo {self.selected}")
                self.db.discard_photo(self.selected)
                self.selected_index = max(0, self.selected_index - 1)
                break
            if key:
                break
        return

    def reset(self, stdscr):
        """Prompt the user to confirm clearing the database."""
        update_footer(stdscr, "Reset DB? y/N: ")
        while True:
            key = get_char(stdscr)
            if key in ACCEPT_KEYS:
                self.logger.info("Resetting the database")
                self.db.scan()
                break
            if key:
                break
        return

    def save(self, stdscr):
        """Prompt the user to confirm saving the database."""
        update_footer(stdscr, "Save? y/N: ")
        while True:
            key = get_char(stdscr)
            if key in ACCEPT_KEYS:
                self.logger.info("Saving the database")
                self.db.save()
                break
            if key:
                break
        return

    def open(self, stdscr):
        """Prompt the user to choose what to open."""
        update_footer(stdscr, "Open: r:raw s:sequence j:jpeg p:pano d:dt")
        while True:
            key = get_char(stdscr)
            if key == "r":
                self.logger.info(f"Opening raw {self.selected}")
                self.db.open_photo(self.selected)
                break
            if key == "s":
                self.logger.info(f"Opening sequence of {self.selected}")
                self.db.open_photos(self.selected)
                break
            if key == "j":
                self.logger.info(f"Opening jpeg {self.selected}")
                self.db.open_jpeg(self.selected)
                break
            if key == "p":
                self.logger.info(f"Opening panoramas for {self.selected}")
                self.db.open_panoramas(self.selected)
                break
            if key == "d":
                self.logger.info(f"Opening {self.selected} in darktable")
                self.db.open_darktable(self.selected)
                break
            if key:
                break
        return

    def convert(self, stdscr):
        """Prompt the user to choose what to convert."""
        update_footer(stdscr, "Convert: j:jpeg p:pano")
        while True:
            key = get_char(stdscr)
            if key == "j":
                self.logger.info(f"Converting {self.selected} to jpeg")
                self.db.convert_jpeg(self.selected)
                break
            if key == "p":
                self.logger.info(f"Creating panorama for {self.selected}")
                self.db.create_panorama(self.selected)
                break
            if key:
                break
        return


def update_footer(stdscr, message):
    """Update the footer with a given message."""
    height, width = stdscr.getmaxyx()
    stdscr.addstr(height - 1, 0, message.ljust(width - 1)[: width - 1], curses.A_BOLD)
    stdscr.refresh()


def get_char(stdscr: curses.window) -> str:
    """Get a character from the user."""
    return chr(k) if (k := stdscr.getch()) >= 0 else ""
