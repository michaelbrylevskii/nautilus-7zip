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

## Releases

Releases are automated from annotated or lightweight tags named
`vMAJOR.MINOR.PATCH`. Before pushing a tag:

1. Set the same version in `meson.build`, `pyproject.toml`, and
   `src/nautilus_7zip/__init__.py`.
2. Move the completed entries from **Unreleased** to a dated, matching section
   in `CHANGELOG.md`.
3. Run the full check sequence above from a clean checkout.
4. Create the tag on the commit to release and push it to GitHub.

The release workflow rejects a tag that does not match the project version or
has no matching changelog section. A successful run publishes that changelog
section as the release notes and attaches a Meson source archive plus its
SHA-256 checksum. Do not manually upload differently built files under the same
release version.
