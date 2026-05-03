---
name: zellij-agent-control
description: Control coding agents running in zellij terminal panes — read their screen output, detect what they're waiting for, and send keystrokes to respond. Use this skill whenever the user wants to automate agent interaction, monitor an agent pane, unblock a running agent, script multi-agent workflows, respond to agent prompts, or do anything involving driving a terminal program through zellij. Triggers on phrases like "agent is waiting", "send a key to", "check the agent pane", "drive the agent", "automate the terminal", "zellij pane", or any request to observe and interact with a running terminal process.
---

# Zellij Agent Control

This skill gives you the ability to **observe and control terminal panes** running inside a zellij session — the key primitive for driving coding agents (Claude, aider, cursor, etc.) from another agent or script.

## Core idea

The loop is simple:
1. **Discover** which pane the agent is in
2. **Dump** the screen to read what it's displaying
3. **Decide** what to send based on what you see
4. **Send** keystrokes or text to the pane
5. **Repeat** until the task is done

All of this works via `zellij action` subcommands — no extra tooling required.

---

## Prerequisite: Targeting a zellij session

`zellij action` commands work in two modes:

### From inside zellij
When you're already inside a session, commands just work — `$ZELLIJ_SESSION_NAME` is set automatically.

### From outside zellij (the useful pattern for agent control)

**Setting `ZELLIJ_SESSION_NAME` as an env var is the key trick** — you don't need to be inside the session, you just export it and all `action` commands target that session:

```bash
export ZELLIJ_SESSION_NAME="my-session"
zellij action list-panes   # targets my-session from outside
```

Or inline per-command:
```bash
ZELLIJ_SESSION_NAME="my-session" zellij action dump-screen --pane-id terminal_1
```

This works for all `zellij action` subcommands. The `--session` flag does **not** exist on action subcommands — the env var is the only way.

### Start a background session (headless)
```bash
# Start a detached session — no terminal required
zellij attach my-session --create-background 2>/dev/null

# Verify it's running
zellij list-sessions

# Now target it from anywhere
export ZELLIJ_SESSION_NAME="my-session"
zellij action list-panes
```

---

## Step 1 — Discover panes

```bash
# List all panes with state and running command
zellij action list-panes --json --state --command --tab

# Compact human-readable view
zellij action list-panes --state --command --tab
```

The JSON output looks like:
```json
[
  {
    "id": "terminal_3",
    "title": "claude",
    "tab_name": "agents",
    "is_focused": false,
    "is_floating": false,
    "running_command": "claude",
    ...
  }
]
```

**Key fields:** `id` (e.g. `terminal_3`), `title`, `running_command`, `is_focused`.

Save the pane ID of the target agent — you'll pass it to every subsequent command.

```bash
AGENT_PANE=$(ZELLIJ_SESSION_NAME="$SESSION" zellij action list-panes --json \
  | jq -r '.[] | select(.running_command | test("claude|aider|opencode|pi")) | .id' \
  | head -1)
echo "Agent pane: $AGENT_PANE"
```

**Tip:** The pane `title` updates to reflect what the agent is working on (e.g. `"OC | Create and run hello.py"`) — useful for monitoring multiple agents.

---

## Step 2 — Read the screen

```bash
# Dump current viewport of a specific pane
zellij action dump-screen --pane-id "$AGENT_PANE"

# Include full scrollback (everything the pane has ever printed)
zellij action dump-screen --pane-id "$AGENT_PANE" --full

# Save to file (useful for large outputs)
zellij action dump-screen --pane-id "$AGENT_PANE" --full --path /tmp/agent-screen.txt

# Strip ANSI escape codes for clean text
zellij action dump-screen --pane-id "$AGENT_PANE" | sed 's/\x1b\[[0-9;]*m//g'
```

### Reading the dump in bash
```bash
SCREEN=$(zellij action dump-screen --pane-id "$AGENT_PANE")
echo "$SCREEN"
```

### Common patterns to detect in the dump

