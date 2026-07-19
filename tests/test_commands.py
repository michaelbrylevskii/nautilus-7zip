from pathlib import Path

import pytest

from nautilus_7zip.commands import CommandSpec, SevenZipCommandBuilder
from nautilus_7zip.models import (
    ArchiveFormat,
    CompressionLevel,
    CreateOptions,
    ExtractOptions,
    IntegrityTestOptions,
    OverwriteMode,
    SolidBlock,
)


def test_command_spec_exposes_executable() -> None:
    assert CommandSpec(("/usr/bin/7z", "i")).executable == "/usr/bin/7z"


def test_builder_rejects_empty_executable() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        SevenZipCommandBuilder("")


def test_build_default_7z_create_command() -> None:
    builder = SevenZipCommandBuilder("/usr/bin/7z")
    spec = builder.create(
        CreateOptions(
            (Path("/tmp/source one"), Path("/tmp/source-two")),
            Path("/tmp/backup"),
        )
    )

    assert spec.argv[:3] == ("/usr/bin/7z", "a", "-t7z")
    assert "-mx=5" in spec.argv
    assert "-mmt=on" in spec.argv
    assert "-ms=on" in spec.argv
    assert spec.argv[-4:] == (
        "/tmp/backup.7z",
        "--",
        "/tmp/source one",
        "/tmp/source-two",
    )
    assert spec.stdin_text is None
    assert spec.title == "Create backup.7z"


def test_existing_suffix_is_not_duplicated() -> None:
    spec = SevenZipCommandBuilder().create(
        CreateOptions((Path("source"),), Path("ARCHIVE.7Z"))
    )
    assert "ARCHIVE.7Z" in spec.argv
    assert all(".7Z.7z" not in argument for argument in spec.argv)


def test_build_encrypted_7z_command_keeps_secret_out_of_argv() -> None:
    spec = SevenZipCommandBuilder().create(
        CreateOptions(
            (Path("source"),),
            Path("archive"),
            level=CompressionLevel.ULTRA,
            threads=8,
            solid_block=SolidBlock.NON_SOLID,
            password="correct horse battery staple",
            encrypt_headers=True,
        )
    )
    assert "-mmt=8" in spec.argv
    assert "-mx=9" in spec.argv
    assert "-ms=off" in spec.argv
    assert "-p" in spec.argv
    assert "-mhe=on" in spec.argv
    assert not any("correct horse" in argument for argument in spec.argv)
    assert spec.stdin_text == "correct horse battery staple\n"


def test_build_encrypted_zip_command() -> None:
    spec = SevenZipCommandBuilder().create(
        CreateOptions(
            (Path("source"),),
            Path("archive.zip"),
            archive_format=ArchiveFormat.ZIP,
            password="secret",
            solid_block=None,
        )
    )
    assert "-tzip" in spec.argv
    assert "-mm=Deflate" in spec.argv
    assert "-mem=AES256" in spec.argv
    assert "-ms=off" not in spec.argv
    assert "-p" in spec.argv
    assert spec.stdin_text == "secret\n"


@pytest.mark.parametrize(
    ("block", "switch"),
    [
        (SolidBlock.AUTO, "-ms=on"),
        (SolidBlock.NON_SOLID, "-ms=off"),
        (SolidBlock.MIB_256, "-ms=256m"),
        (SolidBlock.GIB_1, "-ms=1g"),
        (SolidBlock.GIB_4, "-ms=4g"),
        (SolidBlock.FULL, "-ms=18446744073709551615b"),
    ],
)
def test_build_solid_block_switch(block: SolidBlock, switch: str) -> None:
    spec = SevenZipCommandBuilder().create(
        CreateOptions((Path("source"),), Path("archive"), solid_block=block)
    )
    assert switch in spec.argv


def test_build_volume_command_uses_explicit_bytes() -> None:
    spec = SevenZipCommandBuilder().create(
        CreateOptions((Path("source"),), Path("archive"), volume_size=734_003_200)
    )
    assert "-v734003200b" in spec.argv
    assert "archive.7z" in spec.argv


def test_build_extract_command_with_password() -> None:
    spec = SevenZipCommandBuilder("7z").extract(
        ExtractOptions(
            Path("/tmp/data.7z"),
            Path("/tmp/output folder"),
            overwrite=OverwriteMode.SKIP,
            password="secret",
        )
    )
    assert spec.argv[:2] == ("7z", "x")
    assert "-o/tmp/output folder" in spec.argv
    assert "-aos" in spec.argv
    assert spec.argv[-2:] == ("--", "/tmp/data.7z")
    assert "-p" not in spec.argv
    assert spec.stdin_text == "secret\n"


def test_build_test_command_without_password() -> None:
    spec = SevenZipCommandBuilder().test(IntegrityTestOptions(Path("data.zip")))
    assert spec.argv[:2] == ("7z", "t")
    assert spec.argv[-2:] == ("--", "data.zip")
    assert "-p" not in spec.argv
    assert spec.stdin_text is None
