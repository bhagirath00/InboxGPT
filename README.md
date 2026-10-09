<p align="center">
  <img src="assets/icon.svg" alt="inboxgpt icon" width="48" height="48" style="vertical-align: middle; margin-right: 10px;" />
  <strong style="font-size: 36px; vertical-align: middle;">inboxgpt</strong>
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/inboxgpt"><picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/npm/inboxgpt.svg?variant=outline&amp;font=geist" /><img alt="version" src="https://shieldcn.dev/npm/inboxgpt.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
  <a href="https://github.com/bhagirath00/inboxgpt"><picture><source media="(prefers-color-scheme: dark)" srcset="https://www.shieldcn.dev/github/license/bhagirath00/inboxgpt.svg?variant=outline&amp;font=geist" /><img alt="license" src="https://www.shieldcn.dev/github/license/bhagirath00/inboxgpt.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
  <a href="https://github.com/bhagirath00/inboxgpt"><picture><source media="(prefers-color-scheme: dark)" srcset="https://www.shieldcn.dev/github/stars/bhagirath00/inboxgpt.svg?variant=outline&amp;mode=dark&amp;font=geist" /><img alt="stars" src="https://www.shieldcn.dev/github/stars/bhagirath00/inboxgpt.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
  <a href="https://github.com/bhagirath00/inboxgpt"><picture><source media="(prefers-color-scheme: dark)" srcset="https://shieldcn.dev/views/repo/bhagirath00/inboxgpt.svg?variant=outline&amp;mode=dark&amp;font=geist" /><img alt="views" src="https://shieldcn.dev/views/repo/bhagirath00/inboxgpt.svg?variant=outline&amp;mode=light&amp;font=geist" /></picture></a>
</p>

Terminal-first AI Gmail executive assistant powered by LangGraph, Google Gemini, and Textual TUI with human-in-the-loop safety.

* Lightning-fast keyboard navigation inspired by lazygit and Vim.
* Autonomous LangGraph ReAct agent with email search, context reading, draft generation, and long-term memory.
* Inviolable safety guardrails: Starred, Priority, OTPs, 2FA codes, and financial receipts can never be trashed.
* Zero permanent deletions: Archive cleanly removes the Inbox label while preserving everything in "All Mail".
* Background daemon for automated executive morning briefings and action item digests.
* Multi-account management with seamless switching and token auto-refresh.

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
| `↑` / `↓` or `j` / `k` | **Navigate** | Scroll through emails |
| `Enter` | **Reader** | Open full email reader view |
| `1` – `5` | **Filter** | Switch category tabs: All, Priority, Promo, Social, News |
| `e` | **Archive** | Archive email (safe remove from Inbox, kept in All Mail) |
| `d` | **Trash** | Move email to Bin/Trash |
| `x` | **Select** | Toggle multi-selection checkbox |
| `r` | **Sync** | Sync latest emails from Gmail API |
| `a` / `/` | **Inbox Agent** | Trigger Gemini AI Agent dialog |
| `l` | **Switch Account** | Switch / Logout active Gmail account |
| `?` | **Help** | Open keybindings cheat sheet |
| `Esc` / `q` | **Back / Quit** | Return to list view or exit application |

---

## Empirical Evaluation & Safety Benchmark

InboxGPT includes a reproducible 50-email ground-truth evaluation benchmark covering critical authentication codes, multi-factor OTPs, bank fraud alerts, newsletters, promotions, and hostile prompt-injection attacks.

| Metric | Result | Benchmark Target | Status |
| :--- | :---: | :---: | :---: |
| **Total Benchmark Emails** | **50** | 50 | Verified |
| **Protected Emails Touched** | **0 / 17** | 0 (Strict Zero) | **100% Invariant** |
| **Triage Category Accuracy** | **100.0%** | > 90% | **Passed** |
| **Safety Invariant Rate** | **100.0%** | 100% | **Passed** |
| **Decision Latency** | **< 1 ms / email** | < 100 ms | **Instant** |

Run the benchmark suite locally anytime:
```bash
python scripts/run_eval.py
```

---

## Security Model & Threat Invariants

1. **Local-First Zero-Telemetry Privacy**: OAuth credentials (`credentials.json`) and refresh tokens (`token.json`) are stored strictly on the user's local filesystem (`~/.inboxgpt/`). No tokens or email payloads are transmitted to any central database or cloud telemetry server.
2. **Inviolable Human-in-the-Loop Barrier**: The agent uses LangGraph `interrupt()` barriers. Destructive actions (`execute_trash`, `execute_archive`, `execute_label`) pause execution and yield state to the TUI. Actions are NEVER executed without an explicit interactive confirmation keypress (`y` / `n`).
3. **Adversarial Prompt-Injection Immunity**: Untrusted email bodies cannot hijack agent instructions or trick the planner into modifying protected emails. Starred emails, security verification codes, invoices, and bank alerts are programmatically guarded by deterministic invariant checks (`is_protected_email`).
4. **Least-Privilege Scopes**: InboxGPT requests only `https://www.googleapis.com/auth/gmail.modify`. Full account administrative privileges or Google Drive access are explicitly forbidden.

---

## Reliability Engineering

* **Exponential Backoff**: Upstream Google REST API calls are wrapped with `tenacity` retries (`@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))`).
* **Automatic Token Revocation Recovery**: Stale, expired, or revoked tokens (`RefreshError`) are caught gracefully, purging corrupted cache tokens and guiding the user to re-authenticate cleanly.
* **Structured Log Rotation**: Operating logs are maintained with Python's `RotatingFileHandler` (max 5 MB, 3 historical backups) at `~/.inboxgpt/inboxgpt.log`.

---

## Limitations

* **Attachment Parsing**: Currently extracts plain text and HTML message bodies; does not parse binary attachments (PDF, DOCX, ZIP).
* **Google API Quota**: Operates under standard user project quotas (250 quota units/sec for Gmail REST API).
* **Offline Writes**: Inbox changes require network connectivity to commit to Gmail cloud servers; offline mode functions in read-only sandbox mode.

---

## License

Distributed under the MIT License. See [LICENSE](https://github.com/bhagirath00/inboxgpt/blob/main/LICENSE) for details.
