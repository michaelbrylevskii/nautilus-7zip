from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import nautilus_7zip.diagnostics as diagnostics_module
from nautilus_7zip.backend import SevenZipBackend
from nautilus_7zip.diagnostics import (
    DiagnosticsContext,
    ToolkitVersions,
    collect_diagnostics,
    detect_nautilus_api,
    detect_toolkit_versions,
    probe_command,
)


def context(
    tmp_path: Path,
    *,
    backend: SevenZipBackend | None = None,
    backend_error: str | None = None,
    override: bool = False,
    toolkit: ToolkitVersions | None = None,
) -> DiagnosticsContext:
    return DiagnosticsContext(
        application_version="0.2.0",
        module_path=tmp_path / ".local/lib/nautilus_7zip",
        backend=backend,
        backend_error=backend_error,
        backend_override=override,
        toolkit=toolkit
        or ToolkitVersions(
            gtk=(4, 14, 5),
            libadwaita=(1, 5, 4),
            glib=(2, 80, 3),
        ),
        nautilus_api="4.1",
    )


def fake_probe(argv: tuple[str, ...], timeout: float) -> str | None:
    assert timeout == 2.0
    return {
        ("nautilus", "--version"): "GNOME nautilus 46.2",
        ("pkg-config", "--modversion", "nautilus-python"): "4.0.1",
    }.get(argv)


def test_collect_available_backend_report_is_complete_and_private(tmp_path: Path) -> None:
    home = tmp_path / "private-user"
    backend = SevenZipBackend(str(home / "bin/7z"), "7z", "26.02")
    report = collect_diagnostics(
        context(home, backend=backend),
        command_probe=fake_probe,
        environ={
            "XDG_CURRENT_DESKTOP": "GNOME",
            "XDG_SESSION_TYPE": "wayland",
            "LANG": "ru_RU.UTF-8",
            "SECRET_SELECTION": "/private/archive/source",
        },
        home=home,
        os_release={"PRETTY_NAME": "Test Linux 1"},
    )

    assert "Version: 0.2.0" in report
    assert "Installation: ~/.local/lib/nautilus_7zip" in report
    assert "OS: Test Linux 1" in report
    assert "Desktop: GNOME" in report
    assert "Session: wayland" in report
    assert "Locale: ru_RU.UTF-8" in report
    assert "Nautilus: GNOME nautilus 46.2" in report
    assert "nautilus-python: 4.0.1" in report
    assert "Nautilus API: 4.1" in report
    assert "GTK: 4.14.5" in report
    assert "libadwaita: 1.5.4" in report
    assert "GLib: 2.80.3" in report
    assert "Runtime compatibility: Supported" in report
    assert "Status: Available" in report
    assert "Selection: Automatic" in report
    assert "Command: 7z" in report
    assert "Version: 26.02" in report
    assert "Executable: ~/bin/7z" in report
    assert str(home) not in report
    assert "SECRET_SELECTION" not in report
    assert "/private/archive/source" not in report


def test_collect_unavailable_override_sanitizes_multiline_error(tmp_path: Path) -> None:
    home = tmp_path / "person"
    report = collect_diagnostics(
        context(
            home,
            backend_error=f"Cannot execute\n{home}/custom/7zz",
            override=True,
            toolkit=ToolkitVersions(gtk=(4, 12, 0), libadwaita=(1, 4, 0)),
        ),
        command_probe=lambda _argv, _timeout: None,
        environ={},
        home=home,
        os_release={},
    )

    assert "OS:" in report
    assert "Desktop: Unavailable" in report
    assert "Nautilus: Unavailable" in report
    assert "GLib: Unavailable" in report
    assert "Runtime compatibility: Unsupported (GTK 4.12.0 < 4.14.0" in report
    assert "libadwaita 1.4.0 < 1.5.0)" in report
    assert "Status: Unavailable" in report
    assert "Selection: Override" in report
    assert "Reason: Cannot execute ~/custom/7zz" in report
    assert str(home) not in report


def test_context_rejects_backend_and_error_together(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        context(
            tmp_path,
            backend=SevenZipBackend("/usr/bin/7z", "7z", "26.02"),
            backend_error="broken",
        )


def test_probe_command_is_bounded_and_noninteractive(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    def run(argv: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        received["argv"] = argv
        received.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="\n tool 1.2 \nsecond")

    monkeypatch.setattr(diagnostics_module.subprocess, "run", run)

    assert probe_command(("tool", "--version"), 1.25) == "tool 1.2"
    assert received["argv"] == ("tool", "--version")
    assert received["stdin"] is subprocess.DEVNULL
    assert received["stderr"] is subprocess.DEVNULL
    assert received["timeout"] == 1.25
    assert received["check"] is False


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.CompletedProcess(("tool",), 2, stdout="failed"),
        subprocess.CompletedProcess(("tool",), 0, stdout="\n"),
        OSError("missing"),
        subprocess.TimeoutExpired(("tool",), 2),
    ],
)
def test_probe_command_returns_none_for_unavailable_commands(
    monkeypatch: pytest.MonkeyPatch,
    failure: subprocess.CompletedProcess[str] | Exception,
) -> None:
    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(diagnostics_module.subprocess, "run", run)
    assert probe_command(("tool",)) is None


@pytest.mark.parametrize(("argv", "timeout"), [((), 2.0), (("tool",), 0), (("tool",), -1)])
def test_probe_command_rejects_invalid_arguments(
    argv: tuple[str, ...],
    timeout: float,
) -> None:
    with pytest.raises(ValueError):
        probe_command(argv, timeout)


def test_detection_helpers_are_safe_without_initializing_a_display() -> None:
    toolkit = detect_toolkit_versions()
    assert toolkit.gtk is None or toolkit.gtk[0] == 4
    assert toolkit.libadwaita is None or toolkit.libadwaita[0] == 1
    assert detect_nautilus_api() in {None, "4.0", "4.1"}
