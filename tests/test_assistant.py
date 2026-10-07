"""Tests for Executive Assistant agent and persistent memory."""

from inboxgpt.agent.memory import AgentMemory
from inboxgpt.gmail.mock_client import MockGmailClient
from inboxgpt.agent.assistant import build_assistant_tools


def test_agent_memory(tmp_path):
    mem_file = tmp_path / "memory.json"
    mem = AgentMemory(memory_file=mem_file)

    rules = mem.get_rules()
    assert len(rules) >= 3

    mem.add_rule("Always keep emails from Stripe")
    updated = mem.get_rules()
    assert "Always keep emails from Stripe" in updated

    mem.remove_rule("Always keep emails from Stripe")
    final_rules = mem.get_rules()
    assert "Always keep emails from Stripe" not in final_rules


def test_assistant_tools_building():
    client = MockGmailClient()
    emails = client.list_messages(max_results=5)
    tools = build_assistant_tools(client, emails)
    tool_names = [t.name for t in tools]

    assert "search_mailbox" in tool_names
    assert "read_email_details" in tool_names
    assert "create_email_draft" in tool_names
    assert "save_agent_memory" in tool_names
    assert "get_agent_memories" in tool_names


def test_create_draft_mock():
    client = MockGmailClient()
    res = client.create_draft("test@example.com", "Meeting Followup", "Thanks for your time.")
    assert res.success is True
    assert "Draft created" in res.message
