# 7-Zip for Nautilus

`nautilus-7zip` adds an explicit **7-Zip** submenu to GNOME Files (Nautilus) and
provides a native GTK 4/libadwaita interface for archive creation, extraction,
and integrity testing.

The project uses the system `7z` executable. It does not replace Nautilus'
built-in **Compress…** action and does not bundle an archiving engine.

> [!IMPORTANT]
> The project is currently an alpha-quality MVP. The command model and process
> runner are extensively tested, but the Nautilus and GTK integration still
> needs broader real-world testing across GNOME releases and distributions.

## Features

- A conditional **7-Zip** submenu for local Nautilus selections.
- Interactive creation of `.7z` and `.zip` archives.
- Quick **Create `<name>.7z`** and **Create `<name>.zip`** actions.
- Modern libadwaita forms with grouped, adaptive option rows.
- Compression level, CPU thread, solid-block, destination, and archive name controls.
- Optional multi-volume output with presets and custom binary sizes.
- AES-256 password protection; 7z header encryption is supported.
- Password confirmation and inline validation before archive creation.
- **Extract…**, **Extract here**, and **Extract to `<name>/`** actions.
- Configurable overwrite behavior during extraction.
- Archive integrity testing.
- Cancellable background operations with parsed 7-Zip progress.
- Collapsed technical details with terminal control sequences rendered as plain text.
- English source UI and fallback, with gettext-based localization.
- Complete Russian translation included.
- Passwords are sent through stdin instead of process arguments.

## Context menu

```text
7-Zip
├── Create archive…
├── Create <name>.7z
├── Create <name>.zip
├── Extract…                 # shown for a single archive
├── Extract here             # shown for a single archive
├── Extract to <name>/       # shown for a single archive
└── Test archive             # shown for a single archive
```

Remote locations such as `sftp://` are deliberately excluded because the 7-Zip
CLI requires native filesystem paths.

### Quick-action defaults

The two quick creation actions use compression level **Normal** (`-mx=5`),
automatic threading (`-mmt=on`), no password, and no post-creation integrity
test. The 7z action uses automatic solid-block sizing; the ZIP action uses
Deflate. The output is placed beside the selection, and an incrementing suffix
is added rather than overwriting an existing archive.

During an operation, the window shows its status and progress bar. Detailed
7-Zip output is available under the collapsed **Details** section and opens
automatically if the operation fails.

### Interactive creation options

The creation form presents formats as **7Z (.7z)** and **ZIP (.zip)** and adds
the selected extension automatically. Its collapsed **Advanced Options** row
contains:

- automatic or explicit CPU thread counts;
- automatic, non-solid, 256 MiB, 1 GiB, 4 GiB, and fully solid 7z blocks;
- single-file output, common volume-size presets, and custom values such as
  `1500M` or `4G`.

Split archives are written as numbered files such as `backup.7z.001` and
`backup.7z.002`. Test and extract operations must start with `.001`. The
4095 MiB preset stays below FAT32's per-file limit.

## Requirements

Runtime:

- Linux with GNOME Files/Nautilus 43 or newer;
- Python 3.11 or newer;
- `nautilus-python` API 4;
- PyGObject;
- GTK 4 and libadwaita 1.5 or newer;
- the official 7-Zip CLI, available as `7z`.

Build and development:

- Meson 1.3 or newer;
- Ninja;
- gettext;
- pytest, pytest-cov, and Ruff.

On Arch Linux or Manjaro, the relevant packages are normally named `7zip`,
`nautilus-python`, `python-gobject`, `gtk4`, `libadwaita`, `meson`, `ninja`, and
`gettext`.

## Build and install

### Per-user installation

This is the recommended mode while developing or evaluating the project:

```bash
meson setup build --prefix="$HOME/.local"
meson compile -C build
meson install -C build
nautilus -q
```

`nautilus -q` closes currently open Files windows. Start Files again to load the
extension.

The default user installation places files under:

```text
~/.local/bin/nautilus-7zip
~/.local/lib/python*/site-packages/nautilus_7zip/
~/.local/share/nautilus-python/extensions/nautilus_7zip_extension.py
~/.local/share/locale/
```

If the distribution uses a non-standard extension directory, configure it
explicitly:

