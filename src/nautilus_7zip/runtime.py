"""Runtime compatibility rules for the GTK helper."""

from __future__ import annotations

from dataclasses import dataclass

Version = tuple[int, int, int]

MINIMUM_GTK_VERSION: Version = (4, 14, 0)
MINIMUM_ADWAITA_VERSION: Version = (1, 5, 0)


@dataclass(frozen=True, slots=True)
class RuntimeIssue:
    """A toolkit component that is older than the supported baseline."""

    component: str
    actual: Version
    required: Version


def check_runtime_versions(
    gtk_version: Version,
    adwaita_version: Version,
) -> tuple[RuntimeIssue, ...]:
    """Return every unsupported toolkit component in display order."""

    issues = []
    if gtk_version < MINIMUM_GTK_VERSION:
        issues.append(RuntimeIssue("GTK", gtk_version, MINIMUM_GTK_VERSION))
    if adwaita_version < MINIMUM_ADWAITA_VERSION:
        issues.append(
            RuntimeIssue("libadwaita", adwaita_version, MINIMUM_ADWAITA_VERSION)
        )
    return tuple(issues)


def format_version(version: Version) -> str:
    """Format a three-component library version."""

    return ".".join(str(component) for component in version)
