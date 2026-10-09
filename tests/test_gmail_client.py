"""Tests for Mock Gmail service client."""

from inboxgpt.gmail.mock_client import MockGmailClient


def test_mock_client_list_and_search():
    client = MockGmailClient()
    emails = client.list_messages(max_results=10)
    assert len(emails) > 0

    # Search for an email containing 'security'
    results = client.search_messages if hasattr(client, "search_messages") else client.list_messages(query="Security")
    assert any("Security" in e.subject for e in results)


def test_mock_client_batch_trash():
    client = MockGmailClient()
    initial_emails = client.list_messages()
    initial_count = len(initial_emails)

    to_trash = [initial_emails[0].id]
    result = client.batch_trash(to_trash)

    assert result.success is True
    assert result.affected_count == 1

    remaining = client.list_messages()
    assert len(remaining) == initial_count - 1
    assert to_trash[0] not in [e.id for e in remaining]


def test_mock_client_batch_archive():
    client = MockGmailClient()
    initial_emails = client.list_messages()
    target_id = initial_emails[0].id

    result = client.batch_archive([target_id])
    assert result.success is True

    # Check that INBOX label is removed
    msg = client.get_message(target_id)
    assert "INBOX" not in msg.labels


def test_mock_client_batch_label():
    client = MockGmailClient()
    emails = client.list_messages()
    target_id = emails[0].id

    result = client.batch_add_label([target_id], "CUSTOM_LABEL")
    assert result.success is True

    msg = client.get_message(target_id)
    assert "CUSTOM_LABEL" in msg.labels
