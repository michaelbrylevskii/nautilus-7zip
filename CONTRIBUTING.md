# Contributing

Thank you for helping improve 7-Zip for Nautilus.

## Before opening a change

1. Read [`AGENTS.md`](AGENTS.md), especially the process and security boundaries.
2. Keep the Nautilus extension thin and put reusable behavior in testable modules.
3. Add or update tests before changing command construction or path handling.
4. Use English source strings and gettext for user-visible text.

## Checks

```bash
ruff check .
pytest
meson setup build
meson compile -C build
meson test -C build --print-errorlogs
```

Coverage must remain at least 85%. New non-UI modules should normally achieve
90% or better.

## Commit style

Use short imperative subjects, for example:

```text
Add split-volume controls
Fix compound archive suffix detection
Keep passwords out of process arguments
```

Separate refactoring from behavior changes where practical.

## Reporting bugs

Include:

- distribution and desktop session;
- Nautilus and nautilus-python versions;
- output of `7z i` with personal paths removed;
- selected archive format and relevant options;
- expected and actual behavior.

Never publish archive passwords, private filenames, or unredacted logs.
