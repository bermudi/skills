---
name: agent-browser
description: >
  Unattended browser automation with the agent-browser CLI: navigate, click,
  fill forms, screenshot, scrape, test web apps; also Electron, Slack, Vercel
  Sandbox. If a human should watch in a terminal pane, or the browser is open
  in one, use terminal-browser.
license: Apache-2.0
metadata:
  version: "1.5"
  topic: browser-automation
compatibility: agent-browser CLI (npm i -g agent-browser) + Chrome/Chromium
allowed-tools:
  - Bash(agent-browser:*)
  - Bash(npx agent-browser:*)
---

# agent-browser

Stub: before any `agent-browser` command, load the real workflow from the CLI, which always matches the installed version:

```bash
agent-browser skills get core             # workflows, patterns, troubleshooting
agent-browser skills get core --full      # plus full command reference
```

Older CLI without `skills get`: `agent-browser --help`.

## Launch preferences on this machine

Two modes: pick by task, say which you're running, never escalate without asking.

**Mode 1 — headless managed Chrome (default).** Anything not needing bermudi's session: testing, dev, public scraping. Plain `agent-browser <command>`. Never `--headed` (ask if a visible window seems needed). Managed Chrome trips Cloudflare regardless of flags, so never aim it at his personal accounts.

**Mode 2 — bermudi's browser, attach-only.** For his real session or auth (personal accounts, Cloudflare-protected sites like luma.com); only his profile's cookies and fingerprint pass. Attach, work in your own tab, clean up, leave.

Needs Chromium running with `--remote-debugging-port=9222`. If port 9222 is closed: when nobody asked for the work, tell bermudi and wait; when the task genuinely needs his session (ruled 2026-10-10), launch it yourself (`/usr/bin/chromium --remote-debugging-port=9222`, background). If Chromium is already running without the flag, the launch is absorbed and no port opens; he must quit it fully first. Never pass `--profile` or `AGENT_BROWSER_EXECUTABLE_PATH`.

Attach before the first command:

```bash
export AGENT_BROWSER_SESSION="$(agent-browser session id --scope worktree --prefix task)"
export AGENT_BROWSER_CDP=9222 AGENT_BROWSER_PIN_TAB=1
```

- `PIN_TAB` is mandatory: attach opens a fresh tab instead of adopting his active one, and a lost binding fails with `tab_gone` instead of acting on his other tabs.
- Cleanup = `tab close` on each tab you opened, then stop. Never close, navigate, reload or sign out of other tabs; never change settings or clear data. Never `close`, `quit` or `close --all`.
- RED LINE: his profile holds Proton Pass. Never read passwords (vault UI, filled fields even to "verify", eval, screenshots). Logins go through the extension's autofill: click, never extract. Credentials needed outside the browser go through the `pass-cli` skill.
- An open CDP port lets any local process drive his browser; accepted here, which is why the port exists only while this work does.

## Specialized skills

`agent-browser skills get <name>` for non-web-page targets: `electron`, `slack`, `dogfood` (exploratory QA), `derive-client` (HAR → API client), `vercel-sandbox`, `agentcore`. `agent-browser skills list` shows all.

The dashboard runs on port 4848 independent of sessions; stay on its origin, since session tabs and streams are proxied through it.
