"""Validated option models shared by the UI and command builder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pathlib import Path


class ArchiveFormat(StrEnum):
    """Archive formats supported for creation in the first release."""

    SEVEN_ZIP = "7z"
    ZIP = "zip"

    @property
    def suffix(self) -> str:
        return f".{self.value}"


class CompressionLevel(IntEnum):
    """Compression levels understood by 7-Zip."""

    STORE = 0
    FASTEST = 1
    FAST = 3
    NORMAL = 5
    MAXIMUM = 7
    ULTRA = 9


class OverwriteMode(StrEnum):
    """7-Zip overwrite policies used during extraction."""

    OVERWRITE = "-aoa"
    SKIP = "-aos"
    AUTO_RENAME = "-aou"


@dataclass(frozen=True, slots=True)
class CreateOptions:
    """Options for creating an archive."""

    sources: tuple[Path, ...]
    output: Path
    archive_format: ArchiveFormat = ArchiveFormat.SEVEN_ZIP
    level: CompressionLevel = CompressionLevel.NORMAL
    threads: int | None = None
    solid: bool = True
    password: str | None = None
    encrypt_headers: bool = False
    verify: bool = False

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("At least one source is required")
        if self.threads is not None and self.threads < 1:
            raise ValueError("Thread count must be positive or None")
        if self.encrypt_headers and self.archive_format is not ArchiveFormat.SEVEN_ZIP:
            raise ValueError("Header encryption is only supported by the 7z format")
        if self.encrypt_headers and not self.password:
            raise ValueError("Header encryption requires a password")


@dataclass(frozen=True, slots=True)
class ExtractOptions:
    """Options for extracting one archive."""

    archive: Path
    destination: Path
    overwrite: OverwriteMode = OverwriteMode.AUTO_RENAME
    password: str | None = None


@dataclass(frozen=True, slots=True)
class IntegrityTestOptions:
    """Options for testing archive integrity."""

    archive: Path
    password: str | None = None
