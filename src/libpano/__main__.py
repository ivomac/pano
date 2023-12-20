"""The main file to run the PanoApp."""

from argparse import ArgumentParser

from . import TUI, RawDB, get_logger


def main():
    """Run the PanoApp."""
    args = parse_args()

    set_log_level(args)

    db = RawDB(root=args.db, time_threshold=args.time_threshold)
    tui = TUI(db)
    tui.start()
    return


def parse_args():
    """Parse the command line arguments."""
    parser = ArgumentParser()
    parser.add_argument(
        "db", help="Path to the database", type=str, nargs="?", default="."
    )
    parser.add_argument(
        "-t", "--time-threshold", help="Time threshold", type=int, default=15
    )
    parser.add_argument("-d", "--debug", help="Debug mode", action="store_true")

    return parser.parse_args()


def set_log_level(args):
    """Set the log level based on the command line arguments."""
    if args.debug:
        logger = get_logger(__name__)
        logger.setLevel("DEBUG")
        logger.debug("Logger set to DEBUG")


if __name__ == "__main__":
    main()
