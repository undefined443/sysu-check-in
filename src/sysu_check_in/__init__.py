"""SYSU face-recognition check-in package."""

from sysu_check_in.core import (
    DEFAULT_IMAGE_PATH,
    CheckInRejectedError,
    NoActiveActivityError,
    check_in,
)

__all__ = [
    "DEFAULT_IMAGE_PATH",
    "CheckInRejectedError",
    "NoActiveActivityError",
    "check_in",
]
