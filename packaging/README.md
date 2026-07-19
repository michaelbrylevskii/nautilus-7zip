# Packaging

Meson supports `DESTDIR` staging and is the canonical packaging entry point.

No distribution-specific recipe is currently maintained. Tagged GitHub
Releases provide the Meson source archive and SHA-256 checksum expected by
downstream packagers. Package recipes must use verifiable release sources and
must preserve the runtime requirements documented in `README.md`.
