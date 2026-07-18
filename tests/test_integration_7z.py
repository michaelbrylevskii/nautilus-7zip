import shutil
from pathlib import Path

import pytest

from nautilus_7zip.commands import SevenZipCommandBuilder
from nautilus_7zip.models import CreateOptions, ExtractOptions, IntegrityTestOptions
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
