---
name: herdr-agent-driver
description: >
  Drive coding-agent harnesses (claude, codex, pi, devin and more) as child
  workers via the herdr CLI: launch, prompt, wait, read output, handle blocked
  dialogs, fan out in git worktrees. For plain pane and workspace control, use
  the herdr skill.
disable-model-invocation: true
---

# Driving coding agents with herdr

The orchestrator's playbook: supervision, prompting, per-harness launch recipes. Not a herdr manual: syntax, IDs and the pane-vs-agent model come from `herdr --skill` and `--help`, which match the installed binary.

You are an agent inside herdr (`HERDR_ENV=1`). If it's unset but the operator supplies a socket or session (`HERDR_SOCKET_PATH=…`, `--session <name>`), that is the authorization: prefix commands with it and proceed.

Loop: **baseline → start → prompt → wait for a settled state → read → independently verify → steer or stop.** The child's report is a claim, not evidence; you own scope, repo state, verification and acceptance.

Setup: `herdr status`, `herdr integration status`, `herdr integration install <harness>` (once per harness). `herdr agent start --help` lists `--kind` values (the list grows). Without an integration, state may stay `unknown`: see "No integration".

## Harness launch defaults

Flags come from `<harness> --help`; what it can't tell you:

| `--kind` | Least-privilege launch args | Resume | Fresh context |
|---|---|---|---|
| `claude` | `--permission-mode acceptEdits` | `-c` / `-r <id>` | `/clear` |
| `codex` | `-a on-request -s workspace-write` | `codex resume --last` | `/new` |
| `opencode` | (none) | `-c` / `-s <id>` | — |
| `pi` | `--model <provider/id>` | `-c` / `-r` | `/new` |
| `devin` | `--model <name>` | `-c` / `-r <id>` | `/new` |

**Shell aliases inject flags (this machine).** `~/.shrc` aliases `devin` to `--permission-mode dangerous` and `codex` to `--dangerously-bypass-approvals-and-sandbox`. The launch runs in the pane's interactive shell, so the harness starts in full bypass whatever you append, and repeating the aliased flag fails with `cannot be used multiple times`. A title like `(bypass permissions on)` is the alias, not herdr. Inspect with `herdr pane run <pane-id> "type codex"`; bypass with `\codex …` or the full path, or accept it and tighten in-TUI once `idle` (Devin: `/mode accept-edits`). Symptom: `agent start … -- --permission-mode X` times out (`timed out waiting for agent startup`), `agent get` says `agent_not_found`, and `pane read` shows the "multiple times" error. Agents keep blaming the integration; it's the alias.

Other quirks:
- Claude's workspace-trust and Pi's `.pi/` trust dialogs show as `blocked` on first run in a new directory: read `visible`, confirm once or pre-trust.
- Non-interactive modes (`codex exec`, `pi -p`, `devin -p`, `opencode run`) print and exit: not drivable. Inside herdr run the TUI and use `agent prompt`.
- Devin: `/loop` is an orchestrator-side loop; hold phase boundaries with one-turn prompts plus `/new`. Observed SWE-1.7: good on tightly scoped work, prone to scope expansion and weak self-review; treat its "pre-existing" labels as unverified.

## No integration

No `agent start` kind, so state may stay `unknown`. Either launch with no-prompt flags and match output:

```bash
herdr pane run <pane-id> "cmd -t --auto-accept"      # or --yolo — sandbox only
herdr pane wait-output <pane-id> --match "ready" --timeout 120000
herdr pane wait-output <pane-id> --match "task complete" --regex --timeout 1800000
```

or report state from the harness's hooks (`HERDR_PANE_ID` is set in panes; states `idle|working|blocked|unknown`; raise `--seq` so stale reports are ignored), which gives the pane a real identity for `agent wait`/`agent get`:

```bash
herdr pane report-agent "$HERDR_PANE_ID" --source cmd-hook --agent cmd --state working --seq 1
```

## Core loop

`herdr agent start <name> --kind <kind> --pane <pane-id> -- <harness-args>` (herdr supplies the executable; only harness args follow `--`).

