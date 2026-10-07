# Security Policy

## Supported Versions

We actively provide security patches for the following versions of InboxGPT:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

---

## Data & Credential Safety Architecture

InboxGPT is designed with a **privacy-first, local-execution** philosophy:

1. **Local OAuth Storage:** User OAuth tokens and refresh tokens are stored strictly on your local disk in `~/.inboxgpt/token.json` with user-only file permissions (`0600`).
2. **Zero Telemetry:** InboxGPT does not collect, track, or transmit your emails, queries, metadata, or logs to any remote analytics or telemetry services.
3. **API Keys:** Your `GEMINI_API_KEY` is loaded exclusively from your local environment or `.env` file and passed directly to Google's official Gemini API endpoints over HTTPS.
4. **Destructive Action Prevention:** InboxGPT never permanently deletes emails. Archive and cleanup operations only strip the `INBOX` label (keeping the mail accessible in All Mail).

---

## Reporting a Vulnerability

If you discover a security vulnerability or credential leak issue in InboxGPT, please **do not** open a public GitHub issue.

Instead, please report it privately:

1. **Email:** Send details to the maintainer directly or open a [Private Vulnerability Advisory](https://github.com/bhagirath00/Inboxgpt/security/advisories/new) on GitHub.
2. **Details to include:**
   - Detailed description of the vulnerability
   - Steps or proof-of-concept (PoC) to reproduce the issue
   - Affected versions and environments (OS, Python version)
   - Any suggested mitigations or patches

### Response Timeline
- **Initial Response:** Within 48 hours of report submission.
- **Triage & Assessment:** Within 5 business days.
- **Fix & Disclosure:** Coordinated release once a fix is verified.
