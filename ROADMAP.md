# Roadmap

This roadmap records the intended product direction without promising dates.
Priorities may change in response to compatibility findings and user feedback.

## v0.2.0 — Reliability and distribution

1. Discover and validate `7z` and `7zz` backends, with a strict executable
   override and actionable startup errors.
2. Add a privacy-safe diagnostics view containing application, backend,
   Nautilus, GTK, libadwaita, and locale versions.
3. Verify clean installation and removal from a tagged source archive across a
   small supported-distribution matrix.
4. Publish a maintained Arch/Manjaro package recipe.
5. Expand the Xvfb-backed GTK smoke suite and add contract tests for the
   Nautilus menu provider.

## v0.3.0 — Everyday workflow

- Persist non-secret defaults with GSettings.
- Add reusable Fast, Balanced, Maximum, and Custom presets.
- Improve encrypted-archive prompts and error explanations.
- Add completion notifications and an **Open Destination** action.
- Support queued extraction of multiple selected archives with explicit
  collision behavior.

Passwords and other secrets will never be persisted as defaults.

## v0.4.0 — Advanced compression

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