| What you see | Agent is… | What to send |
|---|---|---|
| `> ` or `? ` at end of last line | Waiting for text input | `write-chars` your response, then `send-keys Enter` |
| `[y/n]` or `(Y/n)` | Asking a yes/no question | `write-chars "y"`, then `send-keys Enter` |
| `Press any key` | Paused | `send-keys "Enter"` |
| `(1) … (2) …` numbered menu | Asking you to pick | `write-chars "1"`, then `send-keys Enter` |
| Cursor blinking on empty line | Waiting for input | `write-chars` your message |
| No new output for 10+ seconds | Still thinking | Wait, then re-dump |
| `Error:` or stack trace | Crashed | Decide: fix, retry, or escalate |

---

## Step 3 — Send input

### Send text (like typing it)
```bash
# Write characters — does NOT send Enter automatically
zellij action write-chars --pane-id "$AGENT_PANE" "yes, continue with that approach"

# To submit the text, send Enter separately
zellij action send-keys --pane-id "$AGENT_PANE" "Enter"
```

> **⚠️ A newline (`\n`) in `write-chars` is NOT the same as pressing Enter.** A bare newline (ASCII 10) may just move the cursor down without submitting the line. Agents running in raw terminal mode (pi, claude, aider, etc.) wait for the actual Enter key event. Always use `send-keys Enter` to submit input — never rely on `\n` inside `write-chars`.

### Send special keys
```bash
# Common keys
zellij action send-keys --pane-id "$AGENT_PANE" "Enter"
zellij action send-keys --pane-id "$AGENT_PANE" "Ctrl c"    # interrupt
zellij action send-keys --pane-id "$AGENT_PANE" "Ctrl d"    # EOF / exit
zellij action send-keys --pane-id "$AGENT_PANE" "Ctrl z"    # suspend
zellij action send-keys --pane-id "$AGENT_PANE" "Escape"
zellij action send-keys --pane-id "$AGENT_PANE" "Tab"
zellij action send-keys --pane-id "$AGENT_PANE" "Up"
zellij action send-keys --pane-id "$AGENT_PANE" "Down"
zellij action send-keys --pane-id "$AGENT_PANE" "F1"

# Multiple keys in one call
zellij action send-keys --pane-id "$AGENT_PANE" "Ctrl a" "k" "Enter"
```

### Paste multi-line text (bracketed paste)
```bash
# Use paste for multi-line inputs — it wraps text in bracketed paste mode
# so the agent's readline doesn't interpret newlines as submits mid-paste
zellij action paste --pane-id "$AGENT_PANE" "line 1
line 2
line 3"
```

### Write raw bytes
```bash
# Rarely needed, but available for binary sequences
zellij action write --pane-id "$AGENT_PANE" 121 101 115 10   # "yes\n" as ASCII bytes
```

---

## Step 4 — The watch loop

A simple polling loop in bash:

```bash
#!/usr/bin/env bash
# wait-and-respond.sh
# Monitors a pane and automatically responds to prompts

AGENT_PANE="${1:-terminal_3}"
POLL_INTERVAL=2   # seconds between screen checks
MAX_WAIT=120      # give up after this many seconds
ELAPSED=0

echo "Watching pane $AGENT_PANE..."

while [ $ELAPSED -lt $MAX_WAIT ]; do
  SCREEN=$(zellij action dump-screen --pane-id "$AGENT_PANE" 2>/dev/null \
    | sed 's/\x1b\[[0-9;]*m//g')   # strip color codes

  LAST_LINE=$(echo "$SCREEN" | tail -3 | tr '\n' ' ')
  echo "[${ELAPSED}s] Last line: $LAST_LINE"

  # Detect common prompts and respond
  if echo "$LAST_LINE" | grep -qiE '\[y/n\]|\(Y/n\)'; then
    echo "→ Yes/No prompt detected, answering y"
    zellij action write-chars --pane-id "$AGENT_PANE" "y"
    zellij action send-keys --pane-id "$AGENT_PANE" "Enter"

  elif echo "$LAST_LINE" | grep -qiE 'press (enter|any key)'; then
    echo "→ 'Press key' prompt, sending Enter"
    zellij action send-keys --pane-id "$AGENT_PANE" "Enter"

  elif echo "$LAST_LINE" | grep -qiE '> $|> $|\? $'; then
    echo "→ Input prompt, needs human decision — exiting watch loop"
    break

  elif echo "$SCREEN" | grep -qiE 'task complete|done|finished'; then
    echo "→ Task appears complete!"
    break
  fi

  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
done
```

