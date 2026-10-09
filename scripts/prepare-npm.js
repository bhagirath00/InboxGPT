const fs = require("fs");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
const readmePath = path.join(rootDir, "README.md");
const backupPath = path.join(rootDir, "README.github.bak");

// 1. Backup original GitHub README.md
if (fs.existsSync(readmePath)) {
  fs.copyFileSync(readmePath, backupPath);
}

// 2. Clean NPM-specific README content
const npmReadmeContent = `<p align="center">
  <img src="https://raw.githubusercontent.com/bhagirath00/inboxgpt/main/assets/icon.svg" alt="inboxgpt icon" width="48" height="48" style="vertical-align: middle; margin-right: 10px;" />
  <strong style="font-size: 36px; vertical-align: middle;">inboxgpt</strong>
</p>

Terminal-first AI Gmail executive assistant powered by LangGraph, Google Gemini, and Textual TUI with human-in-the-loop safety.

* Lightning-fast keyboard navigation inspired by lazygit and Vim.
* Autonomous LangGraph ReAct agent with email search, context reading, draft generation, and long-term memory.
* Inviolable safety guardrails: Starred, Priority, OTPs, 2FA codes, and financial receipts can never be trashed.
* Zero permanent deletions: Archive cleanly removes the Inbox label while preserving everything in All Mail.
* Background daemon for automated executive morning briefings and action item digests.
* Multi-account management with seamless switching and token auto-refresh.

## Quickstart

Run directly without cloning:

\`\`\`bash
npx inboxgpt
\`\`\`

Or install globally:

\`\`\`bash
npm install -g inboxgpt
inboxgpt
\`\`\`

## Integrated Agent Tools
* \`search_mailbox\`: Runs search queries across your inbox (\`is:unread\`, \`from:someone\`, date filters).
* \`read_email_details\`: Retrieves complete email bodies and thread context.
* \`create_email_draft\`: Composes replies as drafts in Gmail without sending without approval.
* \`save_agent_memory\`: Retains persistent user instructions across sessions in \`~/.inboxgpt/agent_memory.json\`.

## Keyboard Controls

| Key | Action | Description |
| :---: | :--- | :--- |
| \`↑\` / \`↓\` | **Navigate** | Scroll through emails |
| \`Enter\` | **Reader** | Open full email reader view |
| \`1\` – \`5\` | **Filter** | Switch category tabs: All, Priority, Promo, Social, News |
| \`e\` | **Archive** | Archive email (safe remove from Inbox, kept in All Mail) |
| \`d\` | **Trash** | Move non-critical email to Trash |
| \`/\` | **Ask AI** | Open autonomous Executive Assistant prompt |
| \`q\` | **Quit** | Exit InboxGPT |
`;

// 3. Write clean NPM README
fs.writeFileSync(readmePath, npmReadmeContent, "utf-8");
console.log("\x1b[36m[NPM Prep]\x1b[0m Temporarily applied clean NPM README.md for packaging.");
