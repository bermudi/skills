# boo — Terminal Session Automation

A terminal multiplexer with automation primitives: `send`, `peek`, `wait`. Drive interactive programs (shells, REPLs, TUIs, build tools) from scripts. Output is parsed through a real terminal emulator — `peek` returns exactly what a human would see.

> Loaded on demand from the `sub-tasks` skill. Read this before driving your first `boo` session.

## When to use boo

- Commands that produce output over time (builds, test suites, servers)
- Interactive programs (REPLs, prompts, TUIs) that need typed input
- Reading terminal screen state without a TTY attached
- Any "run this, wait for X, read the result" workflow

Do **not** use boo for simple one-shot commands — just run them directly with bash.

## Core Loop

```
1. boo new <name> -d -- <command>    # create detached session
2. boo wait <name> --idle            # let output settle
3. boo peek <name>                   # read the screen
4. (repeat send/wait/peek as needed)
5. boo kill <name>                   # clean up
```

Always create sessions detached (`-d`) — you are not attaching interactively.

## Commands

Run `boo help <command>` for canonical flags — `boo` is fully self-documenting. The five you'll touch: `new`, `send`, `peek`, `wait`, `kill` (plus `ls`, `rename` for housekeeping).

Two details worth knowing up front:

- `boo new <name> -d -- <command>` prints the session name to stdout, so `NAME=$(boo new -d -- bash)` captures it for scripting.
- Sessions run with `TERM=xterm-256color` — colors and cursor control render correctly.

The recipes below show these commands in real usage.

## Recipes

### Run a Command and Capture Output

```bash
boo new build -d -- make test
boo wait build --text 'PASS' --timeout 5m
boo peek build --scrollback
boo kill build
```

### Interrupt a Running Session

`--key` sends named keys — `C-c` stops a runaway build or REPL command:

```bash
boo send build --key C-c          # stop it
boo wait build --idle --timeout 5s
boo peek build --scrollback       # see where it stopped
boo kill build
```

Named keys: `C-a`–`C-z`, `Enter`, `Tab`, `Escape`, arrows, `Home`/`End`. `--key` and `--text` can't combine in one call — use two.

### Drive an Interactive Program

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

### Parallel Terminal Work

```bash
boo new lint -d -- npm run lint
boo new test -d -- npm run test
boo wait lint --idle --timeout 2m
boo wait test --idle --timeout 5m
boo peek lint
boo peek test
boo kill --all
```

### Check if a Program Finished

```bash
boo wait build --idle --timeout 10m
if boo peek build --scrollback | grep -q 'BUILD SUCCESSFUL'; then
  # success
else
  # failure — peek scrollback for errors
fi
```

### Long-Running Server (dev server)

Start, gate on readiness, walk away — peek when something breaks.

```bash
# 1. Start detached
boo new dev -d -- bun run dev

# 2. Gate on the ready marker before touching it
#    vite: 'Local:   http://localhost:5173'
#    next: 'Ready in 1.2s'
#    express: 'listening on port 3000'
boo wait dev --text 'localhost:' --timeout 30s

# ...edit files, run other tasks — HMR handles reloads...

# 3. Something broke (compile error, user bug report) — read the history
boo peek dev --scrollback | tail -50

# 4. Config change HMR won't catch (.env, vite.config, tsconfig) → restart
boo kill dev && boo new dev -d -- bun run dev
boo wait dev --text 'localhost:' --timeout 30s

# 5. Done with the session
boo kill dev
```

- **Readiness gate is load-bearing.** Don't sleep blindly or race the server — `wait --text` on the URL/ready string it prints.
- **`peek --scrollback` is the debug lens.** HMR events, compile errors, and request logs all land there.
- **Know what survives HMR.** Code/component changes reload live; `.env`, config files, and port-binding changes need a full restart.
- **Always `boo kill`.** A leaked `bun run dev` holds a port and a PTY.

## Gotchas

- **No `--enter` means no Enter.** `--text` sends exactly the bytes given.
- **`--key` and `--text` are separate calls.** Cannot combine in one `boo send`.
- **`--text` has no escaping.** `'$HOME'` sends literal `$HOME`. Expand yourself: `"$(pwd)"`.
- **One attached client per session.** Always use `-d`, never `attach`.
- **`peek` shows the screen, not a log.** Use `--scrollback` for history.
- **`wait --text` matches the rendered screen only** (not scrollback).
- **Session names must be unique prefixes.** "build" and "builder" makes `bu` ambiguous.
- **Exit code 4 = timeout.** Handle it explicitly.
- **Clean up.** Always `boo kill` when done. Leaked sessions hold PTYs and processes.
