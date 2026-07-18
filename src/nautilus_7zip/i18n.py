"""gettext initialization with English source strings as the fallback."""

from __future__ import annotations

import gettext
import os
from pathlib import Path

DOMAIN = "nautilus-7zip"


def locale_directories() -> tuple[Path, ...]:
    configured = os.environ.get("NAUTILUS_7ZIP_LOCALE_DIR")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        (
            Path.home() / ".local/share/locale",
            Path("/usr/local/share/locale"),
            Path("/usr/share/locale"),
        )
    )
    return tuple(dict.fromkeys(candidates))


def translation() -> gettext.NullTranslations:
    for directory in locale_directories():
        try:
            return gettext.translation(DOMAIN, localedir=directory)
        except FileNotFoundError:
            continue
    return gettext.NullTranslations()


_ = translation().gettext
