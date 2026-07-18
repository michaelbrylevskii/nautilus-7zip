from pathlib import Path

import pytest

import nautilus_7zip.i18n as i18n


def test_locale_directories_honor_override_and_remove_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NAUTILUS_7ZIP_LOCALE_DIR", "/custom/locale")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/test")))
    directories = i18n.locale_directories()
    assert directories[0] == Path("/custom/locale")
    assert Path("/home/test/.local/share/locale") in directories
    assert len(directories) == len(set(directories))


def test_locale_directories_work_without_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NAUTILUS_7ZIP_LOCALE_DIR", raising=False)
    assert i18n.locale_directories()[-1] == Path("/usr/share/locale")


def test_translation_falls_back_to_english(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(i18n, "locale_directories", lambda: (Path("/does/not/exist"),))
    translator = i18n.translation()
    assert translator.gettext("Create archive") == "Create archive"


def test_translation_uses_first_available_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    attempts: list[Path] = []

    def fake_translation(_domain: str, *, localedir: Path):
        attempts.append(localedir)
        if len(attempts) == 1:
            raise FileNotFoundError
        return sentinel

    monkeypatch.setattr(i18n, "locale_directories", lambda: (Path("/one"), Path("/two")))
    monkeypatch.setattr(i18n.gettext, "translation", fake_translation)
    assert i18n.translation() is sentinel
    assert attempts == [Path("/one"), Path("/two")]
