"""Tests for OAuth 1-minute timeout and token destruction behavior."""

import pytest
from unittest.mock import MagicMock, patch
from google_auth_oauthlib.flow import WSGITimeoutError
from inboxgpt.auth.oauth import run_oauth_flow
from inboxgpt.config import Config


def test_oauth_timeout_destroys_token_and_raises(tmp_path, monkeypatch):
    """Verify that when OAuth times out after 60s, any token/session is destroyed."""
    test_config = Config(config_dir=tmp_path)
    test_config.token_file.write_text('{"token": "dummy"}', encoding="utf-8")
    test_config.cache_file.write_text('[]', encoding="utf-8")
    assert test_config.token_file.exists()

    monkeypatch.setattr("inboxgpt.auth.oauth.config", test_config)
    monkeypatch.setattr("inboxgpt.config.config", test_config)

    # Mock InstalledAppFlow to simulate WSGITimeoutError
    mock_flow = MagicMock()
    mock_flow.run_local_server.side_effect = WSGITimeoutError("Timed out waiting for response")

    with patch("inboxgpt.auth.oauth.InstalledAppFlow.from_client_config", return_value=mock_flow):
        with patch.object(test_config, "get_google_client_id", return_value="dummy-id"):
            with patch.object(test_config, "get_google_client_secret", return_value="dummy-secret"):
                with pytest.raises(TimeoutError) as exc_info:
                    run_oauth_flow(timeout_seconds=60)

                assert "Google Sign-In timed out after 60 seconds" in str(exc_info.value)
                assert "destroyed" in str(exc_info.value)

    # Verify that token and session cache were destroyed
    assert not test_config.token_file.exists()
    assert not test_config.cache_file.exists()


def test_cli_login_timeout_handled_gracefully(tmp_path, monkeypatch):
    """Verify CLI login command catches TimeoutError and displays message."""
    from typer.testing import CliRunner
    from inboxgpt.cli import app
    import inboxgpt.cli as cli_mod

    test_config = Config(config_dir=tmp_path)
    monkeypatch.setattr(cli_mod, "config", test_config)
    monkeypatch.setattr(
        cli_mod,
        "run_oauth_flow",
        MagicMock(side_effect=TimeoutError("Google Sign-In timed out after 60 seconds. No login was completed, and any pending token/session was destroyed.")),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["login"])
    assert "Sign-in Timeout" in result.output
    assert "Google Sign-In timed out after 60 seconds" in result.output
