from pathlib import Path


def test_prepare_portable_runtime_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    ps1 = root / "scripts" / "prepare_portable_runtime.ps1"
    cmd = root / "scripts" / "prepare_portable_runtime.cmd"
    assert ps1.exists()
    assert cmd.exists()
