"""Validated option models shared by the UI and command builder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pathlib import Path


class ArchiveFormat(StrEnum):
    """Archive formats supported for creation."""

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


class SolidBlock(StrEnum):
    """7z solid-block modes exposed by the creation UI."""

    AUTO = "on"
    NON_SOLID = "off"
    MIB_256 = "256m"
    GIB_1 = "1g"
    GIB_4 = "4g"
    FULL = "18446744073709551615b"


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
    solid_block: SolidBlock | None = SolidBlock.AUTO
    volume_size: int | None = None
    password: str | None = None
    encrypt_headers: bool = False
    verify: bool = False

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("At least one source is required")
        if self.threads is not None and self.threads < 1:
            raise ValueError("Thread count must be positive or None")
        if self.volume_size is not None and self.volume_size < 1:
            raise ValueError("Volume size must be positive or None")
        if self.archive_format is not ArchiveFormat.SEVEN_ZIP and self.solid_block is not None:
            raise ValueError("Solid blocks are only supported by the 7z format")
        if self.encrypt_headers and self.archive_format is not ArchiveFormat.SEVEN_ZIP:
            raise ValueError("Header encryption is only supported by the 7z format")
        if self.encrypt_headers and not self.password:
            raise ValueError("Header encryption requires a password")

    @property
    def archive_path(self) -> Path:
        """Return the final archive name including its expected suffix."""

        if self.output.name.casefold().endswith(self.archive_format.suffix):
            return self.output
        return self.output.with_name(self.output.name + self.archive_format.suffix)

    @property
    def verification_path(self) -> Path:
        """Return the path 7-Zip must open to test the resulting archive."""

        archive = self.archive_path
        if self.volume_size is None:
            return archive
        return archive.with_name(archive.name + ".001")


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
