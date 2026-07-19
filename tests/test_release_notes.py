from pathlib import Path

import pytest

from nautilus_7zip import __version__
from tools.release_notes import extract_release_notes


def test_extract_release_notes_returns_only_requested_version() -> None:
    changelog = """# Changelog

## [Unreleased]

- Later work.

## [1.2.3] - 2026-07-19

### Added

- Shipped feature.

[Unreleased]: https://example.test/compare
[1.2.3]: https://example.test/release
"""

    assert extract_release_notes(changelog, "1.2.3") == "### Added\n\n- Shipped feature.\n"


@pytest.mark.parametrize(
    ("changelog", "message"),
    [
        ("## [Unreleased]\n\n- Work\n", "has no [1.0.0] section"),
        ("## [1.0.0] - 2026-07-19\n", "section [1.0.0] is empty"),
    ],
)
def test_extract_release_notes_rejects_missing_or_empty_section(
    changelog: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message.replace("[", r"\[").replace("]", r"\]")):
        extract_release_notes(changelog, "1.0.0")


def test_current_release_notes_are_extractable() -> None:
    changelog = (Path(__file__).parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")

    assert extract_release_notes(changelog, __version__).strip()
