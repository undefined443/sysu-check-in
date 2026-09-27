"""Command-line interface for sysu_check_in."""

import argparse
from importlib.metadata import version

import requests

from sysu_check_in import core


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
    return parser.parse_args()


def main() -> None:
    """Run the command-line interface."""
    args = _parse_args()
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
        raise SystemExit(f"Check-in failed: {error}") from error
