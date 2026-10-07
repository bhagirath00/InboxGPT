<p align="center">
  <img src="assets/icon.svg" alt="inboxgpt icon" width="32" height="32" style="vertical-align: middle; margin-right: 8px;" />
  <strong style="font-size: 28px;">inboxgpt</strong>
</p>

<p align="center">
  <a href="https://github.com/bhagirath00/InboxGPT"><picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/bhagirath00/InboxGPT/license.svg?variant=outline&amp;font=geist" /><img alt="license" src="https://shieldcn.dev/github/bhagirath00/InboxGPT/license.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
  <a href="https://www.npmjs.com/package/inboxgpt"><picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/npm/inboxgpt.svg?variant=outline&amp;font=geist" /><img alt="version" src="https://shieldcn.dev/npm/inboxgpt.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
  <a href="https://github.com/bhagirath00/InboxGPT"><picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/github/bhagirath00/InboxGPT/stars.svg?variant=outline&amp;font=geist" /><img alt="stars" src="https://shieldcn.dev/github/bhagirath00/InboxGPT/stars.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
</p>

Terminal-first AI Gmail executive assistant powered by LangGraph, Google Gemini, and Textual TUI with human-in-the-loop safety.

* Lightning-fast keyboard navigation inspired by lazygit and Vim.
* Autonomous LangGraph ReAct agent with email search, context reading, draft generation, and long-term memory.
* Inviolable safety guardrails: Starred, Priority, OTPs, 2FA codes, and financial receipts can never be trashed.
* Zero permanent deletions: Archive cleanly removes the Inbox label while preserving everything in "All Mail".
* Background daemon for automated executive morning briefings and action item digests.
* Multi-account management with seamless switching and token auto-refresh.

→ NPM: https://www.npmjs.com/package/inboxgpt

---

## Quickstart

Run directly without cloning:

```bash
npx inboxgpt
```

Or install globally:

```bash
npm install -g inboxgpt
inboxgpt
```

---

## Architecture

<p align="center">
  <img src="assets/architecture.svg" alt="InboxGPT Architecture" width="100%" />
</p>

### Integrated Agent Tools
* `search_mailbox`: Runs search queries across your inbox (`is:unread`, `from:someone`, date filters).
* `read_email_details`: Retrieves complete email bodies and thread context.
* `create_email_draft`: Composes replies as drafts in Gmail without sending without approval.
* `save_agent_memory`: Retains persistent user instructions across sessions in `~/.inboxgpt/agent_memory.json`.

---

## Keyboard Controls

| Key | Action | Description |
| :---: | :--- | :--- |
| `↑` / `↓` | **Navigate** | Scroll through emails |
| `Enter` | **Reader** | Open full email reader view |
| `1` – `5` | **Filter** | Switch category tabs: All, Priority, Promo, Social, News |
| `e` | **Archive** | Archive email (safe remove from Inbox, kept in All Mail) |
| `d` | **Trash** | Move email to Bin/Trash |
| `/` | **Search** | Filter emails by query |
| `r` | **Refresh** | Sync latest emails from Gmail API |
| `Space` / `a` | **AI Copilot** | Trigger LangGraph agent prompt |
| `Esc` / `q` | **Back / Quit** | Return to list view or exit application |

---

## CLI Commands

```bash
# Launch interactive terminal TUI
inboxgpt

# Switch between multiple Gmail accounts
inboxgpt switch

# Logout and clear local session tokens
inboxgpt logout

# Background Daemon: Monitor inbox & prepare briefings periodically
inboxgpt daemon --interval 30

# One-shot Morning Briefing (prints to terminal and saves to disk)
inboxgpt brief

# Force fresh live scan for Morning Briefing
inboxgpt brief --fresh

# Search emails from CLI
inboxgpt search "invoice" --max 10

# Run local FastAPI backend (optional)
inboxgpt serve --port 8000
```

---

## License

Distributed under the MIT License. See [LICENSE](https://github.com/bhagirath00/InboxGPT/blob/main/LICENSE) for details.
