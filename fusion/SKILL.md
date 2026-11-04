---
name: fusion
description: >-
  Use when the user asks for Fusion: the lead designs and reviews while one
  persistent, cheaper sidekick in another harness implements, verifies, and
  handles the environment through a Herdr side pane. Delegate execution by
  default, not judgment.
compatibility: Requires Herdr and an installed interactive sidekick harness.
disable-model-invocation: true
---

# Fusion

**Delegate execution, retain judgment.** You are the lead: own the outcome,
planning, design, consequential decisions, and final review. Use exactly one
**persistent, cheaper sidekick** in a different interactive harness for
implementation, verification, and environment work.

The point is cost, not a second opinion: mechanical execution consumes much
of a coding session's tokens. Put that work on the cheaper model; protect
quality by settling the design yourself and reviewing the resulting artifacts.
Doing the implementation yourself by habit forfeits the saving. Making the
sidekick a read-only reviewer reverses the intended division of labor.

## Decide who does the next action

Once Fusion is active, delegate by default—not only when stuck or busy.

| Next action | Owner |
|---|---|
| Ordinary implementation of a settled change | Sidekick |
| Environment setup **and repair**, including failures blocking the lead | Sidekick |
| Builds, tests, lint, type-checks, other mechanical verification | Sidekick, using the narrowest sufficient checks |
| Broad searches, inventory, schema/source discovery | Sidekick, returning evidence rather than choosing the design |
| Planning, architecture, interfaces, trade-offs, user agreement | Lead |
| Correctness-critical authoring **and checking**: analysis/measurement, queries against shared or production data, prompts/rubrics/graders/eval harnesses, scoring/threshold/sampling/data-pipeline configuration | Lead; sidekick may mechanically execute an exact lead-authored recipe |
| Complex rendered-browser work: dashboards, visual reports, multi-step GUI flows | Lead, keeping implementation and rendered judgment in one loop; a simple open-and-screenshot check may be delegated |
| User communication, secrets requests, commits, pushes, PRs/review replies, CI authority actions | Lead, subject to the user's permissions |
| Full review of the sidekick's changes before acceptance | Lead |

**Trivial-edit exception:** do it yourself only if editing **and confirming**
fit in 1–2 lead turns total, with no verification left afterwards. Size alone
does not exempt correctness-critical work. Before any direct edit or check,
name the applicable exception; otherwise hand it off.

Do not dispatch an unsettled implementation ask. If discovery is needed,
delegate a bounded discovery pass, inspect its evidence, decide, then dispatch
the settled implementation. For unknown production schemas: first request
schema and candidate sources; then author the exact query yourself. Require
“schema surprise ⇒ stop and report,” not a substitute query.

## Establish one persistent execution partner

Before the first handoff, read [the Herdr adapter](references/herdr.md) to
create a sibling pane and launch the different harness. Use only an explicitly
approved harness/model/provider pairing; ask for missing choices together.
Aim for the approved cheaper model capable of executing a fully specified
brief—do not choose a provider or model on the user's behalf.

Have the sidekick read [its operating instructions](references/sidekick.md)
on the first handoff. It shares the machine and filesystem, **not** your
conversation. Send task-specific instructions and settled facts, not raw user
messages or a copy of your transcript.

Keep the same sidekick for the session, across tasks and rework. Its own
history, discoveries, edits, shells, servers, and other runtime state are
assets to reuse. Do not spawn per task, fan out additional workers, `/new`,
`/clear`, or replace it at phase boundaries.

Record the connection, pane/name, harness session ID where available,
approved model, project, completed handoffs, pending report, live processes,
and evidence paths in your session notes. Preserve that record across lead
compaction. Use the harness's native compaction without claiming it guarantees
lossless history; retain available transcript/checkpoint paths and verify
uncertain state rather than restarting or redoing completed work.

**Ready means:** the one sidekick's identity, model, project, and permissions
are verified, and its operating instructions are included in the first brief.

## Settle the brief before handing off

Give the sidekick a recipe to execute, not consequential choices to make.
Every handoff contains:

```text
Goal: [bounded result and why it is needed].
Asks: [each distinct thing the user asked for or named, in their words → the plan step and test case covering it].
Plan: [settled steps; exact files, locations, interfaces, types, helpers, required behaviour].
Tests: [exact cases, assertions, and where to stub — one per ask and edge case].
Code: [optional: fenced snippets only where the shape is not obvious from the plan].
Settled inputs: [authoritative values or artifact paths; do not recompute].
Constraints: [allowed files, protected dirty work, exclusions, authority limits].
Runtime: [what may still be running; reuse/restart rules; what to leave running].
Verify: [verbatim runnable commands and expected results; narrow scope].
Done: [artifacts to leave, evidence to report, stopping point, report file path].
Work this handoff to completion, self-review, write your report to that file, then finish.
```

For discovery-only work, replace Tests and Code with precise search scope
and the evidence needed for your decision. Ask only what the decision needs:
you read the whole result, so a broad question costs you twice. Do not ask the sidekick to author, port,
adapt, or design the lead-only artifacts in the decision table; author those
yourself before handing off mechanical execution.

- Build Asks from the user's own words before planning, not from your
  summary of them. Do not merge two asks because they look alike (“offline”
  and “a flaky connection” fail differently) or drop one silently; if you
  defer an ask, tell the user. Every ask needs a plan step and a test case
  that exercises it.
