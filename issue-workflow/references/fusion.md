# Fusion

**Delegate execution, retain judgment.** You are the lead and you carry the task to the end: design, consequential decisions, review, verification, the PR and every reply are yours. A **cheaper sidekick** in a different harness implements, runs the checks and fights the errors. A **clean-session verifier** checks what you accepted before it ships.

**Done** = the PR is marked ready after a verifier pass (`issue-workflow`), and the user has your one final report. Merging still needs the user's green light.

The user says "no sidekick" → you implement yourself. Everything else holds: the playbook, review of your own diff against the asks, and the verifier.

Pick the task's playbook from the `engineering` skill and follow its steps. Name it and the principles it uses in the sidekick's brief, so the sidekick reads the same files.

The point is cost, not a second opinion: mechanical execution eats most of a session's tokens. Settle the design yourself, review the artifacts, and put the rest on the cheaper model. Implementing by habit forfeits the saving; making the sidekick a read-only reviewer inverts the division of labor.

## Surface

Detect where you are, then use that surface's own instructions for every mechanic (launching, sending, waiting, cancelling, worktrees):

- `HERDR_ENV=1` → Herdr. Run `herdr --skill` for the commands; it matches the installed binary.
- T3 Code orchestration tools in your tool list → T3. Its rules are in your system prompt.
- Neither → stop and ask the user which surface to use.

## Models

Before starting any agent, ask the user once which harness and model to use for the sidekick and the verifier. Use your harness's question tool with options; skip what the task already names (the user or Goblin may pass the pick in). Offer these, the first as default:

| Option | Sidekick | Verifier |
|---|---|---|
| Default | `pi`, `gpt-6-luna:high` | Devin (`acpRegistry_devin`), `swe-2-high`, thought_level `max` (operator, 2026-11-20: GLM quota is almost out) |
| GLM quota available | `pi`, `gpt-6-luna:high` | Piz (`acpRegistry_piz`), GLM-5.3 (`account:zai-individual-coding-plan/GLM-5.3`), thought_level `max` |
| Other | user types it | user types it |

Use only what the user picks. If one is unavailable, say so and stop; never substitute.

Model notes: `swe-2-flash` means `swe-2-flash-max` (lower levels quit early) and can't see images: visual checks go to `swe-2`. GLM: about 7 at once across all coordinators, so 4 per coordinator when several run.

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

Start one sidekick for the brief, in its auto-approve mode so it never stalls on permission prompts. Its first brief points at [its operating instructions](sidekick.md). It shares the machine and filesystem, **not** your conversation: send task instructions and settled facts, not raw user messages or your transcript.

Reuse that same sidekick for every rework round of the brief: its history, edits, shells and servers are assets. Don't spawn a new one per round or reset its context. Sidekick harnesses cap context at about 250k tokens, so a reused one stays out of the long-context zone where reasoning degrades; when one hits the cap, start a fresh sidekick with the settled facts and its last report. Extra sidekicks are for parallel work only (below). If the surface can't continue a finished sidekick, say so and restate settled facts in the next brief.

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

For genuinely independent settled streams (separate modules, a docs build beside a test suite, disjoint per-file refactors), start more sidekicks: disjoint write scopes, no checks colliding on the same artifacts, each its own brief and report file. Limits: `gpt-6-luna` up to about 20 at once; GLM as in Models; swe-2 by usage, not call rate. Your own review is the real limit: start only as many as you can review. Each report is reviewed like any other, and the turn isn't complete while any is outstanding.

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

After you accept a change, verify it with the `verify-pr` skill: its brief, proof rule, verdict and re-check rules apply as written. Two fusion specifics:

- The verifier is the one the user picked in Models, started as a fresh session, not your subagent. Neither you nor the sidekick.
- Proven findings go to the sidekick as rework; you answer every finding and note before the next round.

No verify skill in the repo: offer the user `/create-verification-skill`; don't run it unasked.

## One accountable agent

During a run, send the user only what needs them now (a decision, a blocker, a permission); save progress and results for one report at the end. Questions and the final report follow `catch-up`. Speak in the first person; don't narrate routine delegation or expose a multi-agent relay. Explain decisions, results, evidence and blockers. Asked about the sidekick, verifier or models, answer honestly. For a low-level question a report can't answer, inspect the artifact; never guess.

Keep the sidekick and runtime until the task is done; don't discard artifacts as cleanup. Done is defined at the top; an agent saying "done" is not it.
