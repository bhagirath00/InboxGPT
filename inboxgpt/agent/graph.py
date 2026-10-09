"""LangGraph workflow definition for InboxGPT with human-in-the-loop approvals."""

from typing import Any, Dict, List, Optional
import uuid
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from inboxgpt.agent.llm import classify_email
from inboxgpt.agent.state import AgentState
from inboxgpt.agent.tools import ApprovalRequiredTools, SafeInboxTools
from inboxgpt.gmail.client import GmailServiceProtocol
from inboxgpt.gmail.models import (
    ActionResult,
    ActionStatus,
    ActionType,
    EmailCategory,
    InboxStats,
    ProposedAction,
    RiskLevel,
)


def create_inbox_graph(
    gmail_client: GmailServiceProtocol,
    enable_interrupt: bool = True,
    dry_run: bool = False,
):
    """Build and compile the LangGraph workflow for inbox triage and cleanup."""
    safe_tools = SafeInboxTools(gmail_client)
    approval_tools = ApprovalRequiredTools(gmail_client)

    # 1. Node: Fetch emails
    def fetch_emails_node(state: AgentState) -> Dict[str, Any]:
        existing_emails = state.get("emails", [])
        if not existing_emails:
            emails = safe_tools.fetch_inbox_emails(max_results=50)
        else:
            emails = existing_emails

        return {
            "emails": emails,
            "status": "emails_fetched",
        }

    # 2. Node: Categorize emails
    def categorize_emails_node(state: AgentState) -> Dict[str, Any]:
        emails = state.get("emails", [])
        categorized: Dict[str, List[str]] = {cat.value: [] for cat in EmailCategory}

        for email in emails:
            if email.category == EmailCategory.UNCATEGORIZED:
                decision = classify_email(email)
                email.category = decision.category
                email.importance_reason = decision.reasoning
            categorized[email.category.value].append(email.id)

        stats = safe_tools.compute_stats(emails)
        return {
            "emails": emails,
            "categorized_emails": categorized,
            "stats": stats,
            "status": "emails_categorized",
        }

    # 3. Node: Generate cleanup proposals
    def generate_proposals_node(state: AgentState) -> Dict[str, Any]:
        emails = state.get("emails", [])
        proposals: List[ProposedAction] = []

        unwanted_ids = [e.id for e in emails if e.category == EmailCategory.UNWANTED]
        promotional_ids = [e.id for e in emails if e.category == EmailCategory.PROMOTIONAL]
        newsletter_ids = [e.id for e in emails if e.category == EmailCategory.NEWSLETTER]
        important_ids = [e.id for e in emails if e.category == EmailCategory.IMPORTANT]

        # Proposal 1: Trash unwanted / spam
        if unwanted_ids:
            proposals.append(
                ProposedAction(
                    id=f"prop_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.TRASH,
                    title=f"Move {len(unwanted_ids)} unwanted/spam emails to Trash",
                    description=(
                        f"Detected {len(unwanted_ids)} suspicious spam, cold outbound pitches, "
                        "or scam emails. Recommended to move directly to Trash."
                    ),
                    target_email_ids=unwanted_ids,
                    count=len(unwanted_ids),
                    risk_level=RiskLevel.MEDIUM,
                    reason="Identified unsolicited sales outreach or suspicious messages.",
                )
            )

        # Proposal 2: Trash promotional marketing emails
        if promotional_ids:
            proposals.append(
                ProposedAction(
                    id=f"prop_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.TRASH,
                    title=f"Move {len(promotional_ids)} promotional emails to Trash",
                    description=(
                        f"Found {len(promotional_ids)} retail marketing discounts, coupons, and sales ads."
                    ),
                    target_email_ids=promotional_ids,
                    count=len(promotional_ids),
                    risk_level=RiskLevel.MEDIUM,
                    reason="Commercial promotions cluttering priority inbox.",
                )
            )

        # Proposal 3: Archive newsletters
        if newsletter_ids:
            proposals.append(
                ProposedAction(
                    id=f"prop_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.ARCHIVE,
                    title=f"Archive {len(newsletter_ids)} newsletter digests",
                    description=(
                        f"Found {len(newsletter_ids)} newsletters (e.g. TLDR, Pragmatic Engineer). "
                        "Archiving keeps them accessible in All Mail while cleaning the inbox."
                    ),
                    target_email_ids=newsletter_ids,
                    count=len(newsletter_ids),
                    risk_level=RiskLevel.LOW,
                    reason="Editorial digests can be safely archived from main inbox.",
                )
            )

        # Proposal 4: Label important emails
        if important_ids:
            proposals.append(
                ProposedAction(
                    id=f"prop_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.LABEL,
                    title=f"Apply 'Important' label to {len(important_ids)} priority emails",
                    description=(
                        f"Identified {len(important_ids)} critical messages (security alerts, management signoffs, invoices)."
                    ),
                    target_email_ids=important_ids,
                    count=len(important_ids),
                    risk_level=RiskLevel.LOW,
                    label_to_apply="INBOXGPT_PRIORITY",
                    reason="Highlights critical correspondence for immediate review.",
                )
            )

        stats = state.get("stats") or safe_tools.compute_stats(emails)
        stats.pending_actions_count = len(proposals)

        return {
            "proposed_actions": proposals,
            "stats": stats,
            "status": "proposals_generated",
        }

    # 4. Node: Human approval gate (HITL)
    def human_approval_gate_node(state: AgentState) -> Dict[str, Any]:
        proposals = state.get("proposed_actions", [])
        if not proposals:
            return {"status": "no_proposals_to_approve"}

        if enable_interrupt:
            # Emit interrupt for human-in-the-loop approval
            user_decision = interrupt({
                "type": "approval_required",
                "proposals": [p.model_dump() for p in proposals],
                "message": (
                    f"InboxGPT generated {len(proposals)} suggested cleanup actions. "
                    "Review and approve or reject before execution."
                ),
            })

            approved = []
            rejected = []
            if isinstance(user_decision, dict):
                approved = user_decision.get("approved_action_ids", [])
                rejected = user_decision.get("rejected_action_ids", [])
            elif isinstance(user_decision, list):
                approved = user_decision

            return {
                "approved_action_ids": approved,
                "rejected_action_ids": rejected,
                "user_approval_decision": user_decision if isinstance(user_decision, dict) else {},
                "status": "approval_received",
            }

        return {"status": "approval_bypassed"}

    # 5. Node: Execute approved actions
    def execute_actions_node(state: AgentState) -> Dict[str, Any]:
        proposals = state.get("proposed_actions", [])
        approved_ids = set(state.get("approved_action_ids", []))
        rejected_ids = set(state.get("rejected_action_ids", []))
        results: List[ActionResult] = []

        for p in proposals:
            if p.id in approved_ids:
                p.status = ActionStatus.APPROVED
                if p.action_type == ActionType.TRASH:
                    res = approval_tools.execute_trash(p, dry_run=dry_run)
                elif p.action_type == ActionType.DELETE:
                    res = approval_tools.execute_delete(p, dry_run=dry_run)
                elif p.action_type == ActionType.ARCHIVE:
                    res = approval_tools.execute_archive(p, dry_run=dry_run)
                elif p.action_type == ActionType.LABEL:
                    label = p.label_to_apply or "INBOXGPT_PRIORITY"
                    res = approval_tools.execute_label(p, label, dry_run=dry_run)
                else:
                    res = ActionResult(
                        action_id=p.id,
                        success=False,
                        affected_count=0,
                        message=f"Unsupported action type: {p.action_type}",
                    )
                p.status = ActionStatus.EXECUTED if res.success else ActionStatus.FAILED
                results.append(res)
            elif p.id in rejected_ids:
                p.status = ActionStatus.REJECTED
                results.append(
                    ActionResult(
                        action_id=p.id,
                        success=True,
                        affected_count=0,
                        message=f"Action '{p.title}' was rejected by user.",
                    )
                )

        return {
            "proposed_actions": proposals,
            "action_results": results,
            "status": "actions_executed",
        }

    # 6. Node: Generate final summary report
    def report_results_node(state: AgentState) -> Dict[str, Any]:
        stats = state.get("stats") or InboxStats()
        results = state.get("action_results", [])
        proposals = state.get("proposed_actions", [])

        lines = [
            "=== InboxGPT Triage Report ===",
            f"Total Emails Analyzed: {stats.total_emails}",
            f"  • Important:   {stats.important_count}",
            f"  • Newsletter:  {stats.newsletter_count}",
            f"  • Social:      {stats.social_count}",
            f"  • Promotional: {stats.promotional_count}",
            f"  • Unwanted:    {stats.unwanted_count}",
            "",
            f"Generated Proposals: {len(proposals)}",
        ]

        if results:
            lines.append("Execution Results:")
            for r in results:
                status_icon = "✅" if r.success else "❌"
                lines.append(f"  {status_icon} {r.message}")

        report = "\n".join(lines)
        return {"summary_report": report, "status": "completed"}

    # Define Graph
    workflow = StateGraph(AgentState)

    workflow.add_node("fetch_emails", fetch_emails_node)
    workflow.add_node("categorize_emails", categorize_emails_node)
    workflow.add_node("generate_proposals", generate_proposals_node)
    workflow.add_node("human_approval_gate", human_approval_gate_node)
    workflow.add_node("execute_actions", execute_actions_node)
    workflow.add_node("report_results", report_results_node)

    workflow.add_edge(START, "fetch_emails")
    workflow.add_edge("fetch_emails", "categorize_emails")
    workflow.add_edge("categorize_emails", "generate_proposals")
    workflow.add_edge("generate_proposals", "human_approval_gate")
    workflow.add_edge("human_approval_gate", "execute_actions")
    workflow.add_edge("execute_actions", "report_results")
    workflow.add_edge("report_results", END)

    if enable_interrupt:
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


def run_inbox_agent(
    graph,
    initial_state: Optional[Dict[str, Any]] = None,
    thread_id: str = "default",
) -> Dict[str, Any]:
    """Execute graph with default thread configuration for checkpointing."""
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(initial_state or {}, config=config)

