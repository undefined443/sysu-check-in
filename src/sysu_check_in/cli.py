"""Command-line interface for sysu_check_in."""

import argparse
import logging
from importlib.metadata import version

import requests

from sysu_check_in import core

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="sysu-check-in",
        description="Submit a face image to the SYSU check-in service.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('sysu-check-in')}",
    )
    parser.add_argument("student_id", help="Student ID used for check-in.")
    parser.add_argument(
        "--image",
        default=core.DEFAULT_IMAGE_PATH,
        metavar="PATH",
        help=f"Path to the JPEG face image (default: {core.DEFAULT_IMAGE_PATH}).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Log progress to stderr; repeat (-vv) for debug details.",
    )
    return parser.parse_args()


def _configure_logging(verbosity: int) -> None:
    """Configure logging to stderr based on the requested verbosity.

    Args:
        verbosity: Number of times the verbose flag was supplied.
    """
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> None:
    """Run the command-line interface."""
    args = _parse_args()
    _configure_logging(args.verbose)
    try:
        print(core.check_in(args.student_id, args.image))
    except (
        FileNotFoundError,
        core.CheckInRejectedError,
        core.NoActiveActivityError,
        requests.RequestException,
        ValueError,
        KeyError,
    ) as error:
        logger.debug("Check-in failed", exc_info=True)
        raise SystemExit(f"Check-in failed: {error}") from error
