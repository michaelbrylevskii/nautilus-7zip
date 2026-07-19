"""Path naming and archive-detection helpers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

ARCHIVE_SUFFIXES = (
    ".7z.001",
    ".zip.001",
    ".7z",
    ".zip",
    ".rar",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".tar.xz",
    ".txz",
    ".tar.zst",
    ".gz",
    ".bz2",
    ".xz",
    ".zst",
    ".cab",
    ".iso",
    ".wim",
)


def is_archive(path: Path) -> bool:
    name = path.name.casefold()
    return any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def archive_stem(path: Path) -> str:
    """Return the filename with a known, potentially compound suffix removed."""

    name = path.name
    folded = name.casefold()
    for suffix in sorted(ARCHIVE_SUFFIXES, key=len, reverse=True):
        if folded.endswith(suffix):
            return name[: -len(suffix)] or "Archive"
    return path.stem or "Archive"


def suggested_archive_name(paths: Iterable[Path]) -> str:
    selected = tuple(paths)
    if not selected:
        return "Archive"
    if len(selected) == 1:
        return archive_stem(selected[0])
    parents = {path.parent for path in selected}
    if len(parents) == 1:
        parent_name = next(iter(parents)).name
        if parent_name:
            return parent_name
    return "Archive"


def common_parent(paths: Iterable[Path]) -> Path:
    selected = tuple(paths)
    if not selected:
        raise ValueError("At least one path is required")
    first_parent = selected[0].parent
    if all(path.parent == first_parent for path in selected):
        return first_parent
    return Path.home()


def unique_path(path: Path) -> Path:
    """Return a non-existing sibling path without touching the filesystem."""

    if not path.exists():
        return path
    suffixes = "".join(path.suffixes)
    stem = path.name[: -len(suffixes)] if suffixes else path.name
    counter = 1
    while True:
        candidate = path.with_name(f"{stem} ({counter}){suffixes}")
        if not candidate.exists():
            return candidate
        counter += 1


def output_path_exists(path: Path, *, split: bool) -> bool:
    """Return whether a regular archive or the first requested volume exists."""

    if path.exists():
        return True
    return split and path.with_name(path.name + ".001").exists()
