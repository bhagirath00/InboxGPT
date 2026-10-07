"""Intelligent Agent Triage Engine with Strict Safety Rules & Zero-Lag Execution."""

from datetime import date, datetime, timedelta
import email.utils
import re
from typing import List, Optional, Tuple
import uuid

from inboxgpt.gmail.models import (
    ActionType,
    EmailCategory,
    EmailMessage,
    ProposedAction,
    RiskLevel,
)


def parse_date_safe(date_str: str) -> Optional[date]:
    """Parse email date from RFC 2822 or ISO format into a date object."""
    if not date_str:
        return None
    try:
        return email.utils.parsedate_to_datetime(date_str).date()
    except Exception:
        try:
            return datetime.fromisoformat(date_str).date()
        except Exception:
            return None


def is_protected_email(email: EmailMessage) -> Tuple[bool, str]:
    """Inviolable safety rule: Starred, Priority, and Security emails are strictly protected."""
    # 1. Starred protection
    if "STARRED" in email.labels or "STAR" in email.labels:
        return True, "Starred email protected by user"

    # 2. Priority label protection
    if "IMPORTANT" in email.labels or email.category == EmailCategory.IMPORTANT:
        return True, "Priority communication protected"

    # 3. Security / OTP / Financial keyword protection
    sub_lower = (email.subject or "").lower()
    critical_keywords = [
        "otp",
        "verification code",
        "your code",
        "security alert",
        "security code",
        "security warning",
        "invoice",
        "receipt",
        "signoff required",
        "action required",
        "password reset",
        "bank alert",
    ]
    for kw in critical_keywords:
        if kw in sub_lower:
            return True, f"Security alert or authentication code ({kw})"

    return False, ""


def plan_agent_cleanup(
    emails: List[EmailMessage],
    prompt: str,
    reference_date: Optional[date] = None,
) -> Tuple[Optional[ProposedAction], str]:
    """
    Intelligently interpret natural language user instruction and generate a safe proposal.
    
    Safety Guarantees:
    - Never deletes Starred or Priority emails.
    - Accurately filters by timeframe ("today", "yesterday", "this week").
    - Accurately filters useless emails (Promo, Social, Newsletter, Unwanted).
    """
    if not prompt or not prompt.strip():
        return None, "No instruction provided."

    p = prompt.lower().strip()
    today = reference_date or date.today()
    yesterday = today - timedelta(days=1)

    # 1. Detect Action Type
    if any(w in p for w in ["archive", "hide", "archive all"]):
        action_type = ActionType.ARCHIVE
        action_verb = "Archive"
    else:
        # Default to Trash for "delete", "trash", "remove", "clean", or general cleanup
        action_type = ActionType.TRASH
        action_verb = "Move"

    # 2. Detect Timeframe
    timeframe = "all"
    timeframe_desc = "all time"
    if "today" in p:
        timeframe = "today"
        timeframe_desc = f"today ({today.strftime('%b %d')})"
    elif "yesterday" in p:
        timeframe = "yesterday"
        timeframe_desc = f"yesterday ({yesterday.strftime('%b %d')})"
    elif "this week" in p or "past week" in p or "week" in p:
        timeframe = "week"
        timeframe_desc = "the past 7 days"

    # 3. Detect Categories
    # "useless mail" / "junk" / "spam" covers promotional, social, and newsletter marketing
    is_promo_only = ("promo" in p or "promotion" in p or "marketing" in p) and "social" not in p and "useless" not in p
    is_social_only = ("social" in p or "linkedin" in p or "github" in p or "job" in p) and "promo" not in p and "useless" not in p
    is_news_only = ("newsletter" in p or "news" in p or "digest" in p) and "promo" not in p and "useless" not in p

    if is_promo_only:
        target_categories = {EmailCategory.PROMOTIONAL}
        category_desc = "promotional discounts and ads"
    elif is_social_only:
        target_categories = {EmailCategory.SOCIAL}
        category_desc = "social media notifications and job alerts"
    elif is_news_only:
        target_categories = {EmailCategory.NEWSLETTER}
        category_desc = "product digests and newsletters"
    else:
        # "useless emails" or general cleanup includes Promo, Social, and Unwanted
        target_categories = {
            EmailCategory.PROMOTIONAL,
            EmailCategory.SOCIAL,
            EmailCategory.UNWANTED,
            EmailCategory.NEWSLETTER,
        }
        category_desc = "useless emails (promotions, social updates, and automated digests)"

    # 4. Filter matching emails and record protected emails
    matching_emails: List[EmailMessage] = []
    protected_count = 0

    for email in emails:
        # Safety Check First:
        protected, reason = is_protected_email(email)
        if protected:
            protected_count += 1
            continue

        # Timeframe Check:
        msg_date = parse_date_safe(email.date)
        if timeframe == "today":
            if msg_date != today:
                continue
        elif timeframe == "yesterday":
            if msg_date != yesterday:
                continue
        elif timeframe == "week":
            if msg_date and msg_date < (today - timedelta(days=7)):
                continue

        # Category Check:
        if email.category in target_categories:
            matching_emails.append(email)

    if not matching_emails:
        msg = f"No {category_desc} found for {timeframe_desc}. (Preserved {protected_count} Starred/Important emails)."
        return None, msg

    count = len(matching_emails)
    destination = "Trash in live Gmail" if action_type == ActionType.TRASH else "Archive (All Mail)"
    title = f"{action_verb} {count} {category_desc} from {timeframe_desc} to {destination}"
    description = (
        f"Identified {count} {category_desc} received {timeframe_desc}. "
        f"Guaranteed safety: strictly preserved all Starred and Priority emails (security codes, OTPs, receipts)."
    )
    reason = (
        f"User requested: '{prompt}'. Matched {count} non-essential emails. "
        f"{protected_count} important/starred emails safely excluded."
    )

    prop = ProposedAction(
        id=f"agent_{uuid.uuid4().hex[:8]}",
        action_type=action_type,
        title=title,
        description=description,
        target_email_ids=[e.id for e in matching_emails],
        count=count,
        risk_level=RiskLevel.MEDIUM if action_type == ActionType.TRASH else RiskLevel.LOW,
        reason=reason,
    )

    return prop, f"Ready to review proposal: {count} emails identified."
