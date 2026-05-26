# Zellij Quick Reference

Core primitives, agent driving patterns, and operational reference for terminal orchestration via zellij.

---

## Gotchas

**Background sessions start narrow** (typically 25 columns). Content wraps aggressively. Resize after creation:
```bash
zellij action resize increase right -p "$PANE"
```

**`dump-screen` gives you rendered terminal output** — the same thing a human sees. ANSI codes, cursor position ambiguity, and narrow-width wrapping all apply. Strip ANSI with `sed 's/\x1b\[[0-9;]*m//g'`.

**`write-chars` with `\n` is NOT the same as pressing Enter.** Programs in raw terminal mode (agents, REPLs, debuggers) need the actual Enter key event. Always pair text with `send-keys Enter`.

**`subscribe` is a blocking stream.** Pipe it through `jq`/`grep` and run in the background, or use `timeout` to cap it.

**Pane IDs change between sessions.** Always discover dynamically with `list-panes`.

**`ZELLIJ_SESSION_NAME` env var is required** when not inside zellij. There is no `--session` flag on `action` subcommands — the env var is the only way to target a session from outside.

**Short-lived commands exit before you can read them.** Redirect output to a file, or use `dump-screen --full` immediately after launch. Do NOT rely on `--block-until-exit-success` for output capture — it blocks until exit 0 and **hangs forever on non-zero**.

**Don't stomp on active sessions.** Never assume an existing zellij session is disposable. If testing, create a dedicated throwaway session.

---

## Core Primitives

| Primitive | Command | Returns |
|---|---|---|
| Run command in new pane | `zellij run -- <cmd>` | `terminal_<id>` |
| List all panes | `zellij action list-panes --json --all` | JSON array |
| Read pane output | `zellij action dump-screen -p <id>` | Text (viewport) |
| Send keystrokes | `zellij action send-keys -p <id> "Enter"` | — |
| Send text | `zellij action write-chars -p <id> "text"` | — |
| Block until exit | `zellij run --block-until-exit -- <cmd>` | Exit code |
| Stream output live | `zellij subscribe -p <id> -f json` | JSON events |

---

## Session Management

```bash
zellij list-sessions                       # list all sessions
zellij list-sessions --json                # JSON output
zellij kill-session my-session             # kill one session
zellij kill-all-sessions                   # kill everything
```

### Creating a headless session

```bash
zellij attach "$SESSION" --create-background 2>/dev/null
zellij list-sessions | grep -qx "$SESSION" || { echo "Session creation failed"; exit 1; }
export ZELLIJ_SESSION_NAME="$SESSION"
```

Always verify — `--create-background` can silently fail.

### Targeting from outside

```bash
export ZELLIJ_SESSION_NAME="my-session"
zellij action list-panes   # now targets my-session
```

From inside zellij, `$ZELLIJ_SESSION_NAME` and `$ZELLIJ_PANE_ID` are set automatically.

---

## Driving Coding Agents

The most common orchestration pattern: launch an agent in a pane, send prompts, monitor output.

### Reuse an existing shell pane (preferred)

```bash
PANE=$(ZELLIJ_SESSION_NAME="$SESSION" zellij action list-panes --json --all \
  | jq -r '.[] | select(.terminal_command == null and .is_plugin == false and .exited == false) | "terminal_" + (.id|tostring)' \
  | head -1)

if [ -z "$PANE" ]; then
  PANE=$(ZELLIJ_SESSION_NAME="$SESSION" zellij run -n "agent" -- pi --extension roundtable)
else
  ZELLIJ_SESSION_NAME="$SESSION" zellij action write-chars -p "$PANE" "pi --extension roundtable"
  ZELLIJ_SESSION_NAME="$SESSION" zellij action send-keys -p "$PANE" "Enter"
fi
```

### Launch in a new pane

```bash
PANE=$(zellij run -n "pi" -- pi "implement feature X")
```

### Sending prompts to a running agent

```bash
# Short prompt
zellij action write-chars -p "$PANE" "implement the scoring module"
zellij action send-keys -p "$PANE" "Enter"

# Long prompt — use paste instead
zellij action paste -p "$PANE" "Analyze the results pipeline. Consider:
1. Per-employee vs aggregate data shapes
2. Shared fetch vs per-guide fetch
3. Scoring math differences between guides"
zellij action send-keys -p "$PANE" "Enter"
```

### Detecting what the agent needs

| Pattern on screen | Agent is… | Send |
|---|---|---|
| `> ` or `? ` at end of last line | Waiting for input | `write-chars` + `send-keys Enter` |
| `[y/n]` or `(Y/n)` | Yes/no prompt | `write-chars "y"` + `send-keys Enter` |
| `(1) … (2) …` numbered menu | Choice prompt | `write-chars "1"` + `send-keys Enter` |
| No new output for 10+ seconds | Thinking | Wait and re-dump |
| `Error:` or stack trace | Failed | Decide: fix, retry, escalate |

### One-shot mode (simpler when you just want a result)

