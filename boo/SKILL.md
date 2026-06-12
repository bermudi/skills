---
name: boo
description: >
  Use when driving interactive terminal programs, running commands in
  detached sessions, automating CLI workflows, or managing persistent
  terminal sessions. Triggers on "run in background", "terminal session",
  "multiplexer", "send keys to terminal", "read terminal output", or
  any task involving interactive CLI programs that need scripted control.

license: MIT
---

# boo — Terminal Session Automation

boo is a terminal multiplexer with first-class automation primitives: `send`, `peek`, `wait`. Use it to drive interactive programs (shells, REPLs, TUIs, build tools) from scripts or agent sessions. Every session's output is parsed through a real terminal emulator (libghostty), so `peek` returns exactly what a human would see — not a raw byte log.

## When to use boo

- Running commands that produce output over time (builds, test suites, servers)
- Driving interactive programs (REPLs, prompts, TUIs) that need typed input
- Reading terminal screen state without a TTY attached
- Any "run this, wait for X, read the result" workflow

Do **not** use boo for simple one-shot commands — just run them directly with bash.

## Core loop

```
1. boo new <name> -d -- <command>    # create detached session
2. boo wait <name> --idle            # let output settle
3. boo peek <name>                   # read the screen
4. (repeat send/wait/peek as needed)
5. boo kill <name>                   # clean up
```

Always create sessions detached (`-d`) — you are not attaching interactively.

## Commands

### Session management

```bash
boo new <name> -d -- <command>     # new detached session running command
boo new <name> -d -- bash          # new detached shell session
boo ls [--json]                     # list sessions
boo kill <name>                     # end a session
boo kill --all                      # end every session
boo rename <name> <new-name>       # rename a session
```

- Without `-- <command>`, the session runs `$SHELL`.
- `boo new -d` prints the session name to stdout.
- Commands accepting `<name>` also accept unique prefixes (e.g., `boo peek bu` matches "build").
- Sessions run with `TERM=xterm-256color`.

### Sending input — `boo send`

```bash
boo send <name> --text 'make test' --enter   # type text + press Enter
boo send <name> --key C-c                     # send Ctrl-C
boo send <name> --key Enter                   # press Enter
boo send <name> --key Up,Enter                # multiple keys
```

**Critical**: `--text` is **literal** — no escape processing, no implicit newline. You must add `--enter` explicitly when the input is a command. `--key` and `--text` cannot be combined in one call; use two `boo send` invocations.

Named keys: `Enter`, `Tab`, `Escape`, `Space`, `Backspace`, `Up`, `Down`, `Left`, `Right`, `Home`, `End`, `C-a` through `C-z`.

### Reading output — `boo peek`

```bash
boo peek <name>                  # current screen
boo peek <name> --scrollback     # screen + scrollback history
boo peek <name> --json           # structured output with cursor/metadata
```

Returns the **rendered screen** — what a human would see right now — reconstructed from terminal state, not a raw byte stream. `--json` outputs:

```json
{
  "session": "build",
  "title": "make",
  "rows": 24,
  "cols": 80,
  "cursor": {"row": 5, "col": 0},
  "screen": "...rendered text..."
}
```

### Waiting — `boo wait`

```bash
boo wait <name> --text 'PASS' --timeout 2m    # until screen contains text
boo wait <name> --idle                         # until output settles (2s quiet)
boo wait <name> --idle --timeout 30s           # settle with timeout
```

Replaces sleep-and-poll loops. `--text` does a plain substring match against the rendered screen. `--idle` waits until no output for 2 seconds. Always set `--timeout` to avoid hanging.

**Exit codes**: `0` condition met, `1` error, `3` no such session, `4` timed out.

## Patterns

### Run a command and capture output

```bash
boo new build -d -- make test
boo wait build --text 'PASS' --timeout 5m
boo peek build --scrollback
boo kill build
```

### Drive an interactive program

```bash
boo new py -d -- python3
boo wait py --idle
boo send py --text 'import os' --enter
boo wait py --text '>>>'
boo send py --text 'os.getcwd()' --enter
boo wait py --text '>>>'
boo peek py
boo kill py
```

### Check if a program finished successfully

```bash
boo wait build --idle --timeout 10m
if boo peek build --scrollback | grep -q 'BUILD SUCCESSFUL'; then
  # success
else
  # failure — peek scrollback for errors
fi
```

### Multiple sessions for parallel work

```bash
boo new lint -d -- npm run lint
boo new test -d -- npm run test
boo wait lint --idle --timeout 2m
boo wait test --idle --timeout 5m
boo peek lint
boo peek test
boo kill --all
```

## Gotchas

- **No `--enter` means no Enter.** `--text` sends exactly the bytes given. If the program waits for input, you probably forgot `--enter`.
- **`--key` and `--text` are separate calls.** You cannot combine them in one `boo send`.
- **`--text` has no escaping.** `boo send s --text '$HOME'` sends literal `$HOME`, not the expanded variable. Expand in the shell yourself if needed: `boo send s --text "$(pwd)"`.
- **One attached client per session.** Attaching steals the previous client. For agent use, always use `-d` and never `attach`.
- **`peek` shows the screen, not a log.** Long-running output scrolls off. Use `--scrollback` to see history, or `--json` for structured access.
- **`wait --text` matches the rendered screen only** (not scrollback) unless the text is currently visible.
- **Session names must be unique prefixes.** If you have "build" and "builder", `boo peek bu` is ambiguous — boo will error. Pick distinct names.
- **Exit code 4 from `wait` means timeout.** Handle it — don't treat it as a generic error.
- **Clean up.** Always `boo kill` sessions when done. Leaked sessions hold PTYs and processes.
