"""Tests for core check-in operations."""

from unittest.mock import Mock

import pytest

from sysu_check_in import core


@pytest.mark.parametrize(
    (
        "collects_gps",
        "requires_face",
        "expected_collects_gps",
        "expected_requires_face",
    ),
    [
        (0, 0, False, False),
        (0, 1, False, True),
        (1, 0, True, False),
        (1, 1, True, True),
    ],
)
def test_get_active_activity_returns_first_active_activity(
    monkeypatch: pytest.MonkeyPatch,
    collects_gps: int,
    requires_face: int,
    expected_collects_gps: bool,
    expected_requires_face: bool,
) -> None:
    """Return the first active activity and its submission settings."""
    response = Mock()
    response.json.return_value = {
        "data": {
            "rows": [
                {
                    "iSignStatus": 1,
                    "sActId": "upcoming-activity",
                    "iCollectGPS": 0,
                    "isNeedFace": 0,
                },
                {
                    "iSignStatus": 2,
                    "sActId": "activity-1",
                    "iCollectGPS": collects_gps,
                    "isNeedFace": requires_face,
                },
            ]
        }
    }
    monkeypatch.setattr(core, "_post", lambda *_: response)

    assert core._get_active_activity("student-1") == core._Activity(
        activity_id="activity-1",
        collects_gps=expected_collects_gps,
        requires_face=expected_requires_face,
    )


def test_get_active_activity_raises_when_no_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise a domain error when the service returns no activities."""
    response = Mock()
    response.json.return_value = {"data": {"rows": []}}
    monkeypatch.setattr(core, "_post", lambda *_: response)

    with pytest.raises(core.NoActiveActivityError, match="No active check-in activity"):
        core._get_active_activity("student-1")


def test_check_in_submits_required_data_for_active_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Submit position and face data for the resolved activity."""
    submissions: list[str] = []

    def _submit_gps(*_: str) -> str:
        submissions.append("gps")
        return "position-submitted"

    def _submit_face(*_: str) -> str:
        submissions.append("face")
        return "submitted"

    monkeypatch.setattr(
        core,
        "_get_active_activity",
        lambda _: core._Activity(
            activity_id="activity-1",
            collects_gps=True,
            requires_face=True,
        ),
    )
    monkeypatch.setattr(
        core,
        "_submit_gps",
        _submit_gps,
    )
    monkeypatch.setattr(core, "_submit_face", _submit_face)

    assert core.check_in("student-1", "face.jpg") == "submitted"
    assert submissions == ["gps", "face"]


def test_check_in_skips_gps_when_activity_does_not_collect_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip position submission when the activity does not collect GPS data."""
    monkeypatch.setattr(
        core,
        "_get_active_activity",
        lambda _: core._Activity(
            activity_id="activity-1",
            collects_gps=False,
            requires_face=True,
        ),
    )
    submit_gps = Mock()
    monkeypatch.setattr(core, "_submit_gps", submit_gps)
    monkeypatch.setattr(core, "_submit_face", lambda *_: "submitted")

    assert core.check_in("student-1") == "submitted"
    submit_gps.assert_not_called()


def test_check_in_skips_face_when_activity_does_not_require_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip face submission when the activity does not require it."""
    monkeypatch.setattr(
        core,
        "_get_active_activity",
        lambda _: core._Activity(
            activity_id="activity-1",
            collects_gps=True,
            requires_face=False,
        ),
    )
    monkeypatch.setattr(core, "_submit_gps", lambda *_: "position-submitted")
    submit_face = Mock()
    monkeypatch.setattr(core, "_submit_face", submit_face)

    assert core.check_in("student-1") == "position-submitted"
    submit_face.assert_not_called()


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


def test_check_in_logs_skipped_submissions(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Log which submissions are skipped for the active activity."""
    monkeypatch.setattr(
        core,
        "_get_active_activity",
        lambda _: core._Activity(
            activity_id="activity-1",
            collects_gps=False,
            requires_face=False,
        ),
    )

    with caplog.at_level("INFO", logger=core.__name__):
        core.check_in("student-1")

    assert "skipping position submission" in caplog.text
    assert "skipping face submission" in caplog.text
