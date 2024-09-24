"""A module to hold the Panorama class.

This module defines the Panorama class,
which represents a group of photos that can be stitched together.

"""

from pathlib import Path
from tempfile import TemporaryDirectory

from .const import AVAIL_PROJECTIONS
from .exec import run
from .log import get_logger
from .photo import convert

logger = get_logger(__name__)


def create_panorama(
    photos: list[Path],
    out_path: Path,
    adjust: bool = False,
    style: str | None = None,
    projections: list[str | int] | None = None,
    from_format: str = ".tif",
    prefix: str = "",
):
    """Stitch the photos together."""
    name: str = get_panorama_name(photos)
    logger.info(f"Starting panorama creation: {name}")

    adj_str = "a" if adjust else "n"

    prefix += f"{name}-{style}-{adj_str}"

    with TemporaryDirectory(prefix="pano_") as tmp:
        tmp_path = Path(tmp)
        from_paths = []
        for photo in photos:
            target_path = tmp_path / photo.with_suffix(from_format).name
            convert(photo, target_path, style, overwrite=True)
            from_paths.append(target_path)
            logger.debug(f"Converted photo {photo} to {from_format} at {target_path}")

        pf = str(tmp_path / f"{prefix}.pto")

        logger.info("Running pto_gen")
        run(["pto_gen", *from_paths, "-o", pf])
        logger.info("Running cpfind")
        run(["cpfind", "--celeste", "-o", pf, pf])
        logger.info("Running cpclean")
        run(["cpclean", "-o", pf, pf])
        logger.info("Running linefind")
        run(["linefind", "--lines", "3", "-o", pf, pf])
        logger.info("Running autooptimiser")
        run(["autooptimiser", "-q", "-a", "-l", "-m", "-s", "-o", pf, pf])

        if projections is None:
            projs = [0]
        else:
            projs = [_get_index(proj) for proj in projections]

        for proj in projs:
            proj_name = AVAIL_PROJECTIONS[proj]

            logger.info(f"Running pano_modify with projection: {proj_name}")
            run(
                [
                    "pano_modify",
                    "--projection",
                    str(proj),
                    "--fov",
                    "AUTO",
                    "--canvas",
                    "AUTO",
                    "--straighten",
                    "--center",
                    "--crop",
                    "0,100,0,100%",
                    "--output-type",
                    "NORMAL",
                    "-o",
                    pf,
                    pf,
                ]
            )

            if adjust:
                logger.info("Running hugin for manual adjustments")
                run(["hugin", pf])

            logger.info("Running nona")
            run(
                [
                    "nona",
                    "-g",
                    "-z",
                    "LZW",
                    "-o",
                    str(tmp_path / prefix),
                    "--bigtiff",
                    "-m",
                    "TIFF_m",
                    pf,
                ]
            )

            nona_output = [str(path) for path in tmp_path.glob(f"{prefix}*.tif")]

            out_file = out_path / f"{prefix}-{proj_name}.tif"

            logger.info("Running enblend")
            run(
                [
                    "enblend",
                    "-o",
                    str(out_file),
                    *nona_output,
                ]
            )

            if not out_file.is_file():
                logger.error(f"Panorama not created: {out_file}")
                raise FileNotFoundError(f"Panorama not created: {out_file}")
            logger.info(f"Panorama created: {out_file}")

    logger.info(f"Panorama creation complete: {name}")
    return


def get_panorama_name(photos: list[Path]) -> str:
    """Get the name of a panorama given its photos."""
    photos.sort(key=lambda x: x.stem)
    name = f"{photos[0].stem}-{photos[-1].stem}"
    logger.debug(f"Retrieved panorama name: {name}")
    return name


def _get_index(proj) -> int:
    index = AVAIL_PROJECTIONS.index(proj) if isinstance(proj, str) else proj
    logger.debug(f"Retrieved projection index: {index}")
    return index
