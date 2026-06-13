---
name: sub-tasks
description: >
  Delegate work to subagents or drive terminal sessions for concurrent/durable
  execution. Use when spawning parallel AI tasks, running several subagents
  at once, or driving interactive programs and waiting for their output.
---

# Sub-Tasks: Multiplying Yourself

Two ways to delegate work, each for different jobs:

| Mechanism | What it does | Use for |
|---|---|---|
| **`delegate`** | Spawn AI subagents with their own context, model, and tools | Code review, investigation, parallel coding tasks, research |
| **`boo`** | Drive terminal sessions — send input, read output, wait for conditions | Builds, REPLs, TUIs, servers, interactive CLI programs |

---

## Decision Tree

```
What are you doing?
│
├─ Single quick thing I can do myself → just do it
│
├─ Multiple independent AI tasks at once → delegate
│
├─ Need specialist eyes (review, investigation) → delegate with the right agent
│
├─ Multi-turn conversation with a subagent → delegate with sessionId
│
├─ Run a build/test/server and read output → boo
│
├─ Drive an interactive program (REPL, TUI, prompts) → boo
│
└─ Multiple terminal tasks in parallel → boo (multiple sessions)
```

**Simple rule**: if it needs *thinking*, use `delegate`. If it needs a *terminal*, use `boo`.

---

# delegate — AI Subagents

Spawn subagents that run in parallel. Each gets independent context, model, tools, and system prompt. Results return to you.

## Available Agents

Discover the agents available in *this* environment by calling `delegate({})` with no tasks — it prints a manual listing every agent with its model, tools, and description. **List first, then reference by name.**

Agents live in `.pi/agents/*.md` (project-local) and `~/.pi/agent/agents/` (global); project-local overrides global by name. A typical roster includes a read-only reviewer, a scout for codebase investigation, and a workhorse for mechanical bulk edits — but the exact names, models, and tool sets are per-install. Don't assume a named agent exists; the recipe examples below use illustrative names.

## Task Fields

| Field | What | Default |
|---|---|---|
| `prompt` | The task description. Required unless `resumeFrom` is set. | — |
| `agent` | Named agent from `.pi/agents/`. Overrides: `model`, `tools`, `thinking`, `systemPrompt` all work inline. | parent model |
| `systemPrompt` | Full system prompt. Required if no `agent`. | — |
| `model` | e.g. `anthropic/claude-sonnet-4`. | agent default → parent |
| `tools` | Array of tool names. **Only** `read`, `write`, `edit`, `bash` exist for subagents — MCP/extension tools are not available. | all four |
| `thinking` | `off`, `minimal`, `low`, `medium`, `high`, `xhigh`. | agent default → off |
| `skills` | Array of skill names to inject into the subagent's system prompt. | — |
| `cwd` | Working directory. Accepts absolute, relative, and `~` paths. | parent session cwd |
| `context` | `fresh` (clean) or `with-parent-transcript` (inject full conversation — expensive). | `fresh` |
| `sessionId` | Named persistent session. First call creates, subsequent reuse. | — |
| `resumeFrom` | Absolute path to a previous session `.jsonl`. Agent resumes with full history. | — |
| `action` | Per-task: `prompt` (default), `close` (tear down a pooled session), `list` (show active sessions). | `prompt` |

**Top-level delegate parameters** sit on the call itself, not inside `tasks[]`:

