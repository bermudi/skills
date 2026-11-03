# Herdr transport for Fusion

Read this before the first launch and when steering or recovering the
sidekick. The operating policy lives in `../SKILL.md`; Herdr is its transport.
Read the `herdr` skill and run `herdr --skill` for the installed reference.
Use the local skill's explicit-connection policy if the embedded copy still
requires `HERDR_ENV=1` unconditionally.

## Connect and launch once

Inside Herdr, use inherited connection/caller context. Outside it, require
a user-supplied socket/session and parent pane; prefix **every** command
with that connection and use explicit IDs, never `--current` or implicit
focus. Do not forge `HERDR_ENV=1` or attach to a focused/default session.

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
Commands assume an inherited connection; add the explicit prefix outside it.

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
Initially request a concise terminal report; leave underlying evidence
artifacts where they were produced.

Blocking is the default:

```bash
herdr agent prompt "$sidekick" "$brief" --wait --timeout 120000
herdr agent read "$sidekick" --source recent-unwrapped --lines 160
```

For independent parallel lead work, omit `--wait`; when finished with that
work, block for completion and read:

```bash
herdr agent wait "$sidekick" --timeout 120000
herdr agent read "$sidekick" --source recent-unwrapped --lines 160
```

Herdr timeouts are milliseconds; allow sufficient time in the enclosing
tool's own units. A timeout does not stop the worker: inspect state/output
before continuing the wait, not resubmitting the brief. Do not script
polling loops. Herdr's settled states (`idle`, `done`, `blocked`) do not prove
successful execution. If output is inaccessible, try a larger bounded read,
then ask the settled agent to save the report to a temporary Markdown file.

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
