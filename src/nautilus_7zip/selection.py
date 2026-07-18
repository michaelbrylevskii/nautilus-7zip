"""Secure transfer of Nautilus selections to the helper process."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def write_selection_file(paths: tuple[Path, ...]) -> Path:
    if not paths:
        raise ValueError("Selection must not be empty")
    descriptor, raw_path = tempfile.mkstemp(prefix="nautilus-7zip-", suffix=".json")
    manifest = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump([str(path) for path in paths], stream, ensure_ascii=False)
            stream.write("\n")
        manifest.chmod(0o600)
    except BaseException:
        manifest.unlink(missing_ok=True)
        raise
    return manifest


def read_selection_file(manifest: Path, *, remove: bool = True) -> tuple[Path, ...]:
    try:
        with manifest.open(encoding="utf-8") as stream:
            value = json.load(stream)
        if not isinstance(value, list) or not value:
            raise ValueError("Selection manifest must contain a non-empty list")
        if not all(isinstance(item, str) and item for item in value):
            raise ValueError("Selection manifest contains an invalid path")
        return tuple(Path(item) for item in value)
    finally:
        if remove:
            manifest.unlink(missing_ok=True)
