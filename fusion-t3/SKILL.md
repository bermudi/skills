---
name: fusion-t3
description: >
  Use when the user asks for Fusion over T3 Code (fusion-t3): the lead
  designs and reviews while cheaper sidekicks on another provider's model
  implement and verify as delegated tasks.
compatibility: Requires T3 Code orchestration (delegate_task, task_cancel).
disable-model-invocation: true
---

# Fusion (T3 Code)

**Delegate execution, retain judgment.** You are the lead: you own the outcome, planning, design, consequential decisions and final review. A **cheaper sidekick** on another provider's model does implementation, verification and environment work, dispatched with `delegate_task`.

The point is cost, not a second opinion: mechanical execution eats much of a session's tokens. Settle the design yourself, review the artifacts, and put the rest on the cheaper model. Implementing by habit forfeits the saving; making the sidekick a read-only reviewer inverts the division of labor.

## Who does the next action

Once active, delegate by default, not only when stuck or busy.

| Next action | Owner |
|---|---|
| Implementation of a settled change | Sidekick |
| Environment setup **and repair**, including failures blocking you | Sidekick |
| Builds, tests, lint, type-checks, mechanical verification | Sidekick, narrowest sufficient checks |
| Broad search, inventory, schema/source discovery | Sidekick, returning evidence, not design choices |
| Planning, architecture, interfaces, trade-offs, user agreement | Lead |
| Correctness-critical authoring **and checking**: analysis/measurement, queries on shared or production data, prompts/rubrics/graders/eval harnesses, scoring/threshold/sampling/pipeline config | Lead; sidekick may execute an exact lead-authored recipe |
| Complex rendered-browser work (dashboards, visual reports, multi-step GUI flows) | Lead; a plain open-and-screenshot may be delegated |
| User communication, secret requests, commits, pushes, PRs, CI authority actions | Lead, within the user's permissions |
| Full review of the sidekick's changes | Lead |

**Trivial-edit exception:** only if editing **and confirming** fit in 1–2 lead turns with no verification left; size alone never exempts correctness-critical work. Name the exception before any direct edit or check; otherwise hand off.

Never dispatch an unsettled ask. Delegate a bounded discovery pass, inspect its evidence, decide, then dispatch. For unknown production schemas: get schema and candidate sources first, then write the exact query yourself, and require "schema surprise ⇒ stop and report", not a substitute query.

## One sidekick target, fresh delegates

Unlike `fusion-herdr`, T3 delegates are **not persistent**: every handoff, review and re-check is a new `delegate_task` — never a `t3_thread_send` continuation. Continuity lives in the shared filesystem and report files, not a shared conversation.

Before the first dispatch, read [the T3 adapter](references/t3.md) and call `orchestrator_capabilities` once. Ask the operator for the sidekick provider/model pairing (and any settings beyond yours) together; never choose for the user. If a named provider or model is unavailable, say so — never switch or fall back unasked. Record the approved `target` and reuse it for every delegate.

Each delegate starts with no memory: every brief is self-contained, restating settled facts, pointing to [the sidekick instructions](references/sidekick.md), and naming previous report/evidence paths. Frozen inputs stay frozen — a fresh delegate that rederives them is paying twice. A delegate that continues earlier work reads the tree and those paths as the record; it never re-verifies unchanged inputs.

Keep in your notes (and across compaction): the approved target, dispatch/request IDs, completed handoffs, report and evidence paths, live processes.

**Ready** = capabilities read, the operator-named target recorded, and the sidekick instructions referenced in the first brief.

## Settle the brief first

Give a recipe to execute, not consequential choices to make:

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

Discovery-only: replace Tests and Code with search scope and the evidence you need. Ask only what the decision needs; you read the whole result, so a broad question costs you twice. Never have the sidekick author or adapt the lead-only artifacts above.

