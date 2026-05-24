---
name: agent-browser
description: >
  Automate web browsers using agent-browser CLI. Use when the user asks to
  open a website, click buttons, fill forms, extract data from pages, take
  screenshots, log into sites, test a web app, scrape content, interact with
  iframes, handle OAuth flows, record videos, mock network requests, debug
  React apps, run parallel browser sessions, or automate any task that
  requires a real browser. Triggers on: "open this url", "click on",
  "fill in the form", "scrape", "screenshot", "log into", "browser",
  "web page", "headless chrome", "automate the browser", "test in browser",
  "check this website", "what does this page look like". Prefer over curl/wget
  when the task needs JavaScript rendering, user interaction, or visual output.
license: Apache-2.0
metadata:
  version: "1.0"
  topic: browser-automation
compatibility: Requires agent-browser CLI (npm install -g agent-browser) and Chrome/Chromium
allowed-tools:
  - Bash(agent-browser:*)
  - Bash(npx agent-browser:*)
---

# agent-browser

Browser automation CLI designed for AI agents. Native Rust, Chrome/Chromium
via CDP. Accessibility-tree snapshots with compact `@eN` refs — agents
interact with pages in ~200-400 tokens instead of parsing raw HTML.

## Prerequisites

```bash
npm install -g agent-browser    # all platforms
agent-browser install           # download Chrome (first time only)
```

If something's broken, run `agent-browser doctor` — it diagnoses env,
Chrome, daemons, config, and auto-cleans stale files.

## The core loop

Every agent-browser task follows this pattern:

```bash
agent-browser open <url>        # 1. Navigate
agent-browser snapshot -i       # 2. Read the page (interactive elements only)
agent-browser click @e3         # 3. Act using refs from the snapshot
agent-browser snapshot -i       # 4. Re-snapshot after any page change
```

**Refs (`@e1`, `@e2`, ...) are assigned fresh on every snapshot.** They go
stale the moment the page changes — navigation, form submit, dynamic
re-render, dialog open. Always re-snapshot before your next ref interaction.

### When something doesn't work as expected

After any action that should change the page, verify it worked:

1. **Did the URL change?** `agent-browser get url`
2. **Did the content change?** `agent-browser snapshot -i` — are the refs different?
3. **Is there a dialog blocking?** `agent-browser dialog status`
4. **Is there a cookie banner or overlay?** Look for dismiss/close buttons in the snapshot
5. **Did the element actually get clicked?** Try `scrollintoview @e3` first, then re-click

If the click did nothing, common causes: overlay blocking it, element
off-screen, SPA didn't re-render yet (try `wait --load networkidle`).

## Reading a page

```bash
agent-browser snapshot -i                 # interactive elements only (preferred)
agent-browser snapshot -i -c              # compact (no empty structural nodes)
agent-browser snapshot -i -d 3            # cap depth at 3 levels
agent-browser snapshot -s "#main"         # scope to a CSS selector
agent-browser snapshot -i --json          # machine-readable
```

Snapshot output:

```
@e1 [heading] "Log in"
@e2 [form]
  @e3 [input type="email"] placeholder="Email"
  @e4 [input type="password"] placeholder="Password"
  @e5 [button type="submit"] "Continue"
```

Targeted extraction without refs:

```bash
agent-browser get text @e1        # visible text
agent-browser get html @e1        # innerHTML
agent-browser get attr @e1 href   # attribute value
agent-browser get value @e1       # input value
agent-browser get title           # page title
agent-browser get url             # current URL
agent-browser get count ".item"   # count matching elements
```

## Interacting with elements

```bash
agent-browser click @e1                   # click
agent-browser fill @e2 "hello"            # clear then type
agent-browser type @e2 " world"           # append without clearing
agent-browser press Enter                 # press key
agent-browser press Control+a             # key combination
agent-browser hover @e1                   # hover
agent-browser select @e4 "option"         # dropdown
agent-browser check @e3                   # checkbox
agent-browser upload @e5 file.pdf         # file upload
agent-browser scroll down 500             # scroll
agent-browser drag @e1 @e2                # drag and drop
```

When refs aren't available or you skipped the snapshot, use semantic locators:

```bash
agent-browser find role button click --name "Submit"
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "user@test.com"
agent-browser find testid "submit-btn" click
```

Or raw CSS selectors as a fallback: `agent-browser click "#submit"`.