```bash
pi -p "list all .ts files"
claude -p "list all .ts files"
agent -p "list all .ts files"
opencode run "list all .ts files"
```

Use interactive panes when you need to monitor progress, intervene, or let a human take over.

### Agent CLI flags

| | Non-interactive | Resume | JSON output | Permission bypass |
|---|---|---|---|---|
| **pi** | `-p` | `-c`, `-r` | `--mode json` | `-nt` / `-t` |
| **claude** | `-p` | `-c`, `-r` | `--output-format json` | `--dangerously-skip-permissions` |
| **agent** | `-p` | `--continue`, `--resume` | `--output-format json` | `-f` / `--yolo` |
| **opencode** | `run` | `-c`, `-s` | `--format json` | — |
| **devin** | `-p` | `-c`, `-r` | — | `--permission-mode dangerous` |

---

## Pane Operations

### Run options

| Flag | Effect |
|---|---|
| `-c, --close-on-exit` | Close pane when command finishes |
| `-n <name>` | Name the pane (shows in list-panes) |
| `-d <right\|down>` | Split direction |
| `-f, --floating` | Open as floating pane |
| `--cwd <dir>` | Working directory |
| `--near-current-pane` | Open near focused pane |

### Management

```bash
zellij action close-pane -p "$PANE"
zellij action focus-pane-id "$PANE"
zellij action move-focus right
zellij action resize increase right -p "$PANE"
zellij action toggle-fullscreen -p "$PANE"
zellij action rename-pane -p "$PANE" "build:feature-x"
zellij action set-pane-color --fg "#00e000" --bg "#001a3a" -p "$PANE"
zellij action set-pane-color --reset -p "$PANE"
```

### Discovery

```bash
zellij action list-panes --json --all

# Find a pane by running command
PANE=$(zellij action list-panes --json \
  | jq -r '.[] | select(.terminal_command | test("make|cargo")) | "terminal_" + (.id|tostring)' \
  | head -1)
```

JSON field reference: `id` (bare int), `title`, `terminal_command`, `is_focused`, `is_floating`, `exited`, `exit_status`, `is_held`, `tab_name`, `is_plugin`, `pane_rows`, `pane_columns`.

---

## Input

| Command | Use for |
|---|---|
| `write-chars` | Typing text content |
| `send-keys` | Control keys (`Enter`, `Ctrl c`, `Ctrl d`, `Escape`) |
| `paste` | Multi-line input (bracketed paste mode) |
| `write` | Raw byte sequences |

```bash
zellij action send-keys -p "$PANE" "Ctrl c"    # interrupt
zellij action send-keys -p "$PANE" "Ctrl d"    # EOF / exit
zellij action send-keys -p "$PANE" "Ctrl a" "k" "Enter"  # chained
```

---

## Reading Output

```bash
zellij action dump-screen -p "$PANE"              # viewport snapshot
zellij action dump-screen -p "$PANE" --full        # full scrollback
zellij action dump-screen -p "$PANE" --full --path /tmp/output.txt
zellij action dump-screen -p "$PANE" | sed 's/\x1b\[[0-9;]*m//g'
```

### Subscribe (real-time stream — blocks until pane closes)

```bash
zellij subscribe -p "$PANE" -f json                # JSON events
zellij subscribe -p "$PANE" --scrollback           # include all scrollback
```

JSON shape: `{"event":"pane_update","pane_id":"terminal_1","viewport":["line1","line2"]}`

---

## Tab Management

```bash
zellij action new-tab -n "agents" --cwd /home/user/project
zellij action go-to-tab 1
zellij action go-to-tab-name "agents"
zellij action rename-tab "build" -t "$TAB"
zellij action close-tab -t "$TAB"
zellij action toggle-active-sync-tab -t "$TAB"    # broadcast input to all panes
```

---

## Monitoring Helpers

### Wait for idle (diff-based — more reliable than `sleep`)

```bash
wait_for_idle() {
  local pane="$1" stable_needed="${2:-3}" stable=0 prev=""
  while [ $stable -lt $stable_needed ]; do
    sleep 2
    curr=$(zellij action dump-screen -p "$pane" 2>/dev/null)
    if [ "$curr" = "$prev" ]; then stable=$((stable + 1))
    else stable=0; prev="$curr"; fi
  done
  echo "Pane $pane is idle"
}
```

### Supervise with change detection

```bash
supervise() {
  local pane="$1" prev="" idle=0 threshold=6
  while true; do
    curr=$(zellij action dump-screen -p "$pane" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
    if [ "$curr" != "$prev" ]; then
      echo "$curr" | tail -20
      echo "────────────────────────────────────"
      prev="$curr"; idle=0
    else
      idle=$((idle + 1))
      [ $idle -eq $threshold ] && echo "⏸ Idle ($((threshold * 2))s)" && break
    fi
    sleep 2
  done
}
```

### React to output

```bash
zellij subscribe -p "$PANE" -f json \
  | jq --unbuffered -r '.viewport[]' \
  | grep -m1 "Server running on" \
  && echo "Server is up!"
```
