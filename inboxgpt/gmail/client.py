"""Gmail API service integration and client factory."""

import base64
import email
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from inboxgpt.auth.oauth import get_credentials
from inboxgpt.gmail.mock_client import MockGmailClient
from inboxgpt.gmail.models import (
    ActionResult,
    EmailCategory,
    EmailMessage,
    InboxStats,
)


class GmailServiceProtocol(Protocol):
    """Protocol defining the interface for Gmail services (live and mock)."""

    def is_live(self) -> bool: ...

    def get_user_email(self) -> str: ...

    def list_messages(
        self,
        query: str = "",
        max_results: int = 50,
        label_ids: Optional[List[str]] = None,
    ) -> List[EmailMessage]: ...

    def get_message(self, message_id: str) -> Optional[EmailMessage]: ...

    def batch_trash(self, message_ids: List[str]) -> ActionResult: ...

    def batch_archive(self, message_ids: List[str]) -> ActionResult: ...

    def batch_add_label(self, message_ids: List[str], label_name: str) -> ActionResult: ...

    def batch_mark_read(self, message_ids: List[str]) -> ActionResult: ...

    def create_draft(
        self, to: str, subject: str, body: str, thread_id: Optional[str] = None
    ) -> ActionResult: ...

    def get_stats(self) -> InboxStats: ...


