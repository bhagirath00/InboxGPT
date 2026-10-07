"""Tests for InboxGPT data models."""

from inboxgpt.gmail.models import (
    ActionStatus,
    ActionType,
    EmailCategory,
    EmailMessage,
    InboxStats,
    ProposedAction,
    RiskLevel,
)


def test_email_message_creation():
    msg = EmailMessage(
        id="123",
        thread_id="th123",
        sender="alex@example.com",
        sender_name="Alex",
        subject="Important project update",
        snippet="Please see details...",
        category=EmailCategory.IMPORTANT,
    )
    assert msg.id == "123"
    assert msg.category == EmailCategory.IMPORTANT
    assert msg.is_unread is False


def test_proposed_action_defaults():
    action = ProposedAction(
        id="prop_1",
        action_type=ActionType.TRASH,
        title="Trash 10 spam messages",
        description="Spam detected",
        target_email_ids=["m1", "m2"],
        count=2,
        risk_level=RiskLevel.MEDIUM,
    )
    assert action.status == ActionStatus.PENDING
    assert action.count == 2
    assert action.risk_level == RiskLevel.MEDIUM


def test_inbox_stats_aggregation():
    stats = InboxStats(
        total_emails=100,
        important_count=10,
        newsletter_count=30,
        social_count=20,
        promotional_count=25,
        unwanted_count=15,
    )
    assert stats.total_emails == 100
    assert stats.newsletter_count == 30
