"""InboxGPT tool suite partitioned strictly into Safe vs. Approval-Required operations."""

from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from inboxgpt.gmail.client import GmailServiceProtocol
from inboxgpt.gmail.models import (
    ActionResult,
    ActionType,
    EmailCategory,
    EmailMessage,
    InboxStats,
    ProposedAction,
    RiskLevel,
)


class SafeInboxTools:
    """Read-only and analysis tools. Executed freely without human approval."""

    def __init__(self, gmail_client: GmailServiceProtocol):
        self.client = gmail_client

    def fetch_inbox_emails(
        self, max_results: int = 50, query: str = ""
    ) -> List[EmailMessage]:
        """Fetch inbox emails matching an optional Gmail query."""
        return self.client.list_messages(query=query, max_results=max_results)

    def get_email_details(self, email_id: str) -> Optional[EmailMessage]:
        """Retrieve full message contents and metadata for a single email."""
        return self.client.get_message(email_id)

    def compute_stats(self, emails: List[EmailMessage]) -> InboxStats:
        """Compute category distributions and unread metrics."""
        stats = InboxStats(
            total_emails=len(emails),
            unread_emails=sum(1 for e in emails if e.is_unread),
            important_count=sum(
                1 for e in emails if e.category == EmailCategory.IMPORTANT
            ),
            newsletter_count=sum(
                1 for e in emails if e.category == EmailCategory.NEWSLETTER
            ),
            social_count=sum(
                1 for e in emails if e.category == EmailCategory.SOCIAL
            ),
            promotional_count=sum(
                1 for e in emails if e.category == EmailCategory.PROMOTIONAL
            ),
            unwanted_count=sum(
                1 for e in emails if e.category == EmailCategory.UNWANTED
            ),
        )
        return stats

    def summarize_content(self, body_text: str, max_chars: int = 500) -> str:
        """Extract quick concise summary snippet of email content."""
        clean = " ".join(body_text.split())
        if len(clean) > max_chars:
            return clean[:max_chars] + "..."
        return clean


class ApprovalRequiredTools:
    """Destructive or bulk modifying operations.

    CRITICAL SAFETY RULE:
    These methods MUST ONLY be invoked after human approval has been registered
    for the corresponding ProposedAction.
    """

    def __init__(self, gmail_client: GmailServiceProtocol):
        self.client = gmail_client

    def execute_trash(
        self, action: ProposedAction, dry_run: bool = False
    ) -> ActionResult:
        """Execute moving emails to Trash."""
        if dry_run:
            return ActionResult(
                action_id=action.id,
                success=True,
                affected_count=len(action.target_email_ids),
                message=f"[DRY RUN] Would move {len(action.target_email_ids)} emails to Trash.",
            )
        return self.client.batch_trash(action.target_email_ids)

    def execute_archive(
        self, action: ProposedAction, dry_run: bool = False
    ) -> ActionResult:
        """Execute archiving emails (removing INBOX label)."""
        if dry_run:
            return ActionResult(
                action_id=action.id,
                success=True,
                affected_count=len(action.target_email_ids),
                message=f"[DRY RUN] Would archive {len(action.target_email_ids)} emails.",
            )
        return self.client.batch_archive(action.target_email_ids)

    def execute_label(
        self, action: ProposedAction, label_name: str, dry_run: bool = False
    ) -> ActionResult:
        """Execute labeling emails."""
        if dry_run:
            return ActionResult(
                action_id=action.id,
                success=True,
                affected_count=len(action.target_email_ids),
                message=f"[DRY RUN] Would apply label '{label_name}' to {len(action.target_email_ids)} emails.",
            )
        return self.client.batch_add_label(action.target_email_ids, label_name)
