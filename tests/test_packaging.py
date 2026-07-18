from pathlib import Path


def test_extension_module_does_not_shadow_application_package() -> None:
    project_root = Path(__file__).parents[1]
    extension_modules = tuple((project_root / "src/extension").glob("*.py"))
    assert extension_modules
    assert all(module.stem != "nautilus_7zip" for module in extension_modules)
