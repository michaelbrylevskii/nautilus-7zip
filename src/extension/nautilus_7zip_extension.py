"""Nautilus menu provider for 7-Zip for Nautilus.

The module filename intentionally differs from the ``nautilus_7zip`` package
name; nautilus-python adds this directory to ``sys.path`` while loading it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import gi

try:
    gi.require_version("Nautilus", "4.1")
except ValueError:
    gi.require_version("Nautilus", "4.0")

from gi.repository import GObject, Nautilus

from nautilus_7zip.i18n import _
from nautilus_7zip.labels import escape_menu_mnemonics
from nautilus_7zip.paths import archive_stem, is_archive, suggested_archive_name
from nautilus_7zip.selection import write_selection_file


class NautilusSevenZipExtension(GObject.GObject, Nautilus.MenuProvider):
    """Add a conditional 7-Zip submenu for local selections."""

    def get_file_items(self, files: list[Nautilus.FileInfo]) -> list[Nautilus.MenuItem]:
        paths = self._local_paths(files)
        if not paths:
            return []

        submenu = Nautilus.Menu()
        base_name = suggested_archive_name(paths)
        self._append(submenu, "create", _("Create archive…"), paths)
        self._append(
            submenu,
            "quick-create-7z",
            _("Create {name}.7z").format(name=base_name),
            paths,
        )
        self._append(
            submenu,
            "quick-create-zip",
            _("Create {name}.zip").format(name=base_name),
            paths,
        )

        if len(paths) == 1 and is_archive(paths[0]):
            archive = paths[0]
            self._append(submenu, "extract", _("Extract…"), paths)
            self._append(submenu, "extract-here", _("Extract here"), paths)
            self._append(
                submenu,
                "extract-to-folder",
                _("Extract to {name}/").format(name=archive_stem(archive)),
                paths,
            )
            self._append(submenu, "test", _("Test archive"), paths)

        root = Nautilus.MenuItem(
            name="NautilusSevenZip::Root",
            label=escape_menu_mnemonics(_("7-Zip")),
        )
        root.set_submenu(submenu)
        return [root]

    @staticmethod
    def _local_paths(files: list[Nautilus.FileInfo]) -> tuple[Path, ...]:
        if not files:
            return ()
        paths = []
        for item in files:
            if item.get_uri_scheme() != "file":
                return ()
            raw_path = item.get_location().get_path()
            if raw_path is None:
                return ()
            paths.append(Path(raw_path))
        return tuple(paths)

    def _append(
        self,
        menu: Nautilus.Menu,
        action: str,
        label: str,
        paths: tuple[Path, ...],
    ) -> None:
        item = Nautilus.MenuItem(
            name=f"NautilusSevenZip::{action}",
            label=escape_menu_mnemonics(label),
        )
        item.connect("activate", self._activate, action, paths)
        menu.append_item(item)

    @staticmethod
    def _activate(
        _item: Nautilus.MenuItem,
        action: str,
        paths: tuple[Path, ...],
    ) -> None:
        helper = os.environ.get("NAUTILUS_7ZIP_HELPER") or shutil.which("nautilus-7zip")
        if helper is None:
            return
        manifest = write_selection_file(paths)
        try:
            subprocess.Popen(
                [helper, action, "--selection-file", str(manifest)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        except OSError:
            manifest.unlink(missing_ok=True)
