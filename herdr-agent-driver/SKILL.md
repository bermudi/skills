---
name: herdr-agent-driver
description: Drive interactive coding-agent harnesses (Claude Code, Codex, OpenCode, Pi, and similar terminal agents) from a parent orchestrator agent using the herdr CLI. Use when starting, prompting, monitoring, waiting on, reading output from, or coordinating one or more coding agents running in herdr panes — including parallel multi-agent setups with git worktrees.
---

# Driving coding agents with herdr

## Mental model

- The herdr server hosts sessions → workspaces → tabs → panes. Each pane runs a terminal; a coding harness (`claude`, `codex`, `opencode`, `pi`, …) runs interactively inside a pane.
- You drive everything through the `herdr` CLI, which talks to the server over the local socket API and prints JSON. Never attach interactively (`terminal attach` / `agent attach` are for humans).
- herdr detects known harnesses on screen and classifies their state as `idle`, `working`, `blocked`, or `unknown`. Official integrations improve this detection — install them first.
- Canonical loop: **start → wait for idle → send prompt → wait for idle/blocked → read output → repeat.**

## Prerequisites

```bash
herdr status                     # is the server up?
herdr integration status         # installed/outdated integrations
herdr integration install claude # run once per harness: claude, codex, opencode, pi, omp, copilot, devin, droid, kimi, kilo, hermes, qodercli, cursor, mastracode
```

If the harness has no official integration, state detection may stay `unknown`. Then either (a) launch it with no-prompt/auto-approve flags and use `herdr wait output` on its pane, or (b) report state from harness hooks via `herdr pane report-agent` (see references/harness-recipes.md).

## Core driving loop

```bash
# 1. One workspace per project
herdr workspace create --cwd ~/src/app --label app --no-focus
#    → note the workspace id from the JSON response (inspect with `jq` — verify field names on first use)

# 2. Start the agent. <name> becomes its unique identity; everything after `--` is the command.
herdr agent start claude-app --workspace <ws_id> --no-focus -- claude --permission-mode acceptEdits

# 3. Wait for the harness to boot to its prompt
herdr agent wait claude-app --status idle --timeout 120000

# 4. Send the task (see "Prompting rules" — prefer a short message pointing at a task file)
herdr agent send claude-app "Read TASK.md in the repo root and implement it."

# 5. Wait for completion, handling blocked
while true; do
  if herdr agent wait claude-app --status idle --timeout 300000; then
    break                                   # finished this turn
  fi
  herdr agent read claude-app --source visible --lines 60   # timed out or changed: inspect
  # If it's a permission/question prompt, answer it (see "Handling blocked"), else keep waiting.
done

# 6. Collect results
herdr agent read claude-app --source recent-unwrapped --lines 300
```

## Agent states

| State | Meaning | Your action |
|---|---|---|
| `idle` | At its input prompt, ready | Send the next prompt |
| `working` | Generating or running tools | Wait |
| `blocked` | Needs attention: permission prompt, question, error | Read `visible`, answer, or escalate to the human |
| `unknown` | Detection is unsure | Read `visible` yourself; do not trust blind waits |

`herdr agent wait <name> --status <idle|working|blocked|unknown> [--timeout MS]` blocks until match or timeout. The pane-level variant `herdr wait agent-status <pane_id> --status <idle|working|blocked|done|unknown>` additionally supports `done`.

## Prompting rules

1. **Use unique names** as targets (`herdr agent rename <target> <name>` if needed). Names/labels are identities; terminal/pane IDs are low-level escape hatches.
2. **Write long specs to a file** (e.g. `/tmp/task-123.md` or `TASK.md` in the repo) and send a one-line prompt referencing it. Multi-line pasted text is unreliable in TUI input boxes (Enter may submit early).
3. `herdr agent send <name> <text>` writes literal text to the agent's terminal. Verify submission with `agent read` or a state change. Deterministic fallback when you need guaranteed text+Enter: `herdr pane run <pane_id> "<text>"` (agent targets accept legacy pane IDs; resolve via `herdr agent get`).
4. **Only prompt while `idle`.** Sending mid-`working` queues or garbles input depending on the harness. To interrupt, most harnesses use Esc: `herdr pane send-keys <pane_id> esc`.
5. For follow-up steering, keep messages short and imperative.

## Handling blocked

```bash
herdr agent read claude-app --source visible --lines 60   # see the actual prompt
herdr pane send-keys <pane_id> enter                      # accept default choice
herdr pane send-keys <pane_id> down enter                 # pick a menu option
herdr agent send claude-app "yes, proceed"                # answer a question
```

- Prefer launching with auto-approval flags (see references/harness-recipes.md) so `blocked` is rare.
- If you cannot resolve it, escalate to the human: `herdr notification show "claude-app blocked" --body "Permission prompt needs a human" --sound request`.

## Reading output

| Source | Use for |
|---|---|
| `visible` | Current screen — prompts, dialogs, permission UIs |
| `recent` | Recent scrollback with terminal wrapping |
| `recent-unwrapped` | Logs and results — best default for parsing |
| `detection` | Exactly what the state classifier sees (debugging) |

`herdr agent read <name> --source recent-unwrapped --lines 300` (`--ansi` / `--format ansi` if you need colors). For non-agent panes (builds, servers, tests): `herdr wait output <pane_id> --match <text> [--regex] [--timeout MS]`.

## Parallel agents

- Isolate git state per agent with worktrees — `herdr worktree create` opens the checkout as its own workspace, grouped with the parent repo:
  ```bash
  herdr worktree create --workspace <ws_id> --branch feat-a --no-focus
  herdr agent start claude-a --workspace <worktree_ws_id> --no-focus -- claude --permission-mode acceptEdits
  herdr agent start codex-b  --workspace <ws_id> --split right --no-focus -- codex -a never -s workspace-write
  ```
- Always launch with `--no-focus` when orchestrating; drive purely by name.
- Fan-in: loop over names, `agent wait`/`agent get` each, collect with `agent read`.
- Announce completion: `herdr notification show "All agents done" --sound done`.

## Troubleshooting detection

- `herdr agent explain <target>` — shows the matched rule, evidence, and why the state was classified. Add `--verbose` for the full rule evaluation.
- `herdr server agent-manifests` — check manifest sources/cache; `herdr server update-agent-manifests` to refresh; `herdr server reload-agent-manifests` after local override edits.
- If a harness upgraded and detection broke, restart/hand off the server after upgrading herdr before using `agent explain`.

## Cleanup

```bash
herdr pane close <pane_id>
herdr workspace close <workspace_id>            # closes herdr state only
herdr worktree remove --workspace <id>          # actually deletes the git checkout (--force if dirty)
```

## Safety

Auto-approval flags (`--dangerously-skip-permissions`, `-a never`, `--auto`, `--yolo`) remove the human from the loop. Use them only in sandboxes/disposable environments. Prefer least-privilege modes (e.g. Codex `-s workspace-write -a on-request`, Claude `--permission-mode acceptEdits`) plus prompt `blocked` handling when the work is destructive or the repo matters.

## Reference

Per-harness launch recipes, resume commands, and unsupported-harness state reporting: **references/harness-recipes.md**.
