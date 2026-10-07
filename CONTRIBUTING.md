# Contributing to InboxGPT

Thank you for your interest in contributing to **InboxGPT**! We welcome bug reports, documentation updates, and feature pull requests.

---

## Local Development Setup

### 1. Fork and Clone
```bash
git clone https://github.com/bhagirath00/Inboxgpt.git
cd Inboxgpt
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
pip install pytest
```

### 3. Run the Test Suite
Ensure that all unit tests pass before making changes:
```bash
pytest -v
```

---

## Architecture & Codebase Map

| Directory | Responsibility |
| :--- | :--- |
| `inboxgpt/tui/` | Interactive terminal UI built with Textual (reader mode, modals, table). |
| `inboxgpt/agent/` | LangGraph ReAct engine, Gemini LLM bindings, and background daemon. |
| `inboxgpt/gmail/` | Gmail API integration (`LiveGmailClient`) and mock sandbox (`MockGmailClient`). |
| `inboxgpt/auth/` | Google OAuth 2.0 flow and token persistence in `~/.inboxgpt/`. |
| `bin/inboxgpt.js` | Zero-dependency Node.js CLI launcher for npm global execution. |
| `tests/` | Pytest test suite covering tools, triage, models, and CLI subcommands. |

---

## Safety-First Rule

InboxGPT is built with non-negotiable safety guardrails:
* **Never call permanent deletion:** Cleanups must only remove the `INBOX` label (archiving to All Mail).
* **Protected Entities:** Starred emails, Priority flags, OTPs, 2FA codes, and financial receipts can **never** be targeted by automated actions.

Any pull request that weakens these protections will be rejected.

---

## Submitting a Pull Request

1. Create a feature branch: `git checkout -b feature/my-new-feature`
2. Make your changes and add tests under `tests/`
3. Verify all tests pass: `pytest`
4. Commit using clear, descriptive messages: `git commit -m "add feature: ..."`
5. Push to your fork: `git push origin feature/my-new-feature`
6. Open a Pull Request on GitHub
