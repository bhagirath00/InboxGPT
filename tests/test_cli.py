"""Tests for InboxGPT CLI subcommands."""

from typer.testing import CliRunner
from inboxgpt.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "InboxGPT" in result.output
    assert "analyze" in result.output
    assert "cleanup" in result.output
    assert "search" in result.output


def test_cli_analyze_mock():
    result = runner.invoke(app, ["analyze", "--mock"])
    assert result.exit_code == 0
    assert "InboxGPT Analysis Report" in result.output
    assert "Important" in result.output
    assert "Newsletters" in result.output


def test_cli_search_mock():
    result = runner.invoke(app, ["search", "security", "--mock"])
    assert result.exit_code == 0
    assert "Search Results" in result.output


def test_cli_auth_status():
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0


def test_cli_switch_help():
    result = runner.invoke(app, ["switch", "--help"])
    assert result.exit_code == 0
    assert "Switch active Gmail account" in result.output


def test_cli_login_help():
    result = runner.invoke(app, ["login", "--help"])
    assert result.exit_code == 0


def test_cli_logout(tmp_path, monkeypatch):
    from inboxgpt.config import Config
    import inboxgpt.cli as cli_mod

    test_config = Config(config_dir=tmp_path)
    test_config.token_file.write_text("{}", encoding="utf-8")
    test_config.cache_file.write_text("[]", encoding="utf-8")
    assert test_config.token_file.exists()
    assert test_config.cache_file.exists()

    monkeypatch.setattr(cli_mod, "config", test_config)
    result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0
    assert "Successfully logged out" in result.output
    assert not test_config.token_file.exists()
    assert not test_config.cache_file.exists()
