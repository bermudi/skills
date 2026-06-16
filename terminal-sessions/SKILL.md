---
name: terminal-sessions
description: >
  Use this skill when terminal work needs a durable or interactive session:
  dev servers, watchers, REPLs, TUIs, prompts, readiness gates, log monitoring,
  or typed input. Do not use for ordinary one-shot shell commands, including long
  builds or tests, unless they require interactive control or later inspection.
---

# Terminal Sessions

Use `boo` only when terminal state has to survive beyond a single command invocation. If a command simply runs to completion, run it directly with bash.

Output is parsed through a real terminal emulator, so `peek` returns what a human attached to the terminal would see — colors, cursor movement, alternate screens, and the rest.

## Route before you run

- **Direct shell:** one-shot builds, tests, linters, codegen, searches, scripts, and any command where final stdout/stderr/exit code is enough.
- `boo`: dev servers, watchers, daemons, REPLs, TUIs, command prompts, or programs that need typed input.
- `boo`: commands that need a readiness gate before other work proceeds, then keep running while you edit/test elsewhere.
- `boo`: sessions you need to inspect later with terminal screen state or scrollback.
- `boo`: multiple independent terminal jobs that need continued monitoring; use one session per job.

## Core loop

1. Pick a unique, purpose-specific session name.
2. Start detached: `boo new <name> -d -- <command>`.
3. Prefer a readiness gate: `boo wait <name> --text '<ready marker>' --timeout <duration>`.
4. Use `boo peek <name>` for current screen state; use `boo peek <name> --scrollback` for history.
5. Send input only when needed: `boo send <name> --text '<literal text>' --enter` or `boo send <name> --key C-c`.
6. Kill sessions when they are no longer needed: `boo kill <name>`.

## Commands

The commands used most often are `new`, `wait`, `peek`, `send`, and `kill` (`ls` and `rename` are for housekeeping). Run `boo help <command>` for canonical flags.

A few details worth knowing up front:

- `boo new <name> -d -- <command>` prints the session name to stdout, so `NAME=$(boo new "dev-$$" -d -- bun run dev)` captures the exact name.
- Commands taking `<name>` accept a unique prefix. Pick names that will not become ambiguous.
- Sessions run with `TERM=xterm-256color`, so colors and cursor control render correctly.

## Recipes

### Long-running server

Start detached, gate on readiness, work elsewhere, then inspect or kill as needed.

```bash
SESSION=$(boo new "dev-$$" -d -- bun run dev)
boo wait "$SESSION" --text 'localhost:' --timeout 30s

# Later, when something breaks or you need logs:
boo peek "$SESSION" --scrollback | tail -80

# Done:
boo kill "$SESSION"
```

- **Readiness gate is load-bearing.** Do not sleep blindly or race the server; wait on the URL/ready string it prints.
- **Use `peek --scrollback` as the debug lens.** HMR events, compile errors, and request logs live there.
- **Restart when HMR is not enough.** `.env`, config files, `tsconfig`, and port-binding changes usually need a full restart.
- **Always clean up.** Leaked dev servers hold ports and PTYs.

### Interrupt a running session

`--key` sends named keys — `C-c` stops a runaway server, prompt, or REPL command:

```bash
boo send "$SESSION" --key C-c          # stop it
boo wait "$SESSION" --idle --timeout 5s
boo peek "$SESSION" --scrollback       # see where it stopped
boo kill "$SESSION"
```

Named keys: `C-a`–`C-z`, `Enter`, `Tab`, `Escape`, arrows, `Home`/`End`.

### Drive an interactive program

```bash
SESSION=$(boo new "py-$$" -d -- uv run python)
boo wait "$SESSION" --text '>>>' --timeout 10s
boo send "$SESSION" --text 'import os' --enter
boo wait "$SESSION" --text '>>>' --timeout 10s
boo send "$SESSION" --text 'os.getcwd()' --enter
boo wait "$SESSION" --text '>>>' --timeout 10s
boo peek "$SESSION"
boo kill "$SESSION"
```

### Parallel terminal work

Use one session per durable process. Do not use this pattern just to parallelize ordinary one-shot commands.

```bash
DEV=$(boo new "dev-$$" -d -- bun run dev)
WORKER=$(boo new "worker-$$" -d -- bun run worker)

boo wait "$DEV" --text 'localhost:' --timeout 30s
boo wait "$WORKER" --text 'ready' --timeout 30s

boo peek "$DEV" --scrollback | tail -40
boo peek "$WORKER" --scrollback | tail -40

boo kill "$DEV"
boo kill "$WORKER"
```

### Handle readiness timeout explicitly

```bash
SESSION=$(boo new "dev-$$" -d -- bun run dev)
boo wait "$SESSION" --text 'localhost:' --timeout 30s
status=$?

if [ "$status" -eq 4 ]; then
  boo peek "$SESSION" --scrollback | tail -100
  boo kill "$SESSION"
  exit 1
elif [ "$status" -ne 0 ]; then
  boo kill "$SESSION"
  exit "$status"
fi
```

## Gotchas

- **One attached client per session.** Always use `-d`, never `attach`.
- **`--text` is literal.** No shell escaping, no implicit Enter. Add `--enter` when the program needs Enter, and expand variables yourself (e.g. `"$(pwd)"`, not `'$HOME'`).
- **`--key` and `--text` are separate calls.** Cannot combine in one `boo send`.
- **`peek` shows the screen, not a log.** Use `--scrollback` for history.
- **`wait --text` matches the rendered screen only** (not scrollback).
- **`wait --idle` is quietness, not completion.** It exits after 2 seconds with no output.
- **Avoid blind sleeps for readiness.** Wait on the program's actual ready text whenever it has one.
- **Session names must be unique prefixes.** `build` and `builder` makes `bu` ambiguous.
- **Exit code 4 = timeout.** Treat it as a real branch: inspect scrollback, adjust the readiness marker, or stop the session.
- **Clean up.** Always `boo kill` when done. Leaked sessions hold PTYs and processes.
