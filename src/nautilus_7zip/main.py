"""Command-line entry point for the standalone GTK helper."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backend import SevenZipBackendError, resolve_sevenzip
from .selection import read_selection_file

ACTIONS = (
    "create",
    "quick-create-7z",
    "quick-create-zip",
    "extract",
    "extract-here",
    "extract-to-folder",
    "test",
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
        )
        application_status = application.run(["nautilus-7zip"])
        return application_status or error.exit_code

    from .application import NautilusSevenZipApplication

    application = NautilusSevenZipApplication(
        action=namespace.action,
        paths=selected,
        backend=backend,
    )
    return application.run(["nautilus-7zip"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
