# Herdr transport for Fusion

Read this before the first launch and when steering or recovering the
sidekick. The operating policy lives in `../SKILL.md`; Herdr is its transport.
Read the `herdr` skill and run `herdr --skill` for the installed reference.
Use the local skill's explicit-connection policy if the embedded copy still
requires `HERDR_ENV=1` unconditionally.

## Connect and launch once

Inside Herdr, use inherited connection/caller context. Outside it, prefer a
user-supplied socket/session and parent pane; prefix **every** command with
that connection and use explicit IDs, never `--current` or implicit focus.
Do not forge `HERDR_ENV=1`.

With no supplied connection, use the default session, which answers
commands without a prefix. Find the workspace for the lead's checkout:
match `worktree.checkout_path` to the CWD, or `worktree.repo_root` to the
main checkout when the CWD is itself a linked worktree. Open a fresh shell
pane there without disturbing its existing panes:

```bash
herdr workspace list        # match .result.workspaces[].worktree
herdr tab create --workspace "$ws_id" --cwd "$project_dir" --no-focus
```

No match: `herdr workspace create --cwd "$project_dir" --no-focus`, then
use its pane. Parse the new pane's ID from each response or `herdr pane
list`; never infer it. If the default session is not running, ask which
session to use rather than attaching to another silently.

Inspect `herdr agent`, `herdr agent start --help`, and `herdr pane` for syntax
and supported kinds. Do not run bare `herdr` or probe a mutating command by
omitting its arguments.

Establish the parent's harness/project and confirm the sidekick harness
differs. Use only the user-approved model/provider; inspect that harness's
local `--help` for native arguments. Do not silently select a default,
substitute models, install integrations, or add permission-bypass flags.
The sidekick needs scoped editing/command capabilities, not a read-only
reviewer configuration. Configure actual authority restrictions where
supported; a brief alone is not enforcement.

Inspect the parent layout and agent list. Choose one unused name (for
example `fusion-worker`), same tab/cwd, and `--no-focus`. Split right if wide,
down if narrow/tall, unless the user requested a direction. Do not create a
workspace or worktree unless requested. Never adopt an unrelated idle agent.

In this Bash example, set `parent_pane`, `project_dir`, `direction`,
`sidekick`, `chosen_kind`, and the `native_args` array from verified choices.
Commands assume an inherited or default-session connection; add the explicit
prefix for a supplied non-default session.

```bash
split_json=$(herdr pane split --pane "$parent_pane" \
  --direction "$direction" --cwd "$project_dir" --no-focus) || exit 1
side_pane=$(printf '%s' "$split_json" \
  | jq -er '.result.pane.pane_id | strings | select(length > 0)') || exit 1
herdr agent start "$sidekick" --kind "$chosen_kind" --pane "$side_pane" \
  -- "${native_args[@]}"
herdr agent get "$sidekick"
herdr agent read "$sidekick" --source visible --lines 80
```

Parse returned IDs; never infer them. If a response is lost, inspect state
before retrying a mutation. `agent start` requires an existing shell pane.
Verify the actual model/provider, permissions, cwd, and harness before
dispatch. If startup is blocked, inspect the dialog and obtain required
approval. On startup timeout use the pane ID: a name may not have registered.
Shell aliases can inject conflicting flags or bypass modes; do not assume
the startup banner matches the intended launch arguments.

## Handoffs to the same session

Resolve `agent get` before a send: same sidekick, same project/session, not
the lead's pane, settled and ready for input. Use `--expect-session` with
the observed session ID where available.

Put a long lead-authored brief in an approved local scratch file and send
its absolute path. First brief: also point to the absolute path of
`references/sidekick.md` in this skill. Later briefs reuse that context.
Name a report file in the brief, one per handoff, and read that file:
pane reads truncate long reports. Leave underlying evidence artifacts where
they were produced.

Submit, then wait. Blocking on the report is the default:

```bash
herdr agent prompt "$sidekick" "$brief"
herdr agent wait "$sidekick" --timeout 7200000   # background it; see below
cat "$report"
```

A handoff can outlast a foreground tool call: in a 2026-11-03 run, foreground
waits hit Claude Code's 10-minute limit repeatedly, each one a paid wake that
learned nothing. Run the wait as a background command if the harness offers
that (`run_in_background` in Claude Code, which re-invokes the lead when the
command exits; not yet exercised in a Fusion run). Do parallel lead work
meanwhile only if it is independent. Without `--timeout` the wait is unbounded,
so keep a generous one for a sidekick that hangs while reporting `working`.

Herdr timeouts are milliseconds. A timeout does not stop the worker: inspect
state/output before continuing the wait, not resubmitting the brief. Do not
script polling loops. Herdr's settled states (`idle`, `done`, `blocked`) do not
prove successful execution, and a wait begun as the prompt lands may return
early. A settled agent with no report file means read `--source visible` and
decide: `blocked` needs a decision; otherwise ask it to write the report.

## Steering is an adapter, not native message injection

Do not assume `agent prompt` into a working TUI implements Devin's
interrupt-in-place semantics. Consult current harness/Herdr documentation
and observe behavior before using a native live-message facility.

Otherwise inspect state/output, use the harness's documented turn-interrupt
key (commonly Esc via `agent send-keys`), confirm it has settled, and send
the update to the **same** session. Include what remains valid and what has
changed. This pauses a turn; it must not reset context or tear down servers.
If safe interruption is not established, wait for a safe boundary or report
the limitation; never improvise raw input or launch a replacement.

## Recovery without losing persistence

- On `agent_prompt_stalled` or a wait timeout, read before retrying: the
  prompt may have arrived.
- On `blocked`, read `--source visible`; obtain the required decision.
  Do not blindly press Enter or route around approval with pane input.
- On `unknown`, inspect visible output rather than assuming completion.
- On quota/auth/model failure, report the blocker and stop prompting until
  resolved/reset. Do not switch models, restart Herdr, or spin up another
  worker as a workaround.
- If identity is lost, re-resolve the recorded pane and harness session;
  do not substitute another occupant or create a fresh context silently.
- Never close the parent/sidekick, clear context, or kill background
  processes as routine cleanup.

This adapter does not provide native completion notifications, guaranteed
live-update delivery, tool-policy enforcement, or usage counters. Preserve
the Fusion behavior with explicit waits and session records; do not claim
these unavailable mechanisms exist.
