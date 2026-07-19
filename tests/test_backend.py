from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import nautilus_7zip.backend as backend_module
from nautilus_7zip.backend import SevenZipBackendError, resolve_sevenzip


def completed(
    output: str = "7-Zip 26.02 (x64)\n",
    returncode: int = 0,
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(("7z", "i"), returncode, stdout=output)


def test_resolver_prefers_7z_and_parses_version(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    def fake_which(candidate: str) -> str | None:
        attempts.append(candidate)
        return f"/usr/bin/{candidate}"

    monkeypatch.setattr(backend_module.shutil, "which", fake_which)
    monkeypatch.setattr(backend_module.subprocess, "run", lambda *_args, **_kwargs: completed())

    backend = resolve_sevenzip()

    assert attempts == ["7z"]
    assert backend.executable == "/usr/bin/7z"
    assert backend.command_name == "7z"
    assert backend.version == "26.02"
    assert backend.display_name == "7z 26.02"


def test_resolver_falls_back_to_7zz_when_7z_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        backend_module.shutil,
        "which",
        lambda candidate: None if candidate == "7z" else "/opt/7zip/7zz",
    )
    monkeypatch.setattr(
        backend_module.subprocess,
        "run",
        lambda *_args, **_kwargs: completed("7-Zip (z) 25.01 (x64)\n"),
    )

    backend = resolve_sevenzip()

    assert backend.executable == "/opt/7zip/7zz"
    assert backend.command_name == "7zz"
    assert backend.version == "25.01"


def test_resolver_falls_back_when_first_candidate_is_unusable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda candidate: f"/bin/{candidate}")
    results = iter((completed(returncode=2), completed("7-Zip 24.09\n")))
    monkeypatch.setattr(backend_module.subprocess, "run", lambda *_args, **_kwargs: next(results))

    backend = resolve_sevenzip()

    assert backend.command_name == "7zz"
    assert backend.version == "24.09"


def test_explicit_override_does_not_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    def fake_which(candidate: str) -> None:
        attempts.append(candidate)

    monkeypatch.setattr(backend_module.shutil, "which", fake_which)

    with pytest.raises(SevenZipBackendError, match="custom-7zip") as error:
        resolve_sevenzip("custom-7zip")

    assert error.value.exit_code == 127
    assert attempts == ["custom-7zip"]


def test_explicit_unusable_backend_reports_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda _candidate: "/opt/bin/custom")
    monkeypatch.setattr(
        backend_module.subprocess,
        "run",
        lambda *_args, **_kwargs: completed(returncode=9),
    )

    with pytest.raises(SevenZipBackendError, match="status 9") as error:
        resolve_sevenzip("/opt/bin/custom")

    assert error.value.exit_code == 126


def test_resolver_reports_missing_default_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda _candidate: None)

    with pytest.raises(SevenZipBackendError, match="providing '7z' or '7zz'") as error:
        resolve_sevenzip()

    assert error.value.exit_code == 127


def test_resolver_reports_all_unusable_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda candidate: f"/bin/{candidate}")
    monkeypatch.setattr(
        backend_module.subprocess,
        "run",
        lambda *_args, **_kwargs: completed(returncode=2),
    )

    with pytest.raises(SevenZipBackendError, match=r"7z: .*; 7zz:") as error:
        resolve_sevenzip()

    assert error.value.exit_code == 126


def test_probe_uses_bounded_noninteractive_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}
    monkeypatch.setattr(backend_module.shutil, "which", lambda _candidate: "/usr/bin/7z")

    def fake_run(argv: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess:
        received["argv"] = argv
        received.update(kwargs)
        return completed("7-Zip 23.01\n")

    monkeypatch.setattr(backend_module.subprocess, "run", fake_run)

    backend = resolve_sevenzip(timeout=1.25)

    assert backend.display_name == "7z 23.01"
    assert received["argv"] == ("/usr/bin/7z", "i")
    assert received["stdin"] is subprocess.DEVNULL
    assert received["stderr"] is subprocess.STDOUT
    assert received["timeout"] == 1.25
    assert received["check"] is False


def test_probe_rejects_unrecognized_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda _candidate: "/usr/bin/not-7zip")
    monkeypatch.setattr(
        backend_module.subprocess,
        "run",
        lambda *_args, **_kwargs: completed("unrelated tool\n"),
    )

    with pytest.raises(SevenZipBackendError, match="recognizable 7-Zip version") as error:
        resolve_sevenzip("/usr/bin/not-7zip")

    assert error.value.exit_code == 126


def test_probe_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda _candidate: "/usr/bin/7z")

    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(("/usr/bin/7z", "i"), 5)

    monkeypatch.setattr(backend_module.subprocess, "run", timeout)

    with pytest.raises(SevenZipBackendError, match="timed out") as error:
        resolve_sevenzip("7z")

    assert error.value.exit_code == 126


def test_probe_reports_os_error_without_command_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_module.shutil, "which", lambda _candidate: "/usr/bin/7z")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise OSError(13, "Permission denied", str(Path("/usr/bin/7z")))

    monkeypatch.setattr(backend_module.subprocess, "run", fail)

    with pytest.raises(SevenZipBackendError, match="Permission denied") as error:
        resolve_sevenzip("7z")

    assert error.value.exit_code == 126


@pytest.mark.parametrize(("executable", "timeout"), [("", 5.0), (None, 0), (None, -1)])
def test_resolver_rejects_invalid_arguments(executable: str | None, timeout: float) -> None:
    with pytest.raises(ValueError):
        resolve_sevenzip(executable, timeout=timeout)
