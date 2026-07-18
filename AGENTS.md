# AGENTS.md

## Purpose

This repository implements **7-Zip for Nautilus** (`nautilus-7zip`): an
explicit 7-Zip context submenu for GNOME Files plus a standalone GTK 4/
libadwaita helper for configurable archive operations.

This file is the continuation brief for future coding sessions. Read it before
changing the project.

## Product decisions

- Repository/package name: `nautilus-7zip`.
- Display name: `7-Zip for Nautilus`.
- Context-menu root label: `7-Zip`.
- Executable: `nautilus-7zip`.
- gettext domain: `nautilus-7zip`.
- Application ID: `io.github.nautilus_7zip.Nautilus7Zip` until a permanent
  GitHub owner/organization is selected.
- The system `7z` executable is the backend. Do not bundle 7-Zip.
- English is the source language and mandatory fallback. Additional locales are
  gettext catalogs selected automatically from the system locale.
- Supported creation formats in the MVP are 7z and ZIP.

## Architecture and boundaries

There are two processes:

1. `src/extension/nautilus_7zip_extension.py` is a deliberately thin
   `Nautilus.MenuProvider`. It filters non-local selections, builds menu items,
   writes a mode-0600 JSON selection manifest, and starts the helper.
2. `src/nautilus_7zip/application.py` is a standalone Adwaita application. It
   owns dialogs and progress UI and delegates all heavy work to a child `7z`
   process through `SubprocessRunner`.

Do not add archive traversal, compression, blocking waits, or complex GTK code
to the Nautilus process. A helper crash must not crash Nautilus.

The extension module must not be named `nautilus_7zip.py`: nautilus-python puts
the extensions directory on `sys.path`, so that filename shadows the installed
`nautilus_7zip` package and breaks imports.

Keep option validation and command generation independent of GTK:

- `models.py`: immutable validated option models;
- `commands.py`: `CommandSpec` and safe 7-Zip argv construction;
- `labels.py`: GTK/Nautilus-safe user-visible label formatting;
- `paths.py`: naming and archive detection;
- `selection.py`: secure selection-manifest transfer;
- `progress.py`: console progress parsing and terminal-control rendering;
- `runner.py`: cancellable subprocess execution;
- `application.py`: platform UI adapter only.

## Security invariants

- Never use `shell=True`, `os.system`, or a joined command string.
- Pass paths as separate argv elements and use 7-Zip's `--` switch.
- Never place a password in argv (`-pPASSWORD`). Creation uses bare `-p` and
  writes the password to stdin. Extraction/testing must omit `-p` so 7-Zip
  prompts, then receive the password through stdin.
- Never log, persist, translate, or include passwords in exceptions.
- Selection manifests must remain mode `0600` and be removed after reading.
- Do not operate on remote/non-native Nautilus URIs.
- Do not add delete-source behavior without explicit product review, recovery
  design, and tests.
- Cancellation sends SIGTERM to the dedicated child process group. Do not send
  signals to a broad or unresolved target.

## UI and localization

- Source all user-visible strings in English and wrap them with `_()`.
- English must remain functional without any compiled catalogs.
- Do not translate technical names (`7z`, ZIP, LZMA2, Deflate, AES-256).
- Escape literal underscores in Nautilus menu labels as doubled underscores;
  GTK treats a single underscore as a mnemonic marker. Never apply this escape
  to filesystem paths or archive names passed to 7-Zip.
- Keep the helper out of the Nautilus process. Current Nautilus uses GTK 4;
  never attempt to mix GTK 3 into an extension.
- Long operations must run outside the GTK main loop. Dispatch UI updates using
  `GLib.idle_add` or an equivalent main-context mechanism.
- Keep progress log memory bounded.
- Keep technical output collapsed by default. Render 7-Zip's terminal controls
  before inserting output into GTK; never expose raw backspace or ANSI control
  sequences as replacement glyphs.
- When replacing a form window with progress, construct and register the
  progress window before closing the form; a closed window may no longer return
  its application from `get_application()`.
- Preserve keyboard accessibility and visible labels for form controls.
- Let option forms request their natural height so all controls are initially
  visible; retain a scroller as the fallback for small displays and large text.
- Keep form windows resizable for long paths, large text, tiling, and adaptive
  layouts. Do not replace adaptive sizing with a fixed, non-resizable window.

## Testing requirements

- The required coverage gate is 85%; aim for 90%+ for non-UI code.
- `application.py` is excluded from line coverage because CI does not provide a
  live display. Keep it thin and add GTK smoke tests when a reliable harness is
  introduced.
- Every command option or security-sensitive behavior needs a unit test.
- Password tests must assert that the secret is absent from argv.
- Add regression tests before fixing bugs in path handling, archive naming,
  selection manifests, progress parsing, or cancellation.
- Run before handoff:

  ```bash
  ruff check .
  pytest
  meson setup build
  meson compile -C build
  meson test -C build --print-errorlogs
  ```

- For backend changes, also run a temporary-directory integration check against
  the installed `7z`: create, test, extract, compare content, and ensure no test
  archive is written into the repository.

## Build and installation

- Meson is the canonical application installer. The setuptools configuration in
  `pyproject.toml` exists only for an editable development install, CLI entry
  point, metadata, and development dependencies.
- A per-user build should use `--prefix="$HOME/.local"`.
- The default extension directory is
  `${datadir}/nautilus-python/extensions`; override it with
  `-Dnautilus_extension_dir=...` if a distribution differs.
- Keep `DESTDIR` staging functional for future Arch/Manjaro packaging.
- Do not commit `.venv`, build output, coverage databases, or generated caches.

## Current status (initial MVP)

Implemented:

- 7-Zip Nautilus submenu for local selections;
- interactive and quick 7z/ZIP creation;
- configurable format, level, solid mode, password, header encryption, output;
- extraction destination and overwrite policy;
- integrity testing, progress, cancellation, and bounded, collapsible logs;
- terminal-style rendering of 7-Zip backspace output for the GTK details view;
- stdin password transport;
- Meson installation, gettext scaffolding, complete Russian catalog;
- unit tests and GitHub Actions workflow.

Known follow-ups:

1. Exercise the UI manually under Nautilus 50 and record screenshots.
2. Persist non-secret defaults with GSettings.
3. Add explicit thread-count controls to the GUI (the command model supports
   `threads`; current GUI uses automatic mode).
4. Improve password-prompt/error behavior for encrypted extraction.
5. Add split volumes and tar+compressor workflows.
6. Add a GTK smoke-test harness and test the extension with mocked Nautilus GI.
7. Decide the permanent GitHub owner and update the application ID if needed.
8. Add a release-backed `PKGBUILD` after the first tag.

## Definition of done for changes

A change is done only when behavior, tests, English UI strings, translations or
POT inputs, README/user documentation, and this continuation brief agree. Do
not lower the coverage threshold or weaken a security invariant to make a check
pass.