- **Asks come from the user's own words**, not your summary. Don't merge look-alikes ("offline" vs "flaky connection" fail differently) or drop one silently; tell the user if you defer one. Each needs a plan step and a test that would fail without it.
- Pin signature, data shape, seam, behaviour and test cases; leave no alternative designs. Leave the implementation body to the sidekick unless a snippet is the clearest way to pin a shape: writing code into the brief moves the costliest output back to you. Rework briefs carry findings and expected behaviour, not a rewrite.
- Snippets and comments you hand over state only verified facts, labelled otherwise: a pasted comment becomes a claim in the codebase.
- Restate what a returning task must know — its context is fresh — but hand lead-derived results over as **frozen inputs**, not invitations to recompute.
- Preserve unrelated dirty work. No overlapping writers in a shared checkout: don't edit its scope while it does, and tell it about files you add mid-handoff.
- Say which servers/jobs to reuse and leave needed processes running.
- The check list is mandatory and its commands and inputs aren't substitutable: a command that can't run as written gets reported, not swapped for one that passes. No "run everything" on every handoff; at most one full-suite final gate. Repo rules still apply (CI-only builds stay on CI).

## Dispatch, wait, steer

One `delegate_task` per handoff — the brief, a consolidated rework, or a re-check is each a new dispatch. Block by default: follow the running delegate's `next`; do not poll (`task_status`, sleep, watchers) and never end the turn with a report owed or invent a result. Go nonblocking only with genuinely independent lead work; when that runs out, wait for the result.

On a new user message, decide first whether it changes the running handoff. If so, `task_cancel` the delegate (never `t3_thread_interrupt` on a child), then dispatch one new `delegate_task` whose brief states what changed, what remains valid, and to preserve completed work and live processes. Never spawn a replacement while the old one still runs.

If the user waits on something urgent, do the minimal unblocking action yourself rather than block behind a busy sidekick; keep slow validation off that path and never claim unfinished checks passed.

## Parallel delegates

The sidekick target is the anchor, not a bottleneck. For genuinely independent settled streams (separate modules, a docs build beside a test suite, disjoint per-file refactors), dispatch several delegates: disjoint write scopes, no checks colliding on the same artifacts, each its own brief and report file, never more than 4 at once. A separate checkout comes only from the delegate's own worktree isolation — never create a child checkout in the shell. When told to run fewer, `task_cancel` the extras; start no replacements. Each report is reviewed like any other, and the turn isn't complete while any is outstanding.

Parallelism scales settled execution only; it never routes around a blocked, hung or failed delegate (steer, recover, or take over per urgency). Only the lead dispatches delegates; a sidekick never launches workers.

## Review every landing point

A report returning implementation is a **landing point** even if the sidekick says it's finished or committed. Before the next task, commit/push, final reply, or asking the user:

1. Read the **full diff** against the handoff baseline, not the summary, plus test output, logs, screenshots and artifact paths. Check against the user's asks, not just your brief: each ask needs code delivering it and a test that would fail without it, and the tests must run what the code or prompt really uses (a substituted command or input passes while proving nothing).
2. Give an explicit verdict: accept, or rework with findings. Prose is a claim; artifacts are evidence.
3. Finish the whole review and send **one consolidated rework dispatch**. Keep execution with the sidekick after a first miss; don't fix its code by reflex. Answer its batched questions concretely in one brief.
4. When rework returns, review the changed diff; don't re-review an identical diff or re-run unchanged checks to recreate evidence.

Review artifacts instead of repeating the sidekick's tests, but verify yourself when the user requires your recorded proof, the sidekick can't reach the surface, or evidence is missing or suspicious; protected correctness-critical checks stay yours. Never describe a child-reported result as a check you ran: say "the test run at <path> shows 13 pass" and keep "I ran" for commands you executed. Neither form mentions the sidekick.

For ordinary execution blockers, pick a concrete direction and hand the repair back, even when your own action exposed the failure. Take over when authority is required, urgency demands it, or repeated failures persist after concrete guidance; keep its useful work.

## One accountable agent

Speak in the first person; don't narrate routine delegation or expose a two-agent relay. Explain decisions, results, evidence and blockers. Asked about the sidekick or model, answer honestly. For a low-level question its report can't answer, inspect the artifact; never guess.

Keep the approved target and runtime understanding for the next handoff; don't discard artifacts as cleanup. A task is complete when the landing-point verdict is recorded, evidence is accounted for and no report is owed, not when an agent says "done".

## Basis and limits

Same division-of-labor policy as `fusion-herdr` (adapted from `/home/daniel/reports/fusion-replica/DESIGN.md`, 2026-11-01, §§2–8, 11). T3 Code `delegate_task` replaces Herdr as the transport, so the persistent sidekick becomes fresh delegates with filesystem continuity (2026-11-07). It adds no tool-enforced authority limits, nudges, compaction hooks, completion notifications or cost accounting; claim no measured savings without usage and pricing evidence.
