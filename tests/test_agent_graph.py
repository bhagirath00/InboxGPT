"""Tests for LangGraph agent workflow and Human-in-the-Loop approval behavior."""

from inboxgpt.agent.graph import create_inbox_graph
from inboxgpt.gmail.mock_client import MockGmailClient
from inboxgpt.gmail.models import ActionStatus, ActionType


def test_agent_graph_triage_and_proposal_generation():
    client = MockGmailClient()
    # Create graph with enable_interrupt=False for automated pipeline test
    graph = create_inbox_graph(client, enable_interrupt=False, dry_run=True)

    result = graph.invoke({})

    assert "stats" in result
    assert result["stats"].total_emails > 0
    assert "proposed_actions" in result
    proposals = result["proposed_actions"]
    assert len(proposals) > 0

    # Ensure proposals cover destructive and non-destructive action types
    action_types = [p.action_type for p in proposals]
    assert ActionType.TRASH in action_types or ActionType.ARCHIVE in action_types


def test_hitl_approval_executes_only_approved_actions():
    client = MockGmailClient()
    graph = create_inbox_graph(client, enable_interrupt=False, dry_run=False)

    # 1. Run analysis to get proposals
    result = graph.invoke({})
    proposals = result["proposed_actions"]
    assert len(proposals) > 0

    trash_proposal = next((p for p in proposals if p.action_type == ActionType.TRASH), None)
    assert trash_proposal is not None

    # Verify that only the explicitly approved action is executed
    from inboxgpt.agent.tools import ApprovalRequiredTools
    approval_tools = ApprovalRequiredTools(client)

    initial_count = len(client.list_messages())
    exec_result = approval_tools.execute_trash(trash_proposal)
    assert exec_result.success is True

    new_count = len(client.list_messages())
    assert new_count == initial_count - trash_proposal.count


def test_langgraph_interrupt_and_resume():
    """Verify LangGraph pause on interrupt and resume with user approval decision."""
    from langgraph.types import Command

    client = MockGmailClient()
    graph = create_inbox_graph(client, enable_interrupt=True, dry_run=True)
    thread_config = {"configurable": {"thread_id": "test_hitl_session"}}

    # Graph runs and pauses at human_approval_gate
    state = graph.invoke({}, config=thread_config)

    # Inspect interrupted state
    snapshot = graph.get_state(thread_config)
    assert len(snapshot.tasks) > 0
    # The interrupt value contains the proposals
    interrupt_data = snapshot.tasks[0].interrupts[0].value
    assert interrupt_data["type"] == "approval_required"
    assert len(interrupt_data["proposals"]) > 0

    first_prop_id = interrupt_data["proposals"][0]["id"]

    # Resume graph with explicit human approval
    resumed_result = graph.invoke(
        Command(resume={"approved_action_ids": [first_prop_id], "rejected_action_ids": []}),
        config=thread_config,
    )
    assert resumed_result["status"] == "completed"
    assert len(resumed_result["action_results"]) > 0

