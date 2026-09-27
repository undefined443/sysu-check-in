"""Client for the SYSU face-recognition check-in service."""

import base64
import time

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# AES-128 key shared by every request; the hex decodes to b"sh12345678901234".
_AES_KEY = bytes.fromhex("73683132333435363738393031323334")

_BASE_URL = "https://facerecog.sysu.edu.cn/sign"

DEFAULT_IMAGE_PATH = "face.jpg"

# Campus coordinates used by the optional position submission.
_CAMPUS_LONGITUDE = "113.9539"
_CAMPUS_LATITUDE = "22.801604"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; FLC-AN00 Build/HONORFLC-AN00; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
        "Chrome/138.0.7204.180 Mobile Safari/537.36 XWEB/1380347 "
        "MMWEBSDK/20250202 MMWEBID/6351 wxwork/5.0.6.66174 "
        "MicroMessenger/8.0.28.48(0x28001c30) MiniProgramEnv/android "
        "Luggage/3.0.2.95ef3f83 NetType/WIFI Language/en ABI/arm64"
    ),
    "Accept-Encoding": "gzip,compress,br,deflate",
    "charset": "utf-8",
}


class NoActiveActivityError(Exception):
    """Raised when the service has no active check-in activity."""


def _timestamp() -> int:
    """Return the current Unix timestamp in seconds."""
    return int(time.time())


def _encrypt(plaintext: str) -> str:
    """Encrypt a payload with AES-128-ECB.

    Args:
        plaintext: Plain-text payload to encrypt.

    Returns:
        The encrypted payload encoded as a hexadecimal string.
    """
    cipher = AES.new(_AES_KEY, AES.MODE_ECB)
    return cipher.encrypt(pad(plaintext.encode(), AES.block_size)).hex()


def _read_image_base64(image_path: str) -> str:
    """Read an image file and encode its content as Base64.

    Args:
        image_path: Path to the image file.

    Returns:
        The Base64-encoded image content.
    """
    with open(image_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def _post(endpoint_path: str, form_data: dict[str, str]) -> requests.Response:
    """Send form data to a check-in endpoint.

    Args:
        endpoint_path: Endpoint path relative to the service base URL.
        form_data: Form data to send in the request body.

    Returns:
        The successful HTTP response.
    """
    response = requests.post(
        f"{_BASE_URL}/{endpoint_path}",
        data=form_data,
        headers=_HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    return response


def _get_activity_id(student_id: str) -> str:
    """Fetch the ID of the currently active check-in activity.

    Args:
        student_id: Student ID used for check-in.

    Returns:
        The active check-in activity ID.
    """
    response = _post(
        "getActivityList", {"sKey": _encrypt(f"{student_id}##{_timestamp()}")}
    )
    activities = response.json()["data"]["rows"]
    if not activities:
        raise NoActiveActivityError("No active check-in activity is available.")
    return activities[0]["sActId"]


def _submit_gps(student_id: str, activity_id: str) -> str:
    """Submit the optional campus position for an activity.

    Args:
        student_id: Student ID used for check-in.
        activity_id: ID of the active check-in activity.

    Returns:
        The raw response returned by the check-in service.
    """
    plaintext = (
        f"{student_id}##{activity_id}####{_CAMPUS_LONGITUDE}##"
        f"{_CAMPUS_LATITUDE}##{_timestamp()}"
    )
    return _post("submitPosition", {"sKey": _encrypt(plaintext)}).text


def _submit_face(student_id: str, activity_id: str, image_path: str) -> str:
    """Submit a face image to complete the check-in.

    Args:
        student_id: Student ID used for check-in.
        activity_id: ID of the active check-in activity.
        image_path: Path to the JPEG face image.

    Returns:
        The raw response returned by the check-in service.
    """
    face_image_base64 = _read_image_base64(image_path)
    form_data = {
        "sKey": _encrypt(f"{student_id}##{activity_id}##{_timestamp()}"),
        "sImage": f"data:image/jpeg;base64,{face_image_base64}",
    }
    return _post("submitSignFace", form_data).text


def check_in(student_id: str, image_path: str = DEFAULT_IMAGE_PATH) -> str:
    """Perform face check-in for a student ID.

    Args:
        student_id: Student ID used for check-in.
        image_path: Path to the JPEG face image.

    Returns:
        The raw response returned by the check-in service.
    """
    activity_id = _get_activity_id(student_id)
    # Optional: enable this for a full position-and-face check-in flow.
    # _submit_gps(student_id, activity_id)
    return _submit_face(student_id, activity_id, image_path)
