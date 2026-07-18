"""Command-line entry point for the standalone GTK helper."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

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
        default="7z",
        help="7-Zip executable to invoke (default: 7z)",
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

    executable = shutil.which(namespace.sevenzip)
    if executable is None:
        print(
            f"nautilus-7zip: 7-Zip executable not found: {namespace.sevenzip}",
            file=sys.stderr,
        )
        return 127

    from .application import NautilusSevenZipApplication

    application = NautilusSevenZipApplication(
        action=namespace.action,
        paths=selected,
        sevenzip=executable,
    )
    return application.run(["nautilus-7zip"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
