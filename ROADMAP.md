# Roadmap

This roadmap records the intended product direction without promising dates.
Priorities may change in response to compatibility findings and user feedback.

## v0.2.0 — Reliability and diagnostics

- [x] Discover and validate `7z` and `7zz` backends, with a strict executable
   override and actionable startup errors.
- [x] Add a privacy-safe diagnostics view containing application, backend,
   Nautilus, GTK, libadwaita, and locale versions.
- [x] Validate the supported GTK/libadwaita runtime before presenting operation
   windows.
- [x] Exercise real GTK widgets under Xvfb in CI and release verification.
- [x] Dispatch desktop `Open With…` requests by selection type.

## v0.3.0 — Distribution and integration

- Verify clean installation and removal from tagged source archives across a
  small supported-distribution matrix.
- Publish a maintained Arch/Manjaro package recipe.
- Expand GTK widget smoke coverage and add contract tests for the Nautilus menu
  provider.

## v0.4.0 — Everyday workflow

- Persist non-secret defaults with GSettings.
- Add reusable Fast, Balanced, Maximum, and Custom presets.
- Improve encrypted-archive prompts and error explanations.
- Add completion notifications and an **Open Destination** action.
- Support queued extraction of multiple selected archives with explicit
  collision behavior.

Passwords and other secrets will never be persisted as defaults.

## v0.5.0 — Advanced compression

- Expose format-aware compression methods, dictionary sizes, word sizes, and
  memory limits where the selected backend supports them.
- Show estimated memory requirements before starting expensive configurations.
- Keep incompatible or irrelevant controls out of the active form.

## Later exploration

- `.tar.zst`, `.tar.xz`, and `.tar.gz` creation as explicit two-stage
  workflows with safe cancellation, atomic output, and meaningful progress.
- Additional native distribution packages.
- Release provenance attestations and stronger repository policy automation.

Flatpak and AppImage are not near-term targets. A Nautilus extension must be
installed where the host file manager can load it, and the helper intentionally
uses a host-provided archiver and native filesystem paths. Native distribution
packages fit those boundaries better.
