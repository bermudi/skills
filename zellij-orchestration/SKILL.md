---
name: zellij-orchestration
description: Use zellij as a process orchestration layer — launch long-running commands, monitor their output, send input, manage panes and tabs, and drive interactive programs including coding agents. Use this skill whenever the task involves zellij panes, terminal orchestration, running agents in zellij, monitoring processes, or automating terminal interaction. Triggers on "zellij", "pane", "terminal orchestration", "run in a pane", "launch agent", "monitor output", "send keys", "dump screen", "block until exit", "subscribe to pane".
---

# Zellij Orchestration

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

**Short-lived commands exit before you can read them.** `pi -p "..."` in a pane finishes fast; by the time you `dump-screen`, zellij may have cleaned the pane. Redirect output to a file, or use `dump-screen --full` immediately after launch. Do NOT rely on `--block-until-exit-success` for output capture — it blocks until exit 0 and **hangs forever on non-zero**.

**Don't stomp on active sessions.** Never assume an existing zellij session is disposable. If testing, create a dedicated throwaway session. If the user says "use zellij session X", that's their active workspace — treat it with care.

---

## Core Primitives

| Primitive | Command | Returns |
|---|---|---|
| **Run command in new pane** | `zellij run -- <cmd>` | `terminal_<id>` |
| **List all panes** | `zellij action list-panes --json --all` | JSON array |
| **Read pane output** | `zellij action dump-screen -p <id>` | Text (viewport) |
| **Send keystrokes** | `zellij action send-keys -p <id> "Enter"` | — |
| **Send text** | `zellij action write-chars -p <id> "text"` | — |
| **Block until exit** | `zellij run --block-until-exit-success -- <cmd>` | Exit code |
| **Stream output live** | `zellij subscribe -p <id> -f json` | JSON events |

---

## Session Management

There is no `zellij session-list` — it doesn't exist. Use `list-sessions` (alias `ls`).

```bash
zellij list-sessions                       # list all sessions
zellij list-sessions --json                # JSON output
zellij kill-session my-session             # kill one session
zellij kill-all-sessions                   # kill everything
```

### Creating a headless session

```bash
zellij attach my-session --create-background 2>/dev/null
```

**Always verify it actually started** — `--create-background` can silently fail. Anchor the grep to avoid substring matches (e.g. `dev` matching `dev-nom035`):
```bash
zellij attach "$SESSION" --create-background 2>/dev/null
zellij list-sessions | grep -qx "$SESSION" || { echo "Session creation failed"; exit 1; }
export ZELLIJ_SESSION_NAME="$SESSION"
```

---

## Targeting a Session

**From inside zellij:** Just works — `$ZELLIJ_SESSION_NAME` is set automatically. Each pane also gets `$ZELLIJ_PANE_ID` (e.g. `terminal_3`) for self-referential commands.

**From outside zellij:**
```bash
export ZELLIJ_SESSION_NAME="my-session"
zellij action list-panes   # targets my-session

# Or inline
ZELLIJ_SESSION_NAME="my-session" zellij action dump-screen -p terminal_1
```

---

## Driving Coding Agents

This is the most common use of zellij orchestration: launching an agent in a pane, sending it prompts, and monitoring its output — while a human watches.

**Key disambiguation:** When the user says "run X in zellij", they mean launch a separate agent process in a pane and drive it remotely. This is different from using your own tools directly. You are piloting a separate program through a terminal pane.

### Option 1: Reuse an existing shell pane (preferred)

When the user says "use zellij session X", they usually want you to run a command in an existing pane — not split their screen with a new one. Find an idle shell and type into it:

```bash
# Find an idle shell pane (not exited, not held, not a plugin)
PANE=$(ZELLIJ_SESSION_NAME="$SESSION" zellij action list-panes --json --all \
  | jq -r '.[] | select(.terminal_command == null and .is_plugin == false and .exited == false) | "terminal_" + (.id|tostring)' \
  | head -1)

if [ -z "$PANE" ]; then
  # No idle pane — create a new one
  PANE=$(ZELLIJ_SESSION_NAME="$SESSION" zellij run -n "agent" -- pi --extension roundtable)
else
  # Reuse the idle shell
  ZELLIJ_SESSION_NAME="$SESSION" zellij action write-chars -p "$PANE" "pi --extension roundtable"
  ZELLIJ_SESSION_NAME="$SESSION" zellij action send-keys -p "$PANE" "Enter"
fi
```

### Option 2: Launch in a new pane

Use when you need a fresh isolated environment or there's no idle pane to reuse:

```bash
PANE=$(zellij run -n "pi" -- pi "implement feature X")
```