```bash
git status --short --branch && git rev-parse HEAD           # baseline before granting write access
WS_JSON=$(herdr workspace create --cwd ~/src/app --label app --no-focus)
WS_ID=$(printf '%s' "$WS_JSON" | jq -r '.result.workspace.workspace_id')
PANE_ID=$(printf '%s' "$WS_JSON" | jq -r '.result.root_pane.pane_id')
herdr agent start claude-app --kind claude --pane "$PANE_ID" -- --permission-mode acceptEdits
herdr agent prompt claude-app "Read TASK.md. Implement only phase 2, verify it, commit it, then stop." --wait --timeout 1200000
herdr agent read claude-app --source recent-unwrapped --lines 300
git status --short --branch && git diff --check && git show --stat --oneline HEAD   # verify yourself
```

JSON paths (0.8.2): `workspace create`/`worktree create` → `.result.workspace.workspace_id`, `.result.root_pane.pane_id`, `.result.tab.tab_id`; `pane split` → `.result.pane.pane_id`; errors → `.error.code`. Never guess IDs.

- `--wait` already waits for the first settled `idle`/`done`/`blocked`; add `--until` only for a state-specific gate.
- `agent start` returns once the agent is ready (default 30s; accepts 3000–300000 ms). On a startup block it returns `agent_not_ready` but the name stays usable: wait for `idle`. A start **`timeout`** leaves **no registered name**: `pane read <pane-id> --source recent-unwrapped`, fix the cause (alias clash, startup error), address the pane by ID, and don't blindly re-run `agent start` on it.
- After every `agent start` and `/new`, read `--source visible` and confirm model and permission-mode before the first prompt: fresh sessions have come up on the wrong model or in bypass.
- **Two timeouts, two units.** herdr `--timeout` is ms; your shell tool's `timeout` has its own unit (pi's `bash`: seconds). Mixing them gives `Invalid timeout: maximum is 2147483.647 seconds`: that's your tool, not herdr. Keep the tool timeout ≥ the herdr wait, in its own unit.
- A wait timeout or interrupted tool call does **not** mean the child stopped: `agent get`, `agent read --source visible --lines 80`, `agent wait`.

## States and reading

| State | Meaning | Action |
|---|---|---|
| `idle` | Ready; result seen | Send next prompt |
| `done` | Idle, result unseen | Read and verify |
| `working` | Generating or running tools | Wait; send nothing |
| `blocked` | Approval, question or error UI | Read `visible`, resolve minimally or escalate |
| `unknown` | Detection unsure | Read `visible` yourself; don't trust blind waits |

Read `recent-unwrapped` for logs/results, `visible` for dialogs, `detection` to debug the classifier. If more `--lines` reveals nothing, the agent may be on the alternate screen: as a fallback prompt it to write the report to a Markdown file (never in the initial prompt).

### Traps

- **Suspicious `done`.** A turn that died on a model, plan or quota error (`Permission denied`, usage limit) settles as `done` with no work done, and waiting on an already-working agent can match that turn's end. Before calling a result stale, measure (elapsed time, `completion_seq`) and `agent read`; real multi-minute turns have been misjudged as instant. For an already-working agent: `agent wait <name> --until working`, then plain `agent wait <name>`.
- **`agent_blocked`:** `agent prompt` refuses while a dialog is open; resolve it first.
- **`agent_prompt_stalled`:** no observed lifecycle change within 5s of a prompt from a non-working state. Check `agent get`/`agent read` before resending: a stalled slash-command may have run, and a blind retry runs it twice.
- **Names** `[a-z][a-z0-9_-]{0,31}`, unique among live agents; commands take a name or the hosting pane ID (never terminal IDs or bare kind labels). A name follows the pane's current occupant and is cleared on exit or replacement: after `/new` (seen with pi), a closed pane or restart, re-resolve with `agent get <pane-id>` and `agent rename`. Hand-launched agents have no name: use the pane ID. `agent_session.value` is a session ID, not a target.
- **Detection lag** after `pane run <harness>`: transient `agent_not_found`; sleep ~5s and retry.

## Prompting rules

