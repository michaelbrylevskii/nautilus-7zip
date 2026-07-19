# ruff: noqa: E402
from __future__ import annotations

import pytest

gi = pytest.importorskip("gi")
try:
    gi.require_version("Adw", "1")
    gi.require_version("Gtk", "4.0")
except ValueError:
    pytest.skip("GTK 4/libadwaita introspection data is unavailable", allow_module_level=True)

import nautilus_7zip.application as application_module
from nautilus_7zip.commands import CommandSpec


@pytest.mark.gtk
def test_startup_error_is_presented_before_any_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[tuple[object, str]] = []

    class FakeApplication:
        startup_error = "backend missing"
        builder = None

    monkeypatch.setattr(
        application_module,
        "_show_standalone_error",
        lambda application, message: received.append((application, message)),
    )
    application = FakeApplication()

    application_module.NautilusSevenZipApplication.do_activate(application)  # type: ignore[arg-type]

    assert received == [(application, "backend missing")]


@pytest.mark.gtk
def test_progress_window_is_created_before_form_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    app = object()
    specs = [CommandSpec(("7z", "i"))]

    class FakeProgress:
        def __init__(self, received_app: object, received_specs: list[CommandSpec]) -> None:
            assert received_app is app
            assert received_specs is specs
            events.append("create-progress")

        def start(self) -> None:
            events.append("start-progress")

    class FakeForm:
        def get_application(self) -> object:
            events.append("get-application")
            return app

        def close(self) -> None:
            events.append("close-form")

    monkeypatch.setattr(application_module, "ProgressWindow", FakeProgress)
    application_module._FormWindow.replace_with_progress(FakeForm(), specs)  # type: ignore[arg-type]

    assert events == [
        "get-application",
        "create-progress",
        "close-form",
        "start-progress",
    ]


@pytest.mark.gtk
def test_missing_application_does_not_close_form() -> None:
    class DetachedForm:
        closed = False

        def get_application(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    form = DetachedForm()
    with pytest.raises(RuntimeError, match="Application is not available"):
        application_module._FormWindow.replace_with_progress(form, [])  # type: ignore[arg-type]
    assert not form.closed
