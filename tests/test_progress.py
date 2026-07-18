import pytest

from nautilus_7zip.progress import parse_progress


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  0% 1 - file", 0),
        (" 42% 10 + file", 42),
        ("100% Everything is Ok", 100),
        ("10% then 55%", 55),
        ("Physical Size = 100", None),
        ("123% is not valid", None),
        ("", None),
    ],
)
def test_parse_progress(text: str, expected: int | None) -> None:
    assert parse_progress(text) == expected
