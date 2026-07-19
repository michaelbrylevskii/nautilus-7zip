# ruff: noqa: E402
"""GTK 4/libadwaita helper application.

The Nautilus extension deliberately launches this module out of process so a
UI or backend failure cannot take down the file manager itself.
"""

from __future__ import annotations

import os
import time
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
    SolidBlock,
)
from .paths import (
    archive_stem,
    common_parent,
    output_path_exists,
    suggested_archive_name,
    unique_path,
)
from .progress import format_duration, parse_file_progress
from .runner import OperationHandle, RunResult, SubprocessRunner
from .sizes import parse_binary_size

APP_ID = "io.github.nautilus_7zip.Nautilus7Zip"

_FORMATS = (ArchiveFormat.SEVEN_ZIP, ArchiveFormat.ZIP)
_LEVELS = (
    CompressionLevel.STORE,
    CompressionLevel.FASTEST,
    CompressionLevel.FAST,
    CompressionLevel.NORMAL,
    CompressionLevel.MAXIMUM,
    CompressionLevel.ULTRA,
)
_SOLID_BLOCKS = (
    SolidBlock.AUTO,
    SolidBlock.NON_SOLID,
    SolidBlock.MIB_256,
    SolidBlock.GIB_1,
    SolidBlock.GIB_4,
    SolidBlock.FULL,
)
_CUSTOM_VOLUME = -1
_VOLUME_SIZES = (
    None,
    100 * 1024**2,
    700 * 1024**2,
    2 * 1024**3,
    4095 * 1024**2,
    _CUSTOM_VOLUME,
)
_OVERWRITE_MODES = (
    OverwriteMode.AUTO_RENAME,
    OverwriteMode.OVERWRITE,
    OverwriteMode.SKIP,
)


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
            solid_block=(SolidBlock.AUTO if archive_format is ArchiveFormat.SEVEN_ZIP else None),
        )
        _present_progress(self, [self.builder.create(options)])


