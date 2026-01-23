from pathlib import Path


def test_bootstrap_runtime_script_mentions_pip_install() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "bootstrap_runtime.py"
    content = script.read_text(encoding="utf-8")
    assert "get-pip.py" in content
    assert "ensurepip" in content
    assert "site-packages" in content
    assert "import site" in content
