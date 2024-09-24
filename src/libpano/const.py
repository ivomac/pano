"""Constants."""

from os import environ
from pathlib import Path

LOG_FOLDER = Path(environ["XDG_DATA_HOME"]) / "pano"

LOG_FOLDER.mkdir(parents=True, exist_ok=True)

DT_STYLE_FOLDER = Path(environ["XDG_CONFIG_HOME"]) / "darktable" / "styles"

DT_STYLES = [f.stem for f in DT_STYLE_FOLDER.glob("*.dtstyle")]

IMAGE_VIEWER = "gwenview"

AVAIL_PROJECTIONS = [
    "rectilinear",
    "circular",
    "equirectangular",
    "fisheye_ff",
    "stereographic",
    "mercator",
    "trans_mercator",
    "sinusoidal",
    "lambert_equal_area_conic",
    "lambert_azimuthal",
    "albers_equal_area_conic",
    "miller_cylindrical",
    "panini",
    "architectural",
    "orthographic",
    "equisolid",
    "equi_panini",
    "biplane",
    "triplane",
    "panini_general",
    "thoby",
    "hammer",
]

PANORAMA_FOLDER = Path("./Panoramas")

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
