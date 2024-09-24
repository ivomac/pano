"""Queue subprocesses."""

import multiprocessing as mp
from queue import Empty

from .log import get_logger
from .panorama import create_panorama, get_panorama_name
from .photo import convert

logger = get_logger(__name__)

MANAGER = mp.Manager()

QUEUE = MANAGER.list()
MP_QUEUE = mp.Queue()
PROC = None


def start_process():
    """Start the process."""
    global PROC
    if PROC is None or not PROC.is_alive():
        logger.info("Starting Process")
        PROC = mp.Process(target=process_queue)
        PROC.start()
    return


def process_queue():
    """Process the queue."""
    global MP_QUEUE, QUEUE
    logger.info(f"Starting queue processing with inputs {QUEUE}")
    try:
        while True:
            fn, args, kwargs = MP_QUEUE.get(timeout=1)
            logger.info(
                f"Processing function {fn.__name__} with args: {args}, kwargs: {kwargs}"
            )
            fn(*args, **kwargs)
            QUEUE.pop(0)
            logger.info(f"Completed processing. Remaining queue: {QUEUE}")
    except Empty:
        logger.info("Queue is empty. Exiting.")
    except Exception as e:
        logger.error(f"Error processing queue: {e}")
        raise
    return


def queue_panorama(*args, **kwargs):
    """Queue a panorama for processing."""
    pano_name = get_panorama_name(args[0])
    QUEUE.append(pano_name)
    MP_QUEUE.put((create_panorama, args, kwargs))
    start_process()
    logger.info(f"Queued panorama: {pano_name}")
    return


def queue_conversion(*args, **kwargs):
    """Queue a photo for conversion."""
    photo_name = args[0].stem
    QUEUE.append(photo_name)
    MP_QUEUE.put((convert, args, kwargs))
    start_process()
    logger.info(f"Queued photo for conversion: {photo_name}")
    return
