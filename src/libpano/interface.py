"""A Textual TUI for managing items linked in sequences."""

from textual.app import App, ComposeResult
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from .const import SPINNER
from .db import RawDB
from .log import get_logger
from .queue import QUEUE

logger = get_logger(__name__)


class PanoApp(App):
    """A Textual TUI for managing items linked in sequences."""

    CSS = """
    #header {
        color: white;
    }
    #footer {
        color: white;
    }
    #data_table {
        height: 1fr;
    }
    """

    def __init__(self, db: RawDB):
        """Initialize the PanoApp."""
        super().__init__()
        self.db = db
        self.table = DataTable(id="data_table")
        self.header = Static("", id="header")
        self.footer = Static(
            "q:quit x:clear c:save ␣:toggle r:raw s:seq"
            + " g:jpg t:to_jpg p:pano u:to_pano (^p)",
            id="footer",
        )

        self.spinner_index = 0
        logger.info("PanoApp initialized")
        return

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield self.header
        yield self.table
        yield self.footer

    def update_spinner(self) -> None:
        """Update the spinner in the header."""
        if QUEUE:
            self.spinner_index = (self.spinner_index + 1) % len(SPINNER)
            que_str = " ".join(QUEUE)
            self.header.update(f"{SPINNER[self.spinner_index]} {que_str}")
        else:
            self.header.update("")
        return

    async def on_mount(self):
        """Mount the application."""
        await self.initialize_table()
        self.set_interval(0.2, self.update_spinner)
        return

    async def initialize_table(self):
        """Initialize the data table with items and their links."""
        logger.info("Initializing data table")
        self.table.clear()
        self.table.cursor_type = "row"
        self.table.show_row_labels = True
        for col in ["Initial Link", "Current Link"]:
            self.table.add_column(col, key=col)
        for stem, row in self.db.data.iterrows():
            stem = str(stem)
            self.table.add_row(row["Next"], row["Next"], key=stem, label=stem)
        logger.info("Data table initialized")
        return

    def link(self, n: int):
        """Link the nth item to the next item."""
        if not self.table.is_valid_row_index(n + 1):
            logger.warning(f"Invalid row index: {n + 1}")
            return

        this, nxt = self.db.data.index[n : n + 2]

        self.db.data.at[this, "Next"] = nxt
        self.db.data.at[nxt, "Prev"] = this

        cell = Coordinate(n, 1)
        self.table.update_cell_at(cell, nxt)
        logger.info(f"Linked {this} to {nxt}")

    def unlink(self, n: int):
        """Unlink the nth item."""
        this = self.db.data.index[n]

        self.db.data.at[this, "Next"] = ""
        self.db.data.at[this, "Prev"] = ""

        cell = Coordinate(n, 1)
        self.table.update_cell_at(cell, "")
        logger.info(f"Unlinked {this}")

    @property
    def row_key(self) -> str:
        """Get the key of the selected item."""
        row_key, _ = self.table.coordinate_to_cell_key(self.table.cursor_coordinate)
        if row_key.value is None:
            logger.error("No item selected")
            raise ValueError("No item selected")
        return row_key.value

    def key_j(self):
        """Move the cursor down."""
        self.table.action_cursor_down()
        return

    def key_k(self):
        """Move the cursor up."""
        self.table.action_cursor_up()
        return

    def key_q(self):
        """Quit the application."""
        self.exit()
        return

    def key_space(self):
        """Toggle the selected item's link."""
        n = self.table.cursor_row
        this = self.db.data.index[n]
        if self.db.data.at[this, "Next"]:
            self.unlink(n)
        else:
            self.link(n)
        return

    def key_x(self):
        """Clear the database."""
        logger.info("Clearing the database")
        self.db.scan()
        return

    def key_c(self):
        """Open the sequence starting from the selected item."""
        logger.info("Saving the database")
        self.db.save()
        return

    def key_r(self):
        """Open the selected item."""
        logger.info(f"Opening raw {self.row_key}")
        self.db.open_photo(self.row_key)
        return

    def key_s(self):
        """Open the sequence starting from the selected item."""
        logger.info(f"Opening raw sequence of {self.row_key}")
        self.db.open_photos(self.row_key)
        return

    def key_g(self):
        """Open the jpeg version of the selected item."""
        logger.info(f"Opening jpeg {self.row_key}")
        self.db.open_jpeg(self.row_key)
        return

    def key_t(self):
        """Convert the selected item to jpeg."""
        logger.info(f"Converting {self.row_key} to jpeg")
        self.db.convert_jpeg(self.row_key)
        return

    def key_p(self):
        """Open the panoramas for the selected item."""
        logger.info(f"Opening panoramas for {self.row_key}")
        self.db.open_panoramas(self.row_key)
        return

    def key_u(self):
        """Create a panorama from the selected item."""
        logger.info(f"Creating panorama for {self.row_key}")
        self.db.create_panorama(self.row_key)

    def key_o(self):
        """Open the photo in darktable."""
        logger.info(f"Opening {self.row_key} in darktable")
        self.db.open_darktable(self.row_key)
        return