---

## Patterns for common agent workflows

### Launch an agent in a new pane, capture its pane ID

```bash
# Start agent in a new split pane
AGENT_PANE=$(zellij action new-pane --direction down --name "claude-agent" \
  -- claude --dangerously-skip-permissions)
echo "Agent started in pane: $AGENT_PANE"
```

### Launch in a named floating pane

```bash
AGENT_PANE=$(zellij action new-pane --floating --name "agent-1" \
  --cwd /home/user/project \
  -- pi "implement feature X")
```

### Wait for the agent to become idle, then send a follow-up

```bash
wait_for_idle() {
  local pane="$1"
  local prev_screen=""
  local stable_count=0
  local needed=3   # screen must be unchanged this many consecutive checks

  while [ $stable_count -lt $needed ]; do
    sleep 2
    curr=$(zellij action dump-screen --pane-id "$pane")
    if [ "$curr" = "$prev_screen" ]; then
      stable_count=$((stable_count + 1))
    else
      stable_count=0
      prev_screen="$curr"
    fi
  done
  echo "Pane $pane appears idle"
}

wait_for_idle "$AGENT_PANE"
zellij action write-chars --pane-id "$AGENT_PANE" "now write the tests"
zellij action send-keys --pane-id "$AGENT_PANE" "Enter"
```

### Scrape and store the agent's final output

```bash
# When the agent is done, grab the full scrollback and save it
zellij action dump-screen --pane-id "$AGENT_PANE" --full \
  | sed 's/\x1b\[[0-9;]*m//g' \
  > /tmp/agent-output-$(date +%s).txt
```

### Run multiple agents in parallel tabs

```bash
for i in 1 2 3; do
  zellij action new-tab --name "agent-$i"
  pane=$(zellij action new-pane -- pi "task number $i")
  echo "agent-$i running in $pane"
done
```

---

## Useful tab and session management

```bash
# Create a dedicated tab for agents
zellij action new-tab --name "agents"

# Focus a pane by ID
zellij action go-to-tab-by-id <tab-id>

# Rename a pane to track what it's doing
zellij action rename-pane --pane-id "$AGENT_PANE" "claude:feature-x"

# Dump the current layout to reproduce it later
zellij action dump-layout

# Save session state to disk
zellij action save-session
```

---

## Limitations and gotchas

**Screen dump is the viewport, not a structured API.** You're reading rendered terminal output — the same thing a human would see. This means:
- ANSI escape codes for colors/styles are present unless you strip them
- Cursor position isn't told to you directly — infer from content
- Output may be truncated if the terminal is narrow (use `--full` for scrollback)

**Timing matters.** Agents think for a while before responding. Don't poll too aggressively (2–5 second intervals work well). The "stable screen" heuristic (check that the screen hasn't changed across N polls) is more reliable than fixed waits.

**write-chars vs send-keys:**
- `write-chars` sends literal characters, like typing. Use it for the text content only.
- `send-keys` sends named keys (`Enter`, `Ctrl c`, `F1`, etc.). Use it for the actual Enter key — never rely on `\n` inside `write-chars` to submit input. Agents in raw terminal mode need the real key event.
- For multi-line input, prefer `paste` to avoid readline interpreting embedded newlines.

**Pane IDs change between sessions.** Don't hardcode `terminal_3` — always discover pane IDs dynamically with `list-panes`.

**Background sessions start with a very narrow terminal** (typically 25 columns). Content will word-wrap aggressively. This doesn't stop the agent from working, but the screen dumps will look garbled. If you need clean output, resize the pane after creation:
```bash
ZELLIJ_SESSION_NAME="$SESSION" zellij action resize --pane-id "$AGENT_PANE" increase right
# Or launch with explicit dimensions via a layout file
```

**`ZELLIJ_SESSION_NAME` env var is required** when not inside zellij. There is no `--session` flag on `action` subcommands — the env var is the only external targeting mechanism.
