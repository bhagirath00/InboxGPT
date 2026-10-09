"""Tests for Reliability Basics: Retries (tenacity), Log Rotation, and Token Refresh."""

from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock, patch
from google.auth.exceptions import RefreshError
from tenacity import retry, stop_after_attempt, wait_fixed

from inboxgpt.auth.oauth import get_credentials
from inboxgpt.config import configure_logging


def test_log_rotation_configuration():
    """Verify logger uses RotatingFileHandler with 5MB maxBytes and 3 backups."""
    log = configure_logging()
    rotating_handlers = [h for h in log.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) > 0, "Logger must have at least one RotatingFileHandler"
    handler = rotating_handlers[0]
    assert handler.maxBytes == 5 * 1024 * 1024, "Max log bytes must be 5MB"
    assert handler.backupCount == 3, "Backup count must be 3"


def test_tenacity_retry_recovers_after_temporary_failure():
    """Verify tenacity exponential retry mechanism executes retries and succeeds."""
    attempts = 0

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.01))
    def flaky_network_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Temporary network timeout")
        return "success"

    result = flaky_network_call()
    assert result == "success"
    assert attempts == 3


def test_refresherror_purges_stale_token_file(tmp_path):
    """When Google OAuth refresh raises RefreshError, stale token file is deleted."""
    fake_token_file = tmp_path / "token.json"
    fake_token_file.write_text('{"token": "fake", "refresh_token": "fake"}', encoding="utf-8")

    with patch("inboxgpt.auth.oauth.config.token_file", fake_token_file):
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file") as mock_creds_factory:
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.refresh_token = "fake"
            mock_creds.refresh.side_effect = RefreshError("Token has been expired or revoked.")
            mock_creds_factory.return_value = mock_creds

            # Calling get_credentials(interactive=False) should catch RefreshError and return None
            creds = get_credentials(interactive=False)
            assert creds is None
            # Verify corrupted token file was unlinked/purged
            assert not fake_token_file.exists(), "Stale token file should be removed on RefreshError"
