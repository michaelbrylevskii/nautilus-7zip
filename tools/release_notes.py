"""Extract one version's release notes from a Keep a Changelog document."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_VERSION_HEADING = re.compile(r"^## \[(?P<version>[^]]+)](?: - .+)?$", re.MULTILINE)
_LINK_DEFINITION = re.compile(r"^\[[^]]+]:\s+\S+", re.MULTILINE)


def extract_release_notes(changelog: str, version: str) -> str:
    """Return the Markdown body for *version* or raise ``ValueError``."""

    headings = list(_VERSION_HEADING.finditer(changelog))
    heading_index = next(
        (index for index, match in enumerate(headings) if match.group("version") == version),
        None,
    )
    if heading_index is None:
        raise ValueError(f"CHANGELOG.md has no [{version}] section")

    heading = headings[heading_index]
    end = (
        headings[heading_index + 1].start()
        if heading_index + 1 < len(headings)
        else len(changelog)
    )
    body = changelog[heading.end() : end]
    footer = _LINK_DEFINITION.search(body)
    if footer is not None:
        body = body[: footer.start()]
    body = body.strip()
    if not body:
        raise ValueError(f"CHANGELOG.md section [{version}] is empty")
    return f"{body}\n"


def main() -> int:
    """Write one changelog section to stdout for the release workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()
    try:
        notes = extract_release_notes(args.changelog.read_text(encoding="utf-8"), args.version)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(notes, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