class _FormWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        application: Adw.Application,
        *,
        title: str,
        default_height: int,
    ) -> None:
        super().__init__(application=application, title=title)

        toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar(
            show_start_title_buttons=False,
            show_end_title_buttons=False,
        )
        self.header.set_title_widget(Adw.WindowTitle(title=title))
        cancel = Gtk.Button(label=_("Cancel"))
        cancel.connect("clicked", lambda _button: self.close())
        self.header.pack_start(cancel)
        toolbar.add_top_bar(self.header)

        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        self.set_content(toolbar)
        # Set the initial size after attaching the adaptive content. This keeps
        # the full collapsed form visible while PreferencesPage still provides
        # scrolling when the monitor cannot accommodate it.
        self.set_default_size(660, default_height)

    def add_primary_action(self, label: str, callback) -> Gtk.Button:
        button = Gtk.Button(label=label)
        button.add_css_class("suggested-action")
        button.connect("clicked", callback)
        self.header.pack_end(button)
        self.set_default_widget(button)
        return button

    def create_path_row(self, label: str, initial: Path) -> Adw.EntryRow:
        entry = Adw.EntryRow(title=label, text=str(initial), activates_default=True)
        browse = Gtk.Button(
            icon_name="folder-open-symbolic",
            tooltip_text=_("Choose a folder"),
            valign=Gtk.Align.CENTER,
        )
        browse.add_css_class("flat")
        browse.connect("clicked", self._choose_folder, entry)
        entry.add_suffix(browse)
        return entry

    def _choose_folder(self, _button: Gtk.Button, entry: Adw.EntryRow) -> None:
        dialog = Gtk.FileDialog(title=_("Select a folder"), modal=True)
        current = Path(entry.get_text()).expanduser()
        if current.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(current)))
        dialog.select_folder(self, None, self._folder_selected, entry)

    def _folder_selected(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult,
        entry: Adw.EntryRow,
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
        super().__init__(application, title=_("Create Archive"), default_height=680)
        self.paths = paths
        self.builder = builder

        archive_group = Adw.PreferencesGroup(title=_("Archive"))
        self.name = Adw.EntryRow(
            title=_("Archive name"),
            text=suggested_archive_name(paths),
            activates_default=True,
        )
        self.destination = self.create_path_row(_("Destination"), common_parent(paths))
        self.format = _described_combo_row(
            _("Format"),
            [
                ("7Z (.7z)", _("High compression; may require 7-Zip on other systems.")),
                (
                    "ZIP (.zip)",
                    _("Widely compatible; AES-256 encryption may require 7-Zip."),
                ),
            ],
        )
        self.format.connect("notify::selected", self._format_changed)
        self.level = _combo_row(
            _("Compression level"),
            [
                _("Store (no compression)"),
                _("Fastest"),
                _("Fast"),
                _("Normal"),
                _("Maximum"),
                _("Ultra"),
            ],
            selected=_LEVELS.index(CompressionLevel.NORMAL),
        )
        archive_group.add(self.name)
        archive_group.add(self.destination)
        archive_group.add(self.format)
        archive_group.add(self.level)
        self.page.add(archive_group)

        encryption_group = Adw.PreferencesGroup(title=_("Encryption"))
        self.password_protection = Adw.ExpanderRow(
            title=_("Password protection"),
            subtitle=_("Encrypts archive contents with AES-256."),
            show_enable_switch=True,
            enable_expansion=False,
            expanded=False,
        )
        self.password = Adw.PasswordEntryRow(
            title=_("Password"),
            activates_default=True,
        )
        self.confirm_password = Adw.PasswordEntryRow(
            title=_("Confirm password"),
            activates_default=True,
        )
        self.encrypt_headers = Adw.SwitchRow(
            title=_("Encrypt file names"),
            subtitle=_("Hides file names until the password is entered."),
        )
        self.password_protection.add_row(self.password)
        self.password_protection.add_row(self.confirm_password)
        self.password_protection.add_row(self.encrypt_headers)
        encryption_group.add(self.password_protection)
        self.page.add(encryption_group)

        options_group = Adw.PreferencesGroup(title=_("Options"))
        self.verify = Adw.SwitchRow(
            title=_("Verify after creation"),
            subtitle=_("Tests archive integrity when compression finishes."),
            active=True,
        )
        self.advanced = Adw.ExpanderRow(title=_("Advanced Options"), subtitle_lines=2)
        hardware_threads = max(1, os.cpu_count() or 1)
        self.threads = _combo_row(
            _("CPU threads"),
            [
                _("Auto ({count})").format(count=hardware_threads),
                *map(str, range(1, hardware_threads + 1)),
            ],
            subtitle=_("Limits CPU usage. Auto uses available processors."),
        )
        self.solid_block = _described_combo_row(
            _("Solid block"),
            [
                (_("Auto"), _("Let 7-Zip choose the block size.")),
                (_("Non-solid"), _("Do not combine files into solid blocks.")),
                ("256 MiB", _("Use blocks up to 256 MiB.")),
                ("1 GiB", _("Use blocks up to 1 GiB.")),
                ("4 GiB", _("Use blocks up to 4 GiB.")),
                (_("Fully solid"), _("Use one block for the entire archive.")),
            ],
        )
        self.solid_block.set_subtitle(
            _("Balances compression ratio and access to individual files.")
        )
        self.volume = _described_combo_row(
            _("Split into volumes"),
            [
                (_("None"), _("Create one archive file.")),
                ("100 MiB", _("Create volumes up to this size.")),
                ("700 MiB", _("Create volumes up to this size.")),
                ("2 GiB", _("Create volumes up to this size.")),
                ("4095 MiB", _("Create volumes up to this size; fits FAT32.")),
                (_("Custom…"), _("Choose an exact volume size.")),
            ],
            selected_labels=[
                _("Single archive"),
                "100 MiB",
                "700 MiB",
                "2 GiB",
                "4095 MiB",
                "1500 MiB",
            ],
        )
        self.volume.set_subtitle(_("Creates one file or numbered .001 volumes."))
        self.volume.connect("notify::selected", self._volume_changed)
        self.edit_custom_volume = Gtk.Button(
            icon_name="document-edit-symbolic",
            tooltip_text=_("Edit custom volume size"),
            valign=Gtk.Align.CENTER,
            visible=False,
        )
        self.edit_custom_volume.add_css_class("flat")
        self.edit_custom_volume.connect("clicked", self._edit_custom_volume)
        self.volume.add_suffix(self.edit_custom_volume)
        self._last_preset_volume = 0
        self._custom_volume_value = 1500.0
        self._custom_volume_unit = "MiB"
        self._custom_volume_size = 1500 * 1024**2
        self._custom_volume_dialog_open = False
        self.advanced.add_row(self.threads)
        self.advanced.add_row(self.solid_block)
        self.advanced.add_row(self.volume)
        options_group.add(self.verify)
        options_group.add(self.advanced)
        self.page.add(options_group)

        self.create_button = self.add_primary_action(_("Create"), self._create)
        for entry in (self.name, self.password, self.confirm_password):
            entry.connect("changed", self._validate_form)
        self.threads.connect("notify::selected", self._advanced_option_changed)
        self.solid_block.connect("notify::selected", self._advanced_option_changed)
        self.encrypt_headers.connect("notify::active", self._validate_form)
        self.password_protection.connect(
            "notify::enable-expansion",
            self._password_protection_changed,
        )
        self._format_changed(self.format, None)
        self._validate_form()

    def _format_changed(self, _combo: Adw.ComboRow, _param) -> None:
        is_7z = self._archive_format() is ArchiveFormat.SEVEN_ZIP
        self.solid_block.set_visible(is_7z)
        self.encrypt_headers.set_visible(is_7z)
        if not is_7z:
            self.encrypt_headers.set_active(False)
        self._update_advanced_summary()
        self._validate_form()

    def _volume_changed(self, _combo: Adw.ComboRow, _param) -> None:
        is_custom = self._selected_volume() == _CUSTOM_VOLUME
        self.edit_custom_volume.set_visible(is_custom)
        if is_custom:
            if not self._custom_volume_dialog_open:
                self._show_custom_volume_dialog()
        else:
            self._last_preset_volume = self.volume.get_selected()
        self._update_advanced_summary()
        self._validate_form()

    def _edit_custom_volume(self, _button: Gtk.Button) -> None:
        self._show_custom_volume_dialog(revert_on_cancel=False)

    def _show_custom_volume_dialog(self, *, revert_on_cancel: bool = True) -> None:
        if self._custom_volume_dialog_open:
            return
        self._custom_volume_dialog_open = True
        self._custom_cancel_selection = self._last_preset_volume if revert_on_cancel else 5

        dialog = Adw.AlertDialog(
            heading=_("Custom Volume Size"),
            body=_("Choose the maximum size of each numbered archive volume."),
        )
        dialog.set_content_width(420)
        size = Adw.SpinRow(
            title=_("Size"),
            adjustment=Gtk.Adjustment(
                value=self._custom_volume_value,
                lower=0.01,
                upper=1024 * 1024,
                step_increment=1,
                page_increment=100,
            ),
            digits=0 if self._custom_volume_unit == "MiB" else 2,
            numeric=True,
        )
        unit = _combo_row(
            _("Unit"),
            ["MiB", "GiB"],
            selected=0 if self._custom_volume_unit == "MiB" else 1,
        )
        self._dialog_previous_unit = self._custom_volume_unit
        unit.connect("notify::selected", self._custom_volume_unit_changed, size)
        group = Adw.PreferencesGroup()
        group.add(size)
        group.add(unit)
        dialog.set_extra_child(group)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("apply", _("Apply"))
        dialog.set_close_response("cancel")
        dialog.set_default_response("apply")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._custom_volume_response, size, unit)
        dialog.present(self)

    def _custom_volume_unit_changed(
        self,
        unit: Adw.ComboRow,
        _param,
        size: Adw.SpinRow,
    ) -> None:
        new_unit = "MiB" if unit.get_selected() == 0 else "GiB"
        old_unit = self._dialog_previous_unit
        if new_unit == old_unit:
            return
        old_multiplier = 1024**2 if old_unit == "MiB" else 1024**3
        new_multiplier = 1024**2 if new_unit == "MiB" else 1024**3
        converted = size.get_value() * old_multiplier / new_multiplier
        size.set_digits(0 if new_unit == "MiB" else 2)
        size.set_value(round(converted, 0 if new_unit == "MiB" else 2))
        self._dialog_previous_unit = new_unit

    def _custom_volume_response(
        self,
        _dialog: Adw.AlertDialog,
        response: str,
        size: Adw.SpinRow,
        unit: Adw.ComboRow,
    ) -> None:
        if response != "apply":
            self._custom_volume_dialog_open = False
            self.volume.set_selected(self._custom_cancel_selection)
            return
        self._custom_volume_unit = "MiB" if unit.get_selected() == 0 else "GiB"
        self._custom_volume_value = round(
            size.get_value(),
            0 if self._custom_volume_unit == "MiB" else 2,
        )
        self._custom_volume_size = parse_binary_size(
            f"{self._custom_volume_value:g}{self._custom_volume_unit}"
        )
        model = self.volume.get_model()
        if isinstance(model, Gtk.StringList):
            model.splice(5, 1, [self._custom_volume_display()])
            self.volume.set_selected(5)
        self._custom_volume_dialog_open = False
        self._update_advanced_summary()

    def _custom_volume_display(self) -> str:
        return f"{self._custom_volume_value:g} {self._custom_volume_unit}"

    def _password_protection_changed(self, row: Adw.ExpanderRow, _param) -> None:
        enabled = row.get_enable_expansion()
        row.set_expanded(enabled)
        if not enabled:
            self.password.set_text("")
            self.confirm_password.set_text("")
            self.encrypt_headers.set_active(False)
        self._validate_form()

    def _advanced_option_changed(self, _combo: Adw.ComboRow, _param) -> None:
        self._update_advanced_summary()

    def _archive_format(self) -> ArchiveFormat:
        return _FORMATS[self.format.get_selected()]

    def _selected_volume(self) -> int | None:
        return _VOLUME_SIZES[self.volume.get_selected()]

    def _volume_size(self) -> int | None:
        selected = self._selected_volume()
        if selected != _CUSTOM_VOLUME:
            return selected
        return self._custom_volume_size

    def _update_advanced_summary(self) -> None:
        parts = [
            _("Threads: {value}").format(value=_selected_combo_label(self.threads))
        ]
        if self._archive_format() is ArchiveFormat.SEVEN_ZIP:
            parts.append(
                _("Solid: {value}").format(value=_selected_combo_label(self.solid_block))
            )
        parts.append(
            _("Volumes: {value}").format(value=_selected_combo_label(self.volume))
        )
        self.advanced.set_subtitle(" · ".join(parts))

    def _validate_form(self, *_args) -> None:
        protection_enabled = self.password_protection.get_enable_expansion()
        password = self.password.get_text() if protection_enabled else ""
        confirm = self.confirm_password.get_text() if protection_enabled else ""
        passwords_match = password == confirm
        headers_valid = not self.encrypt_headers.get_active() or bool(password)
        if not passwords_match:
            encryption_message = _("Passwords do not match.")
        elif not headers_valid:
            encryption_message = _("Enter a password to encrypt file names.")
        else:
            encryption_message = _("Encrypts archive contents with AES-256.")
        self.password_protection.set_subtitle(encryption_message)
        self.create_button.set_sensitive(
            bool(self.name.get_text().strip())
            and passwords_match
            and headers_valid
        )

    def _create(self, _button: Gtk.Button) -> None:
        name = self.name.get_text().strip()
        destination = Path(self.destination.get_text()).expanduser()
        if not name:
            self.show_error(_("Archive name must not be empty."))
            return
        if not destination.is_dir():
            self.show_error(_("Destination folder does not exist."))
            return

        archive_format = self._archive_format()
        protection_enabled = self.password_protection.get_enable_expansion()
        password = (self.password.get_text() or None) if protection_enabled else None
        if protection_enabled and self.password.get_text() != self.confirm_password.get_text():
            self.show_error(_("Passwords do not match."))
            return
        volume_size = self._volume_size()
        encrypt_headers = self.encrypt_headers.get_active()
        if encrypt_headers and not password:
            self.show_error(_("A password is required to encrypt file names."))
            return

        options = CreateOptions(
            sources=self.paths,
            output=destination / name,
            archive_format=archive_format,
            level=_LEVELS[self.level.get_selected()],
            threads=None if self.threads.get_selected() == 0 else self.threads.get_selected(),
            solid_block=(
                _SOLID_BLOCKS[self.solid_block.get_selected()]
                if archive_format is ArchiveFormat.SEVEN_ZIP
                else None
            ),
            volume_size=volume_size,
            password=password,
            encrypt_headers=encrypt_headers,
            verify=self.verify.get_active(),
        )
        if output_path_exists(options.archive_path, split=volume_size is not None):
            self.show_error(_("An archive with this name already exists."))
            return
        specs = [self.builder.create(options)]
        if options.verify:
            verify_options = IntegrityTestOptions(options.verification_path, password)
            specs.append(self.builder.test(verify_options))
        self.replace_with_progress(specs)