### Launching specific agents

```bash
# pi with extensions
PANE=$(zellij run -n "pi" -- pi --extension roundtable)

# pi in an existing pane
zellij action write-chars -p "$PANE" "pi --extension roundtable"
zellij action send-keys -p "$PANE" "Enter"

# claude
PANE=$(zellij run -n "claude" -- claude --dangerously-skip-permissions)

# Multiple agents in parallel tabs
for i in 1 2 3; do
  zellij action new-tab -n "agent-$i"
  zellij run -n "worker-$i" -- pi "task $i"
done
```

### Sending prompts to a running agent

```bash
# Wait for agent to be at a prompt (> or ? at end of screen output)
# Then send your prompt
zellij action write-chars -p "$PANE" "implement the scoring module using discriminated unions"
zellij action send-keys -p "$PANE" "Enter"
```

For long prompts, use `paste` instead of `write-chars`:
```bash
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

### Monitoring a running agent

Poll with `dump-screen` to track progress. Use the `wait_for_idle` or `supervise` helpers from Monitoring Scripts below.

### When to use non-interactive mode instead

Most agents support `-p`/`--print` for one-shot use — simpler than driving a TUI when you just want a result:

```bash
pi -p "list all .ts files"             # pi
claude -p "list all .ts files"         # claude
devin -p "list all .ts files"          # devin
opencode run "list all .ts files"      # opencode
```

Use interactive panes when you need to monitor progress, intervene mid-task, handle unexpected prompts, or let a human take over.

Read `references/coding-agents.md` when launching or configuring a specific coding agent (pi, claude, agent, opencode, devin) — it has per-agent CLI flags, output formats, session resume, and a comparison table.

---

## Launching Processes

```bash
PANE=$(zellij run -n "build" -- make)
```

### Blocking: run and wait for exit code

```bash
zellij run --block-until-exit -- make test           # any exit status
zellij run --block-until-exit-success -- make test    # only exit 0
zellij run --block-until-exit-failure -- tail -f err  # only non-zero
```

The old `--blocking` flag also exists (waits until pane closes).

### Short-lived commands

For commands that exit quickly (tests, one-shot scripts, `pi -p`), the pane closes before you can read output. Strategies:

```bash
# Option 1: Redirect to file, read after (most reliable)
zellij run -n "test" -- bash -c 'pi -p "list files" > /tmp/pi-output.txt 2>&1'
# then: cat /tmp/pi-output.txt

# Option 2: Block until exit (any status), then dump scrollback
zellij run --block-until-exit -n "test" -- pi -p "list files"
zellij action dump-screen -p terminal_N --full  # race: pane may be gone

# Option 3: --close-on-exit off + dump-screen --full
zellij run -n "test" -- bash -c 'pi -p "list files"; echo "---DONE---"'
# poll dump-screen until you see ---DONE---
```

**Warning:** `--block-until-exit-success` hangs forever on non-zero exit codes. Use `--block-until-exit` to block on any exit.

### Pane options

| Flag | Effect |
|---|---|
| `-c, --close-on-exit` | Close pane when command finishes |
| `-n <name>` | Name the pane (shows in list-panes) |
| `-d <right\|down>` | Split direction |
| `-f, --floating` | Open as floating pane |
| `-i, --in-place` | Replace current pane (suspends it) |
| `--cwd <dir>` | Working directory |
| `-s, --start-suspended` | Wait for ENTER before running |
| `--near-current-pane` | Open near focused pane |

### Floating pane geometry

```bash
zellij run -f --x 10% --y 5 --width 80% --height 30% -n "logs" -- tail -f app.log
```

All geometry args accept bare integers or percent (e.g. `10%`). Pin with `--pinned true`.

---

## Reading Output

### Dump screen (snapshot)

```bash
zellij action dump-screen -p "$PANE"              # current viewport
zellij action dump-screen -p "$PANE" --full        # full scrollback
zellij action dump-screen -p "$PANE" --full --path /tmp/output.txt
zellij action dump-screen -p "$PANE" | sed 's/\x1b\[[0-9;]*m//g'  # strip ANSI
```

### Subscribe (real-time stream)

```bash
zellij subscribe -p "$PANE"                        # raw text
zellij subscribe -p "$PANE" -f json                # JSON events
zellij subscribe -p "$PANE" --scrollback           # include all scrollback
zellij subscribe -p "$PANE" --scrollback 100       # last 100 lines
zellij subscribe -p "$PANE" --ansi                 # preserve ANSI
```

Blocking — stays open until pane closes or you kill it.

Subscribe JSON shape:
```json
{"event":"pane_update","is_initial":true,"pane_id":"terminal_1","viewport":["line1","line2"],"scrollback":["..."]}
```

### When to use which

| Use case | Tool |
|---|---|
| Check what's on screen right now | `dump-screen` |
| Wait for specific output to appear | `subscribe` piped to `grep`/`jq` |
| Capture full output after exit | `dump-screen --full` |
| Monitor reactively | `subscribe -f json` |

---

## Sending Input

| Command | What it does | Use for |
|---|---|---|
| `write-chars` | Sends literal characters (like typing) | Text content |
| `send-keys` | Sends named key events | Control keys (`Enter`, `Ctrl c`, etc.) |
| `paste` | Bracketed paste mode | Multi-line input |
| `write` | Raw bytes | Binary sequences |

```bash
# Type text and submit
zellij action write-chars -p "$PANE" "yes, proceed"
zellij action send-keys -p "$PANE" "Enter"

