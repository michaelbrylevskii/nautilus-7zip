import pytest

from nautilus_7zip.sizes import parse_binary_size


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1B", 1),
        ("100M", 100 * 1024**2),
        ("700 MiB", 700 * 1024**2),
        ("2g", 2 * 1024**3),
        ("4 GiB", 4 * 1024**3),
        ("1.5 GiB", 1536 * 1024**2),
        ("0.5G", 512 * 1024**2),
        (" 1500 mb ", 1500 * 1024**2),
    ],
)
def test_parse_binary_size(text: str, expected: int) -> None:
    assert parse_binary_size(text) == expected


@pytest.mark.parametrize("text", ["", "0M", "-1G", "lots", "12T"])
def test_parse_binary_size_rejects_invalid_values(text: str) -> None:
    with pytest.raises(ValueError, match="size"):
        parse_binary_size(text)
