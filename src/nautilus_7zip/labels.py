"""Formatting helpers for user-visible labels."""


def escape_menu_mnemonics(label: str) -> str:
    """Escape GTK mnemonic markers while preserving literal underscores."""

    return label.replace("_", "__")