# Paste multi-line
zellij action paste -p "$PANE" "line 1
line 2
line 3"

# Common keys
zellij action send-keys -p "$PANE" "Ctrl c"    # interrupt
zellij action send-keys -p "$PANE" "Ctrl d"    # EOF / exit
zellij action send-keys -p "$PANE" "Escape"
zellij action send-keys -p "$PANE" "Ctrl a" "k" "Enter"  # multiple
```

---

## Discovery

```bash
# Full JSON dump
zellij action list-panes --json --all

# Find a pane by running command
PANE=$(zellij action list-panes --json \
  | jq -r '.[] | select(.terminal_command | test("make|cargo")) | "terminal_" + (.id|tostring)' \
  | head -1)
```

### JSON field reference

The `id` field is a **bare integer**. Commands accept both `terminal_3` and bare `3`.

| Field | Type | Notes |
|---|---|---|
| `id` | int | Pane ID. Use `"terminal_" + (.id\|tostring)` for commands |
| `title` | string | Pane title (updates dynamically for agents) |
| `terminal_command` | string? | Running command (null for shells, plugins) |
| `pane_command` | string? | Shell binary (e.g. `/usr/bin/bash`) |
| `pane_cwd` | string? | Working directory |
| `is_focused` | bool | Currently focused |
| `is_floating` | bool | Floating pane |
| `exited` | bool | Process has exited |
| `exit_status` | int? | Exit code if exited |
| `is_held` | bool | Exited but pane kept open |
| `tab_name` | string | Parent tab name |
| `tab_id` | int | Parent tab ID |
| `is_plugin` | bool | Plugin vs terminal |
| `pane_rows`, `pane_columns` | int | Size |

---

## Pane Management

```bash
zellij action close-pane -p "$PANE"
zellij action focus-pane-id "$PANE"
zellij action move-focus right                    # or left/up/down
zellij action move-focus-or-tab right             # crosses tab boundary
zellij action move-pane right -p "$PANE"
zellij action resize increase right -p "$PANE"    # or decrease + direction
zellij action toggle-fullscreen -p "$PANE"
zellij action toggle-pane-embed-or-floating -p "$PANE"
zellij action rename-pane -p "$PANE" "build:feature-x"
zellij action set-pane-color --fg "#00e000" --bg "#001a3a" -p "$PANE"
zellij action set-pane-color --reset -p "$PANE"
```

---

## Tab Management

```bash
TAB=$(zellij action new-tab -n "agents" --cwd /home/user/project)
zellij action go-to-tab 1
zellij action go-to-tab-name "agents"
zellij action go-to-next-tab
zellij action rename-tab "build" -t "$TAB"
zellij action close-tab -t "$TAB"
zellij action toggle-active-sync-tab -t "$TAB"    # broadcast to all panes
zellij action move-tab right
```

---

## Layout Management

```bash
zellij action override-layout mylayout                         # reset to layout
zellij action override-layout mylayout \
  --retain-existing-terminal-panes \
  --retain-existing-plugin-panes
zellij action override-layout --layout-string 'layout { pane }'
zellij action next-swap-layout                                # cycle layouts
zellij action previous-swap-layout
zellij action dump-layout                                     # export current layout
```

---

## Monitoring Scripts

### Wait for idle (diff-based)

Detects when a pane stops producing output. More reliable than `sleep`.

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

Prints output only when the screen changes. Stops when idle.

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

### React to output with subscribe

```bash
# Wait for specific string in viewport
zellij subscribe -p "$PANE" -f json \
  | jq --unbuffered -r '.viewport[]' \
  | grep -m1 "Server running on" \
  && echo "Server is up!"
```
