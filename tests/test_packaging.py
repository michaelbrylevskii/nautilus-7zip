import re
import tomllib
from pathlib import Path

from nautilus_7zip import __version__

PROJECT_ROOT = Path(__file__).parents[1]
APP_ID = "io.github.michaelbrylevskii.Nautilus7Zip"


def test_extension_module_does_not_shadow_application_package() -> None:
    extension_modules = tuple((PROJECT_ROOT / "src/extension").glob("*.py"))
    assert extension_modules
    assert all(module.stem != "nautilus_7zip" for module in extension_modules)


def test_project_versions_are_synchronized() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    meson = (PROJECT_ROOT / "meson.build").read_text(encoding="utf-8")
    meson_version = re.search(r"version: '([^']+)'", meson)

    assert meson_version is not None
    assert pyproject["project"]["version"] == meson_version.group(1) == __version__


def test_application_identity_matches_github_owner() -> None:
    application = (PROJECT_ROOT / "src/nautilus_7zip/application.py").read_text(encoding="utf-8")
    desktop = PROJECT_ROOT / "data" / f"{APP_ID}.desktop.in"
    regular_icon = PROJECT_ROOT / "data/icons/hicolor/scalable/apps" / f"{APP_ID}.svg"
    symbolic_icon = PROJECT_ROOT / "data/icons/hicolor/symbolic/apps" / f"{APP_ID}-symbolic.svg"

    assert f'APP_ID = "{APP_ID}"' in application
    assert desktop.is_file()
    desktop_text = desktop.read_text(encoding="utf-8")
    assert f"Icon={APP_ID}" in desktop_text
    assert "Exec=nautilus-7zip open %F" in desktop_text
    assert regular_icon.is_file()
    assert symbolic_icon.is_file()
