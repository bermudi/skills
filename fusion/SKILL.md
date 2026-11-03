---
name: fusion
description: >-
  Use when the user asks for fusion: a sidekick in a different coding-agent
  harness, running beside the main agent in a Herdr side pane. Covers launch,
  bounded delegation, follow-up, and independent verification. Not for ordinary
  same-harness subagents or unrelated pane management.
compatibility: Requires Herdr and an installed interactive sidekick harness.
---

# Fusion

**One lead, one cross-harness sidekick.** Keep responsibility for the task in
this conversation; use a different interactive coding harness in a Herdr sibling
pane for a bounded second opinion, investigation, or delegated implementation.
A different model in the same harness is not fusion. A hidden subagent or
headless subprocess is not a substitute for the requested side pane.

## Establish the connection and launch choices

Read the `herdr` skill and run `herdr --skill` for the installed command
reference. Use the local skill's connection policy if the embedded copy still
insists that callers must always be inside Herdr:

- Inside Herdr (`HERDR_ENV=1`), use the inherited connection and caller pane.
- Outside Herdr, use only an explicit user-supplied socket or session. Prefix
  **every** command with that connection, for example
  `HERDR_SOCKET_PATH=/path/from/user herdr agent list` or
  `herdr --session supplied-name agent list`. Use explicit pane IDs.
- Without either, ask which connection and parent pane to use. Do not attach
  to a focused/default session or set `HERDR_ENV=1` yourself.

Discover syntax without changing layout:

```bash
herdr --help
herdr agent
herdr agent start --help
herdr pane
```

Do not run bare `herdr` (it opens the TUI) or probe mutating commands by
omitting arguments. The installed binary, not copied examples, decides which
agent kinds and flags are supported.

Before creating a pane:

1. Establish the lead's harness, project directory, and parent pane. Inside
   Herdr, use `herdr pane current --current` and, when needed,
   `herdr agent get "$HERDR_PANE_ID"`; outside it, inspect the explicitly
   supplied parent. Use observed identity rather than guessing from a model
   name. If identity cannot be established, ask.
2. Honor the requested sidekick harness and verify it differs from the lead.
   If unspecified, ask which installed alternative to use. If unavailable,
   report that and ask for an alternative; do not silently substitute.
3. Use only a model and provider explicitly approved by the user or standing
   project instructions. Harness approval is not model approval. Ask for
   missing choices together, before launch; do not rely on an unverified
   default or silently switch models on failure.
4. Check the chosen harness's local `--help` for native model and permission
   flags. Prefer a read-only tool/sandbox configuration for review. Do not
   add bypass/YOLO flags, grant repository trust, install integrations, or
   change global defaults just to make startup succeed.

## Create the sibling pane, then start the harness

Default to one sidekick, the same tab and working directory, and no focus
change. Do not create a workspace, tab, or worktree unless the user requests
that topology. Inspect layout and existing agents first:

```bash
herdr pane layout --pane "$parent_pane"
herdr agent list
```

Use an unused agent name such as `fusion-review` (names must match
`[a-z][a-z0-9_-]{0,31}`). Never take over an existing agent just because it
looks idle. Honor a requested split direction; otherwise split a wide pane
right and a narrow/tall pane down.

The following Bash example assumes `parent_pane`, `project_dir`, `direction`,
`sidekick`, `chosen_kind`, and the `native_args` array have been set from
those verified choices. `native_args` contains only the harness's own
arguments, including the approved model/provider selection where supported.
Examples below use an inherited connection; apply the explicit connection
prefix throughout when outside Herdr.

```bash
split_json=$(herdr pane split --pane "$parent_pane" \
  --direction "$direction" --cwd "$project_dir" --no-focus) || exit 1
side_pane=$(printf '%s' "$split_json" \
  | jq -er '.result.pane.pane_id | strings | select(length > 0)') || exit 1

herdr agent start "$sidekick" --kind "$chosen_kind" --pane "$side_pane" \
  -- "${native_args[@]}"
```

`agent start` does not create layout: split first and parse the **returned**
pane ID. Do not infer it from sidebar order or sample IDs. If a split's
response is lost or unparsable, inspect the parent's pane list/layout before
retrying; the pane may already exist.

Wait for startup readiness, then inspect:

```bash
herdr agent get "$sidekick"
herdr agent read "$sidekick" --source visible --lines 80
```

Confirm the actual harness, model/provider, cwd, and permission mode before
submitting work. Use visible startup information and harness-supported
read-only inspection as needed; if model/provider cannot be verified, stop
and label it unverified. Shell aliases can inject permissions or conflicting
flags; inspect actual startup failures rather than guessing at a repair.

