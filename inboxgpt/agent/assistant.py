"""Executive AI Assistant with autonomous ReAct tool calling and long-term memory."""

import json
from typing import Any, Dict, List, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from inboxgpt.agent.llm import get_llm
from inboxgpt.agent.memory import memory
from inboxgpt.gmail.client import GmailServiceProtocol
from inboxgpt.gmail.models import EmailMessage


def build_assistant_tools(client: GmailServiceProtocol, current_emails: List[EmailMessage]):
    """Construct bound LangChain tools for the autonomous executive agent."""

    @tool
    def search_mailbox(query: str, max_results: int = 15) -> str:
        """Search Gmail for emails matching a keyword, sender, or Gmail search syntax."""
        try:
            results = client.list_messages(query=query, max_results=max_results)
            if not results:
                return f"No emails found matching query '{query}'."
            lines = [f"Found {len(results)} emails:"]
            for e in results:
                lines.append(f"- ID: {e.id} | From: {e.sender_name or e.sender} | Date: {e.date} | Subject: {e.subject}")
            return "\n".join(lines)
        except Exception as ex:
            return f"Search error: {ex}"

    @tool
    def read_email_details(email_id: str) -> str:
        """Read the full body text and headers of a specific email by its ID."""
        try:
            msg = client.get_message(email_id)
            if not msg:
                # Search in current loaded emails
                for e in current_emails:
                    if e.id == email_id:
                        msg = e
                        break
            if not msg:
                return f"Email with ID '{email_id}' not found."
            return (
                f"Subject: {msg.subject}\n"
                f"From: {msg.sender_name} <{msg.sender}>\n"
                f"Date: {msg.date}\n"
                f"Category: {msg.category.value}\n"
                f"Body Content:\n{msg.body or msg.snippet}"
            )
        except Exception as ex:
            return f"Error reading email: {ex}"

    @tool
    def create_email_draft(to: str, subject: str, body: str, thread_id: Optional[str] = None) -> str:
        """Create a real draft message in Gmail for the user to review or send."""
        try:
            res = client.create_draft(to=to, subject=subject, body=body, thread_id=thread_id)
            if res.success:
                return f"SUCCESS: Draft created in Gmail for '{to}' (Subject: '{subject}')."
            return f"Failed to create draft: {res.message}"
        except Exception as ex:
            return f"Draft error: {ex}"

    @tool
    def save_agent_memory(rule: str) -> str:
        """Save a user preference, habit, or permanent rule into long-term memory."""
        memory.add_rule(rule)
        return f"Rule successfully remembered: '{rule}'"

    @tool
    def get_agent_memories() -> str:
        """Retrieve all rules and preferences currently stored in long-term memory."""
        return memory.get_context_prompt()

    return [
        search_mailbox,
        read_email_details,
        create_email_draft,
        save_agent_memory,
        get_agent_memories,
    ]


def ask_executive_agent(
    user_prompt: str,
    client: GmailServiceProtocol,
    current_emails: List[EmailMessage],
) -> str:
    """Execute autonomous multi-step reasoning loop with Gemini and Gmail tools."""
    llm = get_llm()
    if not llm:
        return "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file."

    tools = build_assistant_tools(client, current_emails)
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    user_rules = memory.get_context_prompt()

    # Provide high-level context of currently loaded inbox emails
    email_sample = []
    for e in current_emails[:15]:
        email_sample.append(f"• ID: {e.id} | [{e.category.value.upper()}] From: {e.sender_name or e.sender} | Subj: {e.subject}")
    email_overview = "\n".join(email_sample)

    system_prompt = f"""You are the InboxGPT Executive Assistant, powered by Gemini.
You have live access to the user's Gmail mailbox via tools.

CORE PRINCIPLES:
1. Long-Term Preferences:
{user_rules}

2. Inviolable Safety:
- Never delete or trash Starred, Important, Security alerts, OTPs, or financial receipts.
- When the user asks to draft a reply, inspect the conversation first, then call `create_email_draft` with a concise, polite, professional response.

3. Current Inbox Preview:
{email_overview}

Solve the user's request autonomously by invoking relevant tools, and provide a clear, helpful final response."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # ReAct execution loop (max 4 turns)
    for _ in range(4):
        try:
            ai_msg = llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            if not ai_msg.tool_calls:
                # Finished reasoning
                if isinstance(ai_msg.content, list):
                    texts = [c.get("text", "") for c in ai_msg.content if isinstance(c, dict)]
                    return " ".join(texts) or "Done."
                return str(ai_msg.content)

            # Execute tool calls
            for tc in ai_msg.tool_calls:
                fn_name = tc["name"]
                args = tc["args"]
                tool_fn = tools_by_name.get(fn_name)
                if tool_fn:
                    try:
                        observation = tool_fn.invoke(args)
                    except Exception as err:
                        observation = f"Tool execution failed: {err}"
                else:
                    observation = f"Unknown tool: {fn_name}"

                messages.append(
                    ToolMessage(
                        tool_call_id=tc.get("id", "call_1"),
                        content=str(observation),
                    )
                )
        except Exception as e:
            return f"Agent reasoning interrupted: {e}"

    return "Agent completed multi-step analysis."
