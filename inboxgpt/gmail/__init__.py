"""Gmail service package for InboxGPT."""

from .models import (
    EmailCategory,
    ActionType,
    RiskLevel,
    ActionStatus,
    EmailMessage,
    ProposedAction,
    ActionResult,
    InboxStats,
)
from .client import GmailServiceProtocol, LiveGmailClient, get_gmail_client
from .mock_client import MockGmailClient

__all__ = [
    "EmailCategory",
    "ActionType",
    "RiskLevel",
    "ActionStatus",
    "EmailMessage",
    "ProposedAction",
    "ActionResult",
    "InboxStats",
    "GmailServiceProtocol",
    "LiveGmailClient",
    "MockGmailClient",
    "get_gmail_client",
]
