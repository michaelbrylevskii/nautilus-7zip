import json
import stat
from pathlib import Path

import pytest

from nautilus_7zip.selection import read_selection_file, write_selection_file


def test_selection_round_trip_and_removal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    selected = (Path("/tmp/alpha beta"), Path("/tmp/данные"))
    manifest = write_selection_file(selected)

    mode = stat.S_IMODE(manifest.stat().st_mode)
    assert mode == 0o600
    assert read_selection_file(manifest) == selected
    assert not manifest.exists()


def test_read_can_preserve_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "selection.json"
    manifest.write_text('["/tmp/file"]', encoding="utf-8")
    assert read_selection_file(manifest, remove=False) == (Path("/tmp/file"),)
    assert manifest.exists()


@pytest.mark.parametrize("value", [[], {}, [""], [1], ["ok", None]])
def test_invalid_manifest_is_rejected_and_removed(tmp_path: Path, value: object) -> None:
    manifest = tmp_path / "selection.json"
    manifest.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="Selection manifest"):
        read_selection_file(manifest)
    assert not manifest.exists()


def test_write_rejects_empty_selection() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        write_selection_file(())


def test_write_removes_manifest_on_serialization_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("serialization failed")

    monkeypatch.setattr(json, "dump", fail)
    with pytest.raises(RuntimeError, match="serialization failed"):
        write_selection_file((Path("/tmp/file"),))
    assert list(tmp_path.iterdir()) == []
