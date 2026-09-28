---
name: agent-browser
description: >
  Browser automation with agent-browser CLI for unattended work — open pages,
  click, fill forms, screenshot, scrape, test web apps; also Electron, Slack,
  and Vercel Sandbox. Firefox (incl. stealth via the bundled agent-ff CLI)
  lives here too. If the human should watch the page in a terminal pane, or
  the browser is already open in one, that's terminal-browser, not this.
license: Apache-2.0
metadata:
  version: "1.4"
  topic: browser-automation
compatibility: agent-browser CLI (npm i -g agent-browser) + Chrome/Chromium; Firefox via bundled agent-ff (uv, Selenium/geckodriver auto-fetched)
allowed-tools:
  - Bash(agent-browser:*)
  - Bash(npx agent-browser:*)
  - Bash(agent-ff:*)
---

# agent-browser

Fast browser automation CLI for AI agents. Native Rust, Chrome/Chromium via CDP with accessibility-tree snapshots and compact `@eN` element refs.

Install: `npm i -g agent-browser && agent-browser install`

## Start here

This file is a discovery stub, not the usage guide. Before running any `agent-browser` command, load the actual workflow content from the CLI:

```bash
agent-browser skills get core             # start here — workflows, common patterns, troubleshooting
agent-browser skills get core --full      # include full command reference and templates
```

The CLI serves skill content that always matches the installed version, so instructions never go stale. The content in this stub cannot change between releases, which is why it just points at `skills get core`.

If `skills get` is unavailable (older CLI), fall back to `agent-browser --help` and `agent-browser snapshot --help`.

## Launch preferences on this machine

Two modes — pick by task nature, say which one you're running, and never escalate without asking:

**Mode 1 — headless managed Chrome (default).** Anything that doesn't need bermudi's session or auth: testing, dev, scraping public pages. Plain `agent-browser <command>`; the CLI manages its own Chrome. Always headless — never pass `--headed`; if a task seems to need a visible window, ask bermudi. Managed Chrome trips Cloudflare regardless of flags, so never point it at his personal accounts.

**Mode 2 — bermudi's browser, attach-only.** Anything needing his real session or auth (personal accounts, Cloudflare-protected services like luma.com) — his profile's real cookies and fingerprint are the only thing that passes. The browser is his: **he launches it, he closes it.** Agents attach, work in their own tab, clean up, and get out.

He launches Chromium with remote debugging:

```bash
/usr/bin/chromium --remote-debugging-port=9222
```

If Chromium is already running without that flag, the launch is absorbed by the running instance and no CDP port opens — he must quit Chromium fully first. Agents never launch it themselves, and never pass `--profile` or `AGENT_BROWSER_EXECUTABLE_PATH`.

Attach before the first command, then work normally:

```bash
export AGENT_BROWSER_SESSION="$(agent-browser session id --scope worktree --prefix task)"
export AGENT_BROWSER_CDP=9222 AGENT_BROWSER_PIN_TAB=1
```

- `--pin-tab` is not optional: it makes attach open a **fresh tab** instead of adopting his active one, and a lost binding fails with `tab_gone` instead of silently acting on his other tabs.
- Do all work in that tab. Cleanup = `tab close` on every tab you opened, then stop issuing commands. Never close, navigate, reload, or sign out of tabs you didn't open; never change settings or clear data.
- Never run `close`, `quit`, or `close --all` in this mode — that's his browser, not yours. (Attached browsers are exempt from the daemon's idle shutdown anyway.)
- Nothing listening on 9222? Don't launch, don't retry forever — tell bermudi and wait.
- RED LINE: his profile holds Proton Pass. Never read passwords — not from the vault UI, not from filled login fields (not even to "verify" a fill), never via eval or screenshots. Logins happen through the extension's own autofill; the agent may click, never extract. Credentials needed outside the browser go through the `pass-cli` skill.
- An open CDP port lets any local process drive his browser — accepted on this machine, which is exactly why the port exists only when he launches it.

## Firefox: agent-ff (stealth daemon)

agent-browser is Chromium/CDP only. For Firefox — or sites that gate on
`navigator.webdriver`, which managed Chrome trips — use the bundled
`agent-ff` CLI: a resident daemon driving Firefox Developer Edition via
Selenium/geckodriver, sessions persist across CLI calls:

```bash
agent-ff open https://example.com     # spawn daemon + stealth browser (default)
agent-ff snapshot                     # interactive elements as @N refs
agent-ff click @3                     # fill @7 "text" / type @7 "text"
agent-ff eval "navigator.webdriver"   # JS — prints null while stealth holds
agent-ff get text                     # url | title | text
agent-ff screenshot /tmp/shot.png
agent-ff close                        # browser + daemon down, no orphans
```

- Stealth = `navigator.webdriver` hidden by a WebDriver BiDi preload script
  (verified `likely_human` on amiabot.app). Profile-pref tricks are dead —
  Marionette force-sets the flag. Not a general anti-fingerprinting suit;
  limits and the full scoring story in `scripts/agent-ff/README.md` here.
- `open` reuses a running daemon (navigates its tab); flags: `--plain` (no
  stealth patch), `--headless`. Closing the window exits the daemon cleanly.
- Deps resolve via uv from the script's PEP 723 header; geckodriver is
  auto-fetched by Selenium Manager on first run. Nothing to install.

## Specialized skills

Load a specialized skill when the task falls outside browser web pages:

```bash
agent-browser skills get electron          # Electron desktop apps (VS Code, Slack, Discord, Figma, ...)
agent-browser skills get slack             # Slack workspace automation
agent-browser skills get dogfood           # Exploratory testing / QA / bug hunts
agent-browser skills get derive-client     # Record a HAR, derive a standalone API client for a site
agent-browser skills get vercel-sandbox    # agent-browser inside Vercel Sandbox microVMs
agent-browser skills get agentcore         # AWS Bedrock AgentCore cloud browsers
```

Run `agent-browser skills list` to see everything available on the installed version.

## Why agent-browser

- Fast native Rust CLI, not a Node.js wrapper
- Works with any AI agent (Cursor, Claude Code, Codex, Continue, Windsurf, etc.)
- Chrome/Chromium via CDP with no Playwright or Puppeteer dependency
- Accessibility-tree snapshots with element refs for reliable interaction
- Sessions, authentication vault, state persistence, video recording
- Specialized skills for Electron apps, Slack, exploratory testing, cloud providers

## Observability Dashboard

The dashboard runs independently of browser sessions on port 4848 and can also be opened through a proxied or forwarded URL such as `https://dashboard.agent-browser.localhost`. Agents should stay on the dashboard origin: session tabs, status, and stream traffic are proxied internally, so session ports do not need to be exposed.
