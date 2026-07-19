from pathlib import Path

import pytest

from nautilus_7zip.models import ArchiveFormat, CompressionLevel, CreateOptions, SolidBlock


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
        ({"volume_size": 0}, "Volume size"),
        (
            {"archive_format": ArchiveFormat.ZIP},
            "Solid blocks are only supported",
        ),
        (
            {
                "archive_format": ArchiveFormat.ZIP,
                "solid_block": None,
                "encrypt_headers": True,
                "password": "x",
            },
            "Header encryption",
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


def test_create_options_computes_archive_and_volume_paths() -> None:
    options = CreateOptions(
        (Path("source"),),
        Path("backup"),
        volume_size=100 * 1024 * 1024,
    )
    assert options.archive_path == Path("backup.7z")
    assert options.verification_path == Path("backup.7z.001")


def test_create_options_uses_archive_path_for_single_file() -> None:
    options = CreateOptions((Path("source"),), Path("BACKUP.7Z"))
    assert options.archive_path == Path("BACKUP.7Z")
    assert options.verification_path == Path("BACKUP.7Z")


def test_zip_options_disable_solid_blocks() -> None:
    options = CreateOptions(
        (Path("source"),),
        Path("backup"),
        archive_format=ArchiveFormat.ZIP,
        solid_block=None,
    )
    assert options.archive_path == Path("backup.zip")


def test_solid_block_switches_are_valid_7zip_properties() -> None:
    assert [block.value for block in SolidBlock] == [
        "on",
        "off",
        "256m",
        "1g",
        "4g",
        "18446744073709551615b",
    ]
