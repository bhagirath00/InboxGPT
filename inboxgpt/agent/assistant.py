"""Executive AI Assistant with autonomous ReAct tool calling and long-term memory."""

from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
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
        results = []
        try:
            results = client.list_messages(query=query, max_results=max_results)
        except Exception:
            results = []

        if not results:
            # Fallback: search loaded emails in memory
            q_lower = query.lower()
            results = [
                e for e in current_emails
                if q_lower in (e.subject or "").lower()
                or q_lower in (e.sender_name or "").lower()
                or q_lower in (e.sender or "").lower()
                or q_lower in (e.snippet or "").lower()
            ][:max_results]

        if not results:
            return f"No emails found matching query '{query}'."

        lines = [f"Found {len(results)} emails:"]
        for e in results:
            dt = f"({e.date[:10]})" if e.date else ""
            lines.append(f"- ID: {e.id} | From: {e.sender_name or e.sender} | Date: {dt} | Subject: {e.subject}")
        return "\n".join(lines)

    @tool
    def find_emails_by_keyword(keywords: str) -> str:
        """Search current inbox emails by personal keywords, sender name, topic, or subject."""
        terms = [k.strip().lower() for k in keywords.split() if len(k.strip()) > 1]
        if not terms:
            terms = [keywords.strip().lower()]

        matches = []
        for e in current_emails:
            text_blob = f"{e.subject} {e.sender} {e.sender_name or ''} {e.snippet} {e.body or ''}".lower()
            if any(t in text_blob for t in terms):
                matches.append(e)

        if not matches:
            return f"No loaded emails match keyword(s): '{keywords}'."

        lines = [f"Found {len(matches)} matching email(s):"]
        for e in matches[:15]:
            dt = f"({e.date[:10]})" if e.date else ""
            lines.append(f"• ID: {e.id} | From: {e.sender_name or e.sender} | Subj: {e.subject} {dt}")
        return "\n".join(lines)

    @tool
    def read_email_details(email_id: str) -> str:
        """Read the full body text and headers of a specific email by its ID."""
        try:
            msg = client.get_message(email_id)
            if not msg:
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
        find_emails_by_keyword,
        read_email_details,
        create_email_draft,
        save_agent_memory,
        get_agent_memories,
    ]


def _local_search_fallback(query: str, emails: List[EmailMessage]) -> Optional[str]:
    """Offline keyword search helper when LLM is unavailable or fails."""
    terms = [k.strip().lower() for k in query.split() if len(k.strip()) > 2 and k.lower() not in ("find", "mail", "emails", "email", "show", "what", "give")]
    if not terms:
        terms = [query.strip().lower()]

    matched = []
    for e in emails:
        blob = f"{e.subject} {e.sender} {e.sender_name or ''} {e.snippet}".lower()
        if any(t in blob for t in terms):
            matched.append(e)

    if not matched:
        return None

    lines = [
        f"### Found {len(matched)} Email(s) for '{query}':\n",
    ]
    for e in matched[:10]:
        dt = f" ({e.date[:10]})" if e.date else ""
        lines.append(f"- **{e.sender_name or e.sender}**: {e.subject}{dt}")
        if e.snippet:
            lines.append(f"  > {e.snippet[:120]}...\n")
    return "\n".join(lines)


def _local_summary_fallback(emails: List[EmailMessage]) -> str:
    """Offline structured summary briefing."""
    from inboxgpt.gmail.models import EmailCategory

    prio = [e for e in emails if e.category == EmailCategory.IMPORTANT]
    promo = [e for e in emails if e.category == EmailCategory.PROMOTIONAL]
    news = [e for e in emails if e.category == EmailCategory.NEWSLETTER]
    soc = [e for e in emails if e.category == EmailCategory.SOCIAL]
    unread = [e for e in emails if e.is_unread]

    lines = [
        f"### Inbox Overview ({len(emails)} Total Emails)",
        f"- **Unread:** {len(unread)} | **Priority:** {len(prio)} | **Promo:** {len(promo)} | **News:** {len(news)} | **Social:** {len(soc)}\n",
    ]
    if prio:
        lines.append("#### Priority & Important Items:")
        for p in prio[:8]:
            dt = f" ({p.date[:10]})" if p.date else ""
            lines.append(f"- **{p.sender_name or p.sender}**: {p.subject}{dt}")
            if p.snippet:
                lines.append(f"  > {p.snippet[:100]}...\n")
    else:
        lines.append("#### Recent Inbox Items:")
        for p in emails[:6]:
            dt = f" ({p.date[:10]})" if p.date else ""
            lines.append(f"- **{p.sender_name or p.sender}**: {p.subject}{dt}\n")

    return "\n".join(lines)


def ask_executive_agent(
    user_prompt: str,
    client: GmailServiceProtocol,
    current_emails: List[EmailMessage],
) -> str:
    """Execute autonomous multi-step reasoning loop with LLM and Gmail tools, with graceful fallbacks."""
    llm = get_llm()

    # If no LLM configured, fulfill with local heuristics
    if not llm:
        p_lower = user_prompt.lower()
        if any(w in p_lower for w in ("summar", "overview", "brief", "digest")):
            return _local_summary_fallback(current_emails)
        search_res = _local_search_fallback(user_prompt, current_emails)
        if search_res:
            return search_res
        return (
            "No AI model configured. Add an API key in `.env` (NVIDIA_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY).\n\n"
            + _local_summary_fallback(current_emails)
        )

    tools = build_assistant_tools(client, current_emails)
    tools_by_name = {t.name: t for t in tools}

    # Provide high-level context of currently loaded inbox emails
    email_sample = []
    for e in current_emails[:20]:
        email_sample.append(f"• ID: {e.id} | [{e.category.value.upper()}] From: {e.sender_name or e.sender} | Subj: {e.subject}")
    email_overview = "\n".join(email_sample)
    user_rules = memory.get_context_prompt()

    system_prompt = f"""You are the InboxGPT Executive Assistant.
You have live access to the user's Gmail mailbox via tools.

CORE PRINCIPLES:
1. Long-Term Preferences:
{user_rules}

2. Inviolable Safety:
- Never delete or trash Starred, Important, Security alerts, OTPs, or financial receipts.
- When the user asks to draft a reply, inspect the conversation first, then call `create_email_draft` with a concise, polite, professional response.

3. Current Inbox Preview:
{email_overview}

Solve the user's request autonomously. Present findings clearly in Markdown with bold titles and bullet points."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Try tool calling, falling back to direct invoke if provider doesn't support bind_tools
    try:
        llm_with_tools = llm.bind_tools(tools)
    except Exception:
        llm_with_tools = None

    if llm_with_tools is None:
        try:
            res = llm.invoke(messages)
            return str(res.content)
        except Exception:
            return _local_summary_fallback(current_emails)

    # ReAct execution loop (max 4 turns)
    for _ in range(4):
        try:
            ai_msg = llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            if not ai_msg.tool_calls:
                if isinstance(ai_msg.content, list):
                    texts = [c.get("text", "") for c in ai_msg.content if isinstance(c, dict)]
                    return " ".join(texts) or "Done."
                return str(ai_msg.content)

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
            # Fall back gracefully to search or summary
            p_lower = user_prompt.lower()
            if any(w in p_lower for w in ("summar", "overview", "brief", "digest")):
                return _local_summary_fallback(current_emails)
            search_res = _local_search_fallback(user_prompt, current_emails)
            if search_res:
                return search_res
            return f"Agent reasoning interrupted: {e}"

    return _local_summary_fallback(current_emails)
