from pathlib import Path


def test_privacy_policy_exists() -> None:
    policy = Path(__file__).resolve().parents[1] / "PRIVACY.md"
    content = policy.read_text(encoding="utf-8")
    assert "LGPD" in content
    assert "%USERPROFILE%\\AppData\\Local\\AxonZ\\SentinelTray\\UserData" in content
    assert "config.local.yaml" in content
