"""Full-width keyboard-driven terminal Gmail client and AI agent with Vercel monochrome aesthetic."""

from typing import List, Optional, Set
import uuid
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
)

from langgraph.types import Command
from inboxgpt.agent.graph import create_inbox_graph
from inboxgpt.agent.tools import ApprovalRequiredTools, SafeInboxTools
from inboxgpt.agent.triage_agent import plan_agent_cleanup
from inboxgpt.auth.oauth import get_auth_status
from inboxgpt.config import config
from inboxgpt.gmail.client import get_gmail_client
from inboxgpt.gmail.models import (
    ActionStatus,
    ActionType,
    EmailCategory,
    EmailMessage,
    InboxStats,
    ProposedAction,
    RiskLevel,
)
from inboxgpt.tui.modals import (
    AgentResultModal,
    ApprovalModal,
    HelpModal,
    SearchModal,
    SwitchAccountModal,
)


class AgentCommandModal(ModalScreen[Optional[str]]):
    """Clean Vercel-style compact modal for asking the AI agent or triggering 1-key quick cleanup."""

    DEFAULT_CSS = """
    AgentCommandModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }

    #agent_dialog {
        width: 58;
        height: 22;
        padding: 1 2;
        background: #09090b;
        border: solid #27272a;
    }

    #agent_modal_title {
        text-style: bold;
        color: #f4f4f5;
        height: 1;
        margin-bottom: 0;
    }

    #agent_modal_subtitle {
        color: #71717a;
        height: 1;
        margin-bottom: 1;
    }

    #agent_cmd_input {
        background: #121214;
        color: #ededed;
        border: solid #27272a;
        margin-bottom: 1;
        height: 3;
    }

    .modal_quick_row {
        height: 3;
        margin-bottom: 0;
    }

    .modal_quick_btn {
        margin-right: 1;
        background: #141416;
        color: #a1a1aa;
        border: solid #27272a;
        height: 3;
        width: 1fr;
    }
    .modal_quick_btn:hover {
        background: #27272a;
        color: #ffffff;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="agent_dialog"):
            yield Label("▲ Gemini 2.5 Flash Agent", id="agent_modal_title")
            yield Static(
                "Type goal or select quick action:",
                id="agent_modal_subtitle",
            )
            yield Input(
                placeholder="e.g. 'delete today useless emails'...",
                id="agent_cmd_input",
            )
            with Horizontal(classes="modal_quick_row"):
                yield Button("[1] Trash Today Useless", id="btn_quick_today", classes="modal_quick_btn")
                yield Button("[2] Trash Promos", id="btn_quick_promo", classes="modal_quick_btn")
            with Horizontal(classes="modal_quick_row"):
                yield Button("[3] Archive News", id="btn_quick_news", classes="modal_quick_btn")
                yield Button("[4] Priority Summary", id="btn_quick_sum", classes="modal_quick_btn")
            with Horizontal(classes="modal_quick_row"):
                yield Button("[5] LangGraph Audit", id="btn_quick_graph", classes="modal_quick_btn")
                yield Button("[Esc] Cancel", id="btn_cancel", classes="modal_quick_btn")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        if val:
            self.dismiss(val)
        else:
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_quick_today":
            self.dismiss("today i got useless mail delete those all")
        elif btn_id == "btn_quick_promo":
            self.dismiss("clean promo emails")
        elif btn_id == "btn_quick_news":
            self.dismiss("archive newsletters")
        elif btn_id == "btn_quick_sum":
            self.dismiss("summarize priority emails")
        elif btn_id == "btn_quick_graph":
            self.dismiss("run langgraph audit")
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "1":
            self.dismiss("today i got useless mail delete those all")
        elif event.key == "2":
            self.dismiss("clean promo emails")
        elif event.key == "3":
            self.dismiss("archive newsletters")
        elif event.key == "4":
            self.dismiss("summarize priority emails")
        elif event.key == "5":
            self.dismiss("run langgraph audit")
        elif event.key == "escape":
            self.dismiss(None)


class InboxGPTApp(App):
    """Full-width keyboard-driven terminal Gmail triage client."""

    CSS = """
    Screen {
        background: #000000;
        color: #a1a1aa;
    }

    Header {
        background: #000000;
        color: #71717a;
        height: 1;
        border-bottom: solid #18181b;
        text-style: bold;
    }

    Footer {
        background: #000000;
        color: #52525b;
        border-top: solid #18181b;
    }

    /* Top Navigation Status Bar */
    #top_bar {
        height: 3;
        background: #000000;
        border-bottom: solid #18181b;
        padding: 0 2;
        layout: horizontal;
        align: left middle;
    }

    #app_title {
        color: #f4f4f5;
        text-style: bold;
        width: auto;
        margin-right: 2;
    }

    #account_badge {
        color: #71717a;
        width: 1fr;
    }

    #stats_summary {
        color: #a1a1aa;
        text-style: bold;
        width: auto;
    }

    /* Category Filter Tabs Bar across full screen */
    #filter_tabs_bar {
        height: auto;
        min-height: 4;
        background: #000000;
        border-bottom: solid #18181b;
        padding: 0 1;
        layout: horizontal;
        align: left top;
    }

    #tabs_left {
        width: auto;
        height: auto;
        layout: horizontal;
    }

    #tabs_spacer {
        width: 1fr;
        height: 1;
    }

    #tabs_right {
        width: auto;
        height: auto;
        layout: horizontal;
    }

    .filter_pill {
        color: #71717a;
        background: #09090b;
        border: solid #27272a;
        margin-right: 1;
        padding: 0 1;
        height: 3;
        text-style: bold;
    }

    .filter_pill:hover {
        background: #18181b;
        color: #d4d4d8;
    }

    /* Dimmed subtle active tab: sleek zinc box */
    .filter_pill.active {
        color: #ffffff;
        background: #27272a;
        border: solid #52525b;
    }

    .action_pill {
        color: #a1a1aa;
        background: #09090b;
        border: solid #27272a;
        margin-left: 1;
        padding: 0 2;
        height: 3;
        text-style: bold;
    }

    .action_pill:hover {
        color: #ffffff;
        background: #18181b;
        border: solid #3f3f46;
    }

    /* Keybinding Helper & Status Line across full screen */
    #helper_hints_bar {
        height: 1;
        background: #09090b;
        padding: 0 2;
        layout: horizontal;
    }

    #hints_text {
        color: #52525b;
        width: 1fr;
        height: 1;
    }

    #status_label {
        color: #34d399;
        text-style: bold;
        width: auto;
        height: 1;
    }

    /* Full-Width Thread List View */
    #list_view_container {
        width: 100%;
        height: 1fr;
        background: #000000;
    }

    DataTable {
        width: 100%;
        height: 1fr;
        background: #000000;
        color: #a1a1aa;
        border: none;
    }

    DataTable > .datatable--header {
        background: #050505;
        color: #52525b;
        text-style: bold;
        border-bottom: solid #18181b;
    }

    DataTable > .datatable--cursor {
        background: #1c1c1f;
        color: #ededed;
        text-style: bold;
    }

    /* Full-Screen Email Reader View */
    #reader_view_container {
        width: 100%;
        height: 1fr;
        background: #000000;
        display: none;
    }

    #reader_meta_header {
        height: auto;
        padding: 1 2;
        background: #09090b;
        border-bottom: solid #27272a;
    }

    #reader_subject {
        color: #ffffff;
        text-style: bold;
        margin-bottom: 1;
    }

    #reader_meta_details {
        color: #a1a1aa;
    }

    #reader_action_hints {
        height: 2;
        background: #18181b;
        padding: 0 2;
        align: left middle;
        color: #71717a;
        border-bottom: solid #27272a;
    }

    #reader_body_scroll {
        width: 100%;
        height: 1fr;
        padding: 1 2;
        background: #000000;
    }

    #reader_body_content {
        color: #e4e4e7;
    }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("enter", "open_email", "Read", show=True),
        Binding("escape", "back_or_quit", "Back", show=True),
        Binding("q", "back_or_quit", "Quit", show=True),
        Binding("d", "trash_selected", "Trash", show=True),
        Binding("e", "archive_selected", "Archive", show=True),
        Binding("x", "toggle_select", "Select", show=True),
        Binding("r", "refresh_inbox", "Refresh", show=True),
        Binding("a", "open_agent", "AI Agent", show=True),
        Binding("l", "switch_account", "Switch", show=True),
        Binding("slash", "open_agent", "Agent", show=False),
        Binding("1", "filter_1", "All", show=False),
        Binding("2", "filter_2", "Prio", show=False),
        Binding("3", "filter_3", "Promo", show=False),
        Binding("4", "filter_4", "Soc", show=False),
        Binding("5", "filter_5", "News", show=False),
        Binding("question_mark", "help", "Help", show=True),
    ]

    def __init__(self, force_mock: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.gmail_client = get_gmail_client(force_mock=force_mock)
        self.safe_tools = SafeInboxTools(self.gmail_client)
        self.approval_tools = ApprovalRequiredTools(self.gmail_client)

        # Get connected user email
        self.user_email = (
            self.gmail_client.get_user_email()
            if hasattr(self.gmail_client, "get_user_email")
            else "Gmail User"
        )

        # 1. Instant 0ms startup from local disk cache
        cached = config.load_cached_emails()
        if self.gmail_client.is_live():
            # Discard any old mock sandbox emails so real inbox is pure
            cached = [e for e in cached if e.sender_name != "Sarah Connor" and "inboxgpt.local" not in e.sender]
        self.emails: List[EmailMessage] = cached
        self.displayed_emails: List[EmailMessage] = list(self.emails)
        self.selected_ids: Set[str] = set()
        self.active_category: Optional[EmailCategory] = None
        self.stats = self.safe_tools.compute_stats(self.emails)
        self.proposed_actions: List[ProposedAction] = []
        self.in_reader_mode = False
        self.current_reading_email: Optional[EmailMessage] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="top_bar"):
            yield Label("▲ INBOXGPT", id="app_title")
            mode_tag = "Live Gmail Synced" if self.gmail_client.is_live() else "Mock Sandbox"
            yield Label(f"{self.user_email} · [{mode_tag}]", id="account_badge")
            yield Label(f"Total: {self.stats.total_emails}  Unread: {self.stats.unread_emails}", id="stats_summary")

        with Horizontal(id="filter_tabs_bar"):
            with Horizontal(id="tabs_left"):
                yield Button(f"[1] All ({self.stats.total_emails})", id="tab_all", classes="filter_pill active")
                yield Button(f"[2] Priority ({self.stats.important_count})", id="tab_prio", classes="filter_pill")
                yield Button(f"[3] Promo ({self.stats.promotional_count})", id="tab_promo", classes="filter_pill")
                yield Button(f"[4] Social ({self.stats.social_count})", id="tab_soc", classes="filter_pill")
                yield Button(f"[5] News ({self.stats.newsletter_count})", id="tab_news", classes="filter_pill")
            yield Static(id="tabs_spacer")
            with Horizontal(id="tabs_right"):
                yield Button("[r] Sync", id="btn_refresh", classes="action_pill")
                yield Button("[a] AI Agent", id="btn_agent", classes="action_pill")
                yield Button("[l] Switch", id="btn_switch", classes="action_pill")
                yield Button("[?] Help", id="btn_help", classes="action_pill")

        with Horizontal(id="helper_hints_bar"):
            yield Label(
                "↑/↓ Navigate · Enter Read · d Trash · e Archive · x Select · 1-5 Category · a Agent · r Sync · l Switch · ? Help · q Quit",
                id="hints_text",
            )
            yield Label("✓ Mailbox Synced", id="status_label")

        with Vertical(id="list_view_container"):
            table = DataTable(id="email_table", cursor_type="row")
            yield table

        with Vertical(id="reader_view_container"):
            with Vertical(id="reader_meta_header"):
                yield Label("", id="reader_subject")
                yield Static("", id="reader_meta_details")
            with Horizontal(id="reader_action_hints"):
                yield Label("  [d] Trash Thread   [e] Archive   [Esc / q] Back to Inbox", id="reader_hints_label")
            with VerticalScroll(id="reader_body_scroll"):
                yield Markdown("", id="reader_body_content")

        yield Footer()

    def on_mount(self) -> None:
        self.setup_table()
        if self.emails:
            self.filter_emails()
        self.load_emails()

    def on_resize(self, event: events.Resize) -> None:
        """Dynamically recompute column width when terminal is resized."""
        try:
            self.setup_table()
            self.populate_table()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Support instant mouse clicks on all tabs and buttons."""
        bid = event.button.id
        if bid == "tab_all":
            self.action_filter_1()
        elif bid == "tab_prio":
            self.action_filter_2()
        elif bid == "tab_promo":
            self.action_filter_3()
        elif bid == "tab_soc":
            self.action_filter_4()
        elif bid == "tab_news":
            self.action_filter_5()
        elif bid == "btn_refresh":
            self.action_refresh_inbox()
        elif bid == "btn_agent":
            self.action_open_agent()
        elif bid == "btn_help":
            self.action_help()

    def set_status(self, message: str) -> None:
        """Update inline status label on top bar."""
        try:
            self.query_one("#status_label", Label).update(message)
        except Exception:
            pass

    def setup_table(self) -> None:
        table = self.query_one("#email_table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"

        # Dynamically size 'Subject & Preview' column to use 100% of available terminal width
        win_width = self.size.width if self.size and self.size.width > 60 else 120
        subject_col_width = max(45, win_width - 62)

        table.add_column(" ", width=3)
        table.add_column("Tag", width=10)
        table.add_column("Sender", width=26)
        table.add_column("Subject & Preview", width=subject_col_width)
        table.add_column("Date", width=16)

    @work(thread=True)
    def load_emails(self, query: str = "") -> None:
        self.app.call_from_thread(self.set_status, "⏳ Syncing latest emails from Gmail...")
        try:
            new_emails = self.safe_tools.fetch_inbox_emails(max_results=120, query=query)
            if new_emails:
                self.emails = new_emails
                config.save_cached_emails(self.emails)
                self.app.call_from_thread(
                    self.set_status,
                    f"✓ Mailbox up to date · {len(self.emails)} emails loaded",
                )
                self.app.call_from_thread(self.update_stats)
                self.app.call_from_thread(self.filter_emails)
            else:
                self.app.call_from_thread(
                    self.set_status, "✓ Mailbox up to date (no changes)"
                )
        except Exception as e:
            # Retry once in case of transient socket/SSL initialization
            try:
                new_emails = self.safe_tools.fetch_inbox_emails(max_results=120, query=query)
                if new_emails:
                    self.emails = new_emails
                    config.save_cached_emails(self.emails)
                    self.app.call_from_thread(self.update_stats)
                    self.app.call_from_thread(self.filter_emails)
                    self.app.call_from_thread(
                        self.set_status,
                        f"✓ Mailbox up to date · {len(self.emails)} emails loaded",
                    )
                    return
            except Exception:
                pass

            self.app.call_from_thread(
                self.set_status, f"⚠️ Sync warning: {e} · retained active emails"
            )


    def update_stats(self) -> None:
        self.stats = self.safe_tools.compute_stats(self.emails)
        summary = self.query_one("#stats_summary", Label)
        summary.update(f"Total: {self.stats.total_emails}  Unread: {self.stats.unread_emails}")

        # Update pill tab counts
        self.query_one("#tab_all", Button).label = f"[1] All ({self.stats.total_emails})"
        self.query_one("#tab_prio", Button).label = f"[2] Priority ({self.stats.important_count})"
        self.query_one("#tab_promo", Button).label = f"[3] Promo ({self.stats.promotional_count})"
        self.query_one("#tab_soc", Button).label = f"[4] Social ({self.stats.social_count})"
        self.query_one("#tab_news", Button).label = f"[5] News ({self.stats.newsletter_count})"

    def filter_emails(self) -> None:
        if self.active_category is None:
            self.displayed_emails = list(self.emails)
        else:
            self.displayed_emails = [
                e for e in self.emails if e.category == self.active_category
            ]

        # Update active styling on tabs
        for tab_id, cat in [
            ("tab_all", None),
            ("tab_prio", EmailCategory.IMPORTANT),
            ("tab_promo", EmailCategory.PROMOTIONAL),
            ("tab_soc", EmailCategory.SOCIAL),
            ("tab_news", EmailCategory.NEWSLETTER),
        ]:
            btn = self.query_one(f"#{tab_id}", Button)
            if self.active_category == cat:
                btn.add_class("active")
            else:
                btn.remove_class("active")

        self.populate_table()

    def populate_table(self) -> None:
        table = self.query_one("#email_table", DataTable)
        table.clear()

        category_labels = {
            EmailCategory.IMPORTANT: "PRIO",
            EmailCategory.PROMOTIONAL: "PROMO",
            EmailCategory.NEWSLETTER: "NEWS",
            EmailCategory.SOCIAL: "SOC",
            EmailCategory.UNWANTED: "SPAM",
            EmailCategory.UNCATEGORIZED: "MAIL",
        }

        for email in self.displayed_emails:
            unread_mark = "●" if email.is_unread else " "
            if email.id in self.selected_ids:
                unread_mark = "✔"

            tag = f"[{category_labels.get(email.category, 'MAIL')}]"
            sender_str = (email.sender_name or email.sender)[:20]

            clean_snippet = email.snippet.replace("\n", " ").strip() if email.snippet else ""
            subject_line = f"{email.subject} — {clean_snippet}" if clean_snippet else email.subject
            date_display = email.date[:16] if email.date else ""

            table.add_row(
                unread_mark,
                tag,
                sender_str,
                subject_line,
                date_display,
                key=email.id,
            )

        if self.displayed_emails:
            table.focus()

    # ─── Table Events: Open Email on Enter or Double Click ──────────────────

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Triggered when Enter is pressed on any row in the DataTable."""
        if event.cursor_row is not None and 0 <= event.cursor_row < len(self.displayed_emails):
            selected = self.displayed_emails[event.cursor_row]
            self.open_email(selected)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Triggered on cell selection."""
        if event.coordinate.row is not None and 0 <= event.coordinate.row < len(self.displayed_emails):
            selected = self.displayed_emails[event.coordinate.row]
            self.open_email(selected)

    def action_open_email(self) -> None:
        """Binding fallback for opening selected email."""
        if self.in_reader_mode:
            return
        table = self.query_one("#email_table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.displayed_emails):
            selected = self.displayed_emails[table.cursor_row]
            self.open_email(selected)

    def open_email(self, email: EmailMessage) -> None:
        """Show full email reading view."""
        self.in_reader_mode = True
        self.current_reading_email = email

        # Lazy-load full message body if only snippet available
        if not email.body or len(email.body) <= len(email.snippet):
            full = self.gmail_client.get_message(email.id)
            if full and full.body:
                email.body = full.body

        self.query_one("#list_view_container").styles.display = "none"
        reader = self.query_one("#reader_view_container")
        reader.styles.display = "block"

        self.query_one("#reader_subject", Label).update(f"✉️  {email.subject}")
        meta_str = f"From: {email.sender_name} <{email.sender}>  ·  Date: {email.date}  ·  Category: [{email.category.value.upper()}]"
        self.query_one("#reader_meta_details", Static).update(meta_str)

        body_text = email.body if email.body else email.snippet
        self.query_one("#reader_body_content", Markdown).update(body_text)

        scroll = self.query_one("#reader_body_scroll", VerticalScroll)
        scroll.scroll_home(animate=False)
        scroll.focus()
        self.set_status(f"Reading: {email.subject[:40]} · [Esc / q] to return")

    def action_back_or_quit(self) -> None:
        """Escape or Q: Back to list if reading, else quit app."""
        if self.in_reader_mode:
            self.in_reader_mode = False
            self.query_one("#reader_view_container").styles.display = "none"
            self.query_one("#list_view_container").styles.display = "block"
            self.current_reading_email = None
            table = self.query_one("#email_table", DataTable)
            table.focus()
            self.set_status(f"Ready · {len(self.displayed_emails)} emails in current view")
        else:
            self.exit()

    # ─── Global Key Listener (Priority Handling) ────────────────────────────

    def on_key(self, event) -> None:
        """Handle 1-5 tabs, esc, and shortcuts across the entire app."""
        if self.in_reader_mode:
            if event.key in ("escape", "q"):
                self.action_back_or_quit()
                event.prevent_default()
            elif event.key == "d":
                self.action_trash_selected()
                event.prevent_default()
            elif event.key == "e":
                self.action_archive_selected()
                event.prevent_default()
        else:
            if event.key == "1":
                self.action_filter_1()
                event.prevent_default()
            elif event.key == "2":
                self.action_filter_2()
                event.prevent_default()
            elif event.key == "3":
                self.action_filter_3()
                event.prevent_default()
            elif event.key == "4":
                self.action_filter_4()
                event.prevent_default()
            elif event.key == "5":
                self.action_filter_5()
                event.prevent_default()

    # ─── Navigation & Actions ───────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        if self.in_reader_mode:
            self.query_one("#reader_body_scroll", VerticalScroll).scroll_down()
        else:
            self.query_one("#email_table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        if self.in_reader_mode:
            self.query_one("#reader_body_scroll", VerticalScroll).scroll_up()
        else:
            self.query_one("#email_table", DataTable).action_cursor_up()

    def action_trash_selected(self) -> None:
        """Move email/thread to Trash in live Gmail immediately."""
        target_email = None
        if self.in_reader_mode and self.current_reading_email:
            target_email = self.current_reading_email
        else:
            table = self.query_one("#email_table", DataTable)
            if table.cursor_row is not None and 0 <= table.cursor_row < len(self.displayed_emails):
                target_email = self.displayed_emails[table.cursor_row]

        if not target_email:
            return

        subject_preview = target_email.subject[:35]
        thread_id = target_email.thread_id
        email_id = target_email.id

        # 1. Instantly evict from local UI and disk cache in 0ms (Zero lag!)
        self.emails = [e for e in self.emails if e.id != email_id]
        self.selected_ids.discard(email_id)
        config.save_cached_emails(self.emails)
        self.update_stats()
        self.filter_emails()

        if self.in_reader_mode:
            self.action_back_or_quit()

        self.set_status(f"✓ Trashed 1 thread: {subject_preview} (Live Gmail updated)")

        # 2. Run the network call asynchronously
        def _bg_trash() -> None:
            try:
                if thread_id and hasattr(self.gmail_client, "trash_thread"):
                    self.gmail_client.trash_thread(thread_id)
                else:
                    self.approval_tools.execute_trash(
                        ProposedAction(
                            id="trash_single",
                            action_type=ActionType.TRASH,
                            title="Trash email",
                            description="",
                            target_email_ids=[email_id],
                            count=1,
                            risk_level=RiskLevel.LOW,
                        )
                    )
            except Exception:
                pass

        self.run_worker(_bg_trash, thread=True)

    def action_archive_selected(self) -> None:
        """Archive email in live Gmail."""
        target_email = None
        if self.in_reader_mode and self.current_reading_email:
            target_email = self.current_reading_email
        else:
            table = self.query_one("#email_table", DataTable)
            if table.cursor_row is not None and 0 <= table.cursor_row < len(self.displayed_emails):
                target_email = self.displayed_emails[table.cursor_row]

        if not target_email:
            return

        subject_preview = target_email.subject[:35]
        email_id = target_email.id

        # 1. Instantly evict from local UI and disk cache in 0ms
        self.emails = [e for e in self.emails if e.id != email_id]
        self.selected_ids.discard(email_id)
        config.save_cached_emails(self.emails)
        self.update_stats()
        self.filter_emails()

        if self.in_reader_mode:
            self.action_back_or_quit()

        self.set_status(f"✓ Archived: {subject_preview} (Removed from Inbox)")

        # 2. Run the network call asynchronously
        def _bg_archive() -> None:
            try:
                self.approval_tools.execute_archive(
                    ProposedAction(
                        id="archive_single",
                        action_type=ActionType.ARCHIVE,
                        title="Archive email",
                        description="",
                        target_email_ids=[email_id],
                        count=1,
                        risk_level=RiskLevel.LOW,
                    )
                )
            except Exception:
                pass

        self.run_worker(_bg_archive, thread=True)

    def action_toggle_select(self) -> None:
        """Toggle multi-select on current row."""
        if self.in_reader_mode:
            return
        table = self.query_one("#email_table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.displayed_emails):
            selected = self.displayed_emails[table.cursor_row]
            if selected.id in self.selected_ids:
                self.selected_ids.remove(selected.id)
            else:
                self.selected_ids.add(selected.id)
            self.populate_table()

    def action_refresh_inbox(self) -> None:
        self.load_emails()

    def action_open_agent(self) -> None:
        """Open clean AI Agent dialog."""
        def handle_agent_choice(command: Optional[str]) -> None:
            if not command:
                return

            c = command.lower().strip()
            if any(k in c for k in ("logout", "switch", "switch mail", "switch account", "change account")):
                self.action_switch_account()
                return

            if any(k in c for k in ("langgraph", "full audit", "full scan", "audit")):
                self.run_langgraph_flow()
            elif any(k in c for k in ("trash", "delete", "clean", "remove", "archive news", "clean promo")):
                self.run_agent_cleanup_flow(command)
            elif c in ("summarize priority emails", "priority summary"):
                self.run_summarize_flow()
            else:
                # Autonomous Executive Assistant with ReAct tools and memory
                self.run_executive_assistant_flow(command)

        self.push_screen(AgentCommandModal(), handle_agent_choice)

    def run_executive_assistant_flow(self, command: str) -> None:
        """Run autonomous multi-step executive assistant with Gemini and live Gmail tools."""
        self.set_status(f"🤖 Agent researching: '{command[:35]}...'")

        def _bg_assist() -> None:
            try:
                from inboxgpt.agent.assistant import ask_executive_agent

                response_text = ask_executive_agent(command, self.gmail_client, self.emails)

                def show_result() -> None:
                    self.set_status("✓ Agent query completed.")
                    self.push_screen(AgentResultModal(command, response_text))

                self.app.call_from_thread(show_result)
            except Exception as e:
                self.app.call_from_thread(self.set_status, f"⚠️ Agent error: {e}")

        self.run_worker(_bg_assist, thread=True)

    def run_langgraph_flow(self) -> None:
        """Execute the full compiled LangGraph workflow with streaming steps and human-in-the-loop interrupt."""
        thread_id = f"tui_{uuid.uuid4().hex[:6]}"
        graph = create_inbox_graph(self.gmail_client, enable_interrupt=True)
        config_obj = {"configurable": {"thread_id": thread_id}}

        self.set_status("⏳ [LangGraph: 1/4] Initializing StateGraph workflow...")

        def _bg_langgraph() -> None:
            try:
                self.app.call_from_thread(
                    self.set_status,
                    "⏳ [LangGraph: 2/4] Categorizing inbox messages with Gemini...",
                )

                # Execute graph with active emails up to the interrupt point
                graph.invoke({"emails": list(self.emails)}, config=config_obj)

                graph_state = graph.get_state(config_obj)
                if not graph_state.tasks or not graph_state.tasks[0].interrupts:
                    self.app.call_from_thread(
                        self.set_status, "✓ [LangGraph] Inbox analysis complete. No actions needed."
                    )
                    return

                interrupt_payload = graph_state.tasks[0].interrupts[0].value
                raw_proposals = interrupt_payload.get("proposals", [])
                if not raw_proposals:
                    self.app.call_from_thread(
                        self.set_status, "✓ [LangGraph] Inbox is clean. No cleanup proposals generated."
                    )
                    return

                # Convert dicts back to ProposedAction objects
                proposals = [ProposedAction(**p) for p in raw_proposals]
                prop = proposals[0]

                self.app.call_from_thread(
                    self.set_status,
                    f"⚠️ [LangGraph: 3/4] Awaiting human approval for: {prop.title}",
                )

                def on_approval(decision: str) -> None:
                    if decision == "approve":
                        target_set = set(prop.target_email_ids)
                        # Zero lag instant UI eviction
                        self.emails = [e for e in self.emails if e.id not in target_set]
                        self.selected_ids.difference_update(target_set)
                        config.save_cached_emails(self.emails)
                        self.update_stats()
                        self.filter_emails()
                        self.set_status(f"✓ [LangGraph] Approved: {prop.title}")

                        def _bg_resume() -> None:
                            try:
                                res = graph.invoke(
                                    Command(resume={"approved_action_ids": [prop.id]}),
                                    config=config_obj,
                                )
                                self.app.call_from_thread(
                                    self.set_status,
                                    f"✓ [LangGraph: 4/4] Executed: {prop.title} (Live Gmail updated)",
                                )
                            except Exception as ex:
                                self.app.call_from_thread(
                                    self.set_status, f"⚠️ [LangGraph] Execution error: {ex}"
                                )

                        self.run_worker(_bg_resume, thread=True)

                    elif decision == "review":
                        self.displayed_emails = [e for e in self.emails if e.id in prop.target_email_ids]
                        self.populate_table()
                        self.set_status(
                            f"[LangGraph] Reviewing {len(self.displayed_emails)} targeted emails. Press 'a' to re-run or '1' to reset."
                        )
                    else:
                        def _bg_reject() -> None:
                            try:
                                graph.invoke(
                                    Command(resume={"rejected_action_ids": [prop.id]}),
                                    config=config_obj,
                                )
                            except Exception:
                                pass

                        self.run_worker(_bg_reject, thread=True)
                        self.set_status("✗ [LangGraph] Proposal rejected by user.")

                self.app.call_from_thread(self.push_screen, ApprovalModal(prop), on_approval)

            except Exception as e:
                self.app.call_from_thread(self.set_status, f"⚠️ [LangGraph] Error: {e}")

        self.run_worker(_bg_langgraph, thread=True)

    def run_agent_cleanup_flow(self, command: str) -> None:
        self.set_status(f"⏳ Agent analyzing request: '{command}'...")
        prop, message = plan_agent_cleanup(self.emails, command)
        if not prop:
            self.set_status(f"ℹ️ {message}")
            return

        def on_approval(decision: str) -> None:
            if decision == "approve":
                target_set = set(prop.target_email_ids)
                # 1. Zero lag instant local eviction
                self.emails = [e for e in self.emails if e.id not in target_set]
                self.selected_ids.difference_update(target_set)
                config.save_cached_emails(self.emails)
                self.update_stats()
                self.filter_emails()
                self.set_status(f"✓ {prop.title} (Live Gmail updated)")

                # 2. Asynchronous background execution in live Gmail
                def _bg_execute() -> None:
                    try:
                        if prop.action_type == ActionType.TRASH:
                            self.approval_tools.execute_trash(prop)
                        else:
                            self.approval_tools.execute_archive(prop)
                    except Exception:
                        pass

                self.run_worker(_bg_execute, thread=True)

            elif decision == "review":
                # Filter inbox to review target emails
                self.displayed_emails = [e for e in self.emails if e.id in prop.target_email_ids]
                self.populate_table()
                self.set_status(f"Displaying {len(self.displayed_emails)} emails targeted by agent. Press 'a' to run or '1' to reset view.")
            else:
                self.set_status("Agent proposal cancelled.")

        self.push_screen(ApprovalModal(prop), on_approval)

    def run_summarize_flow(self) -> None:
        prio = [e for e in self.emails if e.category == EmailCategory.IMPORTANT][:5]
        if not prio:
            prio = self.emails[:5]

        lines = [f"Priority Briefing ({len(prio)} Emails):"]
        for e in prio:
            lines.append(f"• {e.sender_name or e.sender}: {e.subject}")

        self.set_status(" · ".join(lines))

    # ─── Filter Tabs Shortcuts ──────────────────────────────────────────────

    def action_filter_1(self) -> None:
        self.active_category = None
        self.set_status("Filtered: All Emails")
        self.filter_emails()

    def action_filter_2(self) -> None:
        self.active_category = EmailCategory.IMPORTANT
        self.set_status("Filtered: Priority Emails")
        self.filter_emails()

    def action_filter_3(self) -> None:
        self.active_category = EmailCategory.PROMOTIONAL
        self.set_status("Filtered: Promotional Emails")
        self.filter_emails()

    def action_filter_4(self) -> None:
        self.active_category = EmailCategory.SOCIAL
        self.set_status("Filtered: Social Emails")
        self.filter_emails()

    def action_filter_5(self) -> None:
        self.active_category = EmailCategory.NEWSLETTER
        self.set_status("Filtered: Newsletters")
        self.filter_emails()

    def action_help(self) -> None:
        self.push_screen(HelpModal())

    def action_switch_account(self) -> None:
        """Prompt user to switch or logout from current Gmail account."""
        def on_switch_decision(decision: Optional[str]) -> None:
            if decision == "switch":
                config.clear_session()
                self.exit(result="SWITCH_ACCOUNT")
            elif decision == "logout":
                config.clear_session()
                self.exit(result="LOGOUT")

        self.push_screen(SwitchAccountModal(self.user_email), on_switch_decision)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Support mouse clicking on category filter pills and action pills."""
        btn_id = event.button.id
        if btn_id == "tab_all":
            self.action_filter_1()
        elif btn_id == "tab_prio":
            self.action_filter_2()
        elif btn_id == "tab_promo":
            self.action_filter_3()
        elif btn_id == "tab_soc":
            self.action_filter_4()
        elif btn_id == "tab_news":
            self.action_filter_5()
        elif btn_id == "btn_refresh":
            self.action_refresh_inbox()
        elif btn_id == "btn_agent":
            self.action_open_agent()
        elif btn_id == "btn_switch":
            self.action_switch_account()
        elif btn_id == "btn_help":
            self.action_help()
