"""Interactive modal screens for InboxGPT TUI."""

from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Markdown, Static

from inboxgpt.gmail.models import EmailMessage, ProposedAction, RiskLevel


class ApprovalModal(ModalScreen[str]):
    """Human-in-the-loop modal dialog for reviewing and approving/rejecting cleanup actions."""

    DEFAULT_CSS = """
    ApprovalModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.88);
    }

    #dialog {
        padding: 1 2;
        width: 90;
        max-width: 96%;
        height: auto;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 1;
        width: 100%;
    }

    #description {
        margin-bottom: 1;
        color: #cbd5e1;
        width: 100%;
    }

    #risk_warning {
        padding: 1;
        background: #000000;
        color: #fbbf24;
        text-style: bold;
        margin-bottom: 1;
        border: round #b45309;
        height: auto;
    }

    #target_emails_box {
        background: #000000;
        border: round #27272a;
        padding: 1;
        margin-bottom: 1;
        max-height: 8;
        height: auto;
    }

    #target_emails_title {
        color: #e4e4e7;
        text-style: bold;
        margin-bottom: 0;
    }

    #target_emails_list {
        color: #a1a1aa;
    }

    #reasoning_box {
        margin-bottom: 1;
        color: #94a3b8;
        width: 100%;
    }

    #buttons {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    .action_btn, .action_btn.-style-default {
        height: 3;
        margin-left: 1;
        background: #000000 !important;
        background-tint: transparent !important;
        color: #d4d4d8;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    .action_btn:hover, .action_btn:focus, .action_btn.-active,
    .action_btn.-style-default:hover, .action_btn.-style-default:focus, .action_btn.-style-default.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #approve-btn {
        background: #000000 !important;
        color: #34d399;
        border: round #065f46 !important;
        border-top: round #065f46 !important;
        border-bottom: round #065f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #approve-btn:hover, #approve-btn:focus, #approve-btn.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #10b981 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #reject-btn {
        background: #000000 !important;
        color: #f87171;
        border: round #7f1d1d !important;
        border-top: round #7f1d1d !important;
        border-bottom: round #7f1d1d !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #reject-btn:hover, #reject-btn:focus, #reject-btn.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #ef4444 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    def __init__(self, action: ProposedAction, emails: Optional[List[EmailMessage]] = None):
        super().__init__()
        self.action = action
        self.emails = emails or []

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static(f"Action Approval Required: {self.action.title}", id="title")
            yield Static(self.action.description, id="description")

            risk_text = f"Risk Level: {self.action.risk_level.value.upper()} | Target Emails: {self.action.count}"
            if self.action.risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM):
                risk_text += " | This action will modify your mailbox upon confirmation!"
            yield Static(risk_text, id="risk_warning")

            matched_emails = [e for e in self.emails if e.id in self.action.target_email_ids]
            if matched_emails:
                with Container(id="target_emails_box"):
                    yield Static(f"Emails Affected ({len(matched_emails)}):", id="target_emails_title")
                    lines = []
                    for e in matched_emails[:6]:
                        sender = (e.sender_name or e.sender)[:24]
                        subj = (e.subject or "(No Subject)")[:48]
                        dt = f" ({e.date[:10]})" if e.date else ""
                        lines.append(f"• [{sender}] {subj}{dt}")
                    if len(matched_emails) > 6:
                        lines.append(f"  ... and {len(matched_emails) - 6} more emails")
                    yield Static("\n".join(lines), id="target_emails_list")

            if self.action.reason:
                yield Static(f"AI Reasoning: {self.action.reason}", id="reasoning_box")

            with Horizontal(id="buttons"):
                yield Button("Review Target Emails [v]", id="review-btn", classes="action_btn")
                yield Button("Reject [n]", id="reject-btn", classes="action_btn")
                yield Button("Approve [y]", id="approve-btn", classes="action_btn")
                yield Button("Cancel [Esc]", id="cancel-btn", classes="action_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve-btn":
            self.dismiss("approve")
        elif event.button.id == "reject-btn":
            self.dismiss("reject")
        elif event.button.id == "review-btn":
            def on_review_decision(res: Optional[str]) -> None:
                if res in ("approve", "reject"):
                    self.dismiss(res)
                # If "back", stays in ApprovalModal

            self.app.push_screen(ReviewTargetEmailsModal(self.action, self.emails), on_review_decision)
        else:
            self.dismiss("cancel")

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss("approve")
        elif event.key == "n":
            self.dismiss("reject")
        elif event.key == "v":
            def on_review_decision(res: Optional[str]) -> None:
                if res in ("approve", "reject"):
                    self.dismiss(res)

            self.app.push_screen(ReviewTargetEmailsModal(self.action, self.emails), on_review_decision)
        elif event.key == "escape":
            self.dismiss("cancel")


class ReviewTargetEmailsModal(ModalScreen[str]):
    """Modal displaying all target emails for detailed inspection with clear back/approve/reject buttons."""

    DEFAULT_CSS = """
    ReviewTargetEmailsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.88);
    }

    #review_dialog {
        padding: 1 2;
        width: 88;
        max-width: 96%;
        height: 80%;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #review_title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 0;
    }

    #review_subtitle {
        color: #a1a1aa;
        margin-bottom: 1;
    }

    #review_scroll {
        height: 1fr;
        border-top: solid #18181b;
        border-bottom: solid #18181b;
        padding: 1 0;
        margin-bottom: 1;
    }

    .review_email_row {
        background: #000000;
        border: round #27272a;
        padding: 1;
        margin-bottom: 1;
    }

    .review_email_header {
        color: #f4f4f5;
        text-style: bold;
    }

    .review_email_snippet {
        color: #71717a;
    }

    #review_buttons {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
    }

    .review_btn, .review_btn.-style-default {
        height: 3;
        margin-left: 1;
        background: #000000 !important;
        background-tint: transparent !important;
        color: #d4d4d8;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    .review_btn:hover, .review_btn:focus, .review_btn.-active,
    .review_btn.-style-default:hover, .review_btn.-style-default:focus, .review_btn.-style-default.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_review_approve {
        background: #000000 !important;
        color: #34d399;
        border: round #065f46 !important;
        border-top: round #065f46 !important;
        border-bottom: round #065f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_review_approve:hover, #btn_review_approve:focus, #btn_review_approve.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #10b981 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_review_reject {
        background: #000000 !important;
        color: #f87171;
        border: round #7f1d1d !important;
        border-top: round #7f1d1d !important;
        border-bottom: round #7f1d1d !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_review_reject:hover, #btn_review_reject:focus, #btn_review_reject.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #ef4444 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    def __init__(self, action: ProposedAction, emails: List[EmailMessage]):
        super().__init__()
        self.action = action
        self.target_emails = [e for e in emails if e.id in action.target_email_ids]

    def compose(self) -> ComposeResult:
        with Container(id="review_dialog"):
            yield Static(f"Review Target Emails: {self.action.title}", id="review_title")
            yield Static(
                f"Reviewing {len(self.target_emails)} target emails. Inspect items and approve, reject, or return:",
                id="review_subtitle",
            )
            with VerticalScroll(id="review_scroll"):
                for e in self.target_emails:
                    with Vertical(classes="review_email_row"):
                        sender = e.sender_name or e.sender
                        dt = f" · {e.date[:16]}" if e.date else ""
                        yield Static(f"[{sender}] {e.subject}{dt}", classes="review_email_header")
                        if e.snippet:
                            yield Static(f"  {e.snippet[:140]}...", classes="review_email_snippet")

            with Horizontal(id="review_buttons"):
                yield Button("Back to Proposal [b / Esc]", id="btn_review_back", classes="review_btn")
                yield Button("Reject [n]", id="btn_review_reject", classes="review_btn")
                yield Button("Approve [y]", id="btn_review_approve", classes="review_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_review_approve":
            self.dismiss("approve")
        elif event.button.id == "btn_review_reject":
            self.dismiss("reject")
        else:
            self.dismiss("back")

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss("approve")
        elif event.key == "n":
            self.dismiss("reject")
        elif event.key in ("escape", "b"):
            self.dismiss("back")


class QuitConfirmModal(ModalScreen[bool]):
    """Confirmation modal before quitting InboxGPT."""

    DEFAULT_CSS = """
    QuitConfirmModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.88);
    }

    #quit_dialog {
        padding: 1 2;
        width: 52;
        height: auto;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #quit_title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 1;
    }

    #quit_desc {
        color: #a1a1aa;
        margin-bottom: 1;
    }

    #quit_buttons {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    .quit_btn, .quit_btn.-style-default {
        height: 3;
        margin-left: 1;
        background: #000000 !important;
        background-tint: transparent !important;
        color: #d4d4d8;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    .quit_btn:hover, .quit_btn:focus, .quit_btn.-active,
    .quit_btn.-style-default:hover, .quit_btn.-style-default:focus, .quit_btn.-style-default.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_confirm_quit {
        background: #000000 !important;
        color: #f87171;
        border: round #7f1d1d !important;
        border-top: round #7f1d1d !important;
        border-bottom: round #7f1d1d !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_confirm_quit:hover, #btn_confirm_quit:focus, #btn_confirm_quit.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #ef4444 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="quit_dialog"):
            yield Static("Quit InboxGPT", id="quit_title")
            yield Static("Are you sure you want to quit?", id="quit_desc")
            with Horizontal(id="quit_buttons"):
                yield Button("Cancel [n / Esc]", id="btn_cancel_quit", classes="quit_btn")
                yield Button("Quit [y]", id="btn_confirm_quit", classes="quit_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm_quit":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key in ("y", "enter"):
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)


class SearchModal(ModalScreen[Optional[str]]):
    """Modal dialog for searching inbox emails."""

    DEFAULT_CSS = """
    SearchModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }

    #search_box {
        width: 70;
        height: auto;
        padding: 1 2;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #search_title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 1;
    }

    #search_input {
        background: #000000;
        color: #ffffff;
        border: round #3f3f46;
    }

    #search_input:focus {
        background: #000000;
        border: round #71717a;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="search_box"):
            yield Label("▲ Search Inbox (e.g. from:github, subject:interview, category:promotions)", id="search_title")
            yield Input(placeholder="Enter search query and press Enter...", id="search_input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class HelpModal(ModalScreen[None]):
    """Keybinding cheat sheet modal."""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }

    #help_box {
        width: 75;
        height: auto;
        padding: 1 2;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #close_help, #close_help.-style-default,
    #close_help:hover, #close_help:focus, #close_help.-active,
    #close_help.-style-default:hover, #close_help.-style-default:focus, #close_help.-style-default.-active {
        margin-top: 1;
        background: #000000 !important;
        background-tint: transparent !important;
        color: #d4d4d8;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #close_help:hover, #close_help:focus,
    #close_help.-style-default:hover, #close_help.-style-default:focus {
        background: #000000 !important;
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    HELP_MARKDOWN = """
### InboxGPT Keybindings Cheat Sheet

- **↑ / ↓ or j / k**: Navigate email rows
- **Enter**: Open & read full email text
- **d**: Trash selected email (immediate 0ms local removal)
- **e**: Archive selected email
- **x**: Toggle multi-selection checkbox
- **1 - 5**: Filter category tabs (1: All, 2: Priority, 3: Promo, 4: Social, 5: News)
- **a or /**: Open Gemini 2.5 Flash AI Agent dialog
- **r**: Sync & refresh mailbox from Gmail
- **l**: Switch / Logout active Gmail account
- **?**: Toggle this help screen
- **Esc / q**: Close dialog, back from reader, or quit

Press **Escape** or **Enter** to close this help window.
"""

    def compose(self) -> ComposeResult:
        with Container(id="help_box"):
            yield Markdown(self.HELP_MARKDOWN)
            yield Button("Close [Esc]", id="close_help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter", "q"):
            self.dismiss()


