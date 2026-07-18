import pytest

from nautilus_7zip.labels import escape_menu_mnemonics


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Create Ya_em_golubey.7z", "Create Ya__em__golubey.7z"),
        ("Extract to release_build/", "Extract to release__build/"),
        ("Create archive…", "Create archive…"),
        ("_leading_", "__leading__"),
        ("", ""),
    ],
)
def test_escape_menu_mnemonics(label: str, expected: str) -> None:
    assert escape_menu_mnemonics(label) == expected
