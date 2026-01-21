from sentineltray.cli import _parse_command


def test_parse_command_basic() -> None:
    assert _parse_command("") == ("", "")
    assert _parse_command("status") == ("status", "")
    assert _parse_command("PAUSE") == ("pause", "")
    assert _parse_command("watch 5") == ("watch", "5")
    assert _parse_command("open logs") == ("open", "logs")


def test_parse_command_unknown() -> None:
    assert _parse_command("xyz") == ("xyz", "")
