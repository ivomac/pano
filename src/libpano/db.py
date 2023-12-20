"""Database of raw photos.

This module defines the RawDB class, which represents a database of raw photos.
"""

from itertools import pairwise
from pathlib import Path

import pandas as pd

from .log import LogMixin
from .panorama import create_panorama, get_panorama_name
from .photo import (
    DATE_KEY,
    GROUP_KEYS,
    NAME_KEY,
    TIMEGROUP_KEY,
    convert,
    get_metadata,
    open_darktable,
    open_photo,
)
from .queue import QueueMixin


class RawDB(QueueMixin, LogMixin):
    """A database of raw photos."""

    def __init__(self, root: str | Path = ".", time_threshold: int = 15):
        """Initialize the database.

        Args:
            root (str | Path, optional): The root directory of the database.
            time_threshold (int, optional): Time threshold in seconds.

        Raises:
            FileNotFoundError: Directory not found.

        """
        super().__init__()
        self.root: Path = Path(root).resolve()
        self.time_threshold = time_threshold
        self.logger.info(f"Initializing RawDB: {self}")

        if not self.root.is_dir():
            self.logger.error(f"Directory not found: {self.root}")
            raise FileNotFoundError(f"Directory not found: {self.root}")

        self.jpeg_path: Path = self.root / "Jpeg"
        self.jpeg_path.mkdir(exist_ok=True)
        self.logger.debug(f"JPEG directory set to: {self.jpeg_path}")

        self.pano_path: Path = self.root / "Panoramas"
        self.pano_path.mkdir(exist_ok=True)
        self.logger.debug(f"Panorama directory set to: {self.pano_path}")

        self.trash_path: Path = self.root / "Trash"
        self.trash_path.mkdir(exist_ok=True)
        self.logger.debug(f"Trash directory set to: {self.trash_path}")

        self.db_path: Path = self.root / ".db.csv"

        if self.db_path.is_file():
            self.logger.info("Database file found, loading existing data.")
            self.load()
        else:
            self.logger.info("Database file not found, scanning directory.")
            self.scan()
            self.save()

        return

    def __repr__(self):
        """Return the string representation of the object."""
        return f"RawDB(root={self.root}, time_threshold={self.time_threshold})"

    def clear(self):
        """Clear the database."""
        self.db_path.unlink(missing_ok=True)
        if hasattr(self, "data"):
            delattr(self, "data")
        self.logger.info("Database cleared.")
        return

    def save(self):
        """Save the database to a CSV file."""
        self.data.to_csv(self.db_path)
        self.logger.info(f"Database saved to {self.db_path}")
        return

    def load(self):
        """Load the database from a CSV file."""
        self.data = pd.read_csv(self.db_path, header=0, index_col=0, na_filter=False)
        self.logger.info(f"Database loaded from {self.db_path}")
        return

    def scan(self):
        """Find all lossless images in the root directory."""
        self.logger.info("Starting directory scan for raw images.")
        self.clear()

        paths = []
        for path in sorted(self.root.glob("*")):
            if path.is_file() and path.suffix.lower() in [".raw", ".nef"]:
                paths.append(path)
                self.logger.debug(f"Found raw image: {path}")

        info = []
        for path in paths:
            meta = {
                NAME_KEY: path.stem,
                "Path": str(path),
                "HasJpeg": False,
                "HasPano": False,
                "HasXmp": False,
                TIMEGROUP_KEY: -1,
                "Prev": "",
                "Next": "",
                **get_metadata(path),
            }
            info.append(meta)
            self.logger.debug(f"Metadata extracted for {path.stem}")

        self.data = (
            pd.DataFrame(info).sort_values([NAME_KEY, DATE_KEY]).set_index(NAME_KEY)
        )

        if not self.data.index.is_unique:
            self.logger.error("Duplicate file names found during scan.")
            raise ValueError("Duplicate file names found")

        """Groups of photos by metadata parameters and time threshold."""
        time_diff = self.data[DATE_KEY].diff()

        self.data[TIMEGROUP_KEY] = (time_diff > self.time_threshold).cumsum()

        groups = self.data.groupby(by=GROUP_KEYS, sort=False)

        for _, g in groups:
            if len(g) > 1:
                pano = g.index.tolist()
                for photo, nxt in pairwise(pano):
                    self.data.at[photo, "Next"] = nxt
                    self.data.at[nxt, "Prev"] = photo
                    self.logger.debug(f"Linked {photo} to {nxt}")

        self.data.loc[:, "HasJpeg"] = self.data.index.map(
            lambda x: self._jpeg_path(x).is_file()
        )

        self.data.loc[:, "HasPano"] = self.data.index.map(
            lambda x: bool(self.find_panorama(x))
        )

        self.data.loc[:, "HasXmp"] = self.data.index.map(
            lambda x: self._xmp_path(x).is_file()
        )

        self.logger.info("Directory scan completed.")
        return

    def get_photo(self, name: str) -> Path:
        """Get the path to a photo."""
        photo_path = Path(self.data.at[name, "Path"])
        self.logger.debug(f"Retrieving photo path for {name}: {photo_path}")
        return photo_path

    def _jpeg_path(self, name: str) -> Path:
        """Get the path to a jpeg photo."""
        jpeg_path = self.jpeg_path / f"{name}.jpg"
        self.logger.debug(f"JPEG path for {name}: {jpeg_path}")
        return jpeg_path

    def _xmp_path(self, name: str) -> Path:
        """Get the path to an xmp file."""
        xmp_path = Path(f"{self.get_photo(name)}.xmp")
        self.logger.debug(f"XMP path for {name}: {xmp_path}")
        return xmp_path

    def open_photo(self, name: str):
        """Open a photo given its name."""
        photo_path = self.get_photo(name)
        self.logger.info(f"Opening photo: {photo_path}")
        open_photo(photo_path)
        return

    def open_darktable(self, name: str):
        """Open a photo in darktable."""
        photo_path = self.get_photo(name)
        self.logger.info(f"Opening photo in darktable: {photo_path}")
        open_darktable(photo_path)
        self.update_has_xmp(name)
        return

    def open_jpeg(self, name: str):
        """Open a jpeg photo given its name."""
        photo_path = self._jpeg_path(name)
        self.logger.info(f"Opening jpeg: {photo_path}")
        open_photo(photo_path)
        return

    def convert_jpeg(self, name: str, **kwargs):
        """Queue a photo for conversion to jpeg."""
        photo_path = self.get_photo(name)
        jpeg_path = self._jpeg_path(name)
        self.logger.info(f"Converting {photo_path} to jpeg: {jpeg_path}")
        self.queue.append(name)
        self.mp_queue.put((convert, [photo_path, jpeg_path], kwargs))
        self.start_process()
        self.logger.info(f"Queued photo for conversion: {name}")
        return

    def get_panorama(self, name: str) -> list[Path]:
        """Get the photos that make up a panorama."""
        photos = dict()
        for direction in ["Prev", "Next"]:
            photos[direction] = []
            nxt = self.data.at[name, direction]
            while nxt:
                photos[direction].append(nxt)
                nxt = self.data.at[nxt, direction]
        photos = photos["Prev"][::-1] + [name] + photos["Next"]
        pano = [self.get_photo(photo) for photo in photos]
        self.logger.debug(f"Panorama sequence for {name}: {pano}")
        return pano

    def open_photos(self, name: str):
        """Open photos in a pano given the name of one of the photos."""
        photos = self.get_panorama(name)
        self.logger.info(f"Opening photos in sequence for {name}")
        open_photo(*photos)
        return

    def create_panorama(self, name: str, **kwargs):
        """Queue a panorama for processing."""
        photos = self.get_panorama(name)
        self.logger.info(f"Creating panorama for {name}")
        self.queue.append(name)
        self.mp_queue.put((create_panorama, photos, kwargs))
        self.start_process()
        self.logger.info(f"Queued panorama: {name}")
        return

    def find_panorama(self, name: str):
        """Find all panoramas for a given photo, if any."""
        pano = self.get_panorama(name)
        pano_name = get_panorama_name(pano)
        panos = list(self.pano_path.glob(f"{pano_name}*"))
        self.logger.debug(f"Panoramas found for {name}: {panos}")
        return panos

    def open_panoramas(self, name: str):
        """Open all panoramas for a given photo."""
        panos = self.find_panorama(name)
        self.logger.info(f"Opening panoramas for {name}")
        open_photo(*panos)
        return

    def discard_photo(self, name: str):
        """Discard a photo."""
        photo_path = self.get_photo(name)
        trash_photo_path = self.trash_path / photo_path.name
        photo_path.rename(trash_photo_path)
        self.data = self.data.drop(name)
        self.logger.info(f"Discarded photo {name}, moved to {trash_photo_path}")
        self.save()
        return

    def post_process(self):
        """Post-process the queue."""
        while self.post_queue:
            name = self.post_queue.pop(0)
            self.logger.info(f"Post-processing queue element {name}.")
            self.update_has_jpeg(name)
            self.update_has_pano(name)
            self.update_has_xmp(name)
        return

    def update_has_jpeg(self, name: str):
        """Update the HasJpeg column for a photo."""
        self.data.at[name, "HasJpeg"] = self._jpeg_path(name).is_file()
        self.logger.info(f"Updated HasJpeg for {name}: {self.data.at[name, 'HasJpeg']}")
        return

    def update_has_pano(self, name: str):
        """Update the HasPano column for a photo."""
        pano = self.get_panorama(name)
        pano_name = get_panorama_name(pano)
        panos = list(self.pano_path.glob(f"{pano_name}*"))
        if panos:
            for path in pano:
                self.data.at[path.stem, "HasPano"] = True
        self.logger.info(f"Updated HasPano for {name}: {self.data.at[name, 'HasPano']}")
        return

    def update_has_xmp(self, name: str):
        """Update the HasXmp column for a photo."""
        self.data.at[name, "HasXmp"] = self._xmp_path(name).is_file()
        self.logger.info(f"Updated HasXmp for {name}: {self.data.at[name, 'HasXmp']}")
        return