Rule of thumb: snapshot + `@eN` refs → `find role/text/label` → raw CSS.

## Waiting (read this)

Agents fail more from bad waits than bad selectors. After any page-changing
action:

```bash
agent-browser wait @e1                     # element appears
agent-browser wait --text "Success"        # text appears on page
agent-browser wait --url "**/dashboard"    # URL matches (glob pattern)
agent-browser wait --load networkidle      # network settles (SPA nav)
agent-browser wait --fn "window.ready"     # JS condition
agent-browser wait 2000                    # dumb ms wait (last resort)
```

**Strategy:** `wait --url` for navigation, `wait --text` for content changes,
`wait --load networkidle` as the SPA catch-all. Avoid bare millisecond waits.

## Screenshots

```bash
agent-browser screenshot                   # temp path
agent-browser screenshot page.png          # specific path
agent-browser screenshot --full full.png   # full scroll height
agent-browser screenshot --annotate a.png  # numbered labels matching @eN refs
```

`--annotate` produces a labeled image for vision models — each `[N]` maps to `@eN`.

## Tabs

```bash
agent-browser tab                          # list tabs (stable tabId: t1, t2, ...)
agent-browser tab new https://docs...      # open + switch
agent-browser tab t2                       # switch by id
agent-browser tab close t2                 # close by id
```

Refs belong to the active tab. Switch tabs → re-snapshot.

## Sessions

Every `agent-browser` command talks to a daemon that keeps the browser alive
between calls. A **session** is an isolated browser instance with its own
cookies, localStorage, tabs, and refs.

```bash
# Default session (no name needed)
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser close

# Named sessions — fully isolated from each other
agent-browser --session admin open https://app.example.com
agent-browser --session viewer open https://app.example.com

# See what's running
agent-browser session list

# Close a specific session or nuke everything
agent-browser --session admin close
agent-browser close --all
```

### Three ways to persist state

| Method | What it does | When to use |
|--------|-------------|-------------|
| `--session <name>` | Named isolated browser, in-memory only | Parallel scraping, multi-user flows |
| `--session-name <name>` | Auto-save/restore cookies+storage to disk by name | Repeated tasks with same auth, survive restarts |
| `state save`/`state load` | Explicit file-based save/restore of auth state | One-time auth export, sharing state between tasks |

```bash
# --session: just isolation, nothing persists after close
agent-browser --session scrape open https://example.com
agent-browser --session scrape close   # state gone

# --session-name: auto-persists across runs
agent-browser --session-name myapp open https://app.example.com
# ... login ...
agent-browser close   # state saved to ~/.agent-browser/sessions/
# Next run restores automatically:
agent-browser --session-name myapp open https://app.example.com

# state save/load: explicit file control
agent-browser state save ./auth.json
agent-browser --state ./auth.json open https://app.example.com
```

### Parallel sessions

Each `--session <name>` is a separate browser. Use for multi-user flows or
concurrent scraping:

```bash
agent-browser --session a open https://app.example.com &
agent-browser --session b open https://app.example.com &
wait
agent-browser --session a fill @e1 "alice@test.com"
agent-browser --session b fill @e1 "bob@test.com"
```

## Authentication

Three approaches, in order of preference:

### 1. Manual login + state save (sites with 2FA, captcha, OAuth)

For real accounts (Facebook, Google, GitHub, anything with SSO), don't
automate the login — let the human handle it:

```bash
agent-browser --headed open https://facebook.com
# Browser window opens — user logs in manually (handles 2FA, captchas, etc.)
agent-browser state save ./fb-auth.json
agent-browser close

# Future runs skip login entirely:
agent-browser --state ./fb-auth.json open https://facebook.com
```

### 2. Reuse an existing Chrome profile

If you're already logged in via Chrome, point agent-browser at that profile:

```bash
agent-browser --profile Default open https://facebook.com
# Or a custom profile path:
agent-browser --profile ~/.config/chromium open https://facebook.com
```

Or grab state from a running Chrome without touching its profile:

```bash
# User starts Chrome with: google-chrome --remote-debugging-port=9222
agent-browser --auto-connect state save ./auth.json
agent-browser close
```

### 3. Automated form fill (simple sites, test accounts only)

