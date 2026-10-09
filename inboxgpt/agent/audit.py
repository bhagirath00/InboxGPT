"""Audit logging and transactional action journal with undo capabilities for InboxGPT."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

from inboxgpt.config import config, logger
from inboxgpt.gmail.client import GmailServiceProtocol
from inboxgpt.gmail.models import ActionResult, ProposedAction


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action_type: str  # "trash", "archive", "label"
    target_ids: List[str]
    description: str
    affected_count: int
    undone: bool = False


class AuditManager:
    """Maintains local JSON audit journal and executes undo transactions."""

    def __init__(self, journal_file: Optional[Path] = None):
        self.journal_file = journal_file or (config.config_dir / "audit_log.json")

    def _load_entries(self) -> List[AuditEntry]:
        if not self.journal_file.exists():
            return []
        try:
            with open(self.journal_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [AuditEntry(**item) for item in data]
        except Exception as e:
            logger.warning("Failed to load audit journal: %s", e)
            return []

    def _save_entries(self, entries: List[AuditEntry]) -> None:
        self.journal_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.journal_file, "w", encoding="utf-8") as f:
                json.dump([e.model_dump() for e in entries], f, indent=2)
        except Exception as e:
            logger.warning("Failed to write to audit journal: %s", e)

    def record_action(self, action: ProposedAction, result: ActionResult) -> AuditEntry:
        """Record an executed action into the journal."""
        entry = AuditEntry(
            action_type=action.action_type.value,
            target_ids=action.target_email_ids,
            description=action.description,
            affected_count=result.affected_count,
        )
        entries = self._load_entries()
        entries.append(entry)
        self._save_entries(entries)
        logger.info("Recorded audit entry %s for action %s (%d emails)", entry.id, entry.action_type, entry.affected_count)
        return entry

    def get_entry_by_id(self, action_id: str) -> Optional[AuditEntry]:
        """Find an audit entry by its unique identifier."""
        entries = self._load_entries()
        for entry in entries:
            if entry.id.lower() == action_id.lower():
                return entry
        return None

    def get_last_undoable(self) -> Optional[AuditEntry]:
        """Return the most recent action that has not yet been undone (skips permanent delete)."""
        entries = self._load_entries()
        for entry in reversed(entries):
            if not entry.undone and entry.target_ids and entry.action_type in ("trash", "archive"):
                return entry
        return None

    def list_history(self, limit: int = 10) -> List[AuditEntry]:
        """Return recent audit history."""
        entries = self._load_entries()
        return list(reversed(entries))[:limit]

    def execute_undo(self, client: GmailServiceProtocol, action_id: Optional[str] = None) -> ActionResult:
        """Revert an approved action from the audit journal (by ID or latest)."""
        if action_id:
            entry = self.get_entry_by_id(action_id)
            if not entry:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    affected_count=0,
                    message=f"Audit action ID '{action_id}' not found.",
                )
            if entry.undone:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    affected_count=0,
                    message=f"Action '{action_id}' has already been undone.",
                )
        else:
            entry = self.get_last_undoable()
            if not entry:
                return ActionResult(
                    action_id="undo",
                    success=False,
                    affected_count=0,
                    message="No undoable actions found in audit journal.",
                )

        # Check if action was a permanent delete
        if entry.action_type == "delete":
            return ActionResult(
                action_id=entry.id,
                success=False,
                affected_count=0,
                message="Permanent deletion cannot be undone because messages were permanently purged from Gmail servers.",
            )

        affected = 0
        if entry.action_type == "trash":
            # Revert trash: untrash or move back to Inbox
            if hasattr(client, "batch_untrash"):
                res = client.batch_untrash(entry.target_ids)
                affected = res.affected_count
            else:
                # Fallback for clients without untrash: re-add INBOX label
                res = client.batch_add_label(entry.target_ids, label_name="INBOX")
                affected = res.affected_count

        elif entry.action_type == "archive":
            # Revert archive: re-add INBOX label
            res = client.batch_add_label(entry.target_ids, label_name="INBOX")
            affected = res.affected_count

        else:
            return ActionResult(
                action_id=entry.id,
                success=False,
                affected_count=0,
                message=f"Action type '{entry.action_type}' cannot be automatically undone.",
            )

        # Mark entry as undone
        entries = self._load_entries()
        for e in entries:
            if e.id == entry.id:
                e.undone = True
                break
        self._save_entries(entries)

        logger.info("Successfully undone action %s (%d emails restored)", entry.id, affected)
        return ActionResult(
            action_id=entry.id,
            success=True,
            affected_count=affected,
            message=f"Successfully restored {affected} emails from action '{entry.id}' ({entry.action_type}).",
        )


audit_manager = AuditManager()
