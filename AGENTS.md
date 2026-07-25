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
- GitHub repository: `michaelbrylevskii/nautilus-7zip` (public).
- Application ID: `io.github.michaelbrylevskii.Nautilus7Zip`.
- A validated system `7z` or `7zz` executable is the backend. Prefer `7z`, fall
  back to `7zz`, and keep `--sevenzip` as a strict override. Do not bundle
  7-Zip.
- English is the source language and mandatory fallback. Additional locales are
  gettext catalogs selected automatically from the system locale.
- Supported creation formats are 7z and ZIP.

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
- `backend.py`: bounded backend discovery, validation, and version parsing;
- `commands.py`: `CommandSpec` and safe 7-Zip argv construction;
- `diagnostics.py`: bounded privacy-safe system/backend report collection;
- `labels.py`: GTK/Nautilus-safe user-visible label formatting;
- `paths.py`: naming and archive detection;
- `selection.py`: secure selection-manifest transfer;
- `sizes.py`: validated human-readable binary size parsing;
- `progress.py`: console progress parsing and terminal-control rendering;
- `runner.py`: cancellable subprocess execution;
- `runtime.py`: supported GTK/libadwaita version rules;
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
- Diagnostic collection must use an explicit field allowlist. Never pass
  selections, passwords, the full environment, username, or hostname to it;
  collapse the home directory to `~` in included executable/install paths.
- Diagnostic subprocesses must be noninteractive, shell-free, bounded by a
  short timeout, and run outside the GTK main loop.
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
- Build option forms from libadwaita preferences groups and rows. Keep detailed
  compression controls inside a collapsed `Advanced Options` expander and use
  concise row subtitles instead of adding question-mark buttons.
- Display creation formats with their suffixes (`7Z (.7z)`, `ZIP (.zip)`), but
  keep the editable archive name suffix-free by default.
- Put concise format descriptions inside the format drop-down list. Keep
  password protection disabled and collapsed until the user explicitly enables
  it. Collect custom volume sizes in a compact dialog with explicit units.
- Use short inline hints only for solid-block and volume choices that benefit
  from explanation; do not add redundant text to numeric sizes. Show exact
  selected values in the collapsed advanced summary. Keep a custom volume's
  actual size as a selectable value and `Custom…` as a repeatable dialog action.
- Keep volume presets consistently expressed in MiB and call the unsplit state
  `Single archive` in both the popup and selected-value display. Give selected
  ComboRow values layout priority over wrapping technical subtitles. Keep
  selected values right-aligned in their rows and popup choices left-aligned.
- A split archive is tested and extracted through its first `.001` volume.
  Detect output collisions against that first volume before starting 7-Zip.
- Keep progress actions in the header bar. Show elapsed time unconditionally;
  only show approximate remaining time and item totals when 7-Zip has reported
  enough trustworthy information, and label estimates as approximate.
- Keep option-form header bars focused on Cancel and the primary action. Expose
  About/Troubleshooting as a quiet centered footer action inside the scrollable
  preferences content. In progress windows, show Diagnostics next to Close
  only after an operation failure.

## Testing requirements

- The required coverage gate is 85%; aim for 90%+ for non-UI code.
- `application.py` is excluded from line coverage, but focused real-widget
  behavior belongs in `tests/test_application_widgets.py`. Initialize
  libadwaita explicitly and run these tests with an existing desktop display or
  Xvfb. CI and release workflows must provide Xvfb rather than silently
  skipping widget tests.
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

- On a headless host, wrap both pytest and Meson test runs with `xvfb-run -a`.
- For backend changes, also run a temporary-directory integration check against
  the discovered `7z` or `7zz`: create, test, extract, compare content, and
  ensure no test archive is written into the repository.

## Build and installation

- Meson is the canonical application installer. The setuptools configuration in
  `pyproject.toml` exists only for an editable development install, CLI entry
  point, metadata, and development dependencies.
- A per-user build should use `--prefix="$HOME/.local"`.
- The default extension directory is
  `${datadir}/nautilus-python/extensions`; override it with
  `-Dnautilus_extension_dir=...` if a distribution differs.
- Keep `DESTDIR` staging functional for downstream distribution packaging.
- Do not commit `.venv`, build output, coverage databases, or generated caches.

## Current implementation

Implemented:

- 7-Zip Nautilus submenu for local selections;
- interactive and quick 7z/ZIP creation;
- modern grouped libadwaita forms for creation and extraction;
- configurable format, level, CPU threads, solid block, split volumes,
  password confirmation, header encryption, and output;
- extraction destination and overwrite policy;
- integrity testing, progress, cancellation, and bounded, collapsible logs;
- compact progress header actions plus elapsed, approximate remaining, step,
  and best-effort item statistics;
- terminal-style rendering of 7-Zip backspace output for the GTK details view;
- Xvfb-backed GTK widget smoke tests in CI and release verification;
- native About/Troubleshooting UI and a headless privacy-safe diagnostics
  command;
- explicit GTK 4.14/libadwaita 1.5 runtime compatibility validation;
- stdin password transport;
- validated `7z`/`7zz` discovery with a strict executable override;
- Meson installation, gettext scaffolding, complete Russian catalog;
- unit and backend integration tests;
- GitHub Actions CI on every push and pull request;
- tag-driven GitHub Releases with changelog notes, a Meson source archive, and
  a SHA-256 checksum.

The ordered product plan lives in `ROADMAP.md`. Immediate follow-ups:

1. Exercise clean tagged-release installation across supported distributions.
2. Add a maintained Arch/Manjaro package recipe.
3. Expand GTK widget smoke coverage and test the extension with mocked Nautilus
   GI.

## Definition of done for changes

A change is done only when behavior, tests, English UI strings, translations or
POT inputs, README/user documentation, and this continuation brief agree. Do
not lower the coverage threshold or weaken a security invariant to make a check
pass.
