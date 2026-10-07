"""Tests for core check-in operations."""

from unittest.mock import Mock

import pytest

from sysu_check_in import core


def test_get_active_activity_returns_first_active_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the ID of the first activity that is open for check-in."""
    response = Mock()
    response.json.return_value = {
        "data": {
            "rows": [
                {"iSignStatus": 3, "sActId": "signed-activity", "sActName": "Signed"},
                {"iSignStatus": 2, "sActId": "activity-1", "sActName": "Holiday"},
            ]
        }
    }
    monkeypatch.setattr(core, "_post", lambda *_: response)

    assert core._get_active_activity("student-1") == "activity-1"


def test_get_active_activity_raises_when_no_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise a domain error when the service returns no activities."""
    response = Mock()
    response.json.return_value = {"data": {"rows": []}}
    monkeypatch.setattr(core, "_post", lambda *_: response)

    with pytest.raises(core.NoActiveActivityError, match="No active check-in activity"):
        core._get_active_activity("student-1")


@pytest.mark.parametrize(
    ("sign_status", "sign_status_text", "is_signed"),
    [(3, "已报到", True), (2, "去报到", False)],
)
def test_verify_signed_checks_activity_status(
    monkeypatch: pytest.MonkeyPatch,
    sign_status: int,
    sign_status_text: str,
    is_signed: bool,
) -> None:
    """Accept a signed activity and reject one that is still open."""
    response = Mock()
    response.json.return_value = {
        "data": {
            "rows": [
                {"iSignStatus": 2, "sActId": "other-activity", "sSignStatus": "去报到"},
                {
                    "iSignStatus": sign_status,
                    "sActId": "activity-1",
                    "sSignStatus": sign_status_text,
                },
            ]
        }
    }
    monkeypatch.setattr(core, "_post", lambda *_: response)

    if is_signed:
        core._verify_signed("student-1", "activity-1")
    else:
        with pytest.raises(core.CheckInRejectedError, match="status is 去报到"):
            core._verify_signed("student-1", "activity-1")


def test_check_in_submits_face_and_verifies_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Submit only the face image, then confirm the check-in was recorded."""
    monkeypatch.setattr(core, "_get_active_activity", lambda _: "activity-1")
    submit_gps = Mock()
    monkeypatch.setattr(core, "_submit_gps", submit_gps)
    submit_face = Mock(return_value="submitted")
    monkeypatch.setattr(core, "_submit_face", submit_face)
    verify_signed = Mock()
    monkeypatch.setattr(core, "_verify_signed", verify_signed)

    assert core.check_in("student-1", "face.jpg") == "submitted"
    submit_face.assert_called_once_with("student-1", "activity-1", "face.jpg")
    submit_gps.assert_not_called()
    verify_signed.assert_called_once_with("student-1", "activity-1")


def test_submit_face_encodes_image_and_builds_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Encode the image and submit it with the activity metadata."""
    monkeypatch.setattr(core, "_read_image_base64", lambda _: "encoded-image")
    monkeypatch.setattr(core, "_timestamp", lambda: 123)
    monkeypatch.setattr(core, "_encrypt", lambda plaintext: f"encrypted:{plaintext}")
    response = Mock(text="submitted")
    response.json.return_value = {"code": 1}
    post = Mock(return_value=response)
    monkeypatch.setattr(core, "_post", post)

    assert core._submit_face("student-1", "activity-1", "portrait.jpg") == "submitted"
    post.assert_called_once_with(
        "submitSignFace",
        {
            "sKey": "encrypted:student-1##activity-1##123",
            "sImage": "data:image/jpeg;base64,encoded-image",
        },
    )


def test_submit_gps_builds_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Submit the configured campus coordinates with activity metadata."""
    monkeypatch.setattr(core, "_timestamp_milliseconds", lambda: 123_000)
    monkeypatch.setattr(core, "_encrypt", lambda plaintext: f"encrypted:{plaintext}")
    response = Mock(text="submitted")
    response.json.return_value = {"code": 1}
    post = Mock(return_value=response)
    monkeypatch.setattr(core, "_post", post)

    assert core._submit_gps("student-1", "activity-1") == "submitted"
    post.assert_called_once_with(
        "submitPosition",
        {"sKey": "encrypted:student-1##activity-1####113.9539##22.801604##123000"},
    )


def test_submit_gps_raises_when_service_rejects_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise a domain error when position submission is rejected."""
    response = Mock()
    response.json.return_value = {"code": 0, "msg": "Location verification failed."}
    monkeypatch.setattr(core, "_post", lambda *_: response)

    with pytest.raises(core.CheckInRejectedError, match="Location verification failed"):
        core._submit_gps("student-1", "activity-1")
