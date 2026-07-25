# ruff: noqa: E402
from __future__ import annotations

import pytest

gi = pytest.importorskip("gi")
try:
    gi.require_version("Adw", "1")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Gtk", "4.0")
except ValueError:
    pytest.skip("GTK 4/libadwaita introspection data is unavailable", allow_module_level=True)

from gi.repository import Adw, Gdk, Gtk

import nautilus_7zip.application as application_module

pytestmark = pytest.mark.gtk


@pytest.fixture(scope="module", autouse=True)
def initialize_adwaita() -> None:
    Adw.init()
    assert Gdk.Display.get_default() is not None, (
        "GTK widget tests require a display; use xvfb-run in a headless environment"
    )


def test_simple_combo_uses_separate_selected_and_popup_factories() -> None:
    row = application_module._combo_row("Compression level", ["Fast", "Normal"])
    selected_factory = row.get_factory()
    list_factory = row.get_list_factory()

    assert selected_factory is not None
    assert list_factory is not None
    assert list_factory is not selected_factory

    selected_item = Gtk.ListItem()
    selected_factory.emit("setup", selected_item)
    selected_label = selected_item.get_child()
    assert isinstance(selected_label, Gtk.Label)
    assert selected_label.get_xalign() == 1
    assert selected_label.get_halign() == Gtk.Align.END

    popup_item = Gtk.ListItem()
    list_factory.emit("setup", popup_item)
    popup_label = popup_item.get_child()
    assert isinstance(popup_label, Gtk.Label)
    assert popup_label.get_xalign() == 0
    assert popup_label.get_halign() == Gtk.Align.FILL
