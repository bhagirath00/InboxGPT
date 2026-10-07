"""Mock Gmail Service client for testing, sandbox evaluation, and offline demonstrations."""

import copy
from typing import List, Optional
from inboxgpt.gmail.models import (
    ActionType,
    ActionResult,
    EmailCategory,
    EmailMessage,
    InboxStats,
)
from inboxgpt.gmail.mock_data import MOCK_EMAILS


class MockGmailClient:
    """In-memory Gmail service simulator reflecting live Gmail API behavior."""

    def __init__(self, initial_emails: Optional[List[EmailMessage]] = None):
        if initial_emails is not None:
            self._emails = copy.deepcopy(initial_emails)
        else:
            self._emails = copy.deepcopy(MOCK_EMAILS)
        self._trash: List[EmailMessage] = []
        self._archived: List[EmailMessage] = []

    def is_live(self) -> bool:
        return False

    def get_user_email(self) -> str:
        return "sandbox@inboxgpt.local"

    def list_messages(
        self,
        query: str = "",
        max_results: int = 50,
        label_ids: Optional[List[str]] = None,
    ) -> List[EmailMessage]:
        results = [e for e in self._emails if "TRASH" not in e.labels]

        if label_ids:
            for lbl in label_ids:
                results = [e for e in results if lbl in e.labels]

        if query:
            q = query.lower()
            results = [
                e
                for e in results
                if q in e.subject.lower()
                or q in e.sender.lower()
                or q in e.snippet.lower()
                or q in e.body.lower()
            ]

        return results[:max_results]

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        for e in self._emails:
            if e.id == message_id:
                return e
        for e in self._trash:
            if e.id == message_id:
                return e
        return None

    def batch_trash(self, message_ids: List[str]) -> ActionResult:
        """Move specified email IDs to trash."""
        target_ids = set(message_ids)
        affected = 0

        remaining = []
        for e in self._emails:
            if e.id in target_ids:
                e.labels.append("TRASH")
                if "INBOX" in e.labels:
                    e.labels.remove("INBOX")
                self._trash.append(e)
                affected += 1
            else:
                remaining.append(e)

        self._emails = remaining
        return ActionResult(
            action_id="trash",
            success=True,
            affected_count=affected,
            message=f"Successfully moved {affected} emails to Trash.",
        )

    def batch_archive(self, message_ids: List[str]) -> ActionResult:
        """Archive specified email IDs by removing the INBOX label."""
        target_ids = set(message_ids)
        affected = 0

        for e in self._emails:
            if e.id in target_ids:
                if "INBOX" in e.labels:
                    e.labels.remove("INBOX")
                self._archived.append(e)
                affected += 1

        return ActionResult(
            action_id="archive",
            success=True,
            affected_count=affected,
            message=f"Successfully archived {affected} emails from Inbox.",
        )

    def batch_add_label(self, message_ids: List[str], label_name: str) -> ActionResult:
        """Add label to target emails."""
        target_ids = set(message_ids)
        affected = 0

        for e in self._emails:
            if e.id in target_ids:
                if label_name not in e.labels:
                    e.labels.append(label_name)
                affected += 1

        return ActionResult(
            action_id="label",
            success=True,
            affected_count=affected,
            message=f"Successfully applied label '{label_name}' to {affected} emails.",
        )

    def batch_mark_read(self, message_ids: List[str]) -> ActionResult:
        """Mark target emails as read."""
        target_ids = set(message_ids)
        affected = 0

        for e in self._emails:
            if e.id in target_ids:
                e.is_unread = False
                if "UNREAD" in e.labels:
                    e.labels.remove("UNREAD")
                affected += 1

        return ActionResult(
            action_id="mark_read",
            success=True,
            affected_count=affected,
            message=f"Successfully marked {affected} emails as read.",
        )

    def create_draft(
        self, to: str, subject: str, body: str, thread_id: Optional[str] = None
    ) -> ActionResult:
        return ActionResult(
            action_id="mock_draft_1",
            success=True,
            affected_count=1,
            message=f"Draft created in sandbox for '{to}' with subject '{subject}'.",
        )

    def get_stats(self) -> InboxStats:
        inbox_emails = [e for e in self._emails if "INBOX" in e.labels]
        stats = InboxStats(
            total_emails=len(inbox_emails),
            unread_emails=sum(1 for e in inbox_emails if e.is_unread),
            important_count=sum(
                1 for e in inbox_emails if e.category == EmailCategory.IMPORTANT
            ),
            newsletter_count=sum(
                1 for e in inbox_emails if e.category == EmailCategory.NEWSLETTER
            ),
            social_count=sum(
                1 for e in inbox_emails if e.category == EmailCategory.SOCIAL
            ),
            promotional_count=sum(
                1 for e in inbox_emails if e.category == EmailCategory.PROMOTIONAL
            ),
            unwanted_count=sum(
                1 for e in inbox_emails if e.category == EmailCategory.UNWANTED
            ),
        )
        return stats
