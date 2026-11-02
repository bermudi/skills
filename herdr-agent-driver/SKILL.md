---
name: herdr-agent-driver
description: >-
  Drive interactive coding-agent harnesses as child workers from a parent orchestrator
  agent via the herdr CLI: launch harnesses (claude, codex, pi, devin, and more),
  submit bounded prompts, wait on lifecycle states, read output, verify results,
  handle blocked dialogs, and fan out parallel agents in git worktrees. Use when
  supervising or orchestrating coding agents with herdr. For plain herdr pane and
  workspace control, use the herdr skill instead.
disable-model-invocation: true
---

# Driving coding agents with herdr

## Scope

This is the orchestrator's playbook: supervision discipline, prompting rules, and
per-harness launch recipes. It is not a herdr manual — command syntax, ID handling, and
the pane-vs-agent model come from the `herdr` skill (`herdr --skill` prints the doc that
matches the installed binary). The binary is the authority; this file only layers the
orchestration method on top.

The orchestrator is itself an agent inside herdr (`HERDR_ENV=1`); verify that before
driving. Canonical loop:

**baseline → start → prompt → wait for a settled state → read → independently verify → steer or stop.**

The child agent's report is a claim, not evidence. The parent remains responsible for
scope, repository state, verification, and acceptance.

## Prerequisites

```bash
herdr status                     # is the server up?
herdr integration status         # installed/outdated integrations
herdr integration install claude # run once per harness
```

Accepted `--kind` values: `herdr agent start --help` (the list grows; don't trust a copy
here). Which have an installed state hook: `herdr integration status`. Without an
integration, state detection may stay `unknown` — see *Driving harnesses without an
integration* below.

## Harness launch defaults

For flag syntax, run `<harness> --help` — the installed binary is the authority; do not
trust cached flag lists. What `--help` cannot tell you:

| Harness (`--kind`) | Least-privilege launch args | Resume | Fresh context |
|---|---|---|---|
| `claude` | `--permission-mode acceptEdits` | `-c` / `-r <id>` | `/clear` |
| `codex` | `-a on-request -s workspace-write` | `codex resume --last` | `/new` |
| `opencode` | (none) | `-c` / `-s <id>` | — |
| `pi` | `--model <provider/id>` | `-c` / `-r` | `/new` |
| `devin` | `--model <name>` | `-c` / `-r <id>` | `/new` |

### Shell aliases inject flags (this machine)

`~/.shrc` aliases `devin` to `--permission-mode dangerous` (bypass) and `codex` to
`--dangerously-bypass-approvals-and-sandbox`. The launch command runs in the pane's
interactive shell, so the alias expands: the harness starts in full bypass no matter
what you append, and repeating the aliased flag fails with `cannot be used multiple
times`. A TUI title like `(bypass permissions on)` is the alias talking, not herdr.
Check what a pane's shell resolves with `herdr pane run <pane-id> "type codex"`; skip
the alias with a leading backslash (`\codex ...`) or the full path from `which codex`,
or accept it and tighten in-TUI when `idle` (Devin: `/mode accept-edits`).

Recognizable failure: `agent start … -- --permission-mode X` times out
(`timed out waiting for agent startup`), `agent get <name>` says `agent_not_found`, and
`herdr pane read <pane-id>` shows `error: the argument '--permission-mode …' cannot be
used multiple times`. It is the alias, not herdr's integration — agents repeatedly
mis-blamed the integration. Also read `visible` after start and confirm the model and
mode banner before the first prompt; fresh sessions have come up on an unintended model
or in bypass.

### Other quirks

- **Trust prompts.** Claude's workspace-trust and Pi's `.pi/` trust dialogs surface as
  `blocked` on first run in a new directory — read `visible`, confirm once, or pre-trust.
- **Non-interactive modes are not drivable.** `codex exec`, `pi -p`, `devin -p`,
  `opencode run` print and exit — that's for CI outside herdr. Inside herdr, run the
  TUI and submit with `agent prompt`.
- **Devin.** `/loop` is an orchestrator-side loop; enforce phase boundaries with
  one-turn prompts plus `/new` instead. Observed SWE-1.7 profile: productive on tightly
  scoped work, prone to scope expansion and weak self-review — treat "pre-existing"
  labels as unverified claims.

## Driving harnesses without an integration

No `agent start` kind, so state detection may stay `unknown`. Two patterns:

