"""Data models for Gmail messages, categories, and proposed cleanup actions."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    IMPORTANT = "important"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    PROMOTIONAL = "promotional"
    UNWANTED = "unwanted"
    UNCATEGORIZED = "uncategorized"


class ActionType(str, Enum):
    TRASH = "trash"
    ARCHIVE = "archive"
    LABEL = "label"
    MARK_READ = "mark_read"
    DELETE = "delete"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class EmailMessage(BaseModel):
    """Represents a Gmail email message with parsed headers and categorization."""

    id: str
    thread_id: str
    sender: str
    sender_name: Optional[str] = None
    recipient: str = ""
    subject: str = "(no subject)"
    snippet: str = ""
    body: str = ""
    date: str = ""
    timestamp: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    is_unread: bool = False
    category: EmailCategory = EmailCategory.UNCATEGORIZED
    importance_reason: Optional[str] = None


class ProposedAction(BaseModel):
    """Represents an agent-generated action requiring explicit human-in-the-loop approval."""

    id: str
    action_type: ActionType
    title: str
    description: str
    target_email_ids: List[str]
    count: int
    risk_level: RiskLevel = RiskLevel.MEDIUM
    reason: str = ""
    status: ActionStatus = ActionStatus.PENDING
    label_to_apply: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ActionResult(BaseModel):
    """Result of executing an approved action."""

    action_id: str
    success: bool
    affected_count: int
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class InboxStats(BaseModel):
    """Aggregated statistics for emails in the inbox."""

    total_emails: int = 0
    unread_emails: int = 0
    important_count: int = 0
    newsletter_count: int = 0
    social_count: int = 0
    promotional_count: int = 0
    unwanted_count: int = 0
    pending_actions_count: int = 0
