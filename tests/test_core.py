"""Tests for core check-in operations."""

from unittest.mock import Mock

import pytest

from sysu_check_in import core


def test_get_activity_id_returns_first_active_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the first activity ID from the service response."""
    response = Mock()
    response.json.return_value = {"data": {"rows": [{"sActId": "activity-1"}]}}
    monkeypatch.setattr(core, "_post", lambda *_: response)

    assert core._get_activity_id("student-1") == "activity-1"


def test_get_activity_id_raises_when_no_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise a domain error when the service returns no activities."""
    response = Mock()
    response.json.return_value = {"data": {"rows": []}}
    monkeypatch.setattr(core, "_post", lambda *_: response)

    with pytest.raises(core.NoActiveActivityError, match="No active check-in activity"):
        core._get_activity_id("student-1")


def test_check_in_submits_face_for_active_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Submit the supplied image for the resolved activity."""
    monkeypatch.setattr(core, "_get_activity_id", lambda _: "activity-1")
    monkeypatch.setattr(
        core,
        "_submit_face",
        lambda student_id, activity_id, image_path: (
            f"{student_id}:{activity_id}:{image_path}"
        ),
    )

    assert core.check_in("student-1", "face.jpg") == "student-1:activity-1:face.jpg"


def test_submit_face_encodes_image_and_builds_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Encode the image and submit it with the activity metadata."""
    monkeypatch.setattr(core, "_read_image_base64", lambda _: "encoded-image")
    monkeypatch.setattr(core, "_timestamp", lambda: 123)
    monkeypatch.setattr(core, "_encrypt", lambda plaintext: f"encrypted:{plaintext}")
    response = Mock(text="submitted")
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
