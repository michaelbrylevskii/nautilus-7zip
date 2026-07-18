from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import nautilus_7zip.main as main_module


def test_parser_accepts_supported_action() -> None:
    namespace = main_module.build_parser().parse_args(["create", "/tmp/source"])
    assert namespace.action == "create"
    assert namespace.paths == [Path("/tmp/source")]
    assert namespace.sevenzip == "7z"


def test_resolve_direct_paths() -> None:
    assert main_module.resolve_paths([Path("one"), Path("two")], None) == (
        Path("one"),
        Path("two"),
    )


def test_resolve_selection_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "selection.json"
    manifest.write_text('["/tmp/one"]', encoding="utf-8")
    assert main_module.resolve_paths([], manifest) == (Path("/tmp/one"),)
    assert not manifest.exists()


def test_resolve_rejects_ambiguous_and_empty_inputs(tmp_path: Path) -> None:
    manifest = tmp_path / "selection.json"
    manifest.write_text('["/tmp/one"]', encoding="utf-8")
    with pytest.raises(ValueError, match="not both"):
        main_module.resolve_paths([Path("other")], manifest)
    with pytest.raises(ValueError, match="At least one"):
        main_module.resolve_paths([], None)


def test_main_reports_missing_7zip(capsys: pytest.CaptureFixture[str]) -> None:
    result = main_module.main(["create", "/tmp/source", "--sevenzip", "missing-command"])
    assert result == 127
    assert "not found" in capsys.readouterr().err


def test_main_runs_application(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    class FakeApplication:
        def __init__(self, **kwargs: object) -> None:
            received.update(kwargs)

        def run(self, argv: list[str]) -> int:
            received["argv"] = argv
            return 23

    module = types.ModuleType("nautilus_7zip.application")
    module.NautilusSevenZipApplication = FakeApplication  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "nautilus_7zip.application", module)
    monkeypatch.setattr(main_module.shutil, "which", lambda executable: f"/bin/{executable}")

    assert main_module.main(["test", "/tmp/archive.7z"]) == 23
    assert received == {
        "action": "test",
        "paths": (Path("/tmp/archive.7z"),),
        "sevenzip": "/bin/7z",
        "argv": ["nautilus-7zip"],
    }


def test_main_turns_invalid_selection_into_parser_error() -> None:
    with pytest.raises(SystemExit) as error:
        main_module.main(["create"])
    assert error.value.code == 2
