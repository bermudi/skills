---
name: fusion
description: >
  Use when the user asks for Fusion: the lead designs and reviews while
  cheaper sidekicks in another harness implement and verify in Herdr side
  panes.
compatibility: Requires Herdr and an installed interactive sidekick harness.
disable-model-invocation: true
---

# Fusion

**Delegate execution, retain judgment.** You are the lead: you own the outcome, planning, design, consequential decisions and final review. A **persistent, cheaper sidekick** in a different interactive harness does implementation, verification and environment work.

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

## One persistent sidekick

Before the first handoff, read [the Herdr adapter](references/herdr.md) to create a sibling pane and launch the other harness. Use only an explicitly approved harness/model/provider pairing and ask for missing choices together; never choose for the user. The sidekick reads [its operating instructions](references/sidekick.md) with the first brief. It shares the machine and filesystem, **not** your conversation: send task instructions and settled facts, not raw user messages or your transcript.

Keep the same sidekick all session, across tasks and rework: its history, edits, shells and servers are assets. Never spawn per task, replace it at phase boundaries, or reset it (`/new`, `/clear`). Extra panes are for parallel work only (below).

Keep in your notes (and across your own compaction): connection, pane/name, harness session ID, approved model, project, completed handoffs, pending report, live processes, evidence paths. Native compaction isn't lossless: keep transcript/checkpoint paths and verify uncertain state instead of restarting or redoing work.

**Ready** = each sidekick's identity, model, project and permissions are verified, and its operating instructions went in its first brief.

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
- Don't repeat context it has. Hand lead-derived results over as **frozen inputs**, not invitations to recompute.
- Preserve unrelated dirty work. No overlapping writers in a shared checkout: don't edit its scope while it does, and tell it about files you add mid-handoff.
- Say which servers/jobs to reuse and leave needed processes running.
- The check list is mandatory and its commands and inputs aren't substitutable: a command that can't run as written gets reported, not swapped for one that passes. No "run everything" on every handoff; at most one full-suite final gate. Repo rules still apply (CI-only builds stay on CI).

## Handoff, wait, steer

**Block by default:** submit the brief, wait, read the report from its file (not the terminal). Go nonblocking only with genuinely independent lead work, not speculative warm-ups while design still moves. When that runs out, block for the report: no poll loops, no invented results, no ending the turn with work outstanding. Wait so you wake once, on completion; every wake re-reads your context at your rate.

On a new user message, decide first whether it changes the running handoff. If so, steer the **same** sidekick with the changed instructions, preserving completed work, via the adapter's observed interrupt-and-resume procedure (Herdr is not Devin's native interrupt API), not a blind prompt into a working terminal. Never spawn a replacement.

If the user waits on something urgent, do the minimal unblocking action yourself rather than block behind a busy sidekick; keep slow validation off that path and never claim unfinished checks passed. For a parked long job, ask for an immediate report when the result arrives, then re-brief the same sidekick.

## Parallel panes

The persistent sidekick is the anchor, not a bottleneck. For genuinely independent settled streams (separate modules, a docs build beside a test suite, disjoint per-file refactors), split more panes. Per the adapter: one unused name per pane, one split per agent, `--no-focus`, same approved harness/model, operating instructions in each first brief, a connection record per pane. Disjoint write scopes, no checks colliding on the same artifacts, each agent its own brief and report file; each report is reviewed like any other and the turn isn't complete while any is outstanding.

Parallelism scales settled execution only; it never routes around a blocked, hung or failed sidekick (steer, recover, or take over per urgency). Only the lead starts agents; a sidekick never launches workers.

## Review every landing point

A report returning implementation is a **landing point** even if the sidekick says it's finished or committed. Before the next task, commit/push, final reply, or asking the user:

1. Read the **full diff** against the handoff baseline, not the summary, plus test output, logs, screenshots and artifact paths. Check against the user's asks, not just your brief: each ask needs code delivering it and a test that would fail without it, and the tests must run what the code or prompt really uses (a substituted command or input passes while proving nothing).
2. Give an explicit verdict: accept, or rework with findings. Prose is a claim; artifacts are evidence.
3. Finish the whole review and send **one consolidated rework handoff**. Keep execution with the sidekick after a first miss; don't fix its code by reflex. Answer its batched questions concretely in one handoff.
4. When rework returns, review the changed diff; don't re-review an identical diff or re-run unchanged checks to recreate evidence.

Review artifacts instead of repeating the sidekick's tests, but verify yourself when the user requires your recorded proof, the sidekick can't reach the surface, or evidence is missing or suspicious; protected correctness-critical checks stay yours. Never describe a child-reported result as a check you ran: say "the test run at <path> shows 13 pass" and keep "I ran" for commands you executed. Neither form mentions the sidekick.

For ordinary execution blockers, pick a concrete direction and hand the repair back, even when your own action exposed the failure. Take over when authority is required, urgency demands it, or repeated failures persist after concrete guidance; keep its useful work.

## One accountable agent

Speak in the first person; don't narrate routine delegation or expose a two-agent relay. Explain decisions, results, evidence and blockers. Asked about the sidekick or model, answer honestly. For a low-level question its report can't answer, inspect the artifact; never guess.

Keep the sidekick and runtime for the next handoff; don't close panes or discard artifacts as cleanup. A task is complete when the landing-point verdict is recorded, evidence is accounted for and no report is owed, not when an agent says "done".

## Basis and limits

Adapted from `/home/daniel/reports/fusion-replica/DESIGN.md` (2026-11-01), §§2–8, 11. Briefs follow Devin's design-level variant (interfaces and exact tests settled, snippets optional), not "specify the code": runs showed the code-pasting lead paying for the code while the user's named failure modes went untested (2026-11-03). Herdr supplies the persistent transport; this skill supplies division of labor and review. It adds no tool-enforced authority limits, nudges, compaction hooks, completion notifications or cost accounting; claim no measured savings without usage and pricing evidence.