class EmailDetailModal(ModalScreen[None]):
    """Modal displaying full email headers, body, and AI classification."""

    DEFAULT_CSS = """
    EmailDetailModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #detail_box {
        width: 85%;
        height: 80%;
        padding: 1 2;
        border: round #3f3f46;
        background: #000000;
    }

    #detail_scroll {
        height: 1fr;
        margin-top: 1;
        margin-bottom: 1;
    }

    #close_detail, #close_detail.-style-default,
    #close_detail:hover, #close_detail:focus, #close_detail.-active,
    #close_detail.-style-default:hover, #close_detail.-style-default:focus, #close_detail.-style-default.-active {
        background: #000000 !important;
        background-tint: transparent !important;
        color: #d4d4d8;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #close_detail:hover, #close_detail:focus,
    #close_detail.-style-default:hover, #close_detail.-style-default:focus {
        background: #000000 !important;
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    def __init__(self, email: EmailMessage):
        super().__init__()
        self.email = email

    def compose(self) -> ComposeResult:
        with Container(id="detail_box"):
            yield Label(f"{self.email.subject}", id="detail_title")
            with VerticalScroll(id="detail_scroll"):
                content = f"""
**From:** {self.email.sender_name} `<{self.email.sender}>`
**Date:** {self.email.date}
**Category:** `{self.email.category.value.upper()}`
**AI Reason:** {self.email.importance_reason or 'None'}
**Labels:** {', '.join(self.email.labels)}

