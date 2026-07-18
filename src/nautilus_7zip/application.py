# ruff: noqa: E402
"""GTK 4/libadwaita helper application.

The Nautilus extension deliberately launches this module out of process so a
UI or backend failure cannot take down the file manager itself.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk

from .commands import CommandSpec, SevenZipCommandBuilder
from .i18n import _
from .models import (
    ArchiveFormat,
    CompressionLevel,
    CreateOptions,
    ExtractOptions,
    IntegrityTestOptions,
    OverwriteMode,
)
from .paths import archive_stem, common_parent, suggested_archive_name, unique_path
from .runner import OperationHandle, RunResult, SubprocessRunner

APP_ID = "io.github.nautilus_7zip.Nautilus7Zip"


class NautilusSevenZipApplication(Adw.Application):
    def __init__(self, *, action: str, paths: tuple[Path, ...], sevenzip: str) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.action = action
        self.paths = paths
        self.builder = SevenZipCommandBuilder(sevenzip)

    def do_activate(self) -> None:
        if self.action == "create":
            CreateArchiveWindow(self, self.paths, self.builder).present()
            return
        if self.action == "quick-create-7z":
            self._quick_create(ArchiveFormat.SEVEN_ZIP)
            return
        if self.action == "quick-create-zip":
            self._quick_create(ArchiveFormat.ZIP)
            return

        if len(self.paths) != 1:
            _show_standalone_error(self, _("Extraction and testing require one archive."))
            return

        archive = self.paths[0]
        if self.action == "extract":
            ExtractArchiveWindow(self, archive, self.builder).present()
        elif self.action == "extract-here":
            options = ExtractOptions(archive, archive.parent, OverwriteMode.AUTO_RENAME)
            _present_progress(self, [self.builder.extract(options)])
        elif self.action == "extract-to-folder":
            destination = unique_path(archive.parent / archive_stem(archive))
            options = ExtractOptions(archive, destination, OverwriteMode.AUTO_RENAME)
            _present_progress(self, [self.builder.extract(options)])
        elif self.action == "test":
            _present_progress(self, [self.builder.test(IntegrityTestOptions(archive))])

    def _quick_create(self, archive_format: ArchiveFormat) -> None:
        directory = common_parent(self.paths)
        name = suggested_archive_name(self.paths) + archive_format.suffix
        output = unique_path(directory / name)
        options = CreateOptions(
            self.paths,
            output,
            archive_format=archive_format,
            level=CompressionLevel.NORMAL,
            solid=archive_format is ArchiveFormat.SEVEN_ZIP,
        )
        _present_progress(self, [self.builder.create(options)])


class _FormWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, *, title: str) -> None:
        super().__init__(application=application, title=title)
        self.set_default_size(680, -1)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.form = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
        )
        scroller = Gtk.ScrolledWindow(child=self.form)
        scroller.set_propagate_natural_height(True)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

    def add_field(self, label: str, widget: Gtk.Widget) -> None:
        caption = Gtk.Label(label=label, xalign=0)
        caption.add_css_class("heading")
        self.form.append(caption)
        self.form.append(widget)

    def add_path_field(self, label: str, initial: Path) -> Gtk.Entry:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry = Gtk.Entry(text=str(initial), hexpand=True)
        browse = Gtk.Button(label=_("Browse…"))
        browse.connect("clicked", self._choose_folder, entry)
        row.append(entry)
        row.append(browse)
        self.add_field(label, row)
        return entry

    def _choose_folder(self, _button: Gtk.Button, entry: Gtk.Entry) -> None:
        dialog = Gtk.FileDialog(title=_("Select a folder"), modal=True)
        current = Path(entry.get_text()).expanduser()
        if current.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(current)))
        dialog.select_folder(self, None, self._folder_selected, entry)

    def _folder_selected(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
        entry: Gtk.Entry,
    ) -> None:
        try:
            selected = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        path = selected.get_path()
        if path is not None:
            entry.set_text(path)

    def show_error(self, message: str) -> None:
        dialog = Adw.AlertDialog(heading=_("Unable to start operation"), body=message)
        dialog.add_response("close", _("Close"))
        dialog.present(self)

    def replace_with_progress(self, specs: list[CommandSpec]) -> None:
        """Create the next window before detaching this one from the app."""

        application = self.get_application()
        if application is None:
            raise RuntimeError("Application is not available")
        progress = ProgressWindow(application, specs)
        self.close()
        progress.start()


class CreateArchiveWindow(_FormWindow):
    def __init__(
        self,
        application: Adw.Application,
        paths: tuple[Path, ...],
        builder: SevenZipCommandBuilder,
    ) -> None:
        super().__init__(application, title=_("Create archive"))
        self.paths = paths
        self.builder = builder

        self.destination = self.add_path_field(_("Destination"), common_parent(paths))
        self.name = Gtk.Entry(text=suggested_archive_name(paths), hexpand=True)
        self.add_field(_("Archive name"), self.name)

        self.format = Gtk.ComboBoxText()
        self.format.append(ArchiveFormat.SEVEN_ZIP.value, "7z")
        self.format.append(ArchiveFormat.ZIP.value, "ZIP")
        self.format.set_active_id(ArchiveFormat.SEVEN_ZIP.value)
        self.format.connect("changed", self._format_changed)
        self.add_field(_("Format"), self.format)

        self.level = Gtk.ComboBoxText()
        for level, label in (
            (CompressionLevel.STORE, _("Store (no compression)")),
            (CompressionLevel.FASTEST, _("Fastest")),
            (CompressionLevel.FAST, _("Fast")),
            (CompressionLevel.NORMAL, _("Normal")),
            (CompressionLevel.MAXIMUM, _("Maximum")),
            (CompressionLevel.ULTRA, _("Ultra")),
        ):
            self.level.append(str(int(level)), label)
        self.level.set_active_id(str(int(CompressionLevel.NORMAL)))
        self.add_field(_("Compression level"), self.level)

        self.password = Gtk.PasswordEntry(show_peek_icon=True)
        self.add_field(_("Password (optional)"), self.password)

        switches = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.solid = _switch_row(_("Solid archive"), True)
        self.encrypt_headers = _switch_row(_("Encrypt file names"), False)
        self.verify = _switch_row(_("Test archive after creation"), True)
        switches.append(self.solid)
        switches.append(self.encrypt_headers)
        switches.append(self.verify)
        self.add_field(_("Options"), switches)

        create = Gtk.Button(label=_("Create archive"), halign=Gtk.Align.END)
        create.add_css_class("suggested-action")
        create.connect("clicked", self._create)
        self.form.append(create)

    def _format_changed(self, _combo: Gtk.ComboBoxText) -> None:
        is_7z = self.format.get_active_id() == ArchiveFormat.SEVEN_ZIP.value
        self.solid.set_sensitive(is_7z)
        self.encrypt_headers.set_sensitive(is_7z)
        if not is_7z:
            _row_switch(self.encrypt_headers).set_active(False)

    def _create(self, _button: Gtk.Button) -> None:
        name = self.name.get_text().strip()
        destination = Path(self.destination.get_text()).expanduser()
        if not name:
            self.show_error(_("Archive name must not be empty."))
            return
        if not destination.is_dir():
            self.show_error(_("Destination folder does not exist."))
            return

        archive_format = ArchiveFormat(self.format.get_active_id())
        password = self.password.get_text() or None
        encrypt_headers = _row_switch(self.encrypt_headers).get_active()
        if encrypt_headers and not password:
            self.show_error(_("A password is required to encrypt file names."))
            return

        options = CreateOptions(
            sources=self.paths,
            output=destination / name,
            archive_format=archive_format,
            level=CompressionLevel(int(self.level.get_active_id())),
            solid=_row_switch(self.solid).get_active(),
            password=password,
            encrypt_headers=encrypt_headers,
            verify=_row_switch(self.verify).get_active(),
        )
        specs = [self.builder.create(options)]
        if options.verify:
            output = options.output
            if not output.name.casefold().endswith(options.archive_format.suffix):
                output = output.with_name(output.name + options.archive_format.suffix)
            specs.append(self.builder.test(IntegrityTestOptions(output, password)))
        self.replace_with_progress(specs)


class ExtractArchiveWindow(_FormWindow):
    def __init__(
        self,
        application: Adw.Application,
        archive: Path,
        builder: SevenZipCommandBuilder,
    ) -> None:
        super().__init__(application, title=_("Extract archive"))
        self.archive = archive
        self.builder = builder

        destination = unique_path(archive.parent / archive_stem(archive))
        self.destination = self.add_path_field(_("Destination"), destination)
        self.password = Gtk.PasswordEntry(show_peek_icon=True)
        self.add_field(_("Password (if required)"), self.password)

        self.overwrite = Gtk.ComboBoxText()
        self.overwrite.append(OverwriteMode.AUTO_RENAME.name, _("Rename extracted files"))
        self.overwrite.append(OverwriteMode.OVERWRITE.name, _("Overwrite existing files"))
        self.overwrite.append(OverwriteMode.SKIP.name, _("Skip existing files"))
        self.overwrite.set_active_id(OverwriteMode.AUTO_RENAME.name)
        self.add_field(_("If a file already exists"), self.overwrite)

        extract = Gtk.Button(label=_("Extract"), halign=Gtk.Align.END)
        extract.add_css_class("suggested-action")
        extract.connect("clicked", self._extract)
        self.form.append(extract)

    def _extract(self, _button: Gtk.Button) -> None:
        destination = Path(self.destination.get_text()).expanduser()
        parent = destination.parent
        if not parent.is_dir():
            self.show_error(_("The parent of the destination folder does not exist."))
            return
        overwrite = OverwriteMode[self.overwrite.get_active_id()]
        options = ExtractOptions(
            archive=self.archive,
            destination=destination,
            overwrite=overwrite,
            password=self.password.get_text() or None,
        )
        self.replace_with_progress([self.builder.extract(options)])


class ProgressWindow(Adw.ApplicationWindow):
    _MAX_LOG_CHARS = 100_000

    def __init__(self, application: Adw.Application, specs: list[CommandSpec]) -> None:
        super().__init__(application=application, title=_("7-Zip operation"))
        self.set_default_size(680, 220)
        self._specs = deque(specs)
        self._handle: OperationHandle | None = None
        self._runner = SubprocessRunner(dispatcher=GLib.idle_add)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=20,
            margin_bottom=20,
            margin_start=20,
            margin_end=20,
        )
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("title-3")
        self.progress = Gtk.ProgressBar(show_text=True)
        self.log = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.log.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log.set_left_margin(8)
        self.log.set_right_margin(8)
        self.log.set_top_margin(8)
        self.log.set_bottom_margin(8)
        log_scroller = Gtk.ScrolledWindow(child=self.log)
        log_scroller.set_has_frame(True)
        log_scroller.set_min_content_height(240)
        log_scroller.set_vexpand(True)
        self.details = Gtk.Expander(label=_("Details"), expanded=False)
        self.details.set_child(log_scroller)
        self.details.set_vexpand(True)
        content.append(self.status)
        content.append(self.progress)
        content.append(self.details)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END)
        self.cancel_button = Gtk.Button(label=_("Cancel"))
        self.cancel_button.connect("clicked", self._cancel)
        self.close_button = Gtk.Button(label=_("Close"), sensitive=False)
        self.close_button.connect("clicked", lambda _button: self.close())
        controls.append(self.cancel_button)
        controls.append(self.close_button)
        content.append(controls)
        toolbar.set_content(content)
        self.set_content(toolbar)

    def start(self) -> None:
        self.present()
        self._run_next()

    def _run_next(self) -> None:
        if not self._specs:
            self.status.set_label(_("Operation completed successfully"))
            self.progress.set_fraction(1.0)
            self.progress.set_text("100%")
            self._finish()
            return
        spec = self._specs.popleft()
        self.status.set_label(spec.title)
        self.progress.set_fraction(0.0)
        self.progress.set_text("")
        self._handle = self._runner.start(
            spec,
            on_output=self._append_output,
            on_progress=self._set_progress,
            on_complete=self._completed,
        )

    def _append_output(self, text: str) -> None:
        buffer = self.log.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        overflow = buffer.get_char_count() - self._MAX_LOG_CHARS
        if overflow > 0:
            buffer.delete(buffer.get_start_iter(), buffer.get_iter_at_offset(overflow))
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.log.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        buffer.delete_mark(mark)

    def _set_progress(self, percent: int) -> None:
        self.progress.set_fraction(percent / 100)
        self.progress.set_text(f"{percent}%")

    def _completed(self, result: RunResult) -> None:
        if result.succeeded:
            self._run_next()
            return
        if result.cancelled:
            self.status.set_label(_("Operation cancelled"))
        else:
            detail = result.error or _("7-Zip exited with status {status}.").format(
                status=result.returncode
            )
            self.status.set_label(_("Operation failed"))
            self._append_output("\n" + detail + "\n")
            self.details.set_expanded(True)
        self._finish()

    def _cancel(self, _button: Gtk.Button) -> None:
        if self._handle is not None:
            self._handle.cancel()
        self.cancel_button.set_sensitive(False)
        self.status.set_label(_("Cancelling…"))

    def _finish(self) -> None:
        self.cancel_button.set_visible(False)
        self.close_button.set_sensitive(True)


def _switch_row(label: str, active: bool) -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.append(Gtk.Label(label=label, xalign=0, hexpand=True))
    row.append(Gtk.Switch(active=active, valign=Gtk.Align.CENTER))
    return row


def _row_switch(row: Gtk.Box) -> Gtk.Switch:
    widget = row.get_last_child()
    if not isinstance(widget, Gtk.Switch):
        raise TypeError("Switch row does not contain a Gtk.Switch")
    return widget


def _present_progress(application: Adw.Application | None, specs: list[CommandSpec]) -> None:
    if application is None:
        raise RuntimeError("Application is not available")
    ProgressWindow(application, specs).start()


def _show_standalone_error(application: Adw.Application, message: str) -> None:
    window = Adw.ApplicationWindow(application=application, title=_("7-Zip for Nautilus"))
    window.set_default_size(440, 160)
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
        margin_top=24,
        margin_bottom=24,
        margin_start=24,
        margin_end=24,
    )
    box.append(Gtk.Label(label=message, wrap=True))
    close = Gtk.Button(label=_("Close"), halign=Gtk.Align.END)
    close.connect("clicked", lambda _button: window.close())
    box.append(close)
    window.set_content(box)
    window.present()