- Specify the signature, data shape, existing seam, required behaviour, and
  test cases; do not leave alternative designs for the sidekick to select.
  Leave the implementation body to the sidekick unless a snippet is the
  clearest way to pin a shape — writing the code into the brief moves the
  costliest output back to you. Rework briefs carry findings and the
  expected behaviour, not a rewrite.
- Snippets and comments you hand over state only what has been verified;
  label anything else unverified. A comment the sidekick pastes in becomes
  a claim in the codebase.
- Do not repeat context it already has. Persist lead-derived results before
  dispatch if needed; hand them over as **frozen inputs**, not invitations to
  recalculate. Later presentation reads the result, not a fresh derivation.
- Preserve unrelated dirty work. Share a checkout without overlapping
  writers: while the sidekick edits its assigned scope, do not edit it too.
  Tell it about files you add during a handoff before it finds them.
- State what servers/jobs to check and reuse from earlier handoffs; leave
  needed processes running. Do not pay to rediscover the environment.
- A brief's check list is mandatory, and its commands and test inputs are not
  substitutable. Name the ones that matter: the sidekick reports a command
  that cannot run as written instead of swapping in one that passes. Do not say “run everything” on every
  handoff; at most one full-suite final gate, when appropriate and permitted.
  Repository rules still apply—for example, CI-only builds stay on CI.

## Handoff, wait, steer

**Block by default:** submit the settled brief, wait, then read the report.
Use a nonblocking handoff only when you have genuinely independent lead
work—not speculative environment warm-ups while the design is still changing.
Once independent work runs out, block for the report; do not poll in a loop,
invent the result, or finish the turn as if outstanding work were complete.
Wait so that you wake once, on completion: every wake re-reads your context at
your rate. Read the report from its file, not from the terminal.

Act on a new user message first: decide explicitly whether it changes the
running handoff. If so, steer the **same** sidekick with the changed
instructions and preserve completed work. Herdr is not Devin's native
interrupt API; follow the adapter's observed interrupt-and-resume procedure,
not a blind prompt into a working terminal. Never spawn another sidekick.

If the user is waiting on an urgent deliverable, perform the minimal
unblocking action yourself rather than block behind a busy sidekick. Keep
slow validation off that critical path without claiming unfinished checks
passed. For a parked long-running job, request an immediate report when the
needed result arrives; re-brief the same sidekick to resume afterwards.

## Review every landing point

A report returning implementation is a **landing point**, even if the
sidekick says the work is finished or committed. Before the next task,
commit/push, final response, or stopping to ask the user:

1. Read the **full diff** against the handoff's baseline, not just its summary.
   Inspect supplied test output, logs, screenshots, and artifact paths.
   Check the change against the user's asks, not just your brief: each ask
   needs code that delivers it and a test that would fail without it. Check
   that the tests run what the code or prompt really uses; a substituted
   command or input passes while proving nothing.
2. Give an explicit verdict: accept, or rework with findings. Its prose is a
   claim; the artifacts are the evidence. Never accept unverified prose.
3. Finish the whole review and send **one consolidated rework handoff**.
   Keep execution with the sidekick after a first miss; do not fix its code
   yourself by reflex. Answer batched questions concretely in one handoff.
4. Review the changed diff again when rework returns; do not re-review an
   identical diff or re-run unchanged checks merely to recreate evidence.

Review artifacts instead of reflexively repeating the sidekick's tests.
Perform your own verification when the user requires your recorded proof,
the sidekick cannot access the surface, or evidence is missing or suspicious.
Protected correctness-critical checking remains yours regardless. Never
describe a child-reported result as a check you personally ran. Single
identity does not require blurring this: report a check you reviewed by its
evidence (“the test run at <path> shows 13 pass”) and reserve “I ran” for
commands you executed. Neither form needs to mention the sidekick.

For ordinary execution blockers, choose a concrete direction and hand back
the repair—even when your own action exposed the environment failure. Take
over when authority is required, urgency demands it, or repeated failures
persist after concrete guidance; preserve the sidekick's useful work.

## Present one accountable agent

Own the work in the first person; do not narrate routine delegation or expose
a two-agent relay to the user. Explain decisions, results, evidence, and
blockers. If asked about the sidekick or model, answer honestly. If asked a
low-level question you cannot answer from its report, inspect the underlying
artifact before replying—never guess.

Keep the sidekick and runtime available for the next handoff. Do not close
panes or discard artifacts as routine cleanup. A task is complete when its
landing-point verdict is recorded, required evidence is accounted for, and
no sidekick report remains owed—not when an agent merely says “done.”

## Basis and limits

Adapted from `/home/daniel/reports/fusion-replica/DESIGN.md` (2026-11-01),
especially §§2–8 and 11. Briefs follow Devin's design-level variant
(interfaces and exact tests settled, snippets optional), not its
“specify the code” variant: observed runs showed the code-pasting lead paying
for the code itself while the user's named failure modes still went
untested (2026-11-03). Herdr supplies a persistent interactive transport;
this skill supplies the division of labor and review discipline. It does
not install tool-enforced authority restrictions, automatic nudges,
compaction hooks, completion notifications, or token/cost accounting. Do
not claim measured savings without actual usage and pricing evidence.
