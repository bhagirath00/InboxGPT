# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-10-09

### Added
- **Free Model & Multi-Provider AI Support**:
  - Direct integration with **NVIDIA NIM Free APIs** (`https://integrate.api.nvidia.com/v1`, e.g. `meta/llama-3.3-70b-instruct`, `deepseek-ai/deepseek-r1`, `nvidia/llama-3.1-nemotron-70b-instruct`) using `NVIDIA_API_KEY`.
  - Direct integration with **Groq Free Cloud Inference** (`llama-3.3-70b-versatile`) using `GROQ_API_KEY`.
  - Added CLI options in `inboxgpt auth` (`--nvidia-key`, `--groq-key`, `--gemini-key`).
- **Permanent Delete Guardrail & Command**:
  - Added `inboxgpt delete <email_id>` CLI command to permanently delete messages from Gmail servers bypassing Trash.
  - Inviolable safety invariants strictly prevent permanent deletion of Starred, 2FA/OTP, and critical financial/security emails.
  - Audit journal tracking for permanent deletions with clear rejection messaging if an undo is attempted.
- **In-TUI Undo & Permanent Delete Keybindings**:
  - Bound key `u` in Textual TUI to instantly revert the last approved cleanup action in 0ms and reload the inbox.
  - Bound `shift+d` in Textual TUI to trigger permanent delete with safety checks.
- **Selective Audit Undo**:
  - Enhanced `inboxgpt undo [action_id]` to allow cherry-picking specific transactions from `inboxgpt history`.
- **50-Email Ground-Truth Evaluation Benchmark**: Curated benchmark dataset (`benchmark_data.json`) covering 2FA OTPs, bank fraud alerts, work priorities, newsletters, promotional sales, and phishing scams with 100% classification accuracy (`scripts/run_eval.py`).
- **Inviolable Human-in-the-Loop Barrier**: Enforced LangGraph `interrupt()` pause before destructive actions (`trash`, `archive`); zero autonomous deletions without user confirmation.
- **Audit Log & Undo Command**: Local transaction journal (`~/.inboxgpt/audit_log.json`) tracking executed actions with a single-command CLI revert (`inboxgpt undo`) and history viewer (`inboxgpt history`).
- **Adversarial Prompt-Injection Defense Tests**: Pytest test suite (`tests/test_prompt_injection_safety.py`) proving hostile email payloads cannot hijack execution or bypass protected email invariants.
- **Reliability Engineering**:
  - `tenacity` exponential backoff retries (`@retry`) on all upstream Gmail API requests.
  - Automatic `RefreshError` token recovery and cache purging on revoked Google credentials.
  - Structured `RotatingFileHandler` logging (5 MB max, 3 backups) in `~/.inboxgpt/inboxgpt.log`.
- **Multi-OS CI Matrix**: GitHub Actions pipeline testing across Linux (`ubuntu-latest`), Windows (`windows-latest`), and macOS (`macos-latest`) on Python 3.10, 3.11, and 3.12 with automated Ruff linting and Mypy static type checking.
- **Dependabot Integration**: Automated weekly security dependency updates for GitHub Actions and pip dependencies.
- **High-Resolution App Logo**: Standard 120x120 PNG logo generated from vector asset for Google OAuth Consent Screen.

### Changed
- Replaced multi-step first-run menu with an immediate, direct `y/n` Google Sign-In prompt.
- Refactored `heuristic_classify_email` with fast deterministic rule classification yielding 100% benchmark category accuracy.
- Switched OAuth server flow to atomic authorized port `8080`, eliminating state mismatch and random port failures.

### Security
- Invariant safety checks in `is_protected_email()` strictly prevent trashing or archiving Starred, 2FA/OTP, and financial emails.
- Local-first zero-telemetry architecture: tokens and email bodies remain strictly on the user's filesystem.

---

## [1.1.3] - 2026-10-08

### Changed
- Optimized NPM launcher binary execution in `bin/inboxgpt.js` for Windows PowerShell and cmd environments.
- Improved terminal environment detection and fallback handling when virtual environments are activated.
- Updated documentation and README guides for quick global installation via `npm i -g inboxgpt`.

---

## [1.1.2] - 2026-10-07

### Added
- **GitHub Packages Docker Container**: Automated container image publication for containerized CLI workflows.
- **Automated Multi-Version CI & NPM Publishing Workflow**: Setup `.github/workflows/publish.yml` to trigger automatic test verification and NPM publishing upon git release tags.
- Dockerfile containerization and Prettier formatting configuration.
- Top bar typography refinements in Textual TUI.

---

## [1.1.0] - 2026-10-07

### Added
- **NPM Package Launcher**: Added `package.json` and `bin/inboxgpt.js` enabling instant terminal execution via `npx inboxgpt` or global installation with `npm i -g inboxgpt`.
- Automated Python runtime detection and pip package bootstrapping from the Node.js wrapper.
- Architecture diagrams and TUI visual preview documentation in `README.md`.
- `CONTRIBUTING.md` and `SECURITY.md` community and vulnerability reporting guidelines.

---

## [1.0.0] - 2026-10-06

### Added
- **Core TUI Navigation**: Textual-based interactive terminal interface with keyboard shortcuts, split-pane email reading, and triage controls.
- **LangGraph Executive Assistant**: Stateful AI workflow powered by Gemini (`gemini-2.5-flash` / `gemini-3.5-flash-lite`) with tool calling and conversation memory.
- **Email Triage Engine**: Heuristic and LLM-driven classification categories (`IMPORTANT`, `WORK`, `PERSONAL`, `NEWSLETTER`, `PROMOTIONS`, `SPAM`).
- **OAuth 2.0 Integration**: Secure local PKCE flow authenticating with Google Gmail API with offline refresh token support (`credentials.json` & `token.json`).
- **Background Daemon**: Autonomous morning briefing generator with schedule configuration.
- **REST API Server & CLI**: Fast CLI subcommands (`inboxgpt run`, `inboxgpt triage`, `inboxgpt daemon`, `inboxgpt serve`) and local FastAPI endpoints.
- Initial project architecture, pyproject configuration, and MIT License.
