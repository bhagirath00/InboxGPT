# InboxGPT 📬⚡

A terminal-first AI Gmail executive agent powered by **LangGraph** and **Google Gemini** with human-in-the-loop safety approvals.

[![npm version](https://img.shields.io/npm/v/inboxgpt.svg)](https://www.npmjs.com/package/inboxgpt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Features

- **⚡ Terminal-First TUI**: Lightning-fast keyboard-driven interface inspired by Vim, lazygit, and k9s.
- **🤖 LangGraph Executive Agent**: Multi-step ReAct agent capable of mailbox searching, inspecting email bodies, drafting email replies, and maintaining long-term memory.
- **🛡️ Inviolable Safety Guardrails**: Starred, Priority, OTPs, verification codes, and financial receipts can **never** be trashed or lost.
- **📦 Zero Permanent Deletions**: Never calls permanent deletion endpoints; archives preserve all items in "All Mail".
- **🏷️ Smart Category Filters**: Instant switching between `[1] All`, `[2] Priority`, `[3] Promo`, `[4] Social`, and `[5] News`.
- **🔐 Google OAuth 2.0**: Official Gmail API authentication with built-in multi-account switching (`inboxgpt switch`).

---

## 🚀 Quickstart via NPM

Run instantly without cloning:

```bash
# Run directly via npx
npx inboxgpt

# Or install globally
npm install -g inboxgpt

# Then run anywhere:
inboxgpt
```

---

## 🐍 Installation via Python / Pip

```bash
# Clone the repository
git clone https://github.com/InboxGPT/inboxgpt.git
cd inboxgpt

# Install dependencies in development mode
pip install -e .

# Launch
inboxgpt
```

---

## ⌨️ TUI Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `↑` / `↓` | Navigate emails |
| `Enter` | Read full email (Reader Mode) |
| `1` - `5` | Switch category tabs (All, Priority, Promo, Social, News) |
| `e` | **Archive** email (Removes from Inbox, preserves in All Mail) |
| `d` | Move email to **Trash** |
| `/` | Live Search query |
| `r` | Refresh inbox from Gmail |
| `Space` / `a` | Open **AI Copilot** (Natural language instructions) |
| `Esc` / `q` | Close reader mode or exit |

---

## 🛠️ CLI Commands

```bash
# Launch interactive TUI
inboxgpt

# Switch between multiple Gmail accounts
inboxgpt switch

# Logout and revoke session credentials
inboxgpt logout

# Background Daemon: Monitor inbox & prepare Executive Briefings periodically
inboxgpt daemon --interval 30

# One-shot Morning Briefing (prints to terminal and saves to disk)
inboxgpt brief

# Force fresh live scan for Morning Briefing
inboxgpt brief --fresh

# Run local FastAPI backend (optional)
inboxgpt serve
```

---

## 📄 License
MIT © InboxGPT Team