On `agent_not_ready`, inspect the dialog; the name may still be usable.
On startup timeout, inspect the **pane ID**, because the name may not have
registered. Do not start a second harness in an occupied pane.

## Brief the sidekick

The sidekick does not inherit this conversation. Give it the problem,
relevant context and paths, scope, and a concrete stopping point.
Default to read-only analysis; ask it to report findings rather than
immediately fixing its own review.

Use this shape, replacing the brackets with task-specific details:

```text
You are the sidekick; the lead agent owns integration and the final answer.
Goal: [one bounded question or deliverable].
Project: [absolute directory]. Read its applicable AGENTS.md instructions.
Context: [user intent, relevant files/diff, known constraints].
Scope: read-only investigation; do not edit files or commit.
Do not change Herdr layout, close panes, launch other agents, or choose a
different model/provider. Stop and report if you need additional authority.
Return: findings ranked by impact, file/line or command evidence, proposed
next steps, checks actually run, and remaining uncertainty. Then stop.
```

For implementation explicitly requested by the user, replace the read-only
line with allowed files, excluded files, required checks, and whether a
commit is wanted. Record HEAD and dirty state first. In a shared checkout,
give the sidekick exclusive ownership of its files and do not edit them
concurrently; if clean separation is impossible, serialize work or ask for
an isolated checkout. Do not silently create another topology.

Send a short brief directly with `agent prompt`. For a long brief, write a
task-specific Markdown file in an approved local scratch location and send
its absolute path; do not dump the entire conversation, secrets, or unrelated
transcripts. Request the answer in the terminal initially, not a report file.

## Delegate, observe, and follow up

Immediately before sending, resolve the target again with `agent get`:
it must be the expected harness in the side pane, not the lead's pane,
and ready for input (`idle` or `done`, with no dialog). Where an agent
session ID is available, use the documented `--expect-session` guard.

```bash
herdr agent prompt "$sidekick" "$brief" --wait --timeout 120000
herdr agent read "$sidekick" --source recent-unwrapped --lines 160
```

Herdr timeouts are **milliseconds**; the enclosing tool's timeout may be
seconds. Give that tool enough time. For longer work, continue with a bounded
`herdr agent wait "$sidekick" --timeout 120000` rather than resubmitting.
Do not send another prompt while the sidekick is working. The lead can do
independent, nonconflicting work between supervision checkpoints.

- **Settled is not successful.** `--wait` normally returns on `idle`,
  `done`, or `blocked`. Read the answer; a quota/model error can also end a turn.
- **Timeout or `agent_prompt_stalled`:** inspect `agent get` and
  `agent read` before retrying. Delivery may already have happened.
- **Blocked:** read `--source visible`, explain the actual question to the
  user, and obtain the required decision. Never blindly press Enter or use
  raw pane input to bypass an approval.
- **Unknown state:** inspect visible output; do not equate it with completion
  or launch a duplicate. Do not install/upgrade/restart Herdr to repair it
  without authorization.
- **Quota/auth/model failure:** report it and stop using that sidekick until
  resolved or its stated reset time. Do not keep sending “continue” or
  select another model/provider.
- **Missing answer:** try a larger bounded recent read. If terminal history
  still cannot expose it, ask the settled sidekick to write its answer as
  Markdown in a temporary directory and return the absolute path. Read that
  file on the same machine.

Choose each follow-up from the answer just read. Ask for missing evidence or
one bounded correction; do not run an unattended loop of canned prompts.
Do not reset, replace, or resume a different session without checking its
identity and launch choices again.

## Verify and synthesize

Treat the sidekick's output as a proposal, not authority:

1. Inspect cited source, reproduce key observations, and run the narrowest
   relevant checks. For implementation, inspect the full diff against the
   recorded baseline and preserve unrelated user changes.
2. Reconcile disagreements explicitly: what you accepted, rejected, or
   could not verify, and why. Do not count agreement between models as proof.
3. Give the user one integrated answer, naming the sidekick harness/model,
   its contribution, and the checks **you actually performed**. Distinguish
   child-reported tests from independently observed results.
4. Leave the pane/session available by default. Report its agent name and
   pane ID for follow-up. Close it only when explicitly requested; never
   close the parent or someone else's pane or discard work as cleanup.

Fusion is complete when the bounded sidekick assignment is resolved or
clearly blocked, its claims have been checked to the stated extent, and the
lead has delivered the integrated result and remaining uncertainties.