---

{self.email.body or self.email.snippet}
"""
                yield Markdown(content)
            yield Button("Back to Inbox [Esc]", id="close_detail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter", "q"):
            self.dismiss()


class SwitchAccountModal(ModalScreen[str]):
    """Confirmation modal for switching Gmail account or logging out."""

    DEFAULT_CSS = """
    SwitchAccountModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }

    #switch_box {
        width: 62;
        height: auto;
        padding: 1 2;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #switch_title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 1;
    }

    #switch_email_label {
        color: #71717a;
        margin-bottom: 0;
    }

    #switch_email_val {
        color: #f4f4f5;
        text-style: bold;
        margin-bottom: 1;
    }

    #switch_desc {
        color: #a1a1aa;
        margin-bottom: 1;
    }

    #switch_buttons {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    .switch_btn, .switch_btn.-style-default {
        height: 3;
        margin-left: 1;
        min-width: 12;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        background: #000000 !important;
        background-tint: transparent !important;
        color: #d4d4d8;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    .switch_btn:hover, .switch_btn.-style-default:hover {
        background: #000000 !important;
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    .switch_btn:focus, .switch_btn.-active,
    .switch_btn.-style-default:focus, .switch_btn.-style-default.-active {
        background: #000000 !important;
        color: #ffffff;
        border: round #a1a1aa !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_do_switch {
        border: round #ffffff !important;
        border-top: round #ffffff !important;
        border-bottom: round #ffffff !important;
        color: #ffffff;
    }

    #btn_do_switch:hover, #btn_do_switch:focus, #btn_do_switch.-active {
        border: round #ffffff !important;
        color: #ffffff;
        background: #000000 !important;
        outline: none !important;
        text-style: not reverse bold underline !important;
    }

    #btn_cancel_sw {
        color: #d4d4d8;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
    }

    #btn_cancel_sw:hover, #btn_cancel_sw:focus, #btn_cancel_sw.-active {
        color: #ffffff;
        border: round #71717a !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_logout_sw {
        color: #f87171;
        border: round #7f1d1d !important;
        border-top: round #7f1d1d !important;
        border-bottom: round #7f1d1d !important;
    }

    #btn_logout_sw:hover, #btn_logout_sw:focus, #btn_logout_sw.-active {
        color: #ffffff;
        border: round #ef4444 !important;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    def __init__(self, current_email: str):
        super().__init__()
        self.current_email = current_email

    def compose(self) -> ComposeResult:
        with Container(id="switch_box"):
            yield Label("▲ Switch / Logout Gmail Account", id="switch_title")
            yield Label("Currently Connected:", id="switch_email_label")
            yield Label(f"  {self.current_email}", id="switch_email_val")
            yield Label(
                "Switching clears your local OAuth token and email cache. "
                "You can connect a different Google account immediately.",
                id="switch_desc",
            )
            with Horizontal(id="switch_buttons"):
                yield Button("Cancel [Esc]", id="btn_cancel_sw", classes="switch_btn")
                yield Button("Logout", id="btn_logout_sw", classes="switch_btn")
                yield Button("Switch Account", id="btn_do_switch", classes="switch_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_do_switch":
            self.dismiss("switch")
        elif btn_id == "btn_logout_sw":
            self.dismiss("logout")
        else:
            self.dismiss("cancel")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss("cancel")
        elif event.key == "s":
            self.dismiss("switch")
        elif event.key == "l":
            self.dismiss("logout")


class AgentResultModal(ModalScreen[None]):
    """Modal displaying full output, findings, or draft confirmation from Executive AI Agent."""

    DEFAULT_CSS = """
    AgentResultModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }

    #agent_res_box {
        width: 76;
        height: 80%;
        padding: 1 2;
        border: round #3f3f46;
        background: #000000;
        color: #ededed;
    }

    #agent_res_title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 0;
    }

    #agent_res_prompt {
        color: #71717a;
        margin-bottom: 1;
    }

    #agent_res_scroll {
        height: 1fr;
        border-top: solid #18181b;
        border-bottom: solid #18181b;
        padding: 1 0;
        margin-bottom: 1;
    }

    #btn_close_res, #btn_close_res.-style-default,
    #btn_close_res:hover, #btn_close_res:focus, #btn_close_res.-active,
    #btn_close_res.-style-default:hover, #btn_close_res.-style-default:focus, #btn_close_res.-style-default.-active {
        background: #000000 !important;
        background-tint: transparent !important;
        border: round #3f3f46 !important;
        border-top: round #3f3f46 !important;
        border-bottom: round #3f3f46 !important;
        color: #f4f4f5;
        width: 100%;
        height: 3;
        outline: none !important;
        text-style: not reverse bold !important;
    }

    #btn_close_res:hover, #btn_close_res:focus,
    #btn_close_res.-style-default:hover, #btn_close_res.-style-default:focus {
        background: #000000 !important;
        border: round #71717a !important;
        color: #ffffff;
        outline: none !important;
        text-style: not reverse bold !important;
    }
    """

    def __init__(self, prompt: str, content: str):
        super().__init__()
        self.prompt = prompt
        self.content = content

    def compose(self) -> ComposeResult:
        with Container(id="agent_res_box"):
            yield Label("▲ Executive Assistant Response", id="agent_res_title")
            yield Label(f"Query: {self.prompt}", id="agent_res_prompt")
            with VerticalScroll(id="agent_res_scroll"):
                yield Markdown(self.content)
            yield Button("Back to Inbox [Esc]", id="btn_close_res")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter", "q"):
            self.dismiss()
