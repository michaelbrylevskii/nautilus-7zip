"""Discovery and validation of the external 7-Zip command-line backend."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .i18n import _

DEFAULT_EXECUTABLES = ("7z", "7zz")
DEFAULT_PROBE_TIMEOUT = 5.0
_VERSION_PATTERN = re.compile(r"^7-Zip\b.*?\b(?P<version>\d{2,}(?:\.\d+)+)\b", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class SevenZipBackend:
    """A validated 7-Zip executable and the metadata reported by it."""

    executable: str
    command_name: str
    version: str

    @property
    def display_name(self) -> str:
        """Return a concise label suitable for diagnostics."""

        return f"{self.command_name} {self.version}"


class SevenZipBackendError(RuntimeError):
    """A user-facing backend discovery failure with a CLI exit status."""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def resolve_sevenzip(
    executable: str | None = None,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> SevenZipBackend:
    """Find and validate an explicit executable or the supported defaults."""

    if timeout <= 0:
        raise ValueError("Probe timeout must be positive")
    if executable == "":
        raise ValueError("7-Zip executable must not be empty")

    candidates = (executable,) if executable is not None else DEFAULT_EXECUTABLES
    failures: list[str] = []
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved is None:
            if executable is not None:
                raise SevenZipBackendError(
                    _("7-Zip executable was not found: {executable}").format(
                        executable=candidate
                    ),
                    exit_code=127,
                )
            continue

        try:
            return _probe_backend(resolved, timeout=timeout)
        except SevenZipBackendError as error:
            if executable is not None:
                raise
            failures.append(f"{Path(resolved).name}: {error}")

    if failures:
        raise SevenZipBackendError(
            _("No usable 7-Zip backend was found. Tried: {failures}").format(
                failures="; ".join(failures)
            ),
            exit_code=126,
        )
    raise SevenZipBackendError(
        _(
            "7-Zip was not found. Install a package providing '7z' or '7zz', "
            "or choose an executable with --sevenzip."
        ),
        exit_code=127,
    )


def _probe_backend(executable: str, *, timeout: float) -> SevenZipBackend:
    try:
        completed = subprocess.run(
            (executable, "i"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as error:
        raise SevenZipBackendError(
            _("7-Zip executable timed out during validation: {executable}").format(
                executable=executable
            ),
            exit_code=126,
        ) from error
    except OSError as error:
        raise SevenZipBackendError(
            _("Unable to run 7-Zip executable {executable}: {reason}").format(
                executable=executable,
                reason=error.strerror or type(error).__name__,
            ),
            exit_code=126,
        ) from error

    if completed.returncode != 0:
        raise SevenZipBackendError(
            _(
                "7-Zip executable {executable} exited with status {status} "
                "during validation."
            ).format(executable=executable, status=completed.returncode),
            exit_code=126,
        )

    version_match = _VERSION_PATTERN.search(completed.stdout)
    if version_match is None:
        raise SevenZipBackendError(
            _(
                "Executable did not report a recognizable 7-Zip version: "
                "{executable}"
            ).format(executable=executable),
            exit_code=126,
        )
    return SevenZipBackend(
        executable=executable,
        command_name=Path(executable).name,
        version=version_match.group("version"),
    )
