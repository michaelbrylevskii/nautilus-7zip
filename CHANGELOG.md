# Changelog

All notable changes will be documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases will use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Initial Nautilus **7-Zip** submenu.
- Standalone GTK 4/libadwaita archive creation and extraction dialogs.
- 7z and ZIP creation with compression and encryption controls.
- Quick archive creation, extraction variants, and integrity testing.
- Asynchronous progress display and cancellation.
- Meson installation and gettext localization scaffolding.
- Automated test suite with an 85% coverage gate.

### Fixed

- Keep the application alive when replacing create/extract forms with the
  operation progress window.
- Preserve helper errors in the Nautilus journal instead of discarding stderr.
