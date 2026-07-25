"""Command-line entry point for the standalone GTK helper."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .backend import SevenZipBackendError, resolve_sevenzip
from .diagnostics import (
    DiagnosticsContext,
    collect_diagnostics,
    detect_nautilus_api,
    detect_toolkit_versions,
)
from .selection import read_selection_file

ACTIONS = (
    "create",
    "quick-create-7z",
    "quick-create-zip",
    "extract",
    "extract-here",
    "extract-to-folder",
    "test",
    "diagnostics",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nautilus-7zip",
        description="Create and extract archives with 7-Zip from Nautilus.",
    )
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument(
        "--selection-file",
        type=Path,
        help="JSON manifest created by the Nautilus extension",
    )
    parser.add_argument(
        "--sevenzip",
        metavar="PATH",
        help="7-Zip executable to use instead of auto-detecting 7z or 7zz",
    )
    return parser


def resolve_paths(paths: list[Path], selection_file: Path | None) -> tuple[Path, ...]:
    if selection_file is not None and paths:
        raise ValueError("Pass paths or --selection-file, not both")
    selected = read_selection_file(selection_file) if selection_file is not None else tuple(paths)
    if not selected:
        raise ValueError("At least one selected path is required")
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(argv)
    if namespace.action == "diagnostics":
        if namespace.paths or namespace.selection_file is not None:
            parser.error("Diagnostics does not accept selected paths")
        backend = None
        backend_error = None
        try:
            backend = resolve_sevenzip(namespace.sevenzip)
        except SevenZipBackendError as error:
            backend_error = str(error)
        report = collect_diagnostics(
            DiagnosticsContext(
                application_version=__version__,
                module_path=Path(__file__).parent,
                backend=backend,
                backend_error=backend_error,
                backend_override=namespace.sevenzip is not None,
                toolkit=detect_toolkit_versions(),
                nautilus_api=detect_nautilus_api(),
            )
        )
        print(report, end="")
        return 0

    try:
        selected = resolve_paths(namespace.paths, namespace.selection_file)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    try:
        backend = resolve_sevenzip(namespace.sevenzip)
    except SevenZipBackendError as error:
        print(f"nautilus-7zip: {error}", file=sys.stderr)
        from .application import NautilusSevenZipApplication

        application = NautilusSevenZipApplication(
            action=namespace.action,
            paths=selected,
            startup_error=str(error),
            backend_override=namespace.sevenzip is not None,
        )
        application_status = application.run(["nautilus-7zip"])
        return application_status or error.exit_code

    from .application import NautilusSevenZipApplication

    application = NautilusSevenZipApplication(
        action=namespace.action,
        paths=selected,
        backend=backend,
        backend_override=namespace.sevenzip is not None,
    )
    return application.run(["nautilus-7zip"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
