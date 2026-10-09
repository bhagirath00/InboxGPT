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


def test_keyword_search_and_fallback():
    from inboxgpt.agent.assistant import ask_executive_agent, _local_search_fallback, _local_summary_fallback

    client = MockGmailClient()
    emails = client.list_messages(max_results=5)

    # Test summary fallback
    summary_text = _local_summary_fallback(emails)
    assert "Inbox Overview" in summary_text
    assert "Priority" in summary_text

    # Test search fallback
    search_text = _local_search_fallback("google", emails)
    # If no google in mock emails, search_text is None
    # Test with actual sender
    if emails:
        first_sender = emails[0].sender_name or emails[0].sender
        found = _local_search_fallback(first_sender, emails)
        assert found is not None
        assert first_sender in found

    # Test ask_executive_agent (either via live LLM or local fallback)
    ans = ask_executive_agent("give me summary overview", client, emails)
    assert "summary" in ans.lower() or "overview" in ans.lower()


def test_modal_previews():
    from inboxgpt.gmail.models import ActionType, ProposedAction, RiskLevel
    from inboxgpt.tui.modals import ApprovalModal, QuitConfirmModal

    client = MockGmailClient()
    emails = client.list_messages(max_results=5)

    prop = ProposedAction(
        id="act_1",
        title="Move to Trash",
        action_type=ActionType.TRASH,
        target_email_ids=[emails[0].id, emails[1].id] if len(emails) >= 2 else [emails[0].id],
        count=2 if len(emails) >= 2 else 1,
        risk_level=RiskLevel.MEDIUM,
        description="Move useless emails to trash",
    )

    modal = ApprovalModal(prop, emails=emails)
    assert len(modal.emails) == len(emails)
    assert modal.action.id == "act_1"

    quit_modal = QuitConfirmModal()
    assert quit_modal is not None

    from inboxgpt.tui.modals import ReviewTargetEmailsModal
    review_modal = ReviewTargetEmailsModal(prop, emails)
    assert len(review_modal.target_emails) >= 1
    assert review_modal.action.id == "act_1"
