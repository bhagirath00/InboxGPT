"""Tests for the Safe Intelligent Agent Triage Engine."""

from datetime import date, timedelta
from inboxgpt.agent.triage_agent import is_protected_email, plan_agent_cleanup
from inboxgpt.gmail.models import ActionType, EmailCategory, EmailMessage


def test_starred_and_security_emails_are_never_deleted():
    today = date(2026, 10, 7)
    today_str = "Wed, 07 Oct 2026 08:00:00 +0000"

    emails = [
        EmailMessage(
            id="e1",
            thread_id="t1",
            sender="google@google.com",
            subject="Security alert",
            body="New signin detected",
            date=today_str,
            labels=["INBOX"],
            category=EmailCategory.IMPORTANT,
        ),
        EmailMessage(
            id="e2",
            thread_id="t2",
            sender="telegram@telegram.org",
            subject="Your Code - 93946",
            body="Login code",
            date=today_str,
            labels=["INBOX"],
            category=EmailCategory.IMPORTANT,
        ),
        EmailMessage(
            id="e3",
            thread_id="t3",
            sender="friend@example.com",
            subject="Starred personal notes",
            body="Remember this",
            date=today_str,
            labels=["INBOX", "STARRED"],
            category=EmailCategory.UNCATEGORIZED,
        ),
        EmailMessage(
            id="e4",
            thread_id="t4",
            sender="newsletter@medium.com",
            subject="10 Tips for Python",
            body="Daily read",
            date=today_str,
            labels=["INBOX"],
            category=EmailCategory.NEWSLETTER,
        ),
        EmailMessage(
            id="e5",
            thread_id="t5",
            sender="jobs@wellfound.com",
            subject="New jobs: DevOps Engineer",
            body="Open positions",
            date=today_str,
            labels=["INBOX"],
            category=EmailCategory.SOCIAL,
        ),
    ]

    # Verify protection helper
    assert is_protected_email(emails[0])[0] is True
    assert is_protected_email(emails[1])[0] is True
    assert is_protected_email(emails[2])[0] is True
    assert is_protected_email(emails[3])[0] is False
    assert is_protected_email(emails[4])[0] is False

    # Test "today i got useless mail delete those all"
    prop, msg = plan_agent_cleanup(emails, "today i got useless mail delete those all", reference_date=today)
    assert prop is not None
    assert prop.count == 2
    assert set(prop.target_email_ids) == {"e4", "e5"}
    assert "e1" not in prop.target_email_ids
    assert "e2" not in prop.target_email_ids
    assert "e3" not in prop.target_email_ids
    assert prop.action_type == ActionType.TRASH


def test_timeframe_filtering():
    today = date(2026, 10, 7)
    today_str = "Wed, 07 Oct 2026 08:00:00 +0000"
    yesterday_str = "Tue, 06 Oct 2026 08:00:00 +0000"

    emails = [
        EmailMessage(
            id="today_promo",
            thread_id="t1",
            sender="deals@shop.com",
            subject="50% Off Today",
            body="Promo code",
            date=today_str,
            labels=["INBOX"],
            category=EmailCategory.PROMOTIONAL,
        ),
        EmailMessage(
            id="yesterday_promo",
            thread_id="t2",
            sender="deals@shop.com",
            subject="Old discount",
            body="Expired code",
            date=yesterday_str,
            labels=["INBOX"],
            category=EmailCategory.PROMOTIONAL,
        ),
    ]

    # Clean only today's promo
    prop, _ = plan_agent_cleanup(emails, "delete today promo", reference_date=today)
    assert prop is not None
    assert prop.count == 1
    assert prop.target_email_ids == ["today_promo"]

    # Clean all promos
    prop_all, _ = plan_agent_cleanup(emails, "delete all promo", reference_date=today)
    assert prop_all is not None
    assert prop_all.count == 2
    assert set(prop_all.target_email_ids) == {"today_promo", "yesterday_promo"}
