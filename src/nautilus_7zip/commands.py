"""Safe construction of 7-Zip process arguments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import ArchiveFormat, CreateOptions, ExtractOptions, IntegrityTestOptions


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """A command and optional data written to its standard input."""

    argv: tuple[str, ...]
    stdin_text: str | None = None
    title: str = "7-Zip"

    @property
    def executable(self) -> str:
        return self.argv[0]


class SevenZipCommandBuilder:
    """Build 7-Zip commands without invoking a shell."""

    _progress_flags = ("-bb1", "-bsp1", "-bso1", "-bse1")

    def __init__(self, executable: str = "7z") -> None:
        if not executable:
            raise ValueError("7-Zip executable must not be empty")
        self.executable = executable

    def create(self, options: CreateOptions) -> CommandSpec:
        output = _with_expected_suffix(options.output, options.archive_format)
        args = [
            self.executable,
            "a",
            f"-t{options.archive_format.value}",
            f"-mx={int(options.level)}",
            "-mmt=on" if options.threads is None else f"-mmt={options.threads}",
            *self._progress_flags,
        ]

        if options.archive_format is ArchiveFormat.SEVEN_ZIP:
            args.append("-ms=on" if options.solid else "-ms=off")
        else:
            args.append("-mm=Deflate")

        stdin_text = _append_password_options(
            args,
            options.password,
            include_switch=True,
            encrypt_headers=options.encrypt_headers,
            archive_format=options.archive_format,
        )
        args.extend((str(output), "--", *(str(path) for path in options.sources)))
        return CommandSpec(tuple(args), stdin_text, f"Create {output.name}")

    def extract(self, options: ExtractOptions) -> CommandSpec:
        args = [
            self.executable,
            "x",
            f"-o{options.destination}",
            options.overwrite.value,
            *self._progress_flags,
        ]
        stdin_text = _append_password_options(args, options.password)
        args.extend(("--", str(options.archive)))
        return CommandSpec(tuple(args), stdin_text, f"Extract {options.archive.name}")

    def test(self, options: IntegrityTestOptions) -> CommandSpec:
        args = [self.executable, "t", *self._progress_flags]
        stdin_text = _append_password_options(args, options.password)
        args.extend(("--", str(options.archive)))
        return CommandSpec(tuple(args), stdin_text, f"Test {options.archive.name}")


def _with_expected_suffix(output: Path, archive_format: ArchiveFormat) -> Path:
    if output.name.lower().endswith(archive_format.suffix):
        return output
    return output.with_name(output.name + archive_format.suffix)


def _append_password_options(
    args: list[str],
    password: str | None,
    *,
    include_switch: bool = False,
    encrypt_headers: bool = False,
    archive_format: ArchiveFormat | None = None,
) -> str | None:
    if not password:
        return None

    # Creating an encrypted archive requires a bare -p switch. Reading an
    # encrypted archive must omit -p: 7-Zip then prompts and consumes stdin.
    # In both cases, the secret stays out of /proc/<pid>/cmdline.
    if include_switch:
        args.append("-p")
    if archive_format is ArchiveFormat.ZIP:
        args.append("-mem=AES256")
    if encrypt_headers:
        args.append("-mhe=on")
    return password + "\n"
