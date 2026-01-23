from pathlib import Path


def test_package_portable_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    ps1 = root / "scripts" / "package_portable.ps1"
    cmd = root / "scripts" / "package_portable.cmd"
    assert ps1.exists()
    assert cmd.exists()
