# Privacy Policy for InboxGPT

Last updated: October 2026

## 1. Overview
InboxGPT is a local-first, open-source terminal application designed to help users triage and manage their Gmail accounts securely using AI assistance.

## 2. Data Storage and Privacy
- **Zero Central Telemetry:** InboxGPT does not operate any central servers, external databases, or analytics tracking.
- **Local Credentials:** All Google OAuth credentials (`credentials.json`) and access tokens (`token.json`) are stored strictly on your local machine (`~/.inboxgpt/`).
- **No Third-Party Transmission:** Your email messages and personal data never leave your local machine, except for direct communication between your computer and Google's official Gmail APIs, and optional LLM analysis via Google Gemini.

## 3. Google API Data Usage
InboxGPT accesses Google user data via the Gmail API scope `https://www.googleapis.com/auth/gmail.modify`:
- Email metadata and bodies are read solely to display them in your terminal user interface and compute category triage proposals.
- No destructive actions (such as trashing or archiving) are ever executed without explicit, interactive human confirmation (`y`/`n`).
- InboxGPT complies with Google API Services User Data Policy, including the Limited Use requirements.

## 4. Open Source Transparency
The full source code of InboxGPT is publicly available for audit on GitHub:
https://github.com/bhagirath00/InboxGPT