```bash
agent-browser open https://app.example.com/login
agent-browser snapshot -i
agent-browser fill @e3 "user@example.com"
agent-browser fill @e4 "password"
agent-browser click @e5
agent-browser wait --url "**/dashboard"
agent-browser state save ./auth.json
```

**Don't use approach 3 for real accounts.** 2FA, captcha, and suspicious-login
detection will block automated credentials. Prefer approach 1 or 2.

**Security:** Never echo or paste secrets in chat. State files contain session
tokens — add to `.gitignore`, delete when no longer needed.

## Data extraction

```bash
# Structured snapshot
agent-browser snapshot -i --json > page.json

# Arbitrary shape via JS (use heredoc for complex scripts)
cat <<'EOF' | agent-browser eval --stdin
const rows = document.querySelectorAll("table tbody tr");
Array.from(rows).map(r => ({
  name: r.cells[0].innerText,
  price: r.cells[1].innerText,
}));
EOF
```

Use `eval --stdin` or `eval -b <base64>` for any JS with quotes/special
characters. Inline `eval "..."` only works for simple expressions.

## Iframes

Iframes are auto-inlined in snapshots — their refs work without switching
frames:

```bash
agent-browser snapshot -i
# @e3 [Iframe] "payment-frame"
#   @e4 [input] "Card number"
#   @e5 [button] "Pay"
agent-browser fill @e4 "4111111111111111"
agent-browser click @e5
```

For scoped interaction: `frame @e3` → `snapshot -i` → work → `frame main`.

## Dialogs

`alert` and `beforeunload` are auto-accepted so agents never block. For
`confirm` and `prompt`:

```bash
agent-browser dialog status          # is there a pending dialog?
agent-browser dialog accept          # accept
agent-browser dialog accept "text"   # accept with prompt input
agent-browser dialog dismiss         # cancel
```

## Gotchas

- **Refs stale after page changes.** Re-snapshot after clicks that navigate,
  form submits, or dynamic updates. "Ref not found" always means "re-snapshot."
- **Cookie banners block clicks.** Snapshot, find the dismiss button, click
  it, re-snapshot.
- **Fill doesn't work on custom inputs.** Try `focus @e1` then
  `keyboard inserttext "text"` to bypass key event interception.
- **Elements not in snapshot.** Probably off-screen or not rendered. Scroll
  or `wait --text` then re-snapshot.
- **`eval` with quotes breaks.** Use `eval --stdin` with a heredoc or
  `eval -b <base64>` instead of inline strings.
- **Daemon persists between commands.** The browser stays alive across
  separate `agent-browser` calls. Use `close` when done, `close --all` to
  nuke everything.
- **Cross-origin iframes may be empty.** If the iframe blocks accessibility
  tree access, use `frame "#iframe"` to switch in explicitly, or fall back
  to `eval` with CORS headers.

## Common flags

```bash
--headed                # show browser window (default: headless)
--session <name>        # isolated browser session
--session-name <name>   # auto-save/restore state by name
--state <path>          # load saved auth state from file
--profile <name|path>   # reuse Chrome profile (login survives restarts)
--auto-connect          # discover and attach to running Chrome
--cdp <port>            # connect via Chrome DevTools Protocol port
--json                  # JSON output for machine parsing
--proxy <url>           # proxy server (HTTP, HTTPS, SOCKS5)
```

## Cleanup

Always close when done:

```bash
agent-browser close              # close current session
agent-browser close --all        # close every session
```

## Deeper reference

Read these when the task needs them:

| Read when... | File |
|---|---|
| Debugging a React app, inspecting components, measuring Web Vitals | `references/react-devtools.md` |
| Mocking API responses, blocking requests, recording HAR | `references/network.md` |
| Recording the browser session as video | `references/video.md` |
| Device emulation, proxy, CDP, extensions, init scripts, custom config | `references/advanced.md` |

The CLI also ships its own version-matched docs with the full command
reference, authentication deep-dives, profiling, and starter templates:

```bash
agent-browser skills get core --full     # everything
agent-browser skills list                # all available skills
```

Specialized skills for non-standard targets:

```bash
agent-browser skills get electron        # VS Code, Slack desktop, Figma...
agent-browser skills get slack           # Slack workspace automation
agent-browser skills get dogfood         # exploratory testing / QA
agent-browser skills get vercel-sandbox  # ephemeral microVMs
agent-browser skills get agentcore       # AWS Bedrock AgentCore
```
