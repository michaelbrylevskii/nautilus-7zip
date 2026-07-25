"""Privacy-safe diagnostics collection independent of the GTK UI."""

from __future__ import annotations

import locale
import os
import platform
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .backend import SevenZipBackend
from .runtime import Version, check_runtime_versions, format_version

DEFAULT_PROBE_TIMEOUT: Final = 2.0
UNAVAILABLE: Final = "Unavailable"
CommandProbe = Callable[[tuple[str, ...], float], str | None]


@dataclass(frozen=True, slots=True)
class ToolkitVersions:
    """Versions of the libraries loaded by the GTK process."""

    gtk: Version | None = None
    libadwaita: Version | None = None
    glib: Version | None = None


@dataclass(frozen=True, slots=True)
class DiagnosticsContext:
    """Known application state that is safe to include in a report."""

    application_version: str
    module_path: Path
    backend: SevenZipBackend | None
    backend_error: str | None
    backend_override: bool
    toolkit: ToolkitVersions
    nautilus_api: str | None

    def __post_init__(self) -> None:
        if self.backend is not None and self.backend_error is not None:
            raise ValueError("Backend and backend error are mutually exclusive")


def probe_command(
    argv: tuple[str, ...],
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> str | None:
    """Return the first output line from a bounded, noninteractive command."""

    if not argv:
        raise ValueError("Diagnostic command must not be empty")
    if timeout <= 0:
        raise ValueError("Diagnostic timeout must be positive")
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return _first_line(completed.stdout)


def detect_toolkit_versions() -> ToolkitVersions:
    """Read installed toolkit versions without initializing a display."""

    try:
        import gi

        gi.require_version("Adw", "1")
        gi.require_version("Gtk", "4.0")
        from gi.repository import Adw, GLib, Gtk
    except (ImportError, ValueError):
        return ToolkitVersions()
    return ToolkitVersions(
        gtk=(Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()),
        libadwaita=(
            Adw.get_major_version(),
            Adw.get_minor_version(),
            Adw.get_micro_version(),
        ),
        glib=(GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION),
    )


def detect_nautilus_api() -> str | None:
    """Return the newest Nautilus GI API namespace available to the helper."""

    try:
        import gi
    except ImportError:
        return None
    for version in ("4.1", "4.0"):
        try:
            gi.require_version("Nautilus", version)
            from gi.repository import Nautilus
        except (ImportError, ValueError):
            continue
        return str(getattr(Nautilus, "_version", version))
    return None


def collect_diagnostics(
    context: DiagnosticsContext,
    *,
    command_probe: CommandProbe = probe_command,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_release: Mapping[str, str] | None = None,
) -> str:
    """Collect and render a bounded report containing no operation paths."""

    environment = os.environ if environ is None else environ
    home_path = Path.home() if home is None else home
    release = _os_release() if os_release is None else os_release
    nautilus_version = command_probe(("nautilus", "--version"), DEFAULT_PROBE_TIMEOUT)
    nautilus_python = command_probe(
        ("pkg-config", "--modversion", "nautilus-python"),
        DEFAULT_PROBE_TIMEOUT,
    )

    lines = [
        "7-Zip for Nautilus Diagnostics",
        "",
        "Application",
        f"Version: {_clean(context.application_version)}",
        f"Installation: {_sanitize_path(context.module_path, home_path)}",
        f"Python: {_clean(platform.python_version())}",
        "",
        "Desktop",
        f"OS: {_clean(release.get('PRETTY_NAME') or _fallback_os_name())}",
        f"Desktop: {_environment_value(environment, 'XDG_CURRENT_DESKTOP')}",
        f"Session: {_environment_value(environment, 'XDG_SESSION_TYPE')}",
        f"Locale: {_locale_value(environment)}",
        f"Nautilus: {_clean(nautilus_version)}",
        f"nautilus-python: {_clean(nautilus_python)}",
        f"Nautilus API: {_clean(context.nautilus_api)}",
        f"GTK: {_optional_version(context.toolkit.gtk)}",
        f"libadwaita: {_optional_version(context.toolkit.libadwaita)}",
        f"GLib: {_optional_version(context.toolkit.glib)}",
        f"Runtime compatibility: {_runtime_status(context.toolkit)}",
        "",
        "7-Zip Backend",
        f"Status: {'Available' if context.backend is not None else 'Unavailable'}",
        f"Selection: {'Override' if context.backend_override else 'Automatic'}",
    ]
    if context.backend is not None:
        lines.extend(
            (
                f"Command: {_clean(context.backend.command_name)}",
                f"Version: {_clean(context.backend.version)}",
                f"Executable: {_sanitize_text(context.backend.executable, home_path)}",
            )
        )
    elif context.backend_error is not None:
        lines.append(f"Reason: {_sanitize_text(context.backend_error, home_path)}")
    return "\n".join(lines) + "\n"


def _runtime_status(toolkit: ToolkitVersions) -> str:
    if toolkit.gtk is None or toolkit.libadwaita is None:
        return "Unknown"
    issues = check_runtime_versions(toolkit.gtk, toolkit.libadwaita)
    if not issues:
        return "Supported"
    return "Unsupported (" + ", ".join(
        f"{issue.component} {format_version(issue.actual)}"
        f" < {format_version(issue.required)}"
        for issue in issues
    ) + ")"


def _os_release() -> Mapping[str, str]:
    try:
        return platform.freedesktop_os_release()
    except OSError:
        return {}


def _fallback_os_name() -> str:
    return f"{platform.system()} {platform.release()}".strip()


def _locale_value(environment: Mapping[str, str]) -> str:
    configured = environment.get("LC_ALL") or environment.get("LANG")
    if configured:
        return _clean(configured)
    try:
        return _clean(locale.setlocale(locale.LC_CTYPE))
    except locale.Error:
        return UNAVAILABLE


def _environment_value(environment: Mapping[str, str], name: str) -> str:
    return _clean(environment.get(name))


def _optional_version(version: Version | None) -> str:
    return UNAVAILABLE if version is None else format_version(version)


def _sanitize_path(path: Path, home: Path) -> str:
    return _sanitize_text(str(path.resolve()), home)


def _sanitize_text(value: str, home: Path) -> str:
    cleaned = _clean(value)
    home_text = str(home)
    if home_text and home_text != os.sep:
        cleaned = cleaned.replace(home_text, "~")
    return cleaned


def _clean(value: object | None) -> str:
    if value is None:
        return UNAVAILABLE
    text = " ".join(str(value).split())
    if not text:
        return UNAVAILABLE
    return text[:500]


def _first_line(value: str) -> str | None:
    for line in value.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:500]
    return None
