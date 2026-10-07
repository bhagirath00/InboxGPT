"""Textual TUI interface package for InboxGPT."""

from .app import InboxGPTApp
from .modals import ApprovalModal, SearchModal, HelpModal, EmailDetailModal

__all__ = [
    "InboxGPTApp",
    "ApprovalModal",
    "SearchModal",
    "HelpModal",
    "EmailDetailModal",
]
