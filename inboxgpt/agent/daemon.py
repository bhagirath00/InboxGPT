"""Background Daemon & Executive Morning Briefing Engine for InboxGPT."""

from datetime import datetime
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel

from inboxgpt.config import config
from inboxgpt.gmail.client import GmailServiceProtocol, get_gmail_client
from inboxgpt.gmail.models import EmailCategory, EmailMessage
from inboxgpt.agent.llm import get_llm
from inboxgpt.agent.triage_agent import is_protected_email

console = Console(legacy_windows=False)


class DaemonEngine:
    """Orchestrates periodic inbox monitoring and Executive Morning Briefings."""

    def __init__(self, client: Optional[GmailServiceProtocol] = None, force_mock: bool = False):
        self.client = client or get_gmail_client(force_mock=force_mock)
        self.briefings_dir = config.config_dir / "briefings"
        self.briefings_dir.mkdir(parents=True, exist_ok=True)
        self.latest_briefing_file = self.briefings_dir / "latest_briefing.md"
        self.history_file = self.briefings_dir / "history.json"

    def fetch_recent_emails(self, max_results: int = 50) -> List[EmailMessage]:
        """Fetch latest unread or recent emails for synthesis."""
        return self.client.list_messages(query="", max_results=max_results)

    def generate_briefing(self, emails: List[EmailMessage]) -> str:
        """Synthesize an Executive Briefing using Gemini or structured offline heuristic."""
        if not emails:
            return "### 📭 Inbox Zero!\n\nNo unread or recent emails found. You are all caught up!"

        llm = get_llm()
        if llm:
            try:
                # Prepare compact context for the LLM
                email_summaries = []
                for e in emails[:25]:
                    email_summaries.append(
                        f"- ID: {e.id} | From: {e.sender_name or e.sender} | Date: {e.date} | "
                        f"Category: {e.category.value} | Starred: {'STARRED' in e.labels} | "
                        f"Subject: {e.subject} | Snippet: {e.snippet[:120]}"
                    )

                prompt = (
                    "You are an elite Executive Assistant. Read the following emails and synthesize a concise, "
                    "high-impact Morning Executive Briefing in Markdown.\n\n"
                    "Structure the report with these sections:\n"
                    "1. 🚨 **Immediate Action Items & Urgencies** (Deadlines, requests needing reply, payments)\n"
                    "2. ⭐ **Key Highlights & Important Communications** (Boss, clients, team, high-priority updates)\n"
                    "3. 🛡️ **Security & System Notices** (OTPs, password resets, login alerts)\n"
                    "4. 📊 **Inbox Digest Stats** (Total analyzed, promotional/newsletter volume)\n\n"
                    "Be crisp, actionable, and professional. Avoid fluff.\n\n"
                    "Emails:\n" + "\n".join(email_summaries)
                )

                resp = llm.invoke(prompt)
                content = getattr(resp, "content", "")
                if content and isinstance(content, str) and len(content.strip()) > 30:
                    return content.strip()
            except Exception:
                pass

        # Offline fallback synthesis
        return self._generate_offline_briefing(emails)

    def _generate_offline_briefing(self, emails: List[EmailMessage]) -> str:
        """Structured heuristic briefing generator when offline."""
        action_items = []
        starred_items = []
        security_items = []
        clutter_count = 0

        for e in emails:
            sub = (e.subject or "").lower()
            snd = (e.sender_name or e.sender or "").lower()
            is_starred = "STARRED" in e.labels

            if is_starred:
                starred_items.append(f"- ⭐ **{e.sender_name or e.sender}**: {e.subject} *({e.date[:10] if e.date else ''})*")

            if any(w in sub for w in ["action required", "urgent", "review", "sign", "deadline", "invoice", "meeting"]):
                action_items.append(f"- 📌 **{e.sender_name or e.sender}**: {e.subject}")
            elif any(w in sub for w in ["otp", "code", "security alert", "password reset", "verification"]):
                security_items.append(f"- 🔒 **{e.sender_name or e.sender}**: {e.subject}")
            elif e.category in (EmailCategory.PROMOTIONAL, EmailCategory.NEWSLETTER, EmailCategory.SOCIAL):
                clutter_count += 1

        now_str = datetime.now().strftime("%A, %b %d, %Y at %I:%M %p")
        lines = [
            "# 🌅 Executive Morning Briefing",
            f"*Generated on {now_str}*",
            "",
            "## 🚨 Immediate Action Items",
        ]

        if action_items:
            lines.extend(action_items[:5])
        else:
            lines.append("- *No urgent deadlines or action items detected.*")

        lines.extend(["", "## ⭐ Starred & Priority Communications"])
        if starred_items:
            lines.extend(starred_items[:5])
        else:
            lines.append("- *No unread starred emails.*")

        lines.extend(["", "## 🛡️ Security & Authentication"])
        if security_items:
            lines.extend(security_items[:5])
        else:
            lines.append("- *No pending authentication or security alerts.*")

        lines.extend([
            "",
            "## 📊 Mailbox Volume Overview",
            f"- Total analyzed: **{len(emails)}** emails",
            f"- Detected marketing & newsletters: **{clutter_count}** items",
        ])

        return "\n".join(lines)

    def save_briefing(self, briefing_text: str, email_count: int) -> None:
        """Persist the briefing to disk."""
        with open(self.latest_briefing_file, "w", encoding="utf-8") as f:
            f.write(briefing_text)

        # Update history
        history: List[Dict[str, Any]] = []
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append({
            "timestamp": datetime.now().isoformat(),
            "emails_analyzed": email_count,
            "preview": briefing_text[:120].replace("\n", " "),
        })
        # Keep last 50 runs
        history = history[-50:]

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def run_cycle(self, auto_archive_clutter: bool = False) -> Tuple[str, int]:
        """Execute a single scan, synthesis, and optional safe clutter management."""
        emails = self.fetch_recent_emails(max_results=50)
        briefing = self.generate_briefing(emails)
        self.save_briefing(briefing, len(emails))

        # Optional auto-archiving of purely promotional/newsletter clutter
        if auto_archive_clutter and emails:
            clutter_ids = []
            for e in emails:
                protected, _ = is_protected_email(e)
                if not protected and e.category in (EmailCategory.PROMOTIONAL, EmailCategory.NEWSLETTER):
                    clutter_ids.append(e.id)
            if clutter_ids:
                try:
                    self.client.batch_archive(clutter_ids)
                except Exception:
                    pass

        return briefing, len(emails)

    def start_loop(self, interval_minutes: int = 30, auto_archive_clutter: bool = False) -> None:
        """Run continuous daemon monitoring."""
        console.print(Panel.fit(
            f"[bold cyan]InboxGPT Daemon Service Active[/bold cyan]\n"
            f"• Polling Interval: [green]{interval_minutes} minutes[/green]\n"
            f"• Clutter Auto-Archive: [{'green]Enabled' if auto_archive_clutter else 'yellow]Disabled (Briefing only)'}[/]\n"
            f"• Output Location: [dim]{self.latest_briefing_file}[/dim]\n"
            f"[dim]Press Ctrl+C to terminate.[/dim]"
        ))

        cycle = 1
        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            console.print(f"\n[cyan][{timestamp}][/cyan] Running Cycle #{cycle}...")
            try:
                briefing, count = self.run_cycle(auto_archive_clutter=auto_archive_clutter)
                console.print(f"[green]✓ Analyzed {count} emails. Executive briefing updated.[/green]")
            except Exception as e:
                console.print(f"[red]Error during daemon cycle: {e}[/red]")

            cycle += 1
            time.sleep(interval_minutes * 60)
