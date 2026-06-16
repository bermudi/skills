# boo — Terminal Session Automation

A terminal multiplexer with automation primitives: `send`, `peek`, and `wait`. Use it when `terminal-sessions` has routed the task to a durable or interactive terminal session. Output is parsed through a real terminal emulator, so `peek` returns what a human attached to the terminal would see.

> Read this before driving the first `boo` session in a task. Do not use `boo` for ordinary one-shot commands where final stdout/stderr/exit code is enough.

## When to use boo

- Dev servers, file watchers, daemons, and other processes that should keep running while you work.
- Interactive programs: REPLs, prompts, shells, TUIs, debuggers, CLIs awaiting input.
- Readiness gates: start a process, wait for a printed ready marker, then continue with other work.
- Later inspection: read current terminal state or scrollback after a process has kept running.
- Parallel long-lived terminal jobs, one session per job.

Do **not** use `boo` for simple one-shot commands, including long builds/tests/lints, unless they need interactive control or must keep running for later inspection. Run those directly with bash.

## Core Loop

```
1. boo new <name> -d -- <command>                 # create detached session
2. boo wait <name> --text '<ready>' --timeout 30s # gate on readiness when possible
3. boo peek <name>                                # read current screen
4. repeat send/wait/peek as needed
5. boo kill <name>                                # clean up when done
```

Always create sessions detached (`-d`) when automating. Do not attach from an agent.

## Commands

Run `boo help <command>` for canonical flags. The commands used most often are `new`, `wait`, `peek`, `send`, and `kill` (`ls` and `rename` are for housekeeping).

Two details worth knowing up front:

- `boo new <name> -d -- <command>` prints the session name to stdout, so `NAME=$(boo new "dev-$$" -d -- bun run dev)` captures the exact name.
- Commands taking `<name>` accept a unique prefix. Pick names that will not become ambiguous.
- Sessions run with `TERM=xterm-256color`, so colors and cursor control render correctly.

The recipes below show these commands in real usage.

## Recipes

### Long-Running Server

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

### Interrupt a Running Session

`--key` sends named keys — `C-c` stops a runaway server, prompt, or REPL command:

```bash
boo send "$SESSION" --key C-c          # stop it
boo wait "$SESSION" --idle --timeout 5s
boo peek "$SESSION" --scrollback       # see where it stopped
boo kill "$SESSION"
```

Named keys: `C-a`–`C-z`, `Enter`, `Tab`, `Escape`, arrows, `Home`/`End`. `--key` and `--text` can't combine in one call — use two.

### Drive an Interactive Program

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

### Parallel Terminal Work

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

### Handle Readiness Timeout Explicitly

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

- **No `--enter` means no Enter.** `--text` sends exactly the bytes given.
- **`--key` and `--text` are separate calls.** Cannot combine in one `boo send`.
- **`--text` has no escaping.** `'$HOME'` sends literal `$HOME`. Expand yourself: `"$(pwd)"`.
- **One attached client per session.** Always use `-d`, never `attach`.
- **`peek` shows the screen, not a log.** Use `--scrollback` for history.
- **`wait --text` matches the rendered screen only** (not scrollback).
- **`wait --idle` is quietness, not completion.** It exits after 2 seconds with no output.
- **Session names must be unique prefixes.** "build" and "builder" makes `bu` ambiguous.
- **Exit code 4 = timeout.** Handle it explicitly.
- **Clean up.** Always `boo kill` when done. Leaked sessions hold PTYs and processes.
