"""Tests for the command-line interface."""

import logging
import sys
from importlib.metadata import version
from unittest.mock import Mock

import pytest

from sysu_check_in import cli, core


def test_main_prints_service_response(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Print the response returned by the core check-in function."""
    monkeypatch.setattr(sys, "argv", ["sysu-check-in", "student-1"])
    monkeypatch.setattr(core, "check_in", lambda *_: "checked in")

    cli.main()

    assert capsys.readouterr().out == "checked in\n"


def test_main_passes_image_option(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pass the supplied image path to the core check-in function."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["sysu-check-in", "student-1", "--image", "portrait.jpg"],
    )
    check_in = Mock(return_value="checked in")
    monkeypatch.setattr(core, "check_in", check_in)

    cli.main()

    assert capsys.readouterr().out == "checked in\n"
    check_in.assert_called_once_with("student-1", "portrait.jpg")


def test_main_prints_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Print the installed package version."""
    monkeypatch.setattr(sys, "argv", ["sysu-check-in", "--version"])

    with pytest.raises(SystemExit):
        cli.main()

    assert capsys.readouterr().out == f"sysu-check-in {version('sysu-check-in')}\n"


def test_main_reports_no_active_activity(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Convert a missing activity into a concise command-line error."""
    monkeypatch.setattr(sys, "argv", ["sysu-check-in", "student-1"])

    def _raise_no_activity(*_: str) -> str:
        raise core.NoActiveActivityError("No active check-in activity is available.")

    monkeypatch.setattr(core, "check_in", _raise_no_activity)

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 1
    assert caplog.record_tuples[-1][1] == logging.ERROR
    assert "Check-in failed: No active check-in activity" in caplog.text


def test_main_reports_rejected_check_in(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Convert a rejected submission into a concise command-line error."""
    monkeypatch.setattr(sys, "argv", ["sysu-check-in", "student-1"])

    def _raise_rejection(*_: str) -> str:
        raise core.CheckInRejectedError("Location verification failed.")

    monkeypatch.setattr(core, "check_in", _raise_rejection)

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 1
    assert caplog.record_tuples[-1][1] == logging.ERROR
    assert "Check-in failed: Location verification failed" in caplog.text


@pytest.mark.parametrize(
    ("flags", "expected_level"),
    [([], logging.WARNING), (["-v"], logging.INFO), (["-vv"], logging.DEBUG)],
)
def test_main_configures_log_level(
    monkeypatch: pytest.MonkeyPatch, flags: list[str], expected_level: int
) -> None:
    """Map repeated verbose flags to increasingly detailed log levels."""
    monkeypatch.setattr(sys, "argv", ["sysu-check-in", "student-1", *flags])
    monkeypatch.setattr(core, "check_in", lambda *_: "checked in")
    basic_config = Mock()
    monkeypatch.setattr(logging, "basicConfig", basic_config)

    cli.main()

    assert basic_config.call_args.kwargs["level"] == expected_level
