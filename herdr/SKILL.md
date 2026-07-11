---
name: herdr
description: "Control Herdr, a terminal multiplexer for coding agents. Use only when the user explicitly mentions Herdr or asks to use it to inspect or control another agent's pane or session. Do not use merely because a task could benefit from a background terminal, delegation, or parallel work."
---

# Herdr

Herdr is a terminal multiplexer and runtime for coding agents, exposing the running session through the `herdr` CLI.

Before any control command, confirm this agent runs inside a Herdr pane:

```bash
test "${HERDR_ENV:-}" = 1
```

If this fails, you are not running inside Herdr. You may still issue control commands if the user names an explicit target — a pane ID (e.g. `w1:p3`) or an agent name. Either removes the targeting hazard. Otherwise stop; without `--current` or an explicit target, a control command lands on whatever pane some other client has focused, which is usually not what the user wants.

## Discover the CLI

The installed binary is the authority for syntax. Start with `herdr --help`, then run a command group without a subcommand (e.g. `herdr pane`) to print its options.

Two footguns: **bare `herdr` launches the TUI** — always use `--help` or a subcommand. **Never run a mutating nested command bare for discovery** — some, like `herdr workspace create`, are valid with defaults and will execute. Use the no-arg group output instead.

Most control commands print JSON. Read IDs and state from responses; never construct either.

## Model

Terminals organize into workspaces → tabs → panes. An agent runs inside a pane; **the pane ID is the control surface** for agents, shells, servers, tests, and logs — spawning, input, reads, waits, and cleanup all key off it. Agent commands (`agent read`, `agent wait`, `agent send`, `agent get`) also accept the agent's name or label as a target — use whichever identifier the user gave you, or the pane ID you parsed from JSON.

IDs (`w1`, `w1:t1`, `w1:p1`, `term_...`) are opaque strings whose suffix can grow beyond one char. **Re-read JSON after any mutation** (create, split, move, list, get); never derive an ID from a workspace or display number. Closed IDs aren't reused; a moved pane gets a new ID.

Herdr injects stable context into each pane (`$HERDR_WORKSPACE_ID`, `$HERDR_TAB_ID`, `$HERDR_PANE_ID`). Prefer `--current` to target the calling pane; omitting a target may hit another client's focused pane.

A pane's `agent_status` is `idle`, `working`, `blocked`, `done`, or `unknown`. `idle` (waiting, result seen) and `done` (finished, result not yet seen) are the same semantic state — the difference is only attention. Focusing the pane, switching to its tab, or regaining outer focus marks it seen, so `done` becomes `idle`. Treat either as completed.

## Start an agent

Default to a sibling pane in the current tab and cwd. Don't create a workspace/tab/worktree or change cwd unless the user asks.

Split without moving focus. Pick direction from the caller's rectangle — right for wide panes, down for narrow/tall; avoid repeated same-direction splits:

```bash
herdr pane layout --pane "$HERDR_PANE_ID"   # inspect geometry first
herdr pane split --current --direction right --no-focus
```

Read `result.pane.pane_id` from the response. Label the pane, then **launch the agent with only its normal executable** so its interactive TUI opens — no prompt in argv, no non-interactive flags:

```bash
herdr pane rename <pane-id> "reviewer"
herdr pane run <pane-id> "codex"   # claude | pi | opencode | omp
```

Wait for the idle transition, then submit the task. `pane run` sends text + Enter together; use it for initial prompts and follow-ups alike:

```bash
herdr wait agent-status <pane-id> --status idle --timeout 30000
herdr pane run <pane-id> "Review the current diff; report only actionable findings."
```

To get a finished result, wait for `done` (background tab) or `idle` (foreground), then read:

```bash
herdr wait agent-status <pane-id> --status done --timeout 120000
herdr pane read <pane-id> --source recent-unwrapped --lines 120
```

On any wait timeout (exits status `1`), run `pane get` and `pane read` before deciding: `blocked` needs input, `unknown` has no detected agent yet.

## Run an ordinary command

Same split rule without moving focus, then run, wait, read:

```bash
herdr pane split --current --direction right --no-focus
# read the new pane_id
herdr pane run <pane-id> "just test"
herdr wait output <pane-id> --match "test result" --timeout 120000
herdr pane read <pane-id> --source recent-unwrapped --lines 120
```

**Inspect before waiting** — read current output first, then wait for the next state or output you expect. Use `--format ansi` when color or styling is evidence; otherwise text. (`pane read --help` lists read sources.)

If the user asks for a different tab, workspace, or worktree, discover that command group and use its returned IDs. Don't infer a larger topology from a request to start an agent or command.

## Safety

- `--no-focus` for background work unless the user asked to switch context.
- `--current` or an explicit target (pane ID or agent name); never another client's focused pane.
- Parse IDs from JSON; never from sidebar order or examples.
- Don't close workspaces, tabs, panes, or sessions you didn't create unless explicitly asked.
- Never run `herdr server stop` from an active session, and never kill the main Herdr process.