```bash
meson setup build \
  --prefix="$HOME/.local" \
  -Dnautilus_extension_dir="$HOME/.local/share/nautilus-python/extensions"
```

### System package

Meson honors `DESTDIR`, so distribution packages can stage an installation in
the usual way:

```bash
meson setup build --prefix=/usr
meson compile -C build
DESTDIR="$pkgdir" meson install -C build
```

An Arch/Manjaro `PKGBUILD` will be added after the first tagged release has a
stable source URL and checksum.

### Uninstall a development installation

Keep the build directory and run:

```bash
ninja -C build uninstall
nautilus -q
```

## Development

Create a virtual environment that can see the distribution-provided PyGObject:

```bash
python -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

The editable install is only a development convenience for the Python package
and CLI entry point. Meson remains the canonical installer for the Nautilus
extension, desktop metadata, icons, and translations.

Run the checks:

```bash
ruff check .
pytest
meson setup build
meson compile -C build
meson test -C build --print-errorlogs
```

The coverage gate is 85%. Platform adapters requiring a live GTK display or a
running Nautilus instance are excluded from line coverage; their logic is kept
thin, while command construction, input validation, path handling, selection
manifests, terminal-output rendering, progress parsing, and process execution
are covered directly.

### Running the helper without Nautilus

During development, the helper can be run directly:

```bash
PYTHONPATH=src python -m nautilus_7zip.main create /path/to/file /path/to/folder
PYTHONPATH=src python -m nautilus_7zip.main extract /path/to/archive.7z
PYTHONPATH=src python -m nautilus_7zip.main test /path/to/archive.zip
```

Use `--sevenzip /path/to/7z` to test another executable.

## Architecture

The project separates the file-manager adapter from the application:

```text
Nautilus process
└── small nautilus-python MenuProvider
    └── secure JSON selection manifest
        └── standalone GTK/libadwaita helper
            ├── validated option models
            ├── safe argv command builder
            ├── cancellable subprocess runner
            └── system /usr/bin/7z
```

The extension never performs compression and never opens GTK windows inside the
Nautilus process. This keeps Files responsive and limits the impact of helper
failures.

The helper invokes 7-Zip with an argument array, never through a shell. Archive
creation uses a bare `-p` and writes the password to stdin; extraction and
testing omit the password switch and answer 7-Zip's prompt through stdin. This
keeps secrets out of shell history and `/proc/<pid>/cmdline`.

See [`AGENTS.md`](AGENTS.md) for detailed invariants and continuation notes.

## Localization

All source strings and the guaranteed fallback are English. Translations use
GNU gettext and are selected from the process locale (`LC_MESSAGES`/`LANG`).
The repository currently includes a complete Russian catalog.

To update translation templates after changing UI strings:

```bash
meson setup build
meson compile -C build nautilus-7zip-pot
meson compile -C build nautilus-7zip-update-po
```

Technical identifiers such as `LZMA2`, `Deflate`, and archive extensions should
not be translated.

## Security considerations

- Never concatenate selected paths into a shell command.
- Never use `shell=True`.
- Never persist, log, or include passwords in process arguments.
- Selection manifests are created with mode `0600` and removed after reading.
- Only local `file://` selections are accepted by the Nautilus extension.
- A failed or cancelled archive operation must not delete source data.
- Destructive post-archive actions are intentionally outside the MVP scope.

Users should still understand the encryption properties of the selected archive
format. ZIP AES encryption is not supported by every ZIP implementation; 7z
AES-256 with encrypted headers is preferable when confidentiality matters and
7-Zip-compatible extraction is available.

## Roadmap

- Persist non-secret defaults with GSettings.
- Add compression-method, dictionary-size, and memory-limit controls.
- Add reusable compression presets.
- Add `.tar.zst`, `.tar.gz`, and `.tar.xz` workflows.
- Add desktop notifications and an optional “open destination” action.
- Add automated GTK smoke tests.
- Test and package for additional distributions.
- Publish an Arch/Manjaro `PKGBUILD` after the first tagged release.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Bug reports should include the
Nautilus version, `nautilus-python` version, 7-Zip version, distribution, and the
console output produced by the helper with secrets removed.

## License

MIT — see [`LICENSE`](LICENSE).
