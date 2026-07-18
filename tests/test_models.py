from pathlib import Path

import pytest

from nautilus_7zip.models import ArchiveFormat, CompressionLevel, CreateOptions


def test_archive_format_suffixes() -> None:
    assert ArchiveFormat.SEVEN_ZIP.suffix == ".7z"
    assert ArchiveFormat.ZIP.suffix == ".zip"


def test_compression_levels_match_7zip_values() -> None:
    assert [int(level) for level in CompressionLevel] == [0, 1, 3, 5, 7, 9]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"sources": ()}, "At least one source"),
        ({"threads": 0}, "Thread count"),
        (
            {"archive_format": ArchiveFormat.ZIP, "encrypt_headers": True, "password": "x"},
            "only supported",
        ),
        ({"encrypt_headers": True}, "requires a password"),
    ],
)
def test_create_options_reject_invalid_combinations(kwargs: dict, message: str) -> None:
    arguments = {"sources": (Path("source"),), "output": Path("archive")}
    arguments.update(kwargs)
    with pytest.raises(ValueError, match=message):
        CreateOptions(**arguments)


def test_create_options_accept_valid_encryption() -> None:
    options = CreateOptions(
        (Path("source"),),
        Path("archive"),
        password="secret",
        encrypt_headers=True,
        threads=4,
    )
    assert options.password == "secret"
    assert options.threads == 4
