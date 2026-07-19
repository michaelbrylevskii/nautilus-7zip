import pytest

from nautilus_7zip.progress import (
    FileProgress,
    format_duration,
    parse_file_progress,
    parse_progress,
    render_terminal_output,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  0% 1 - file", 0),
        (" 42% 10 + file", 42),
        ("100% Everything is Ok", 100),
        ("10% then 55%", 55),
        ("Physical Size = 100", None),
        ("123% is not valid", None),
        ("", None),
    ],
)
def test_parse_progress(text: str, expected: int | None) -> None:
    assert parse_progress(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "  0%\b\b\b\b    \b\b\b\b+ Ya_em_golubey/region/r.0.0.mca\n",
            "+ Ya_em_golubey/region/r.0.0.mca\n",
        ),
        (
            "  0M Scan  /usr/bin/" + "\b" * 20 + " " * 20 + "\b" * 20 + "1 file\n",
            "1 file\n",
        ),
        ("old\rnew\n", "new\n"),
        ("plain\x00 text\x07\n", "plain text\n"),
        ("\x1b[31mError\x1b[0m\n", "Error\n"),
        ("name\tvalue\n", "name    value\n"),
        ("partial", "partial"),
        ("", ""),
    ],
)
def test_render_terminal_output(text: str, expected: str) -> None:
    assert render_terminal_output(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+ first\n+ second\n", FileProgress(processed=2)),
        ("- first\nT second\nU third\n", FileProgress(processed=3)),
        (
            "Add new data to archive: 2915 files, 20 GiB\n",
            FileProgress(total=2915),
        ),
        ("Add new data to archive: 1 file, 10 bytes\n", FileProgress(total=1)),
        ("Files: 42\n", FileProgress(total=42)),
        ("Scanning the drive: 8 files\n", FileProgress()),
        ("plain output\n", FileProgress()),
    ],
)
def test_parse_file_progress(text: str, expected: FileProgress) -> None:
    assert parse_file_progress(text) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (-1, "0:00"),
        (0, "0:00"),
        (9.9, "0:09"),
        (65, "1:05"),
        (3661, "1:01:01"),
    ],
)
def test_format_duration(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected
