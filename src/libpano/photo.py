"""Photo class for handling photo metadata and conversion."""

import subprocess as sp
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, field_validator

from .const import DT_STYLES, IMAGE_VIEWER
from .exec import run
from .log import get_logger

logger = get_logger(__name__)

TIMEGROUP_KEY = "TimeGroup"
NAME_KEY = "FileName"
DATE_KEY = "DateTimeOriginal"


def open_photo(*path: Path | str):
    """View a photo."""
    paths = [k for p in path if (k := Path(p)).is_file()]
    if paths:
        logger.info(f"Opening photo(s): {paths}")
        run([IMAGE_VIEWER, *[str(p) for p in paths]], allow_error=True)
    else:
        logger.error(f"Photo(s) not found: {path}")
    return


def open_darktable(path: Path):
    """Edit a photo in Darktable."""
    logger.info(f"Opening photo in Darktable: {path}")
    run(["darktable", str(path)], allow_error=True)
    return


def convert(
    path: Path,
    target_path: Path,
    dt_style: str | None = None,
    overwrite: bool = False,
):
    """Convert the photo to another format using Darktable."""
    if not overwrite and target_path.is_file():
        logger.info(f"Conversion skipped, target exists: {target_path}")
        return

    if dt_style is None:
        args = []
    else:
        if dt_style not in DT_STYLES:
            logger.error(f"Invalid Darktable style: {dt_style}")
            raise ValueError(f"Darktable style not found: {dt_style}")
        args = ["--style-overwrite", "--style", dt_style]

    logger.info(f"Converting photo {path} to {target_path} with style {dt_style}")
    run(
        [
            "darktable-cli",
            str(path),
            str(target_path),
            *args,
        ]
    )
    if not target_path.is_file():
        logger.error(f"Conversion failed: {target_path}")
        raise RuntimeError(f"Conversion failed: {target_path}")
    logger.info(f"Conversion successful: {target_path}")

    return


class RawMeta(BaseModel):
    """Raw photo metadata."""

    Contrast: int
    DateTimeOriginal: int
    ExposureBiasValue: str
    ExposureMode: int
    ExposureProgram: int
    ExposureTime: str
    FNumber: str
    Flash: int
    FocalLength: str
    GainControl: int
    ISOSpeedRatings: int
    LightSource: int
    MaxApertureValue: str
    MeteringMode: int
    RecommendedExposureIndex: int
    Saturation: int
    SceneCaptureType: int
    SensingMethod: int
    SensitivityType: int
    Sharpness: int
    WhiteBalance: int

    @field_validator("DateTimeOriginal", mode="before")
    @classmethod
    def _convert_datetime_to_int(cls, v):
        return int(datetime.strptime(v, "%Y:%m:%d %H:%M:%S").timestamp())

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        extra = "ignore"


def get_metadata(path: Path):
    """Get the metadata of the photo as a Series."""
    logger.info(f"Getting metadata for {path}")
    exiv_output = (
        sp.check_output(
            ["exiv2", "-g", "Exif.Photo", "-Pkv", str(path)],
            text=True,
        )
        .rstrip("\n")
        .split("\n")
    )

    def parse_line(line):
        key, value = line.split(maxsplit=1)
        key = key.split(".")[-1]
        return key, value

    data = {key: value for key, value in (parse_line(line) for line in exiv_output)}

    logger.debug(f"Parsed metadata for {path}: {data}")
    return RawMeta(**data).model_dump()  # type: ignore


GROUP_KEYS = list(RawMeta.model_fields.keys()) + [TIMEGROUP_KEY]
GROUP_KEYS.remove(DATE_KEY)
