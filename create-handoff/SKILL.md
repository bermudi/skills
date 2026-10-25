---
name: create-handoff
description: >
  Compact the current session into a high-signal handoff document for a fresh,
  stateless agent: decisions with authority provenance, failed approaches with
  verbatim errors, an implementation readiness gate, and executable pointer
  verification. Use when the user asks for a handoff, session transfer, or
  context compaction before ending work or resuming in a new session.
disable-model-invocation: false
allowed-tools:
  - read
  - grep
  - glob
  - exec
---

You are executing a context-compaction and state-transfer protocol. Distill our current session into a high-signal handoff document for a fresh, stateless agent.

Target Focus for Next Session:
(The user request accompanying this skill invocation, if any. If it is empty, generate a general state-transfer covering all active threads. If it contains text, treat it as the immediate next slice, not as permission to discard the larger plan. Heavily tailor detail toward that objective while preserving the parent goal, ordered roadmap, downstream steps, and any dependencies that come after it.)

OUTPUT INSTRUCTIONS:
Save the output to the OS temporary directory (`mktemp`) as `agent_handoff_XXXXXXXX.md`. Do NOT save it in the current workspace. After saving, respond with the handoff path so the user can pass it to the next session.

COMPACTION DIRECTIVES:
1. **Pointer-First & Zero Fabrication**: Reference files, commits, and artifacts via exact paths, SHAs, or URLs. **Never fabricate a pointer, quote, or line number.** If the exact data has scrolled out of context, write `[lost: paraphrase]` or `[approximate: ...]`. Honest fog beats confident fiction.
2. **Causal Chain & Provenance**: Every decision must cite its forcing constraint. Every abandoned approach must include the error or observation that killed it (or `[lost: paraphrase]`). Mark conversation-only facts as `[chat-sourced: ...]` and reasoned conclusions as `[inferred: reasoning + confidence]`.
3. **Decision Authority, Not Agent Confidence**: Classify choices as `[confirmed:user]`, `[confirmed:repository-contract]`, `[proposed:agent]`, or `[inferred: ... + confidence]`. Use `[locked]` only when the user explicitly accepted the choice or an existing repository contract requires it, and cite that authority. An inference or recommendation is never locked merely because confidence is high. Preserve disagreements and competing options instead of silently resolving them.
4. **Conversation-Only Source Preservation**: If requirements, a feature proposal, or architectural discussion exist only in this conversation, the handoff becomes their source of truth. Include a self-contained **Requirement Record** with the user's request and motivation, exact user quotations still present in context, alternatives discussed, explicit approvals/rejections, and unresolved choices. If exact wording is unavailable, mark it `[lost: paraphrase]`; never replace it with the agent's preferred design. `None beyond current conversation` in **Source Material** is a warning, not sufficient transfer by itself.
5. **Verbatim Preservation of Conversation-Only Artifacts**: Some content loses its value when summarized: detailed plans, drafted code or configs, schemas, API payloads, data samples, exact prompts, templates, or any text the next session may need to reuse as-is. If such content exists only in this conversation, do NOT compress it into the handoff narrative. Persist it verbatim as a sibling file next to the handoff in the temp dir (e.g., `agent_handoff_XXXXXXXX_plan.md`) and link it in **Artifacts** with a one-line description. In the handoff body, keep only the pointer plus the minimal context needed to use it. When unsure whether content qualifies, prefer spilling it verbatim over summarizing — storage is cheap, lost detail is not.
6. **Implementation Readiness Gate**: If the next objective is implementation, include a concrete **Implementation Contract**: approved v1 scope, non-goals, observable acceptance criteria, representative input/output or behavior examples, API/compatibility impact, failure semantics, and security/privacy boundaries. Mark missing behavior-affecting items as unresolved. If an unresolved product, scope, API, or safety decision changes what should be built, the immediate next action must resolve or durably document that decision—not begin implementation. Do not invent approval to keep momentum.
7. **Dual-Memory & High Signal**: Keep semantic facts (architecture, schemas) separate from episodic history (what was tried). Omit conversational filler and routine terminal outputs; retain final states and critical stack traces.
8. **Roadmap Continuity & Honest Scope**: Preserve the entire parent sequence with status per item; a focused target marks where to resume, not permission to discard downstream work. Define the single immediate next action via the Plan Cursor. Do not call a proposal active implementation work when it is awaiting approval, and do not turn open product questions into coding discretion.
9. **Substantial Knowledge Transfer (Content Test)**: Transfer the working map: mental models, invariants, topology, and test strategies. **Content Test:** Every section in the Operational Knowledge Ledger must contain substantive understanding or an explicit `[null: reason]` (e.g., `[null: no testing occurred]`). **Scale total length to session complexity:** a short session may collapse ledger subsections to a few bullets or `[null]`s; a long, multi-thread session deserves full capsules. Do not pad, but do not underfit.
10. **Repository State Is Evidence**: Record the current `HEAD` SHA and branch, exact porcelain status, and whether cited work is committed, staged, unstaged, or untracked. Never say "clean" without checking. For uncommitted work, identify the changed paths and summarize the diff; distinguish verification performed before the changes from verification of the current tree.
11. **Context Retrieval & Traps**: Provide exact `rg`, `git`, or test commands to rehydrate context. Explicitly list "Fresh-Agent Traps" (likely misunderstandings, rework loops, misleading names).
12. **Handoff Lineage**: If this session began from a prior handoff, record it in **Source Material** (the single home for lineage) and summarize which parts of the previous roadmap were completed, pending, or superseded.

