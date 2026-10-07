"""Authentication package for InboxGPT."""

from .oauth import get_credentials, run_oauth_flow, get_auth_status, SCOPES

__all__ = ["get_credentials", "run_oauth_flow", "get_auth_status", "SCOPES"]