class ExtractArchiveWindow(_FormWindow):
    def __init__(
        self,
        application: Adw.Application,
        archive: Path,
        builder: SevenZipCommandBuilder,
    ) -> None:
        super().__init__(application, title=_("Extract Archive"), default_height=500)
        self.archive = archive
        self.builder = builder

        destination = unique_path(archive.parent / archive_stem(archive))
        group = Adw.PreferencesGroup(title=_("Extraction"))
        self.destination = self.create_path_row(_("Destination"), destination)
        self.password = Adw.PasswordEntryRow(
            title=_("Password (if required)"),
            activates_default=True,
        )
        self.overwrite = _combo_row(
            _("If a file already exists"),
            [
                _("Rename extracted files"),
                _("Overwrite existing files"),
                _("Skip existing files"),
            ],
        )
        group.add(self.destination)
        group.add(self.password)
        group.add(self.overwrite)
        self.page.add(group)
        self.add_primary_action(_("Extract"), self._extract)

    def _extract(self, _button: Gtk.Button) -> None:
        destination = Path(self.destination.get_text()).expanduser()
        parent = destination.parent
        if not parent.is_dir():
            self.show_error(_("The parent of the destination folder does not exist."))
            return
        overwrite = _OVERWRITE_MODES[self.overwrite.get_selected()]
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
        self.set_default_size(700, 300)
        self._specs = deque(specs)
        self._total_steps = len(specs)
        self._current_step = 0
        self._handle: OperationHandle | None = None
        self._runner = SubprocessRunner(dispatcher=GLib.idle_add)
        self._overall_started_at = 0.0
        self._phase_started_at = 0.0
        self._last_percent = 0
        self._processed_items = 0
        self._total_items: int | None = None
        self._timer_id = 0
        self._finished = False
        self.connect("close-request", self._close_requested)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(
            show_start_title_buttons=False,
            show_end_title_buttons=False,
        )
        header.set_title_widget(Adw.WindowTitle(title=_("7-Zip operation")))
        self.cancel_button = Gtk.Button(label=_("Cancel"))
        self.cancel_button.connect("clicked", self._cancel)
        header.pack_start(self.cancel_button)
        self.close_button = Gtk.Button(label=_("Close"), visible=False)
        self.close_button.add_css_class("suggested-action")
        self.close_button.connect("clicked", lambda _button: self.close())
        header.pack_end(self.close_button)
        toolbar.add_top_bar(header)
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=20,
            margin_bottom=20,
            margin_start=20,
            margin_end=20,
        )
        self.status = Gtk.Label(xalign=0, wrap=True)
        self.status.add_css_class("title-3")
        self.progress = Gtk.ProgressBar(show_text=True)
        self.statistics = Gtk.Label(xalign=0)
        self.statistics.add_css_class("dim-label")
        self.statistics.add_css_class("caption")
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
        content.append(self.statistics)
        content.append(self.details)
        toolbar.set_content(content)
        self.set_content(toolbar)

    def start(self) -> None:
        self._overall_started_at = time.monotonic()
        self._timer_id = GLib.timeout_add_seconds(1, self._refresh_statistics)
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
        self._current_step += 1
        self._phase_started_at = time.monotonic()
        self._last_percent = 0
        self._processed_items = 0
        self._total_items = None
        self.status.set_label(spec.title)
        self.progress.set_fraction(0.0)
        self.progress.set_text("")
        self._refresh_statistics()
        self._handle = self._runner.start(
            spec,
            on_output=self._append_output,
            on_progress=self._set_progress,
            on_complete=self._completed,
        )

    def _append_output(self, text: str) -> None:
        file_progress = parse_file_progress(text)
        self._processed_items += file_progress.processed
        if file_progress.total is not None:
            self._total_items = file_progress.total
        if file_progress.processed or file_progress.total is not None:
            self._refresh_statistics()
        buffer = self.log.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        overflow = buffer.get_char_count() - self._MAX_LOG_CHARS
        if overflow > 0:
            buffer.delete(buffer.get_start_iter(), buffer.get_iter_at_offset(overflow))
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.log.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        buffer.delete_mark(mark)

    def _set_progress(self, percent: int) -> None:
        self._last_percent = percent
        self.progress.set_fraction(percent / 100)
        self.progress.set_text(f"{percent}%")
        self._refresh_statistics()

    def _refresh_statistics(self) -> bool:
        if not self._overall_started_at:
            return GLib.SOURCE_CONTINUE
        now = time.monotonic()
        parts = [
            _("Elapsed {duration}").format(
                duration=format_duration(now - self._overall_started_at),
            )
        ]
        if self._total_steps > 1 and self._current_step:
            parts.append(
                _("Step {current}/{total}").format(
                    current=self._current_step,
                    total=self._total_steps,
                )
            )
        if self._processed_items:
            if self._total_items is not None and self._processed_items <= self._total_items:
                parts.append(
                    _("Items {current}/{total}").format(
                        current=self._processed_items,
                        total=self._total_items,
                    )
                )
            else:
                parts.append(
                    _("Items processed: {count}").format(count=self._processed_items)
                )
        phase_elapsed = now - self._phase_started_at
        if 0 < self._last_percent < 100 and phase_elapsed >= 3:
            remaining = phase_elapsed * (100 - self._last_percent) / self._last_percent
            parts.append(
                _("About {duration} remaining").format(
                    duration=format_duration(remaining),
                )
            )
        self.statistics.set_label(" · ".join(parts))
        return GLib.SOURCE_REMOVE if self._finished else GLib.SOURCE_CONTINUE

    def _completed(self, result: RunResult) -> None:
        self._handle = None
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

    def _close_requested(self, _window: Adw.ApplicationWindow) -> bool:
        if self._finished:
            return False
        self._cancel(self.cancel_button)
        return True

    def _finish(self) -> None:
        self._finished = True
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0
        self._refresh_statistics()
        self.cancel_button.set_visible(False)
        self.close_button.set_visible(True)
        self.set_default_widget(self.close_button)


