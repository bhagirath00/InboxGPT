"""Tests for the Background Daemon and Executive Briefing Engine."""

import os
from pathlib import Path
from inboxgpt.agent.daemon import DaemonEngine
from inboxgpt.gmail.mock_client import MockGmailClient
from inboxgpt.gmail.models import EmailCategory, EmailMessage


def test_daemon_engine_generate_briefing():
    client = MockGmailClient()
    engine = DaemonEngine(client=client)

    emails = client.list_messages()
    briefing = engine.generate_briefing(emails)

    assert isinstance(briefing, str)
    assert len(briefing) > 50
    assert "Executive" in briefing or "Action" in briefing or "Inbox" in briefing


def test_daemon_engine_run_cycle(tmp_path, monkeypatch):
    from inboxgpt.config import Config
    test_config = Config(config_dir=tmp_path)
    monkeypatch.setattr("inboxgpt.agent.daemon.config", test_config)

    client = MockGmailClient()
    engine = DaemonEngine(client=client)
    engine.briefings_dir = tmp_path / "briefings"
    engine.briefings_dir.mkdir(parents=True, exist_ok=True)
    engine.latest_briefing_file = engine.briefings_dir / "latest_briefing.md"
    engine.history_file = engine.briefings_dir / "history.json"

    briefing, count = engine.run_cycle(auto_archive_clutter=False)

    assert count > 0
    assert engine.latest_briefing_file.exists()
    assert engine.history_file.exists()

    saved_text = engine.latest_briefing_file.read_text(encoding="utf-8")
    assert saved_text == briefing


def test_daemon_empty_inbox():
    class EmptyClient(MockGmailClient):
        def list_messages(self, *args, **kwargs):
            return []

    engine = DaemonEngine(client=EmptyClient())
    briefing = engine.generate_briefing([])
    assert "Inbox Zero" in briefing