REQUIRED MARKDOWN STRUCTURE:

# Agent Handoff: [Project/Feature Name]
**Generated:** [Current Date/Time]
**Source Material:** [Handoff lineage, prior paths, docs, PRDs, logs, URLs. If none are durable, state `None beyond current conversation; Requirement Record below is the transferred source of truth` and actually provide that record.]
**Next Session Objective:** [Immediate objective synthesized from Target Focus. Include `Parent Objective: ...` if part of a larger effort. Do not say "implement" when the Readiness Gate says a behavior-affecting decision is unresolved.]

## 1. Semantic State (The "What")
* **Requirement Record:** [Self-contained original problem and motivation; exact user quotes still available; requested outcome; alternatives discussed; explicit approvals/rejections; unresolved choices. Separate what the user asked from what the agent recommended. Use `[null: no feature requirements were discussed]` only when genuinely inapplicable.]
* **Implementation Contract:** [When implementation is next: approved v1 scope, non-goals, observable acceptance criteria, representative examples, API/compatibility impact, failure semantics, and security/privacy boundaries. Each item needs authority provenance. Missing behavior-affecting items are `UNRESOLVED`, not invitations to guess. Otherwise state `[null: implementation is not the next objective]`.]
* **Completed:** [What is definitively done. Distinguish committed work from uncommitted work and design/research from implementation.]
* **Workspace Snapshot:** [Repository root; branch; exact `HEAD` SHA; exact `git status --short`; changed/untracked paths and concise diff summary. State whether tests described below ran on this exact tree or an earlier state.]
* **Parent Roadmap:** [The larger ordered plan with status per item and provenance. Example: `1. Delete junk — done; 2. Extract fixtures — active; 3. Fix tests — pending`. Append newly discovered follow-ups at the end, marked `[new]` — they join the queue, they do not displace planned work. If none, state `No broader sequence found in context`.]
* **Blockers:** [What is preventing progress right now, including unresolved product/scope/API/safety decisions required by the Implementation Readiness Gate.]
* **Decisions:** [Classify every choice as `[confirmed:user]`, `[confirmed:repository-contract]`, `[proposed:agent]`, or `[inferred: ... + confidence]`. Cite its forcing constraint or authority. Append `[locked]` only to confirmed choices; never to proposals or inferences.]

## 2. Execution Logic & Debugging (The "How" & "Why")
* **Failed Approaches:** [Attempted -> Verbatim error/observation -> Why abandoned. Include definitively ruled-out paths with the smoking gun that killed them. **Do not summarize the error; provide the exact payload or terminal output.** If the exact string is gone, you MUST use `[lost: paraphrase]`.]
* **Active Context:** [Exact truncated stack traces, terminal errors, flaky behaviors, unresolved environmental state.]

