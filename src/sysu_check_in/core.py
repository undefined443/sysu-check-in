"""Client for the SYSU face-recognition check-in service."""

import base64
import logging
import time

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

logger = logging.getLogger(__name__)

# AES-128 key shared by every request; the hex decodes to b"sh12345678901234".
_AES_KEY = bytes.fromhex("73683132333435363738393031323334")

_BASE_URL = "https://facerecog.sysu.edu.cn/sign"
_ACTIVE_SIGN_STATUS = 2

DEFAULT_IMAGE_PATH = "face.jpg"

# Maximum number of response-body characters written to debug logs.
_LOGGED_BODY_LIMIT = 500

# Campus coordinates used for position submission.
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


class CheckInRejectedError(Exception):
    """Raised when the service rejects a check-in submission."""


def _timestamp() -> int:
    """Return the current Unix timestamp in seconds."""
    return int(time.time())


def _timestamp_milliseconds() -> int:
    """Return the current Unix timestamp in milliseconds."""
    return int(time.time() * 1000)


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
        content = file.read()
    logger.debug("Read %d bytes from image %s", len(content), image_path)
    return base64.b64encode(content).decode("utf-8")


def _post(endpoint_path: str, form_data: dict[str, str]) -> requests.Response:
    """Send form data to a check-in endpoint.

    Args:
        endpoint_path: Endpoint path relative to the service base URL.
        form_data: Form data to send in the request body.

    Returns:
        The successful HTTP response.
    """
    url = f"{_BASE_URL}/{endpoint_path}"
    logger.debug("POST %s with fields %s", url, sorted(form_data))
    started = time.monotonic()
    response = requests.post(url, data=form_data, headers=_HEADERS, timeout=30)
    logger.debug(
        "POST %s returned HTTP %d in %.2fs: %s",
        url,
        response.status_code,
        time.monotonic() - started,
        response.text[:_LOGGED_BODY_LIMIT],
    )
    response.raise_for_status()
    return response


def _raise_for_rejection(response: requests.Response) -> None:
    """Raise an error when the service reports a rejected submission.

    Args:
        response: HTTP response returned by the check-in service.

    Raises:
        CheckInRejectedError: If the service response has a non-success code.
    """
    payload = response.json()
    if payload["code"] != 1:
        logger.debug("Service rejected submission: %s", payload)
        raise CheckInRejectedError(payload["msg"])


def _get_active_activity(student_id: str) -> str:
    """Fetch the ID of the currently active check-in activity.

    Args:
        student_id: Student ID used for check-in.

    Returns:
        The active check-in activity ID.
    """
    logger.info("Fetching activity list")
    plaintext = f"{student_id}##{_timestamp()}"
    logger.debug("Activity list payload: %s", plaintext)
    response = _post("getActivityList", {"sKey": _encrypt(plaintext)})
    activities = response.json()["data"]["rows"]
    logger.info("Service returned %d activities", len(activities))
    for activity in activities:
        logger.debug(
            "Activity %s: iSignStatus=%s iCollectGPS=%s isNeedFace=%s",
            activity.get("sActId"),
            activity.get("iSignStatus"),
            activity.get("iCollectGPS"),
            activity.get("isNeedFace"),
        )
        if activity["iSignStatus"] == _ACTIVE_SIGN_STATUS:
            logger.info("Selected active activity %s", activity["sActName"])
            return activity["sActId"]
    raise NoActiveActivityError("No active check-in activity is available.")


def _submit_gps(student_id: str, activity_id: str) -> str:
    """Submit the campus position for an activity.

    Args:
        student_id: Student ID used for check-in.
        activity_id: ID of the active check-in activity.

    Returns:
        The raw response returned by the check-in service.
    """
    plaintext = (
        f"{student_id}##{activity_id}####{_CAMPUS_LONGITUDE}##"
        f"{_CAMPUS_LATITUDE}##{_timestamp_milliseconds()}"
    )
    logger.info("Submitting position for activity %s", activity_id)
    logger.debug("Position payload: %s", plaintext)
    response = _post("submitPosition", {"sKey": _encrypt(plaintext)})
    _raise_for_rejection(response)
    return response.text


def _submit_face(student_id: str, activity_id: str, image_path: str) -> str:
    """Submit a face image to complete the check-in.

    Args:
        student_id: Student ID used for check-in.
        activity_id: ID of the active check-in activity.
        image_path: Path to the JPEG face image.

    Returns:
        The raw response returned by the check-in service.
    """
    logger.info("Submitting face image %s for activity %s", image_path, activity_id)
    face_image_base64 = _read_image_base64(image_path)
    plaintext = f"{student_id}##{activity_id}##{_timestamp()}"
    logger.debug("Face payload: %s", plaintext)
    form_data = {
        "sKey": _encrypt(plaintext),
        "sImage": f"data:image/jpeg;base64,{face_image_base64}",
    }
    response = _post("submitSignFace", form_data)
    _raise_for_rejection(response)
    return response.text


def check_in(student_id: str, image_path: str = DEFAULT_IMAGE_PATH) -> str:
    """Perform all required check-in submissions for a student ID.

    Args:
        student_id: Student ID used for check-in.
        image_path: Path to the JPEG face image.

    Returns:
        The raw response returned by the check-in service.
    """
    activity_id = _get_active_activity(student_id)
    # Optional: enable this to also submit the hardcoded campus position.
    # _submit_gps(student_id, activity_id)
    # The face submission completes the check-in, even when isNeedFace is 0.
    response = _submit_face(student_id, activity_id, image_path)
    logger.info("Check-in completed for activity %s", activity_id)
    return response