def _described_combo_row(
    title: str,
    options: list[tuple[str, str]],
    *,
    selected_labels: list[str] | None = None,
) -> Adw.ComboRow:
    popup_labels = [label for label, _description in options]
    if selected_labels is not None and len(selected_labels) != len(options):
        raise ValueError("Selected labels must match described options")
    row = _combo_row(title, selected_labels or popup_labels)
    descriptions = [description for _label, description in options]
    factory = Gtk.SignalListItemFactory()

    def setup(_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            margin_top=6,
            margin_bottom=6,
            margin_start=2,
            margin_end=12,
        )
        primary = Gtk.Label(xalign=0)
        secondary = Gtk.Label(xalign=0, wrap=True, max_width_chars=48)
        secondary.add_css_class("dim-label")
        secondary.add_css_class("caption")
        box.append(primary)
        box.append(secondary)
        list_item.set_child(box)

    def bind(_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        box = list_item.get_child()
        if not isinstance(box, Gtk.Box):
            return
        primary = box.get_first_child()
        secondary = primary.get_next_sibling() if primary is not None else None
        position = list_item.get_position()
        if isinstance(primary, Gtk.Label) and position < len(popup_labels):
            primary.set_label(popup_labels[position])
        if isinstance(secondary, Gtk.Label) and position < len(descriptions):
            secondary.set_label(descriptions[position])

    factory.connect("setup", setup)
    factory.connect("bind", bind)
    row.set_list_factory(factory)
    return row


def _selected_combo_label(row: Adw.ComboRow) -> str:
    item = row.get_selected_item()
    if not isinstance(item, Gtk.StringObject):
        return ""
    return item.get_string()


def _combo_row(
    title: str,
    labels: list[str],
    *,
    selected: int = 0,
    subtitle: str | None = None,
) -> Adw.ComboRow:
    row = Adw.ComboRow(
        title=title,
        model=Gtk.StringList.new(labels),
        selected=selected,
    )
    if subtitle is not None:
        row.set_subtitle(subtitle)
    return row


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