## 3. Operational Knowledge Ledger (The "Working Map")
*(Pass the Content Test: Substantive understanding or explicit `[null: reason]` for each applicable subsection)*
* **Project/Subsystem Map:** [Module boundaries, where behavior lives vs tests.]
* **Context Capsules:** [Deep-dive capsules by concern/topic, e.g., `Rate limiting mental model`, `Fixture strategy`.]
* **Domain Vocabulary & Invariants:** [Business rules, data contracts, assumptions.]
* **Testing/Verification Model:** [Trusted vs suspect tests, how to run slices, known flaky tests. Separate commands run against the current workspace from baseline/pre-change commands; include exact pass/fail/not-run status. Unit/plumbing verification is not evidence of product usefulness—state any evaluation gap.]
* **Patterns & Conventions:** [Naming, style, accepted mock boundaries.]
* **Hazards & Gotchas:** [Non-obvious traps, misleading names, environment quirks.]
* **Fresh-Agent Trap List:** [Specific misunderstandings or rework loops the next agent is likely to fall into.]
* **Retrieval Seeds:** [Exact `rg`, `git`, test commands, or artifact paths to expand context on demand.]
* **User Preferences:** [Constraints expressed during this session; cite as `[chat-sourced]`.]
* **Open Questions:** [Suspicions not yet verified; mark with confidence/provenance.]

## 4. Lossless Pointers (The "Where")
* **Key Files:** [Grouped by concern. Prefer `[path:line-range]` or `[path: approx. line X]` if exact range is lost.]
* **Commits:** `[SHA]` — [Message] — [What it validates]
* **Artifacts:** `[path/URL]` — [Relevance. Persist large logs/traces and all verbatim spillover artifacts from Directive 5 (plans, drafted code, configs, schemas, payloads, data samples, prompts) as sibling files next to the handoff in the temp dir and link them here.]

## 5. Plan Cursor & Next Action
* **Plan Cursor:** [Where we are in the larger sequence. Format: `Parent goal -> Completed: A -> Active/Next: B -> Remaining: C, D (with dependencies)`.]
* **Immediate Next Action:** [The single, clear next step derived from the cursor and context. It must obey the Implementation Readiness Gate: resolve a required decision before coding when scope/behavior/API/safety remains unapproved.]

---

## Handoff Verification
*(Execute these checks after writing the document. Print each command's result to session chat — do not include this section in the handoff. A check that cannot be run honestly must be reported as failed, not checked off.)*
1. **SHAs resolve:** Run `git cat-file -t <SHA>` for every SHA cited in the handoff. Any that fail must be corrected or downgraded to `[lost: paraphrase]`.
2. **Paths exist:** Run `test -e <path>` for every file path cited. Dead pointers must be fixed or downgraded to `[lost: paraphrase]`.
3. **Retrieval seeds execute:** Run every retrieval seed command. Each must succeed and return relevant output; fix or delete any that don't.
4. **Provenance and authority sweep:** Re-read Requirement Record, Implementation Contract, Decisions, and Failed Approaches. Fix any decision without a forcing constraint, any inference without an `[inferred]` tag, any proposal presented as confirmed, and any `[locked]` item lacking explicit user or repository-contract authority.
5. **Conversation-source completeness:** If Source Material says requirements exist only in conversation, verify the Requirement Record is self-contained enough for a stateless agent to distinguish the user's request from the agent's recommendation. A bare statement that context existed only in chat fails this check.
6. **Readiness gate:** If the objective or immediate action says to implement, verify that v1 scope, non-goals, acceptance criteria, examples, API impact, failure semantics, and security/privacy boundaries are either approved or explicitly non-applicable. Otherwise change the next action to resolve the missing behavior-affecting decision.
7. **Workspace snapshot:** Run `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, and `git diff --stat` (plus list untracked files). Ensure the handoff matches this exact state and labels tests as current-tree or pre-change.
8. **Verification claims:** Every claimed passing command must have been run against the state it claims to validate. Downgrade stale or unrun claims to baseline/not-run; do not imply that pre-change tests validate new work.
9. **Verbatim spillover sweep:** Scan the session for conversation-only content whose value depends on its exact form (plans, drafted code, configs, schemas, API payloads, data samples, prompts, templates). Verify each is either preserved verbatim as a linked sibling artifact (run `test -e` on it) or explicitly judged safe to summarize, with the reason stated. Summarizing such content inline by default fails this check.
