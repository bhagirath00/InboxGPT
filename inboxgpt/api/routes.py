"""API routes for email reading, triage, and human-in-the-loop approval execution."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from inboxgpt.agent.graph import create_inbox_graph
from inboxgpt.agent.tools import ApprovalRequiredTools, SafeInboxTools
from inboxgpt.auth.oauth import get_auth_status
from inboxgpt.gmail.client import get_gmail_client
from inboxgpt.gmail.models import (
    ActionResult,
    ActionType,
    EmailCategory,
    EmailMessage,
    InboxStats,
    ProposedAction,
)

router = APIRouter()


class ActionApprovalRequest(BaseModel):
    action: ProposedAction
    dry_run: bool = False


class ActionRejectRequest(BaseModel):
    action_id: str
    reason: Optional[str] = None


@router.get("/status")
def status_endpoint() -> Dict[str, Any]:
    client = get_gmail_client()
    auth = get_auth_status()
    return {
        "is_live_gmail": client.is_live(),
        "auth_status": auth,
    }


@router.get("/stats", response_model=InboxStats)
def get_stats_endpoint():
    client = get_gmail_client()
    return client.get_stats()


@router.get("/emails", response_model=List[EmailMessage])
def list_emails_endpoint(
    query: str = Query("", description="Gmail search query"),
    max_results: int = Query(50, ge=1, le=200),
):
    client = get_gmail_client()
    safe_tools = SafeInboxTools(client)
    return safe_tools.fetch_inbox_emails(max_results=max_results, query=query)


@router.get("/emails/{email_id}", response_model=EmailMessage)
def get_email_endpoint(email_id: str):
    client = get_gmail_client()
    safe_tools = SafeInboxTools(client)
    msg = safe_tools.get_email_details(email_id)
    if not msg:
        raise HTTPException(status_code=404, detail=f"Email '{email_id}' not found.")
    return msg


@router.post("/analyze")
def analyze_inbox_endpoint(
    dry_run: bool = Query(False, description="Simulate without mutations")
):
    """Run LangGraph triage analysis and return generated proposals."""
    client = get_gmail_client()
    graph = create_inbox_graph(client, enable_interrupt=False, dry_run=dry_run)
    result = graph.invoke({})

    return {
        "stats": result.get("stats"),
        "proposed_actions": result.get("proposed_actions", []),
        "summary": result.get("summary_report", ""),
    }


@router.post("/actions/approve", response_model=ActionResult)
def approve_action_endpoint(req: ActionApprovalRequest):
    """Explicit Human-in-the-Loop approval endpoint. Executes action on Gmail."""
    client = get_gmail_client()
    approval_tools = ApprovalRequiredTools(client)
    action = req.action

    if action.action_type == ActionType.TRASH:
        return approval_tools.execute_trash(action, dry_run=req.dry_run)
    elif action.action_type == ActionType.ARCHIVE:
        return approval_tools.execute_archive(action, dry_run=req.dry_run)
    elif action.action_type == ActionType.LABEL:
        label = action.label_to_apply or "INBOXGPT_PRIORITY"
        return approval_tools.execute_label(action, label, dry_run=req.dry_run)
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported action type: {action.action_type}"
        )


@router.post("/actions/reject")
def reject_action_endpoint(req: ActionRejectRequest):
    """Record rejection of a proposed action."""
    return {
        "action_id": req.action_id,
        "status": "rejected",
        "message": f"Action {req.action_id} rejected. No modifications made.",
    }
