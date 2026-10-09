"""Tests for Audit Log Journal and Transactional Undo Capability."""

from typer.testing import CliRunner

from inboxgpt.agent.audit import AuditManager
from inboxgpt.agent.tools import ApprovalRequiredTools
from inboxgpt.cli import app
from inboxgpt.gmail.mock_client import MockGmailClient
from inboxgpt.gmail.models import ActionType, ProposedAction, RiskLevel

runner = CliRunner()


def test_audit_manager_records_and_retrieves_actions(tmp_path):
    journal_file = tmp_path / "audit_test.json"
    mgr = AuditManager(journal_file=journal_file)

    action = ProposedAction(
        id="act_01",
        title="Trash Promotions",
        action_type=ActionType.TRASH,
        target_email_ids=["msg_01", "msg_02"],
        description="Clean up promotions",
        risk_level=RiskLevel.HIGH,
        count=2,
    )
    from inboxgpt.gmail.models import ActionResult
    res = ActionResult(action_id="act_01", success=True, affected_count=2, message="Success")

    entry = mgr.record_action(action, res)
    assert entry.action_type == "trash"
    assert entry.affected_count == 2
    assert entry.undone is False

    last = mgr.get_last_undoable()
    assert last is not None
    assert last.id == entry.id


def test_undo_reverts_trashed_emails(tmp_path):
    journal_file = tmp_path / "audit_test_undo.json"
    mgr = AuditManager(journal_file=journal_file)

    client = MockGmailClient()
    initial_inbox_count = len(client._emails)
    assert len(client._trash) == 0

    # Trash first email
    target_id = client._emails[0].id
    action = ProposedAction(
        id="act_trash",
        title="Trash Single Email",
        action_type=ActionType.TRASH,
        target_email_ids=[target_id],
        description="Trash single email",
        risk_level=RiskLevel.HIGH,
        count=1,
    )

    tools = ApprovalRequiredTools(client)
    trash_res = tools.execute_trash(action)
    assert trash_res.success is True
    assert len(client._trash) == 1
    assert len(client._emails) == initial_inbox_count - 1

    # Record and Undo
    mgr.record_action(action, trash_res)
    undo_res = mgr.execute_undo(client)

    assert undo_res.success is True
    assert undo_res.affected_count == 1
    # Email should be restored to inbox and removed from trash
    assert len(client._trash) == 0
    assert len(client._emails) == initial_inbox_count


def test_cli_undo_command(tmp_path):
    result = runner.invoke(app, ["undo", "--help"])
    assert result.exit_code == 0
    assert "Revert an approved cleanup action" in result.output


def test_cli_history_command():
    result = runner.invoke(app, ["history", "--limit", "5"])
    assert result.exit_code == 0


def test_selective_undo_by_action_id(tmp_path):
    journal_file = tmp_path / "audit_selective.json"
    mgr = AuditManager(journal_file=journal_file)
    client = MockGmailClient()

    # Create two actions
    a1 = ProposedAction(
        id="act_01",
        title="Trash 1",
        action_type=ActionType.TRASH,
        target_email_ids=[client._emails[0].id],
        count=1,
        description="Trash 1",
    )
    from inboxgpt.gmail.models import ActionResult
    r1 = ActionResult(action_id="act_01", success=True, affected_count=1, message="ok")
    mgr.record_action(a1, r1)

    a2 = ProposedAction(
        id="act_02",
        title="Trash 2",
        action_type=ActionType.TRASH,
        target_email_ids=[client._emails[1].id],
        count=1,
        description="Trash 2",
    )
    r2 = ActionResult(action_id="act_02", success=True, affected_count=1, message="ok")
    entry2 = mgr.record_action(a2, r2)

    # Undo specific action a1 by ID
    entry1 = mgr._load_entries()[0]
    undo_res = mgr.execute_undo(client, action_id=entry1.id)
    assert undo_res.success is True
    assert entry1.id in undo_res.message

