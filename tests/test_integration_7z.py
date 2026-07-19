import shutil
from hashlib import sha256
from pathlib import Path

import pytest

from nautilus_7zip.commands import SevenZipCommandBuilder
from nautilus_7zip.models import (
    ArchiveFormat,
    CreateOptions,
    ExtractOptions,
    IntegrityTestOptions,
    SolidBlock,
)
from nautilus_7zip.runner import SubprocessRunner


@pytest.mark.integration
def test_encrypted_create_test_extract_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = shutil.which("7z")
    if executable is None:
        pytest.skip("7z is not installed")

    source = tmp_path / "source"
    source.mkdir()
    payload = source / "payload.txt"
    payload.write_text("Nautilus 7-Zip integration test\n", encoding="utf-8")
    archive = tmp_path / "encrypted.7z"
    destination = tmp_path / "extracted"
    password = "integration-test-password"
    monkeypatch.chdir(tmp_path)

    builder = SevenZipCommandBuilder(executable)
    runner = SubprocessRunner()
    create = builder.create(
        CreateOptions(
            (Path("source/payload.txt"),),
            archive,
            password=password,
            encrypt_headers=True,
        )
    )

    assert runner.run_blocking(create).succeeded
    assert runner.run_blocking(
        builder.test(IntegrityTestOptions(archive, password))
    ).succeeded
    assert not runner.run_blocking(
        builder.test(IntegrityTestOptions(archive, "incorrect-password"))
    ).succeeded
    assert runner.run_blocking(
        builder.extract(ExtractOptions(archive, destination, password=password))
    ).succeeded
    assert (destination / "source/payload.txt").read_text(encoding="utf-8") == payload.read_text(
        encoding="utf-8"
    )


@pytest.mark.integration
@pytest.mark.parametrize("archive_format", [ArchiveFormat.SEVEN_ZIP, ArchiveFormat.ZIP])
def test_multivolume_create_test_extract_round_trip(
    tmp_path: Path,
    archive_format: ArchiveFormat,
) -> None:
    executable = shutil.which("7z")
    if executable is None:
        pytest.skip("7z is not installed")

    source = tmp_path / "payload.bin"
    original = b"".join(sha256(str(index).encode()).digest() for index in range(8192))
    source.write_bytes(original)
    destination = tmp_path / "extracted"
    options = CreateOptions(
        (source,),
        tmp_path / f"split-backup-{archive_format.value}",
        archive_format=archive_format,
        solid_block=SolidBlock.FULL if archive_format is ArchiveFormat.SEVEN_ZIP else None,
        volume_size=32 * 1024,
    )
    builder = SevenZipCommandBuilder(executable)
    runner = SubprocessRunner()

    assert runner.run_blocking(builder.create(options)).succeeded
    assert options.verification_path.exists()
    assert options.archive_path.with_name(options.archive_path.name + ".002").exists()
    test_options = IntegrityTestOptions(options.verification_path)
    assert runner.run_blocking(builder.test(test_options)).succeeded
    assert runner.run_blocking(
        builder.extract(ExtractOptions(options.verification_path, destination))
    ).succeeded
    assert (destination / source.name).read_bytes() == original