1. **Pin the target before every send:** unique name (`herdr agent rename` if needed); `agent get` shows the expected kind and cwd; not your own pane (`$HERDR_PANE_ID`); `agent prompt --expect-session <id>` refuses if the occupant changed; env inherited from another herdr session needs `--session`. Prompt agents only with `agent prompt`: a `pane send-text` + `send-keys enter` loop has submitted a task to the wrong pane. Never `head`-truncate `agent list` before declaring an agent absent.
2. **Long specs go in a file** (`/tmp/task-123.md` or `TASK.md`); send a one-line prompt referencing it. Multi-line pastes are unreliable in TUI inputs (Enter may submit early).
3. **Prompt only while `idle`.** Mid-`working` input queues or garbles. Interrupt with `herdr agent send-keys <name> esc` (`ctrl+c` heavier), confirm it settled, then prompt. Where `agent prompt` is unreliable (slash commands, input widgets): `herdr pane run <pane-id> "<text>"`, or text then `agent send-keys <name> enter`.
4. **Bound every implementation turn:** phase or issue, allowed scope, required checks, commit expectation, stopping point. Steering stays short and imperative. Useful: `Implement only <unit>; run <checks>; commit only scoped files with <message>; report unrelated failures without fixing them; then stop.`
5. **Reset context at phase or review boundaries** (`/clear` or `/new`): long-lived context, not prompt text, burns the subscription window, and stale context makes agents defend earlier work and blur scope.

## Blocked dialogs

```bash
herdr agent read claude-app --source visible --lines 60   # the actual dialog
herdr agent send-keys claude-app enter                    # default choice
herdr agent send-keys claude-app down enter               # menu option
herdr pane run "$PANE_ID" "yes, proceed"                  # type an answer (agent prompt refuses while blocked)
```

Launch with the least-privilege flags above so `blocked` is rare. Unresolvable: `herdr notification show "claude-app blocked" --body "Permission prompt needs a human" --sound request`.

## Supervision and acceptance

Agents are implementers, not authorities.

1. **Baseline first:** HEAD, dirty state, relevant failing tests; name pre-existing files that must stay untouched.
2. **Inspect at milestones.** Every follow-up is chosen from what you just read: no polling loops, timers or canned "continue" prompts across panes. At a usage/quota wall stop prompting until the stated reset and say so; probing only stacks dead prompts. When the operator asks what a child is doing, answer with its assigned task and progress (brief + transcript), not the current screen; keep that read-only. piz's status-bar quota readout (`5h: 78% ↻3h · 7d: 96% ↻6d22h`) is **remaining** usage and time left, not consumed (operator, 2026-11-09) — do not read it as near-exhaustion.
3. **Distrust completion summaries:** inspect the full diff and commit, reconcile task ledgers/specs, rerun the narrowest relevant checks. A "pre-existing" failure needs reproduction or history evidence.
4. **Review ≠ fixing.** A reviewer that edits violated its task: use a read-only configuration or disposable worktree rather than prompt-only prohibitions. Start accepted fixes in fresh context.
5. **Stop scope drift early:** Esc, inspect the dirty tree, keep any useful patch, restore only identified out-of-scope paths. Never discard a mixed diff blindly.
6. **Attribute cross-change drift historically** (`git log`, blame, historical views); don't rewrite an earlier contract because HEAD moved past it.
7. **Atomic commits:** one phase or review-fix set each; verify only intended paths were staged; unrelated baseline repairs get their own change.

## Parallel agents

- Isolate git state with worktrees: `herdr worktree create --workspace "$WS_ID" --branch feat-a --no-focus` opens the checkout (under `~/.herdr/worktrees/`) as its own workspace, with the same `.result.root_pane.pane_id` path. Or `herdr pane split --pane "$PANE_ID" --direction right --no-focus` for a sibling.
- Create with `--no-focus` and drive purely by name.
- Tell every child in the brief not to touch herdr layout (no `pane/tab/workspace close` or move): a child "cleaning up" once closed the workspace it shared with the orchestrator, killing both.
- Fan-in: loop names with `agent wait`/`get`, collect with `agent read`; `herdr notification show "All agents done" --sound done`.

## Detection troubleshooting

`herdr agent explain <target>` (`--verbose`) shows the matched rule and evidence. `herdr server agent-manifests` / `update-agent-manifests` / `reload-agent-manifests` for manifest cache and local overrides. After a harness upgrade breaks detection, restart or hand off the server after upgrading herdr before using `explain`.

## Cleanup and safety

`herdr pane close`, `herdr workspace close` (herdr state only), `herdr worktree remove --workspace <id>` (**deletes the git checkout**; `--force` if dirty).

Auto-approval flags (`--dangerously-skip-permissions`, `-a never`, `--auto`, `--yolo`) remove the human from the loop: sandboxes and disposable environments only. Otherwise use least-privilege modes plus `blocked` handling.
