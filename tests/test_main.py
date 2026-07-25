from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import nautilus_7zip.main as main_module
from nautilus_7zip.backend import SevenZipBackend, SevenZipBackendError
from nautilus_7zip.diagnostics import ToolkitVersions


def test_parser_accepts_supported_action() -> None:
    namespace = main_module.build_parser().parse_args(["create", "/tmp/source"])
    assert namespace.action == "create"
    assert namespace.paths == [Path("/tmp/source")]
    assert namespace.sevenzip is None


def test_parser_accepts_desktop_open_action() -> None:
    namespace = main_module.build_parser().parse_args(["open", "/tmp/source"])
    assert namespace.action == "open"


def test_parser_accepts_diagnostics_without_paths() -> None:
    namespace = main_module.build_parser().parse_args(["diagnostics"])
    assert namespace.action == "diagnostics"
    assert namespace.paths == []


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


def test_desktop_open_extracts_single_archive_and_first_volume(tmp_path: Path) -> None:
    archive = tmp_path / "backup.7z"
    first_volume = tmp_path / "backup.zip.001"
    archive.touch()
    first_volume.touch()

    assert main_module.resolve_open_action((archive,)) == "extract"
    assert main_module.resolve_open_action((first_volume,)) == "extract"


def test_desktop_open_creates_for_other_selections(tmp_path: Path) -> None:
    regular_file = tmp_path / "document.txt"
    archive_named_directory = tmp_path / "folder.zip"
    archive = tmp_path / "backup.7z"
    regular_file.touch()
    archive_named_directory.mkdir()
    archive.touch()

    assert main_module.resolve_open_action((regular_file,)) == "create"
    assert main_module.resolve_open_action((archive_named_directory,)) == "create"
    assert main_module.resolve_open_action((archive, regular_file)) == "create"


def test_main_reports_missing_7zip(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    received: dict[str, object] = {}

    class FakeApplication:
        def __init__(self, **kwargs: object) -> None:
            received.update(kwargs)

        def run(self, argv: list[str]) -> int:
            received["argv"] = argv
            return 0

    module = types.ModuleType("nautilus_7zip.application")
    module.NautilusSevenZipApplication = FakeApplication  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "nautilus_7zip.application", module)
    monkeypatch.setattr(
        main_module,
        "resolve_sevenzip",
        lambda _executable: (_ for _ in ()).throw(
            SevenZipBackendError("backend missing", exit_code=127)
        ),
    )

    result = main_module.main(["create", "/tmp/source", "--sevenzip", "missing-command"])

    assert result == 127
    assert "backend missing" in capsys.readouterr().err
    assert received == {
        "action": "create",
        "paths": (Path("/tmp/source"),),
        "startup_error": "backend missing",
        "backend_override": True,
        "argv": ["nautilus-7zip"],
    }


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
    backend = SevenZipBackend("/bin/7zz", "7zz", "25.01")
    monkeypatch.setattr(main_module, "resolve_sevenzip", lambda executable: backend)

    assert main_module.main(["test", "/tmp/archive.7z", "--sevenzip", "7zz"]) == 23
    assert received == {
        "action": "test",
        "paths": (Path("/tmp/archive.7z"),),
        "backend": backend,
        "backend_override": True,
        "argv": ["nautilus-7zip"],
    }


def test_main_dispatches_desktop_open_to_extraction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    received: dict[str, object] = {}

    class FakeApplication:
        def __init__(self, **kwargs: object) -> None:
            received.update(kwargs)

        def run(self, argv: list[str]) -> int:
            received["argv"] = argv
            return 0

    module = types.ModuleType("nautilus_7zip.application")
    module.NautilusSevenZipApplication = FakeApplication  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "nautilus_7zip.application", module)
    backend = SevenZipBackend("/usr/bin/7z", "7z", "26.02")
    monkeypatch.setattr(main_module, "resolve_sevenzip", lambda _executable: backend)
    archive = tmp_path / "backup.tar.xz"
    archive.touch()

    assert main_module.main(["open", str(archive)]) == 0
    assert received["action"] == "extract"
    assert received["paths"] == (archive,)


def test_main_turns_invalid_selection_into_parser_error() -> None:
    with pytest.raises(SystemExit) as error:
        main_module.main(["create"])
    assert error.value.code == 2


def test_main_prints_diagnostics_without_starting_gtk(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    backend = SevenZipBackend("/usr/bin/7z", "7z", "26.02")
    received: dict[str, object] = {}
    monkeypatch.setattr(main_module, "resolve_sevenzip", lambda executable: backend)
    monkeypatch.setattr(
        main_module,
        "detect_toolkit_versions",
        lambda: ToolkitVersions(gtk=(4, 14, 0), libadwaita=(1, 5, 0)),
    )
    monkeypatch.setattr(main_module, "detect_nautilus_api", lambda: "4.1")

    def collect(context: object) -> str:
        received["context"] = context
        return "diagnostic report\n"

    monkeypatch.setattr(main_module, "collect_diagnostics", collect)

    assert main_module.main(["diagnostics"]) == 0
    assert capsys.readouterr().out == "diagnostic report\n"
    context = received["context"]
    assert context.backend is backend  # type: ignore[attr-defined]
    assert context.backend_error is None  # type: ignore[attr-defined]
    assert context.backend_override is False  # type: ignore[attr-defined]


def test_diagnostics_reports_backend_failure_and_rejects_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}
    monkeypatch.setattr(
        main_module,
        "resolve_sevenzip",
        lambda _executable: (_ for _ in ()).throw(
            SevenZipBackendError("backend missing", exit_code=127)
        ),
    )
    monkeypatch.setattr(main_module, "detect_toolkit_versions", ToolkitVersions)
    monkeypatch.setattr(main_module, "detect_nautilus_api", lambda: None)
    monkeypatch.setattr(
        main_module,
        "collect_diagnostics",
        lambda context: received.setdefault("context", context) and "report\n",
    )

    assert main_module.main(["diagnostics", "--sevenzip", "missing"]) == 0
    context = received["context"]
    assert context.backend is None  # type: ignore[attr-defined]
    assert context.backend_error == "backend missing"  # type: ignore[attr-defined]
    assert context.backend_override is True  # type: ignore[attr-defined]

    with pytest.raises(SystemExit) as error:
        main_module.main(["diagnostics", "/private/source"])
    assert error.value.code == 2
