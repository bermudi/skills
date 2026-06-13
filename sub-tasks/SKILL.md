---
name: sub-tasks
description: >
  Delegate work to subagents or terminal sessions — spawn parallel AI tasks,
  run code reviews, investigate codebases, drive interactive programs, automate
  CLI workflows, manage long-running processes.
  Triggers on: "subagent", "spawn", "delegate", "in parallel", "review this",
  "scout", "investigate", "launch agent", "code review", "multi-agent",
  "do these at the same time", "while that runs", "run in background",
  "terminal session", "send keys", "read terminal output", "multiplexer",
  "interactive program", "REPL", "TUI".
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

Agents live in `.pi/agents/*.md`. Project-local agents override global ones. Current roster:

| Agent | Model | Specialty | Tools |
|---|---|---|---|
| **reviewer** | deepseek-v4-pro | Code review: bugs, security, edge cases. Read-only. | read, bash |
| **scout** | deepseek-v4-flash | Codebase investigation: map architecture, trace imports. | read, bash |
| **workhorse** | deepseek-v4-pro | Mechanical execution: bulk edits, boilerplate, refactors. | all |

## Task Fields

| Field | What | Default |
|---|---|---|
| `prompt` | The task description. Required unless `resumeFrom` is set. | — |
| `agent` | Named agent from `.pi/agents/`. Overrides: `model`, `tools`, `thinking`, `systemPrompt` all work inline. | parent model |
| `systemPrompt` | Full system prompt. Required if no `agent`. | — |
| `model` | e.g. `anthropic/claude-sonnet-4`. | agent default → parent |
| `tools` | Array: `read`, `write`, `edit`, `bash`. | all four |
| `thinking` | `off`, `minimal`, `low`, `medium`, `high`, `xhigh`. | agent default → off |
| `skills` | Array of skill names to inject into the subagent's system prompt. | — |
| `cwd` | Working directory. Accepts absolute, relative, and `~` paths. | parent session cwd |
| `context` | `fresh` (clean) or `with-parent-transcript` (inject full conversation — expensive). | `fresh` |
| `sessionId` | Named persistent session. First call creates, subsequent reuse. | — |
| `resumeFrom` | Absolute path to a previous session `.jsonl`. Agent resumes with full history. | — |
| `action` | `prompt` (default), `close` (tear down session), `list` (show active). | `prompt` |

## Session Reuse (Multi-Turn)

Keep a subagent alive across multiple interactions:

```json
// Create and run
{ "prompt": "Investigate the auth module", "agent": "scout", "sessionId": "auth-research" }

// Continue the same agent
{ "prompt": "Now check the tests for that module", "sessionId": "auth-research" }

// Clean up
{ "sessionId": "auth-research", "action": "close" }
```

Pooled agents auto-close after 10 minutes of inactivity.

## Async Mode

Fire tasks in the background, keep working:

```json
delegate({ "async": true, "tasks": [{ "agent": "scout", "prompt": "Map the auth module" }] })
```

Returns a ticket ID immediately. Poll with:
- `delegate({ "action": "poll" })` — list all tickets
- `delegate({ "action": "poll", "ticket": "abc123" })` — check one
- `delegate({ "action": "cancel", "ticket": "abc123" })` — abort

Max 5 concurrent async tickets. Completed tickets auto-deliver results.

## Handling Failures

When tasks fail, results include a `resumeFrom` path pointing to the failed session. Recovery: read the successful results, then `resumeFrom` the failed one with a corrective prompt.

## `with-parent-transcript`

Injects your full conversation into the subagent. Token-expensive — only use when the subagent genuinely needs your entire context. For everything else, summarize what it needs in the `prompt`.

## Recipes

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

Specify thoroughness: **Quick** (key files), **Medium** (follow imports, default), **Thorough** (all deps + tests + types).

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

- Subagents only have core tools (read, write, edit, bash). They don't inherit MCP tools or skills unless you specify `skills`.
- `delegate` is synchronous by default. Use `async: true` to fire-and-forget.
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

### Session Management

```bash
boo new <name> -d -- <command>     # new detached session running command
boo new <name> -d -- bash          # new detached shell session
boo ls [--json]                     # list sessions
boo kill <name>                     # end a session
boo kill --all                      # end every session
boo rename <name> <new-name>       # rename a session
```

- Without `-- <command>`, the session runs `$SHELL`.
- Commands accepting `<name>` also accept unique prefixes (e.g., `boo peek bu` matches "build").

### Sending Input — `boo send`

```bash
boo send <name> --text 'make test' --enter   # type text + press Enter
boo send <name> --key C-c                     # send Ctrl-C
boo send <name> --key Enter                   # press Enter
boo send <name> --key Up,Enter                # multiple keys
```

**Critical**: `--text` is **literal** — no escape processing, no implicit newline. Add `--enter` explicitly. `--key` and `--text` cannot be combined in one call; use two `boo send` invocations.

Named keys: `Enter`, `Tab`, `Escape`, `Space`, `Backspace`, `Up`, `Down`, `Left`, `Right`, `Home`, `End`, `C-a` through `C-z`.

### Reading Output — `boo peek`

```bash
boo peek <name>                  # current screen
boo peek <name> --scrollback     # screen + scrollback history
boo peek <name> --json           # structured output with cursor/metadata
```

Returns the **rendered screen** — what a human would see right now. `--scrollback` for history.

### Waiting — `boo wait`

```bash
boo wait <name> --text 'PASS' --timeout 2m    # until screen contains text
boo wait <name> --idle                         # until output settles (2s quiet)
boo wait <name> --idle --timeout 30s           # settle with timeout
```

`--text` does a substring match against the rendered screen. `--idle` waits until no output for 2 seconds. Always set `--timeout`.

**Exit codes**: `0` condition met, `1` error, `3` no such session, `4` timed out.

## Recipes

### Run a Command and Capture Output

```bash
boo new build -d -- make test
boo wait build --text 'PASS' --timeout 5m
boo peek build --scrollback
boo kill build
```

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