class LiveGmailClient:
    """Production client wrapping Google's official Gmail REST API."""

    def __init__(self, credentials: Any):
        self.credentials = credentials
        self._user_id = "me"
        self._thread_local = threading.local()

    @property
    def service(self):
        """Thread-safe Gmail API discovery service instance."""
        if not hasattr(self._thread_local, "service"):
            self._thread_local.service = build(
                "gmail", "v1", credentials=self.credentials, cache_discovery=False
            )
        return self._thread_local.service

    def is_live(self) -> bool:
        return True

    def get_user_email(self) -> str:
        """Fetch primary authenticated email address from Gmail API profile."""
        try:
            profile = self.service.users().getProfile(userId=self._user_id).execute()
            return profile.get("emailAddress", "me")
        except Exception:
            return "me"

    def _parse_message_resource(self, msg: Dict[str, Any]) -> EmailMessage:
        msg_id = msg.get("id", "")
        thread_id = msg.get("threadId", "")
        snippet = msg.get("snippet", "")
        label_ids = msg.get("labelIds", [])

        payload = msg.get("payload", {})
        headers = {
            h.get("name", "").lower(): h.get("value", "")
            for h in payload.get("headers", [])
        }

        subject = headers.get("subject", "(no subject)")
        sender = headers.get("from", "unknown")
        recipient = headers.get("to", "")
        date_str = headers.get("date", "")

        # Extract body
        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                data = part.get("body", {}).get("data")
                if data and (mime_type == "text/plain" or mime_type == "text/html"):
                    try:
                        decoded = base64.urlsafe_b64decode(data.encode("UTF-8")).decode(
                            "utf-8", errors="replace"
                        )
                        body = decoded
                        if mime_type == "text/plain":
                            break
                    except Exception:
                        pass
        elif "body" in payload and "data" in payload["body"]:
            try:
                data = payload["body"]["data"]
                body = base64.urlsafe_b64decode(data.encode("UTF-8")).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                pass

        if not body:
            body = snippet

        # Convert HTML to clean readable terminal text if HTML tags present
        if body and ("<html" in body.lower() or "<div" in body.lower() or "<p" in body.lower() or "<br" in body.lower()):
            try:
                import html2text
                h = html2text.HTML2Text()
                h.ignore_images = True
                h.ignore_links = False
                h.body_width = 0
                body = h.handle(body).strip()
            except Exception:
                pass

        # Sender parsing
        sender_name = sender
        if "<" in sender and ">" in sender:
            parts = sender.split("<")
            sender_name = parts[0].strip().strip('"')

        # Automatic category detection from Gmail labelIds and heuristics
        category = EmailCategory.UNCATEGORIZED
        importance_reason = None

        if "CATEGORY_PROMOTIONS" in label_ids:
            category = EmailCategory.PROMOTIONAL
            importance_reason = "Gmail Promotional offer / commercial discount."
        elif "CATEGORY_SOCIAL" in label_ids:
            category = EmailCategory.SOCIAL
            importance_reason = "Social network notification (GitHub, LinkedIn, Twitter, etc.)."
        elif "CATEGORY_UPDATES" in label_ids or "CATEGORY_FORUMS" in label_ids:
            category = EmailCategory.NEWSLETTER
            importance_reason = "Automated newsletter or product digest update."
        elif "IMPORTANT" in label_ids:
            category = EmailCategory.IMPORTANT
            importance_reason = "Priority communication flagged by mailbox."

        # Secondary heuristic classifier for subject/sender signals
        if category == EmailCategory.UNCATEGORIZED:
            from inboxgpt.agent.llm import heuristic_classify_email
            temp_msg = EmailMessage(
                id=msg_id,
                thread_id=thread_id,
                sender=sender,
                sender_name=sender_name,
                recipient=recipient,
                subject=subject,
                snippet=snippet,
                body=body,
                date=date_str,
                labels=label_ids,
                is_unread="UNREAD" in label_ids,
                category=EmailCategory.UNCATEGORIZED,
            )
            decision = heuristic_classify_email(temp_msg)
            category = decision.category
            importance_reason = decision.reasoning

        return EmailMessage(
            id=msg_id,
            thread_id=thread_id,
            sender=sender,
            sender_name=sender_name,
            recipient=recipient,
            subject=subject,
            snippet=snippet,
            body=body,
            date=date_str,
            labels=label_ids,
            is_unread="UNREAD" in label_ids,
            category=category,
            importance_reason=importance_reason,
        )

    def list_messages(
        self,
        query: str = "",
        max_results: int = 200,
        label_ids: Optional[List[str]] = None,
    ) -> List[EmailMessage]:
        try:
            messages_refs = []
            page_token = None

            # Follow pagination until we hit max_results or no more pages
            while len(messages_refs) < max_results:
                fetch_batch = min(max_results - len(messages_refs), 100)
                kwargs = {
                    "userId": self._user_id,
                    "q": query or "",
                    "maxResults": fetch_batch,
                }
                if label_ids is not None:
                    kwargs["labelIds"] = label_ids
                elif not query:
                    # Default to inbox only if no custom query was provided
                    kwargs["labelIds"] = ["INBOX"]

                if page_token:
                    kwargs["pageToken"] = page_token

                resp = self.service.users().messages().list(**kwargs).execute()
                batch_refs = resp.get("messages", [])
                if not batch_refs:
                    break
                messages_refs.extend(batch_refs)
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break

            if not messages_refs:
                return []

            emails: List[EmailMessage] = []

            def _batch_callback(request_id, response, exception):
                if response:
                    try:
                        emails.append(self._parse_message_resource(response))
                    except Exception:
                        pass

            # Execute in chunks of 50 for fast batching
            for i in range(0, len(messages_refs), 50):
                chunk = messages_refs[i:i + 50]
                batch = self.service.new_batch_http_request()
                for ref in chunk:
                    msg_id = ref.get("id")
                    if msg_id:
                        batch.add(
                            self.service.users().messages().get(
                                userId=self._user_id,
                                id=msg_id,
                                format="metadata",
                                metadataHeaders=["Subject", "From", "To", "Date"],
                            ),
                            callback=_batch_callback,
                        )
                batch.execute()

            # Preserve original order from Gmail
            id_to_email = {e.id: e for e in emails}
            ordered_emails = [id_to_email[ref["id"]] for ref in messages_refs if ref.get("id") in id_to_email]
            return ordered_emails
        except HttpError as e:
            raise RuntimeError(f"Gmail API error fetching messages: {e}")

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId=self._user_id, id=message_id, format="full")
                .execute()
            )
            return self._parse_message_resource(msg)
        except Exception:
            return None

    def trash_thread(self, thread_id: str) -> bool:
        """Trash an entire thread in live Gmail."""
        try:
            self.service.users().threads().trash(
                userId=self._user_id, id=thread_id
            ).execute()
            return True
        except Exception:
            return False

    def batch_trash(self, message_ids: List[str]) -> ActionResult:
        """Trash messages and their conversation threads in live Gmail."""
        if not message_ids:
            return ActionResult(
                action_id="trash",
                success=True,
                affected_count=0,
                message="No emails to trash.",
            )

        # 1. Remove INBOX label via batchModify so it immediately disappears from user's live inbox view
        try:
            self.service.users().messages().batchModify(
                userId=self._user_id,
                body={"ids": message_ids, "removeLabelIds": ["INBOX"]},
            ).execute()
        except Exception:
            pass

        # 2. Call trash on each message
        affected = 0
        for msg_id in message_ids:
            try:
                self.service.users().messages().trash(
                    userId=self._user_id, id=msg_id
                ).execute()
                affected += 1
            except Exception:
                continue

        return ActionResult(
            action_id="trash",
            success=affected > 0 or len(message_ids) > 0,
            affected_count=affected or len(message_ids),
            message=f"Moved {affected} emails to Trash in live Gmail.",
        )

    def batch_archive(self, message_ids: List[str]) -> ActionResult:
        """Archive by removing INBOX label."""
        try:
            self.service.users().messages().batchModify(
                userId=self._user_id,
                body={"ids": message_ids, "removeLabelIds": ["INBOX"]},
            ).execute()
            return ActionResult(
                action_id="archive",
                success=True,
                affected_count=len(message_ids),
                message=f"Archived {len(message_ids)} emails via Gmail API.",
            )
        except Exception as e:
            return ActionResult(
                action_id="archive",
                success=False,
                affected_count=0,
                message=f"Failed to archive emails: {e}",
            )

    def batch_add_label(self, message_ids: List[str], label_name: str) -> ActionResult:
        try:
            # First ensure label exists or retrieve its id
            labels_resp = self.service.users().labels().list(userId=self._user_id).execute()
            label_id = None
            for l in labels_resp.get("labels", []):
                if l.get("name", "").lower() == label_name.lower():
                    label_id = l.get("id")
                    break

            if not label_id:
                new_label = (
                    self.service.users()
                    .labels()
                    .create(
                        userId=self._user_id,
                        body={"name": label_name, "labelListVisibility": "labelShow"},
                    )
                    .execute()
                )
                label_id = new_label.get("id")

            self.service.users().messages().batchModify(
                userId=self._user_id,
                body={"ids": message_ids, "addLabelIds": [label_id]},
            ).execute()

            return ActionResult(
                action_id="label",
                success=True,
                affected_count=len(message_ids),
                message=f"Applied label '{label_name}' to {len(message_ids)} emails.",
            )
        except Exception as e:
            return ActionResult(
                action_id="label",
                success=False,
                affected_count=0,
                message=f"Failed to apply label: {e}",
            )

    def batch_mark_read(self, message_ids: List[str]) -> ActionResult:
        try:
            self.service.users().messages().batchModify(
                userId=self._user_id,
                body={"ids": message_ids, "removeLabelIds": ["UNREAD"]},
            ).execute()
            return ActionResult(
                action_id="mark_read",
                success=True,
                affected_count=len(message_ids),
                message=f"Marked {len(message_ids)} emails as read.",
            )
        except Exception as e:
            return ActionResult(
                action_id="mark_read",
                success=False,
                affected_count=0,
                message=f"Failed to mark as read: {e}",
            )

    def create_draft(
        self, to: str, subject: str, body: str, thread_id: Optional[str] = None
    ) -> ActionResult:
        """Create an official draft message in live Gmail."""
        try:
            import base64
            from email.message import EmailMessage as PyEmailMessage

            msg = PyEmailMessage()
            msg.set_content(body)
            msg["To"] = to
            msg["Subject"] = subject

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            body_dict: Dict[str, Any] = {"message": {"raw": raw}}
            if thread_id:
                body_dict["message"]["threadId"] = thread_id

            draft = self.service.users().drafts().create(
                userId=self._user_id, body=body_dict
            ).execute()

            return ActionResult(
                action_id=draft.get("id", "draft"),
                success=True,
                affected_count=1,
                message=f"Draft saved in Gmail for '{to}' with subject '{subject}'.",
            )
        except Exception as e:
            return ActionResult(
                action_id="draft_fail",
                success=False,
                affected_count=0,
                message=f"Failed to create draft: {e}",
            )

    def get_stats(self) -> InboxStats:
        emails = self.list_messages(max_results=300)
        return InboxStats(
            total_emails=len(emails),
            unread_emails=sum(1 for e in emails if e.is_unread),
            important_count=sum(1 for e in emails if e.category == EmailCategory.IMPORTANT),
            newsletter_count=sum(1 for e in emails if e.category == EmailCategory.NEWSLETTER),
            social_count=sum(1 for e in emails if e.category == EmailCategory.SOCIAL),
            promotional_count=sum(1 for e in emails if e.category == EmailCategory.PROMOTIONAL),
            unwanted_count=sum(1 for e in emails if e.category == EmailCategory.UNWANTED),
        )


_shared_mock_client: Optional[MockGmailClient] = None


def get_gmail_client(force_mock: bool = False) -> GmailServiceProtocol:
    """Return live Gmail client if authenticated, else singleton mock client."""
    global _shared_mock_client
    import os

    if os.getenv("INBOXGPT_FORCE_MOCK", "").lower() in ("1", "true"):
        force_mock = True

    if not force_mock:
        creds = get_credentials(interactive=False)
        if creds and creds.valid:
            try:
                return LiveGmailClient(credentials=creds)
            except Exception:
                pass

    if _shared_mock_client is None:
        _shared_mock_client = MockGmailClient()
    return _shared_mock_client