**1. Launch with no-prompt flags and pattern-match output:**

```bash
herdr pane run <pane-id> "cmd -t --auto-accept"      # or --yolo — sandbox only
herdr pane wait-output <pane-id> --match "ready" --timeout 120000
herdr pane wait-output <pane-id> --match "task complete" --regex --timeout 1800000
```

**2. Report state from harness hooks**, using the pane's own environment
(`HERDR_PANE_ID` is set inside herdr panes):

```bash
herdr pane report-agent "$HERDR_PANE_ID" --source cmd-hook --agent cmd --state working --seq 1
herdr pane report-agent "$HERDR_PANE_ID" --source cmd-hook --agent cmd --state idle    --seq 2
```

States: `idle|working|blocked|unknown`; raise `--seq` so stale reports are ignored.
This gives the pane a real agent identity usable by `agent wait`/`agent get`.

## Core driving loop

Generic form: `herdr agent start <name> --kind <kind> --pane <pane-id> -- <harness-args...>`
— herdr supplies the executable, so only harness args go after `--`. Pick args from the
launch-defaults table above; run `<harness> --help` for exact syntax. Worked example,
Claude:

```bash
# 0. Record the baseline before granting write access.
git status --short --branch && git rev-parse HEAD

# 1. Create a workspace; parse IDs out of the JSON — never guess them.
WS_JSON=$(herdr workspace create --cwd ~/src/app --label app --no-focus)
WS_ID=$(printf '%s' "$WS_JSON" | jq -r '.result.workspace.workspace_id')
PANE_ID=$(printf '%s' "$WS_JSON" | jq -r '.result.root_pane.pane_id')

# 2. Start the harness in that shell pane.
herdr agent start claude-app --kind claude --pane "$PANE_ID" -- --permission-mode acceptEdits

# 3. Submit one bounded task and block on the first settled state.
herdr agent prompt claude-app "Read TASK.md. Implement only phase 2, verify it, commit it, then stop." \
  --wait --timeout 1200000

# 4. Read the report, then verify the repository yourself.
herdr agent read claude-app --source recent-unwrapped --lines 300
git status --short --branch && git diff --check && git show --stat --oneline HEAD
```

Response paths (verified on 0.8.2): `workspace create` and `worktree create` return
`.result.workspace.workspace_id` (not `.id`), `.result.root_pane.pane_id`, and
`.result.tab.tab_id`; `pane split` returns `.result.pane.pane_id`; `worktree remove`
prints the deleted checkout path. Errors arrive as a JSON envelope with `.error.code`.

- `--wait` alone already waits for the first settled `idle`, `done`, or `blocked` state;
  do not restate those with `--until`. Use an explicit `--until` only for a
  state-specific gate (e.g. waiting for an already-running agent to raise `blocked`).
- `agent start` returns only once the agent is detected and ready for input (30s
  default timeout). On a startup block it returns `agent_not_ready` but keeps the name
  usable — wait for `idle` before prompting.
