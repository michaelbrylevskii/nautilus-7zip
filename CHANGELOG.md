# Changelog

All notable changes will be documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases will use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-07-26

### Added

- Automatic discovery and validation of `7z` and `7zz`, preferring the
  plugin-capable `7z` command when both are available.
- A strict `--sevenzip PATH` override with visible startup errors for missing,
  unusable, or timed-out backends.
- An Xvfb-backed GTK widget smoke-test harness for headless CI and release
  verification.
- Native About/Troubleshooting information and a headless
  `nautilus-7zip diagnostics` command with a privacy-safe application,
  desktop, toolkit, Nautilus, locale, and backend report.
- Explicit runtime validation for the supported GTK 4.14 and libadwaita 1.5
  baseline.
- Type-aware desktop opening that extracts a single archive and creates an
  archive for regular files, directories, and multiple selections.

### Fixed

- Restored left alignment for choices in simple option drop-downs while
  keeping the selected row value right-aligned.
- Kept primary form actions at the edge of the header bar by moving
  About/Troubleshooting to a quiet footer action; failed operations expose
  Diagnostics alongside Close.

## [0.1.0] - 2026-07-19

### Added

- Nautilus **7-Zip** submenu for local files and folders.
- Interactive and quick creation of 7z and ZIP archives.
- Compression level, CPU thread, 7z solid-block, and split-volume controls.
- Password-protected archives with stdin secret transport and optional 7z
  header encryption.
- Configurable extraction, convenient extract-here variants, and integrity
  testing.
- Cancellable operation window with parsed progress, elapsed and estimated
  time, item statistics, and a bounded collapsible technical log.
- English source interface, Russian gettext translation, desktop metadata, and
  scalable application icons.
- Meson installation with `DESTDIR` staging and an editable Python development
  package.
- Unit and real-7z integration tests with an 85% coverage gate.
- Continuous integration for pushes and pull requests, plus tag-driven GitHub
  Releases built from this changelog.

### Security

- Archive operations use argument arrays without a shell.
- Passwords are excluded from process arguments, logs, and persisted state.
- Nautilus selections are transferred through mode-0600 manifests and limited
  to native filesystem paths.

[Unreleased]: https://github.com/michaelbrylevskii/nautilus-7zip/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/michaelbrylevskii/nautilus-7zip/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/michaelbrylevskii/nautilus-7zip/releases/tag/v0.1.0
