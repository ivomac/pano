"""Queue Mixin for handling subprocesses."""

import multiprocessing as mp
from queue import Empty

from .log import LogMixin


class QueueMixin(LogMixin):
    """Mixin class to handle queuing of tasks."""

    def __init__(self):
        """Initialize the QueueMixin."""
        super().__init__()
        self.manager = mp.Manager()
        self.queue = self.manager.list()
        self.post_queue = self.manager.list()
        self.mp_queue = mp.Queue()
        self.proc = None

    def start_process(self):
        """Start the process."""
        if self.proc is None or not self.proc.is_alive():
            self.logger.info("Starting Process")
            self.proc = mp.Process(target=self.process_queue)
            self.proc.start()

    def process_queue(self):
        """Process the queue."""
        self.logger.info(f"Starting queue processing with inputs {self.queue}")
        try:
            while True:
                fn, args, kwargs = self.mp_queue.get(timeout=1)
                self.logger.info(
                    f"Processing function {fn.__name__} with args: {args},"
                    + f" kwargs: {kwargs}"
                )
                fn(*args, **kwargs)
                self.post_queue.append(self.queue.pop(0))
                self.logger.info(f"Completed processing. Remaining queue: {self.queue}")
        except Empty:
            self.logger.info("Queue is empty. Exiting.")
        except Exception as e:
            self.logger.error(f"Error processing queue: {e}")
            raise