- **Two timeouts, two units.** herdr `--timeout` is milliseconds; your own shell tool's
  `timeout` argument has its own unit (pi's `bash`: seconds). Copying one into the other
  yields `Invalid timeout: maximum is 2147483.647 seconds` — that is your tool rejecting
  its argument, not herdr. Keep the tool timeout ≥ the herdr wait, in its own unit.
- `agent start` accepts `--timeout` of 3000–300000 ms. A start **`timeout`** (as opposed
  to `agent_not_ready`) leaves **no registered name**: diagnose with
  `herdr pane read <pane-id> --source recent-unwrapped`, fix the cause (alias flag clash,
  extension/startup error), and address the pane by ID. Re-running `agent start` on the
  same pane has returned `agent_pane_busy`.
- A wait timeout or an interrupted parent tool call does **not** mean the child stopped.
  Re-read state and output before acting:

```bash
herdr agent get claude-app
herdr agent read claude-app --source visible --lines 80
herdr agent wait claude-app --timeout 1200000
```

## Agent states

| State | Meaning | Your action |
|---|---|---|
| `idle` | Ready for input; its result has been seen | Send the next prompt |
| `done` | Same idle state, but the result is unseen | Read and verify the result |
| `working` | Generating or running tools | Wait — send nothing |
| `blocked` | Approval prompt, question, or error UI | Read `visible`, resolve minimally, or escalate |
| `unknown` | Agent present but detection unsure | Read `visible` yourself; don't trust blind waits |

Reading: default to `--source recent-unwrapped` (logs/results), `visible` for dialogs,
`detection` to debug the classifier. If larger `--lines` reveals nothing more, the agent
may be on the terminal's alternate screen — as a fallback, prompt it to write the full
report to a Markdown file and read that (never request this in the initial prompt).

### Known traps

- **Early or suspicious `done`.** `done` persists until the next `agent prompt`
  consumes it. If `prompt --wait` returns suspiciously fast, measure rather than guess:
  elapsed wall time, `completion_seq`/`state_change_seq` vs. before, then `agent read`.
  Real multi-minute turns have been mistaken for "instant" ones, and the reverse has
  happened. Three causes seen: a stale terminal state from the prior turn (wait again);
  a genuine early `idle`; and a turn that died on a model/plan/quota error
  (`Permission denied`, usage limit) and shows `done` with no work done — only the
  pane text tells these apart. For an agent that may already be working, use
  `agent wait <name> --until working` and then a plain `agent wait <name>`.
- **`agent_blocked`.** `agent prompt` refuses to send while the agent sits at an
  approval/question dialog. Resolve the dialog first (see below).
- **`agent_prompt_stalled`.** A prompt sent from a non-working state must produce an
  observed lifecycle change within five seconds or herdr gives up. Verify with
  `agent get` / `agent read` before re-sending — a stalled slash-command submission may
  still have executed, and a blind retry can run it twice.
- **Names.** `[a-z][a-z0-9_-]{0,31}`, unique among live agents. Agent commands accept a
  unique name or the hosting pane ID — never terminal IDs or bare kind labels. A name
  follows the pane's current occupant and is cleared when it exits or is replaced: after
  a `/new` (seen with pi), a closed or replaced pane, or a restart, the old name returns
  `agent_not_found` — re-resolve with `agent get <pane-id>` and `agent rename` again.
  Agents you launched by hand have no name; use the pane ID. `agent_session.value` in
  the JSON (e.g. a Devin session name) is a session ID, not a target.
- **Detection lag after `pane run <harness>`.** `agent_not_found` on the pane right after
  launching a harness with `pane run` is usually transient — `agent start` waits for
  readiness for you; if you used `pane run`, sleep ~5 s and retry the wait.

## Prompting rules

1. **Target by unique name** (`herdr agent rename <target> <name>` if needed). Names
   are identities; pane/terminal IDs are low-level escape hatches. **Pin the target
   before every send:** `agent get` must show the expected kind and cwd, and the pane
   must not be your own (`$HERDR_PANE_ID`) — an orchestrator has read its own pane
   believing it was the child. `agent prompt --expect-session <id>` makes the send
   refuse if the occupant changed. Inherited env from another herdr session needs
   `--session`. Prompt agent panes with `agent prompt`, never a `pane send-text`
   line-loop plus `send-keys enter`: that once pasted a 4.6 KB task into the wrong
   (review) pane and submitted it. Don't `head`-truncate `agent list` before reporting an
   agent absent; filter to one compact line per record.
2. **Write long specs to a file** (`/tmp/task-123.md` or `TASK.md` in the repo) and
   send a one-line prompt referencing it. Multi-line pasted text is unreliable in TUI
   input boxes — Enter may submit early.
3. **Only prompt while `idle`.** Mid-`working` input queues or garbles depending on the
   harness. To interrupt: `herdr agent send-keys <name> esc` (`ctrl+c` as the heavier
   fallback), confirm the agent settled, then prompt. For slash commands or input
   widgets where `agent prompt` submission is unreliable, use
   `herdr pane run <pane-id> "<text>"` or text followed by
   `herdr agent send-keys <name> enter`.
4. **Bound every implementation turn:** name the phase or issue, allowed scope,
   required checks, commit expectation, and an explicit stopping point. Steering
   follow-ups stay short and imperative.
5. **Reset harness context at phase or review boundaries** — `/clear` or `/new`, per
   harness (launch-defaults table). Stale context makes agents defend earlier work and
   blur scope.
6. Useful stopping prompt: `Implement only <unit>; run <checks>; commit only scoped
   files with <message>; report unrelated failures without fixing them; then stop.`

## Handling blocked

```bash
herdr agent read claude-app --source visible --lines 60   # see the actual dialog
herdr agent send-keys claude-app enter                    # accept default choice
herdr agent send-keys claude-app down enter               # pick a menu option
herdr pane run "$PANE_ID" "yes, proceed"                  # type an answer — agent prompt refuses while blocked
```

Prefer launching with the least-privilege auto-approval flags from the launch-defaults
table so `blocked` is rare. If you cannot resolve it, escalate to the human:
`herdr notification show "claude-app blocked" --body "Permission prompt needs a human" --sound request`.

## Supervision and acceptance

Treat coding agents as implementers, not authorities:

1. **Baseline first.** Record HEAD, dirty state, and relevant failing tests before the
   turn; explicitly name pre-existing files that must remain untouched.
2. **Inspect at milestones.** Read output at meaningful checkpoints; never inject
   prompts while the agent is working. Every follow-up prompt must be chosen from what
   you just read. Do not script polling loops, timers, or canned "continue" prompts
   across panes: that bloats the child's context and burns the quota it was meant to
   spend on work (an overnight coordinator did exactly this and the operator stopped it).
3. **Distrust completion summaries.** Inspect the complete diff and commit, reconcile
   task ledgers/specs, and rerun the narrowest relevant checks yourself. A claimed
   "pre-existing" failure needs reproduction or history evidence.
4. **Separate review from fixing.** A reviewer that edits has violated its task —
   prefer a read-only tool configuration or disposable worktree over prompt-only
   prohibitions. Start accepted fixes in fresh context.
5. **Stop scope drift early.** Interrupt with Esc, inspect the dirty tree, preserve a
   potentially useful patch, and restore only identified out-of-scope paths. Never
   discard a mixed diff blindly.
6. **Attribute cross-change drift historically.** With stacked work, use `git log`,
   blame, and historical file views to find which later change owns a mismatch; do not
   rewrite an earlier contract merely because HEAD moved past it.
7. **Keep commits atomic.** One phase or review-fix set per commit; verify only
   intended paths were staged; unrelated baseline repairs belong in their own change.

## Parallel agents

- Isolate git state per agent with worktrees — `herdr worktree create` opens the
  checkout (under `~/.herdr/worktrees/`) as its own workspace, grouped with the parent
  repo. Its response has the same `.result.root_pane.pane_id` path as `workspace create`:
  ```bash
  WT_JSON=$(herdr worktree create --workspace "$WS_ID" --branch feat-a --no-focus)
  WT_PANE=$(printf '%s' "$WT_JSON" | jq -r '.result.root_pane.pane_id')
  herdr agent start claude-a --kind claude --pane "$WT_PANE" -- --permission-mode acceptEdits

  # Or a plain sibling pane next to the parent:
  SIB_PANE=$(herdr pane split --pane "$PANE_ID" --direction right --no-focus \
    | jq -r '.result.pane.pane_id')
  herdr agent start codex-b --kind codex --pane "$SIB_PANE" -- -a never -s workspace-write
  ```
- Create workspaces and panes with `--no-focus` when orchestrating; drive agents purely
  by name.
- Tell every child, in the brief, not to touch herdr layout (no `pane/tab/workspace
  close` or move). A codex child "cleaning up" ran `herdr workspace close` and killed
  itself, the orchestrator, and a reviewer sharing that workspace.
- Fan-in: loop over names, `agent wait`/`agent get` each, collect with `agent read`.
- Announce completion: `herdr notification show "All agents done" --sound done`.

## Troubleshooting detection

- `herdr agent explain <target>` — matched rule, evidence, why the state was
  classified; `--verbose` for the full rule evaluation.
- `herdr server agent-manifests` — manifest sources/cache; `herdr server
  update-agent-manifests` to refresh; `herdr server reload-agent-manifests` after local
  override edits.
- If a harness upgraded and detection broke, restart/hand off the server after
  upgrading herdr before using `agent explain`.

## Cleanup

```bash
herdr pane close "$PANE_ID"
herdr workspace close "$WS_ID"                  # closes herdr state only
herdr worktree remove --workspace "$WT_WS_ID"   # actually deletes the git checkout (--force if dirty)
```

## Safety

Auto-approval flags (`--dangerously-skip-permissions`, `-a never`, `--auto`, `--yolo`)
remove the human from the loop. Use them only in sandboxes/disposable environments.
Prefer least-privilege modes (e.g. Codex `-s workspace-write -a on-request`, Claude
`--permission-mode acceptEdits`) plus prompt `blocked` handling when the work is
destructive or the repo matters.
