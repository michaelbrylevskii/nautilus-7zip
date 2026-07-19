from pathlib import Path

import pytest

from nautilus_7zip.paths import (
    archive_stem,
    common_parent,
    is_archive,
    output_path_exists,
    suggested_archive_name,
    unique_path,
)


@pytest.mark.parametrize(
    "name",
    [
        "backup.7z",
        "DATA.ZIP",
        "source.tar.gz",
        "image.iso",
        "logs.tar.zst",
        "backup.7z.001",
        "BACKUP.ZIP.001",
    ],
)
def test_archive_detection(name: str) -> None:
    assert is_archive(Path(name))


def test_non_archive_detection() -> None:
    assert not is_archive(Path("document.txt"))


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("source.tar.gz", "source"),
        ("BACKUP.7Z", "BACKUP"),
        ("backup.7z.001", "backup"),
        ("BACKUP.ZIP.001", "BACKUP"),
        ("document.txt", "document"),
        (".zip", "Archive"),
    ],
)
def test_archive_stem(name: str, expected: str) -> None:
    assert archive_stem(Path(name)) == expected


def test_suggested_name_for_empty_and_single_selection() -> None:
    assert suggested_archive_name([]) == "Archive"
    assert suggested_archive_name([Path("/data/Project")]) == "Project"


def test_suggested_name_for_multiple_siblings() -> None:
    paths = [Path("/data/photos/a.jpg"), Path("/data/photos/b.jpg")]
    assert suggested_archive_name(paths) == "photos"


def test_suggested_name_for_different_parents() -> None:
    paths = [Path("/one/a"), Path("/two/b")]
    assert suggested_archive_name(paths) == "Archive"


def test_common_parent() -> None:
    assert common_parent([Path("/tmp/a"), Path("/tmp/b")]) == Path("/tmp")


def test_common_parent_falls_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/fake/home")))
    assert common_parent([Path("/a/one"), Path("/b/two")]) == Path("/fake/home")


def test_common_parent_rejects_empty_selection() -> None:
    with pytest.raises(ValueError, match="At least one"):
        common_parent([])


def test_unique_path(tmp_path: Path) -> None:
    original = tmp_path / "archive.tar.gz"
    assert unique_path(original) == original
    original.touch()
    (tmp_path / "archive (1).tar.gz").touch()
    assert unique_path(original) == tmp_path / "archive (2).tar.gz"


def test_unique_path_without_suffix(tmp_path: Path) -> None:
    original = tmp_path / "output"
    original.mkdir()
    assert unique_path(original) == tmp_path / "output (1)"


def test_output_path_exists_checks_first_volume(tmp_path: Path) -> None:
    archive = tmp_path / "backup.7z"
    assert not output_path_exists(archive, split=False)
    assert not output_path_exists(archive, split=True)
    (tmp_path / "backup.7z.001").touch()
    assert not output_path_exists(archive, split=False)
    assert output_path_exists(archive, split=True)


def test_output_path_exists_checks_regular_archive(tmp_path: Path) -> None:
    archive = tmp_path / "backup.zip"
    archive.touch()
    assert output_path_exists(archive, split=False)
    assert output_path_exists(archive, split=True)
