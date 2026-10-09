"""Unit tests for permanent delete guardrails, execution, and undo restrictions."""

from inboxgpt.agent.audit import AuditManager
from inboxgpt.agent.tools import ApprovalRequiredTools
from inboxgpt.agent.triage_agent import is_protected_email
from inboxgpt.gmail.mock_client import MockGmailClient
from inboxgpt.gmail.models import ActionType, ProposedAction, RiskLevel


def test_permanent_delete_safety_invariants_blocks_critical_emails():
    client = MockGmailClient()
    # Find protected emails (e.g. security audit or starred)
    protected_msgs = [e for e in client._emails if is_protected_email(e)[0]]
    assert len(protected_msgs) > 0

    target = protected_msgs[0]
    is_prot, reason = is_protected_email(target)
    assert is_prot is True
    assert len(reason) > 0


def test_permanent_delete_purges_unprotected_email_and_cannot_be_undone(tmp_path):
    journal_file = tmp_path / "audit_perm_del.json"
    audit_mgr = AuditManager(journal_file=journal_file)

    client = MockGmailClient()
    initial_count = len(client._emails)

    # Pick an unprotected email (e.g. newsletter)
    unprotected = [e for e in client._emails if not is_protected_email(e)[0]][0]
    target_id = unprotected.id

    action = ProposedAction(
        id="act_del_01",
        title="Permanent Delete",
        action_type=ActionType.DELETE,
        target_email_ids=[target_id],
        count=1,
        risk_level=RiskLevel.HIGH,
        description="Permanently delete test email",
    )

    tools = ApprovalRequiredTools(client)
    res = tools.execute_delete(action)
    assert res.success is True
    assert res.affected_count == 1

    # Email is gone from client inbox AND trash
    assert len(client._emails) == initial_count - 1
    assert target_id not in [e.id for e in client._emails]
    assert target_id not in [e.id for e in client._trash]

    # Verify audit log records it as DELETE
    entry = audit_mgr.record_action(action, res)
    last = audit_mgr.get_entry_by_id(entry.id)
    assert last is not None
    assert last.action_type == "delete"

    # Verify undo refuses to restore permanent delete
    undo_res = audit_mgr.execute_undo(client, action_id=last.id)
    assert undo_res.success is False
    assert "Permanent deletion cannot be undone" in undo_res.message
