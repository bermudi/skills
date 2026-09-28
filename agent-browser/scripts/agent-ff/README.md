# agent-ff — stealth Firefox automation for agents

A resident-daemon CLI that drives Firefox Dev Edition with
Selenium/geckodriver and **hides `navigator.webdriver`** via a BiDi preload
script. Lives in the agent-browser skill (`scripts/agent-ff/`), on PATH as
`~/.pi/agent/bin/agent-ff` (symlink). Plus the full story of how we got
there, verified against https://amiabot.app/ on 2026-09-28 (Firefox Dev
157.0b5, geckodriver 0.37.1, Selenium 4.49.0).

## The CLI

```bash
agent-ff open <url> [--plain] [--headless]   # spawn daemon + stealth browser
agent-ff snapshot                            # interactive elements as @N refs
agent-ff click @2                            # refs resolve against last snapshot
agent-ff fill @7 "text"                      # auto-opens collapsed <details>
agent-ff eval "navigator.webdriver"          # JS, completion-value semantics
agent-ff get <url|title|text>
agent-ff screenshot [path]                   # default ~/.cache/agent-ff/shots/
agent-ff status                              # daemon/browser state
agent-ff close                               # quit browser + daemon, clean
```

- Daemon spawns on first `open`, lives at `~/.cache/agent-ff/daemon.sock`
  (0600, newline-JSON), logs every command to `daemon.log` beside it, and
  exits when the browser window closes.
- Single daemon guaranteed: a flock on `daemon.sock.lock` picks the winner if
  two agents race `open`; the loser exits without touching the socket.
- Commands over 90s (slow page loads) time out on the client with a pointer
  to the log — the daemon keeps working; check `agent-ff status`.
- Stealth persists across navigations; `--plain` skips it.
- Closing the browser window yourself = clean daemon exit; stale sockets are
  detected and respawned on the next `open`.
- Edits to the script only reach a *running* daemon after `close` + `open` —
  the daemon loads its own copy at spawn.

The rest of this file is the detective story behind the stealth patch —
what was tried, what scored what, and why the winner works.

## TL;DR — the working recipe

Inject a tiny JS patch **before page scripts** via a WebDriver BiDi preload
script. Six lines, scores `likely_human (88/100)` on amiabot:

```python
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common._bidi.script import Script

opts = Options()
opts.binary_location = "/usr/lib/firefox-developer-edition/firefox"
opts.web_socket_url = True                      # ask geckodriver for the BiDi websocket

driver = webdriver.Firefox(options=opts)
Script(driver).add_preload_script("""() => {
  Object.defineProperty(navigator, 'webdriver', {get: () => undefined, configurable: true});
}""")
driver.get("https://example.com")
```

`Script(driver)` self-starts the BiDi connection (Selenium 4.49 API — the old
`driver.bidi_connection()` context manager is CDP-legacy and raises on Firefox).
Preload scripts also run in iframes; workers are a non-issue on Firefox because
it doesn't expose `webdriver` in worker contexts (Chrome does).

**Both details matter:**
- *Instance-level* (`navigator`, not `Navigator.prototype`) — some detector
  stacks compare the descriptor against the native prototype.
- *`configurable: true`* — non-configurable props crash instrumentation code
  that touches the property, which visibly freezes pages (amiabot hung on
  "Collecting signals..." until we fixed this).

## The ladder — what we tried and what it scored

amiabot scoring economics learned along the way:
`navigator.webdriver` = −40 (high), behavior score low = −25, borderline = −12.
Cloudflare's own bot score is computed independently (it gave the raw Selenium
session a 99/"human" while amiabot said suspicious — different detectors care
about different things).

| rung | approach | score | verdict | why |
|---|---|---|---|---|
| 0 | raw Selenium Firefox | 60 | suspicious | webdriver −40, nothing else |
| 1 | pref `dom.webdriver.enabled=false` | 48 | suspicious | **dead** — Marionette force-sets it at runtime; profile prefs lose |
| 2 | prototype getter, non-configurable | — | page froze | property collision crashed their collector |
| 2b | instance getter, configurable, BiDi preload | **88** | **likely_human** | automation section came back empty |

Reference points from the same day: human-driven Firefox and Chrome both scored
100; agent-browser's managed Chrome scored 35 (`likely_bot` — webdriver + zero
behavior).

## Running the reference scripts

```bash
cd ~/build/skills/agent-browser/scripts/agent-ff
uv run --with selenium stealth.py    # working recipe, amiabot demo
uv run --with selenium plain.py      # raw Selenium, for comparison runs
```

(For agent work, prefer the `agent-ff` CLI above; these are the minimal
teaching versions.) Scripts idle keeping the browser open; close the window
and they exit cleanly.
`uv run --with selenium` needs no venv — Selenium Manager auto-fetches
geckodriver on first run (`~/.cache/selenium/`).

## Extras in stealth.py

- **Report capture**: amiabot POSTs its JSON to `/api/report`. stealth.py hooks
  `window.fetch` in the same preload script and stashes the response in
  `window.__report`, readable via `driver.execute_script`. More reliable than
  clicking "Download JSON" (the click silently did nothing under automation).
- Useful report paths: `verdict.{score,classification,risk,reasons[]}`,
  `client.automation.webdriver`, `client.workers.{webWorker,iframe,serviceWorker}.webdriver`,
  `client.behavior.score`, `cloudflareBotManagement.score`.

## Chasing the last 12 points

Remaining penalty is `behavior_score_borderline` (behavior 0.25 — no mouse
movement during their 15s collection window). Next rung if wanted: synthetic
pointer traffic via `driver.actions` (ActionChains) during collection.
Untried. Not needed unless a perfect score matters.

## Honest limits

This defeats *this* checker's webdriver line-item. The report shows dozens of
other surfaces (TLS fingerprint, stack probes, extension detection,
prototype-check sweeps) that heavier detectors do score. Enough for sites that
just gate on `navigator.webdriver`; not a general anti-fingerprinting suit
(that's fork territory: Camoufox for Firefox, undetected-chromedriver for
Chromium).

## Gotchas that cost us time

- `pkill -f <pattern>` matches your *own* shell wrapper when the pattern
  appears in the command line — killed our own bash twice (exit 143). Kill by
  PID.
- `uv run` heredocs: bare `python3` is blocked on this machine; use
  `uv run - <<'EOF'`.
- Profile-pref "fixes" for webdriver are all stale blog lore on modern Firefox.
  Marionette owns that flag.
- Multiple runs = multiple Firefox windows. Count them before launching
  another, and clean orphaned geckodrivers by PID (`~/.cache/selenium/`).
