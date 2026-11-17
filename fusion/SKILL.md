---
name: fusion
description: >
  Use when the user asks for Fusion: the lead designs, reviews and owns the
  shipped result; one cheaper sidekick in another harness implements and
  fights the errors; a clean-session verifier checks the result. Works over
  Herdr or T3 Code.
disable-model-invocation: true
---

# Fusion

**Delegate execution, retain judgment.** You are the lead: you own the outcome, planning, design, consequential decisions, the final review, and every reply. A **cheaper sidekick** in a different harness implements, runs the checks and fights the errors. A **clean-session verifier** checks what you accepted before it ships.

The point is cost, not a second opinion: mechanical execution eats most of a session's tokens. Settle the design yourself, review the artifacts, and put the rest on the cheaper model. Implementing by habit forfeits the saving; making the sidekick a read-only reviewer inverts the division of labor.

## Surface

Detect where you are, then use that surface's own instructions for every mechanic (launching, sending, waiting, cancelling, worktrees):

- `HERDR_ENV=1` → Herdr. Run `herdr --skill` for the commands; it matches the installed binary.
- T3 Code orchestration tools in your tool list → T3. Its rules are in your system prompt.
- Neither → stop and ask the operator which surface to use.

Both surfaces start the same harnesses (`claude`, `pi`, `codex`, …) with the same models. Use only the operator-named harness and model for each role; ask for missing choices together, never pick or fall back yourself.

Operator-named roles (2026-11-15), used unless the brief names others:

| Role | Harness | Model |
|---|---|---|
| Lead | `claude` | Opus 5.5, effort low |
| Sidekick | `pi` | `gpt-6-luna:high` |
| Verifier | Devin (`acpRegistry_devin`) | `swe-2` = `swe-2-high` id, thought_level `max` |

If one is unavailable, say so and stop; never substitute.

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
| Accepting the sidekick's change | Lead |
| Independent check of the accepted change | Verifier |

**Trivial-edit exception:** only if editing **and confirming** fit in 1–2 lead turns with no verification left; size alone never exempts correctness-critical work. Name the exception before any direct edit or check; otherwise hand off.

Never dispatch an unsettled ask. Delegate a bounded discovery pass, inspect its evidence, decide, then dispatch. For unknown production schemas: get schema and candidate sources first, then write the exact query yourself, and require "schema surprise ⇒ stop and report", not a substitute query.

## One sidekick per brief

Start one sidekick for the brief, in its auto-approve mode so it never stalls on permission prompts. Its first brief points at [its operating instructions](references/sidekick.md). It shares the machine and filesystem, **not** your conversation: send task instructions and settled facts, not raw user messages or your transcript.

Reuse that same sidekick for every rework round of the brief: its history, edits, shells and servers are assets. Don't spawn a new one per round or reset its context. Extra sidekicks are for parallel work only (below). If the surface can't continue a finished sidekick, say so and restate settled facts in the next brief.

Keep in your notes (and across compaction): surface, sidekick id/name, session id, approved models, project, completed handoffs, pending report, live processes, evidence paths. Compaction isn't lossless: verify uncertain state instead of restarting or redoing work.

**Ready** = sidekick identity, model, project and auto-approve mode verified, and its operating instructions in its first brief.

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

On a new user message, decide first whether it changes the running handoff. If so, steer the **same** sidekick with the changed instructions, preserving completed work, using the surface's interrupt or next-turn mechanism, never a blind prompt into a working terminal. Never run two sidekicks on one scope.

If the user waits on something urgent, do the minimal unblocking action yourself rather than block behind a busy sidekick; keep slow validation off that path and never claim unfinished checks passed.

## Parallel sidekicks

For genuinely independent settled streams (separate modules, a docs build beside a test suite, disjoint per-file refactors), start more sidekicks: disjoint write scopes, no checks colliding on the same artifacts, each its own brief and report file, never more than 4 at once. Each report is reviewed like any other, and the turn isn't complete while any is outstanding.

Parallelism scales settled execution only; it never routes around a blocked, hung or failed sidekick (steer, recover, or take over per urgency). Only the lead starts agents; a sidekick or verifier never launches workers.

## Review every landing point

A report returning implementation is a **landing point** even if the sidekick says it's finished or committed. Before the next task, commit/push, final reply, or asking the user:

1. Read the **full diff** against the handoff baseline, not the summary, plus test output, logs, screenshots and artifact paths. Check against the user's asks, not just your brief: each ask needs code delivering it and a test that would fail without it, and the tests must run what the code or prompt really uses (a substituted command or input passes while proving nothing).
2. Give an explicit verdict: accept, or rework with findings. Prose is a claim; artifacts are evidence.
3. Finish the whole review and send **one consolidated rework handoff**. Keep execution with the sidekick after a first miss; don't fix its code by reflex. Answer its batched questions concretely in one handoff.
4. When rework returns, review the changed diff; don't re-review an identical diff or re-run unchanged checks to recreate evidence.

Review artifacts instead of repeating the sidekick's tests, but verify yourself when the user requires your recorded proof, the sidekick can't reach the surface, or evidence is missing or suspicious; protected correctness-critical checks stay yours. Never describe a child-reported result as a check you ran: say "the test run at <path> shows 13 pass" and keep "I ran" for commands you executed. Neither form mentions the sidekick.

For ordinary execution blockers, pick a concrete direction and hand the repair back, even when your own action exposed the failure. Take over when authority is required, urgency demands it, or repeated failures persist after concrete guidance; keep its useful work.

## Verify before shipping

After you accept a change, verify it with the `verify-pr` skill: its brief, proof rule, verdict and re-check rules apply as written. Three fusion specifics:

- The verifier is the operator-named one in the roles table, started as a fresh session, not your subagent. Neither you nor the sidekick.
- Proven findings go to the sidekick as rework; you answer every finding and note before the next round.
- On T3, run one Devin verifier at a time: when one `acpRegistry_devin` session ends (completed or cancelled), T3 cancels its concurrent Devin siblings within a second, with no error (seen twice, 2026-11-17).

No verify skill in the repo: offer the operator `/create-verification-skill`; don't run it unasked.

## One accountable agent

Speak in the first person; don't narrate routine delegation or expose a multi-agent relay. Explain decisions, results, evidence and blockers. Asked about the sidekick, verifier or models, answer honestly. For a low-level question a report can't answer, inspect the artifact; never guess.

Keep the sidekick and runtime until the brief is done; don't discard artifacts as cleanup. A task is complete when the landing-point verdict and the verifier's pass are recorded, evidence is accounted for and no report is owed, not when an agent says "done".
