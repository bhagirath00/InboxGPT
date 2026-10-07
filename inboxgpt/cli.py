import sys
from typing import Optional
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from inboxgpt.auth.oauth import get_auth_status, run_oauth_flow
from inboxgpt.config import config
from inboxgpt.gmail.client import get_gmail_client
from inboxgpt.gmail.models import ActionStatus, ActionType, EmailCategory
from inboxgpt.agent.graph import create_inbox_graph
from inboxgpt.agent.tools import ApprovalRequiredTools, SafeInboxTools

app = typer.Typer(
    name="inboxgpt",
    help="InboxGPT: Terminal-first AI Gmail management agent with human-in-the-loop safety.",
    invoke_without_command=True,
)
console = Console(legacy_windows=False)



@app.callback()
def default_entry(
    ctx: typer.Context,
    mock: bool = typer.Option(
        False, "--mock", help="Force use of simulated mock inbox rather than live Gmail."
    ),
):
    """Launch the interactive TUI if no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        from inboxgpt.tui.app import InboxGPTApp

        tui_app = InboxGPTApp(force_mock=mock)
        result = tui_app.run()
        if result == "SWITCH_ACCOUNT":
            switch_command()
        elif result == "LOGOUT":
            logout_command()


@app.command("auth")
def auth_command(
    set_gemini_key: Optional[str] = typer.Option(
        None, "--gemini-key", help="Provide and save your Gemini API key."
    ),
):
    """Authenticate with Google OAuth and configure Gemini API key."""
    console.print(Panel.fit("[bold cyan]InboxGPT Authentication & Setup[/bold cyan]"))

    if set_gemini_key:
        config.set_gemini_api_key(set_gemini_key)
        console.print("[green]✓[/green] Gemini API key stored successfully in local config.")

    current_status = get_auth_status()
    console.print(f"• Config directory: [bold]{config.config_dir}[/bold]")
    console.print(
        f"• Gemini API Key: {'[green]Configured[/green]' if current_status['gemini_api_key_configured'] else '[yellow]Not configured (using heuristic fallback)[/yellow]'}"
    )
    console.print(
        f"• Google Client Secrets: {'[green]Found[/green]' if current_status['google_credentials_file_found'] else f'[red]Missing at {config.credentials_file}[/red]'}"
    )
    console.print(
        f"• Google OAuth Token: {'[green]Active & Valid[/green]' if current_status['google_token_valid'] else '[yellow]Not authorized yet[/yellow]'}"
    )

    # Prompt for Gemini key if missing
    if not current_status["gemini_api_key_configured"] and not set_gemini_key:
        if Confirm.ask("Would you like to input a Gemini API key now?", default=True):
            key = Prompt.ask("Enter Gemini API key", password=True)
            if key.strip():
                config.set_gemini_api_key(key)
                console.print("[green]✓[/green] Gemini API key saved.")

    # Run Google OAuth if credentials file exists
    if current_status["google_credentials_file_found"] and not current_status["google_token_valid"]:
        if Confirm.ask("Start Google OAuth consent login flow in browser now?", default=True):
            try:
                run_oauth_flow()
                console.print("[green]✓ Google OAuth login succeeded! Token saved.[/green]")
                if Confirm.ask("Launch InboxGPT TUI now?", default=True):
                    from inboxgpt.tui.app import InboxGPTApp
                    tui_app = InboxGPTApp()
                    tui_app.run()
            except Exception as e:
                console.print(f"[red]OAuth flow failed: {e}[/red]")
    elif not current_status["google_credentials_file_found"]:
        console.print(
            "\n[dim]To connect your real Gmail account, download your OAuth 2.0 Client credentials JSON "
            f"from Google Cloud Console and save it as: [bold]{config.credentials_file}[/bold]\n"
            "Without live credentials, InboxGPT runs in sandbox mock mode automatically.[/dim]"
        )


@app.command("logout")
def logout_command():
    """Logout from current Gmail account and clear local session cache."""
    config.clear_session()
    console.print(
        Panel.fit(
            "[bold green]✓ Successfully logged out of InboxGPT.[/bold green]\n\n"
            "• Active Google OAuth token removed.\n"
            "• Local email disk cache cleared.\n"
            "• Gemini API key and Client credentials preserved.\n\n"
            "[dim]To connect a new account, run [bold cyan]inboxgpt switch[/bold cyan] or [bold cyan]inboxgpt[/bold cyan].[/dim]",
            title="InboxGPT Logout",
        )
    )


@app.command("switch")
def switch_command():
    """Switch active Gmail account by clearing session and opening Google OAuth account picker."""
    console.print(Panel.fit("[bold cyan]InboxGPT · Switch Gmail Account[/bold cyan]"))
    config.clear_session()
    console.print("[dim]Existing session & local cache cleared.[/dim]")
    console.print("[yellow]Opening browser to select a Google account...[/yellow]\n")

    try:
        run_oauth_flow(select_account=True)
        import inboxgpt.gmail.client as gc
        gc._shared_mock_client = None

        client = get_gmail_client()
        email_addr = (
            client.get_user_email()
            if hasattr(client, "get_user_email")
            else "Gmail User"
        )
        config.update_settings({"last_authenticated_email": email_addr})
        console.print(f"[bold green]✓ Successfully connected to: {email_addr}[/bold green]\n")

        if Confirm.ask("Launch InboxGPT now with this account?", default=True):
            from inboxgpt.tui.app import InboxGPTApp

            tui_app = InboxGPTApp()
            result = tui_app.run()
            if result == "SWITCH_ACCOUNT":
                switch_command()
            elif result == "LOGOUT":
                logout_command()
    except Exception as e:
        console.print(f"[bold red]Account switch failed: {e}[/bold red]")


@app.command("login")
def login_command():
    """Sign in to Gmail with Google OAuth consent."""
    if config.has_google_token():
        status = get_auth_status()
        current_email = status.get("email") or "Gmail User"
        console.print(f"[yellow]Active session already detected for: [bold]{current_email}[/bold][/yellow]")
        if Confirm.ask("Do you want to switch or sign into another account?", default=False):
            switch_command()
            return
        else:
            console.print("Run [bold green]inboxgpt[/bold green] to open your inbox.")
            return

    try:
        run_oauth_flow(select_account=True)
        import inboxgpt.gmail.client as gc
        gc._shared_mock_client = None

        client = get_gmail_client()
        email_addr = (
            client.get_user_email()
            if hasattr(client, "get_user_email")
            else "Gmail User"
        )
        config.update_settings({"last_authenticated_email": email_addr})
        console.print(f"[bold green]✓ Successfully connected to: {email_addr}[/bold green]\n")

        if Confirm.ask("Launch InboxGPT now?", default=True):
            from inboxgpt.tui.app import InboxGPTApp

            tui_app = InboxGPTApp()
            result = tui_app.run()
            if result == "SWITCH_ACCOUNT":
                switch_command()
            elif result == "LOGOUT":
                logout_command()
    except Exception as e:
        console.print(f"[bold red]Login failed: {e}[/bold red]")


@app.command("analyze")
def analyze_command(
    mock: bool = typer.Option(False, "--mock", help="Force mock inbox mode."),
    max_emails: int = typer.Option(50, "--max", help="Max emails to analyze."),
):
    """Analyze inbox emails, categorize them, and report statistics."""
    client = get_gmail_client(force_mock=mock)
    console.print(
        f"[bold cyan]Analyzing inbox using {'Mock Sandbox' if not client.is_live() else 'Live Gmail'}...[/bold cyan]"
    )

    graph = create_inbox_graph(client, enable_interrupt=False)
    with console.status("[bold green]Agent categorizing emails and assessing priority..."):
        result = graph.invoke({})

    stats = result.get("stats")
    proposals = result.get("proposed_actions", [])

    table = Table(title="📬 InboxGPT Analysis Report")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Description", style="dim")

    table.add_row("Total Analyzed", str(stats.total_emails), "Total messages scanned")
    table.add_row("⭐ Important", str(stats.important_count), "Direct work, invoices, critical notices")
    table.add_row("📰 Newsletters", str(stats.newsletter_count), "Curated tech and business publications")
    table.add_row("👥 Social", str(stats.social_count), "GitHub, LinkedIn, Twitter notifications")
    table.add_row("🏷️ Promotional", str(stats.promotional_count), "Retail discounts and marketing coupons")
    table.add_row("🚫 Unwanted", str(stats.unwanted_count), "Spam, cold outbound sales pitches")
    console.print(table)

    if proposals:
        console.print(f"\n[bold yellow]Agent generated {len(proposals)} cleanup proposals:[/bold yellow]")
        for i, p in enumerate(proposals, 1):
            console.print(f"  {i}. [bold]{p.title}[/bold] (Risk: {p.risk_level.value.upper()})")
            console.print(f"     [dim]{p.description}[/dim]")
        console.print("\nRun [bold green]inboxgpt cleanup[/bold green] to review and execute actions.")


@app.command("cleanup")
def cleanup_command(
    mock: bool = typer.Option(False, "--mock", help="Force mock sandbox mode."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without executing changes."),
):
    """Generate cleanup proposals with Human-in-the-Loop review and approval."""
    client = get_gmail_client(force_mock=mock)
    console.print("[bold cyan]Scanning inbox for cleanup candidates...[/bold cyan]")

    graph = create_inbox_graph(client, enable_interrupt=False, dry_run=dry_run)
    result = graph.invoke({})

    proposals = result.get("proposed_actions", [])
    if not proposals:
        console.print("[green]✨ Your inbox is already spotless! No cleanup actions needed.[/green]")
        return

    approval_tools = ApprovalRequiredTools(client)

    console.print(f"\n[bold yellow]Found {len(proposals)} cleanup actions awaiting your approval:[/bold yellow]\n")

    for idx, p in enumerate(proposals, 1):
        console.print(Panel(
            f"[bold]{p.title}[/bold]\n"
            f"[dim]{p.description}[/dim]\n\n"
            f"Target Emails: [bold]{p.count}[/bold] | Risk: [bold red]{p.risk_level.value.upper()}[/bold red]\n"
            f"Reason: [italic]{p.reason}[/italic]",
            title=f"Proposal {idx} of {len(proposals)}"
        ))

        decision = Prompt.ask(
            "Action",
            choices=["approve", "reject", "skip"],
            default="skip"
        )

        if decision == "approve":
            console.print(f"[yellow]Executing approved action: {p.title}...[/yellow]")
            if p.action_type == ActionType.TRASH:
                res = approval_tools.execute_trash(p, dry_run=dry_run)
            elif p.action_type == ActionType.ARCHIVE:
                res = approval_tools.execute_archive(p, dry_run=dry_run)
            elif p.action_type == ActionType.LABEL:
                res = approval_tools.execute_label(p, p.label_to_apply or "INBOXGPT_PRIORITY", dry_run=dry_run)
            else:
                res = None

            if res and res.success:
                console.print(f"[bold green]✓ {res.message}[/bold green]\n")
            else:
                console.print(f"[bold red]✗ Failed to execute: {res.message if res else 'Unknown error'}[/bold red]\n")
        elif decision == "reject":
            console.print(f"[dim]Rejected {p.title}. No changes made.[/dim]\n")
        else:
            console.print(f"[dim]Skipped {p.title}.[/dim]\n")


@app.command("search")
def search_command(
    query: str = typer.Argument(..., help="Search query (e.g. 'invoice', 'dan', 'meeting')"),
    mock: bool = typer.Option(False, "--mock", help="Force mock inbox mode."),
    max_results: int = typer.Option(20, "--max", help="Max results to display."),
):
    """Search emails using Gmail search syntax."""
    client = get_gmail_client(force_mock=mock)
    safe_tools = SafeInboxTools(client)
    emails = safe_tools.fetch_inbox_emails(max_results=max_results, query=query)

    if not emails:
        console.print(f"[yellow]No emails found matching '{query}'.[/yellow]")
        return

    table = Table(title=f"🔍 Search Results for '{query}' ({len(emails)} matches)")
    table.add_column("Category", style="cyan")
    table.add_column("From", style="green")
    table.add_column("Subject", style="white")
    table.add_column("Date", style="dim")

    for e in emails:
        table.add_row(
            e.category.value.upper(),
            e.sender_name or e.sender,
            e.subject,
            e.date[:16] if e.date else "",
        )
    console.print(table)


@app.command("serve")
def serve_command(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind."),
    port: int = typer.Option(8000, "--port", help="Port number."),
):
    """Start the FastAPI backend server for remote or hosted usage."""
    import uvicorn
    from inboxgpt.api.app import create_app

    console.print(f"[bold cyan]Starting InboxGPT API server on http://{host}:{port}...[/bold cyan]")
    uvicorn.run("inboxgpt.api.app:app", host=host, port=port, reload=False)


@app.command("daemon")
def daemon_command(
    interval: int = typer.Option(30, "--interval", "-i", help="Interval in minutes between checks."),
    once: bool = typer.Option(False, "--once", help="Run a single check and print executive briefing, then exit."),
    mock: bool = typer.Option(False, "--mock", help="Force mock inbox mode."),
    auto_archive_clutter: bool = typer.Option(
        False, "--auto-archive-clutter", help="Safely auto-archive non-protected marketing/newsletter clutter."
    ),
):
    """Run background inbox monitor and Executive Morning Briefing engine."""
    from rich.markdown import Markdown
    from inboxgpt.agent.daemon import DaemonEngine

    engine = DaemonEngine(force_mock=mock)
    if once:
        console.print("[cyan]Running one-shot Executive Briefing analysis...[/cyan]")
        briefing, count = engine.run_cycle(auto_archive_clutter=auto_archive_clutter)
        console.print(Panel(Markdown(briefing), title="🌅 Executive Briefing", border_style="cyan"))
        console.print(f"[green]✓ Analysis complete across {count} emails.[/green]")
        console.print(f"[dim]Saved to: {engine.latest_briefing_file}[/dim]")
    else:
        try:
            engine.start_loop(interval_minutes=interval, auto_archive_clutter=auto_archive_clutter)
        except KeyboardInterrupt:
            console.print("\n[yellow]InboxGPT Daemon stopped by user.[/yellow]")


@app.command("brief")
def brief_command(
    mock: bool = typer.Option(False, "--mock", help="Force mock inbox mode."),
    fresh: bool = typer.Option(False, "--fresh", help="Force fresh email scan rather than cached briefing."),
):
    """View the latest Executive Morning Briefing (or generate a fresh one)."""
    from rich.markdown import Markdown
    from inboxgpt.agent.daemon import DaemonEngine

    engine = DaemonEngine(force_mock=mock)
    if not fresh and engine.latest_briefing_file.exists():
        with open(engine.latest_briefing_file, "r", encoding="utf-8") as f:
            content = f.read()
        console.print(Panel(Markdown(content), title="🌅 Latest Executive Briefing", border_style="cyan"))
        console.print(f"[dim]File: {engine.latest_briefing_file} (use --fresh to re-scan)[/dim]")
    else:
        console.print("[cyan]Generating fresh Executive Briefing...[/cyan]")
        briefing, count = engine.run_cycle()
        console.print(Panel(Markdown(briefing), title="🌅 Executive Briefing", border_style="cyan"))
        console.print(f"[green]✓ Briefing updated across {count} emails.[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