- `tasks` — the array of task objects above.
- `async` (boolean) — fire tasks in the background; returns a ticket ID immediately (see [Async Mode](#async-mode)).
- `action` + `ticket` — async ticket control, no `tasks` needed: `poll` (list all tickets, or check one via `ticket`), `cancel` (abort a running ticket).

Per-task `action` (`prompt` / `close` / `list`) and top-level `action` (`poll` / `cancel`) are different namespaces — don't mix them.

## Session Reuse (Multi-Turn)

Keep a subagent alive across multiple interactions:

```json
// Create and run
{ "tasks": [{ "prompt": "Investigate the auth module", "agent": "scout", "sessionId": "auth-research" }] }

// Continue the same agent
{ "tasks": [{ "prompt": "Now check the tests for that module", "sessionId": "auth-research" }] }

// Clean up
{ "tasks": [{ "sessionId": "auth-research", "action": "close" }] }
```

Pooled agents auto-close after 10 minutes of inactivity. Async tickets have a 30-minute hard timeout.

## Async Mode

Fire tasks in the background, keep working:

```json
delegate({ "async": true, "tasks": [{ "agent": "scout", "prompt": "Map the auth module" }] })
```

Returns a ticket ID immediately. Poll with:
- `delegate({ "action": "poll" })` — list all tickets
- `delegate({ "action": "poll", "ticket": "abc123" })` — check one
- `delegate({ "action": "cancel", "ticket": "abc123" })` — abort

Max 5 concurrent async tickets (default; configurable via `~/.pi/agent/delegate.json` → `maxAsyncTickets`). Completed tickets auto-deliver results.

## Handling Failures

When tasks fail, results include a `resumeFrom` path pointing to the failed session. Recover by resuming with a corrective prompt:

```json
{
  "tasks": [{
    "prompt": "Continue — the server is running on :3000, retry the failed request",
    "resumeFrom": "/home/user/.pi/agent/sessions/project/2026-01-01T12-00-00Z_abc123.jsonl"
  }]
}
```

Combine `resumeFrom` with `sessionId` to resume AND pool for further turns.

## `with-parent-transcript`

Injects your full conversation into the subagent. Token-expensive — only use when the subagent genuinely needs your entire context. For everything else, summarize what it needs in the `prompt`.

## Recipes

Examples use illustrative agent names (`reviewer`, `scout`, `workhorse`). Run `delegate({})` to see what's available in your env and substitute — or omit `agent` to inherit the parent model.

### Code Review

```json
{
  "tasks": [{
    "prompt": "Review src/handler.go:42-120 for race conditions and error handling gaps",
    "agent": "reviewer"
  }]
}
```

**DO:** Point at exact files/line ranges/diffs. State what to look for.
**DON'T:** Ask "also suggest fixes" (triggers overcorrection bias). Open-ended fishing. Vague "be thorough".

### Codebase Investigation

```json
{
  "tasks": [{
    "prompt": "Find all files related to authentication, trace how they connect, identify the middleware chain",
    "agent": "scout"
  }]
}
```

State the thoroughness you want in the prompt — e.g. key files only, follow imports (a sensible default), or trace all deps + tests + types.

### Parallel Swarm

```json
{
  "tasks": [
    { "prompt": "Review the API handlers for security issues", "agent": "reviewer" },
    { "prompt": "Map the database schema and trace all migrations", "agent": "scout" },
    { "prompt": "Research best practices for rate limiting in Go web services", "skills": ["web-content"] }
  ]
}
```

### Bulk Mechanical Work

```json
{
  "tasks": [{
    "prompt": "Rename getUserById to fetchUser in all files under src/. Update imports, exports, and test references.",
    "agent": "workhorse"
  }]
}
```

## When NOT to Delegate

- You can answer by reading one or two files directly.
- The question is trivial (typos, formatting).
- The user wants an explanation, not a critique.
- Tasks are tightly sequential (step B depends on step A's output).

## Gotchas

- Subagents are sandboxed to the four core tools (read, write, edit, bash). The `tools` field only accepts those names; MCP and extension tools are **never** available to subagents. Passing `skills` injects a skill's `SKILL.md` *instructions* into the system prompt (text) — it does not unlock extra tools.
- `delegate` is synchronous by default. Sync calls run at most **3 tasks at once** (the rest queue, not fail) — default ceiling, configurable via `~/.pi/agent/delegate.json` → `maxConcurrent`. `async: true` moves execution to the background so you keep working: up to 5 tickets run independently, each internally capped the same way.
- `with-parent-transcript` injects your *entire* conversation. A 50k-token session means the subagent starts 50k tokens deep.

---

# boo — Terminal Session Automation

A terminal multiplexer with automation primitives: `send`, `peek`, `wait`. Drive interactive programs (shells, REPLs, TUIs, build tools) from scripts. Output is parsed through a real terminal emulator — `peek` returns exactly what a human would see.

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
