from __future__ import annotations

from nautilus_7zip.runtime import (
    MINIMUM_ADWAITA_VERSION,
    MINIMUM_GTK_VERSION,
    RuntimeIssue,
    check_runtime_versions,
    format_version,
)


def test_supported_runtime_has_no_issues() -> None:
    assert check_runtime_versions(MINIMUM_GTK_VERSION, MINIMUM_ADWAITA_VERSION) == ()
    assert check_runtime_versions((4, 22, 1), (1, 9, 0)) == ()


def test_runtime_issues_are_reported_in_display_order() -> None:
    assert check_runtime_versions((4, 12, 9), (1, 4, 2)) == (
        RuntimeIssue("GTK", (4, 12, 9), (4, 14, 0)),
        RuntimeIssue("libadwaita", (1, 4, 2), (1, 5, 0)),
    )


def test_format_version() -> None:
    assert format_version((4, 14, 0)) == "4.14.0"
