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
        background: rgba(0, 0, 0, 0.85);
    }

    #dialog {
        padding: 1 2;
        width: 76;
        height: auto;
        border: solid #27272a;
        background: #09090b;
        color: #ededed;
    }

    #title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 1;
    }

    #description {
        margin-bottom: 1;
        color: #d4d4d8;
    }

    #risk_warning {
        padding: 1;
        background: #18181b;
        color: #f59e0b;
        text-style: bold;
        margin-bottom: 1;
        border: solid #27272a;
    }

    #buttons {
        width: 100%;
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    .action_btn {
        height: 3;
        margin-left: 1;
        padding: 0 1;
        background: #141416;
        color: #a1a1aa;
        border: solid #27272a;
        text-style: bold;
    }

    .action_btn:hover {
        background: #27272a;
        color: #ffffff;
        border: solid #3f3f46;
    }

    #approve-btn {
        background: #27272a;
        color: #ffffff;
        border: solid #52525b;
        text-style: bold;
    }

    #approve-btn:hover {
        background: #3f3f46;
        color: #ffffff;
        border: solid #71717a;
    }

    #reject-btn {
        background: #141416;
        color: #f87171;
        border: solid #27272a;
    }

    #reject-btn:hover {
        background: #27272a;
        color: #ef4444;
        border: solid #7f1d1d;
    }

    #review-btn {
        background: #141416;
        color: #a1a1aa;
        border: solid #27272a;
    }

    #cancel-btn {
        background: #141416;
        color: #71717a;
        border: solid #27272a;
    }
    """

    def __init__(self, action: ProposedAction, emails: Optional[List[EmailMessage]] = None):
        super().__init__()
        self.action = action
        self.emails = emails or []

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"Action Approval Required: {self.action.title}", id="title")
            yield Static(self.action.description, id="description")

            risk_text = f"Risk Level: {self.action.risk_level.value.upper()} | Target Emails: {self.action.count}"
            if self.action.risk_level == RiskLevel.HIGH or self.action.risk_level == RiskLevel.MEDIUM:
                risk_text += " | ⚠️ This action will modify your mailbox upon confirmation!"
            yield Label(risk_text, id="risk_warning")

            if self.action.reason:
                yield Static(f"AI Reasoning: {self.action.reason}")

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
            self.dismiss("review")
        else:
            self.dismiss("cancel")

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss("approve")
        elif event.key == "n":
            self.dismiss("reject")
        elif event.key == "v":
            self.dismiss("review")
        elif event.key == "escape":
            self.dismiss("cancel")


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
        border: solid #27272a;
        background: #09090b;
        color: #ededed;
    }

    #search_title {
        text-style: bold;
        color: #ffffff;
        margin-bottom: 1;
    }

    #search_input {
        background: #18181b;
        color: #ffffff;
        border: solid #3f3f46;
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
        border: solid #27272a;
        background: #09090b;
        color: #ededed;
    }

    Button {
        margin-top: 1;
        background: #ffffff;
        color: #000000;
        text-style: bold;
        border: none;
    }
    Button:hover {
        background: #e4e4e7;
    }
    """

    HELP_MARKDOWN = """
### ⌨️ InboxGPT Keybindings Cheat Sheet

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
            yield Button("Close [Esc]", id="close_help", variant="primary")

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
        border: thick $accent;
        background: $surface;
    }

    #detail_scroll {
        height: 1fr;
        margin-top: 1;
        margin-bottom: 1;
    }
    """

    def __init__(self, email: EmailMessage):
        super().__init__()
        self.email = email

    def compose(self) -> ComposeResult:
        with Container(id="detail_box"):
            yield Label(f"✉️ {self.email.subject}", id="detail_title")
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
            yield Button("Back to Inbox [Esc]", id="close_detail", variant="default")

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
        border: solid #27272a;
        background: #09090b;
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

    .switch_btn {
        height: 3;
        margin-left: 1;
        min-width: 12;
        border: solid #27272a;
        background: #18181b;
        color: #d4d4d8;
    }

    .switch_btn:hover {
        background: #27272a;
        color: #ffffff;
    }

    #btn_do_switch {
        background: #ededed;
        color: #09090b;
        text-style: bold;
    }

    #btn_do_switch:hover {
        background: #ffffff;
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
        border: solid #27272a;
        background: #09090b;
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

    #btn_close_res {
        background: #18181b;
        border: solid #27272a;
        color: #f4f4f5;
        width: 100%;
        height: 3;
    }

    #btn_close_res:hover {
        background: #27272a;
        color: #ffffff;
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
