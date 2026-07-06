# Writing skills well — a diagnostic rubric

> A skill exists to wrangle determinism out of a stochastic system. The root virtue is **predictability**: the agent taking the same *process* every run, not producing the same output. A brainstorming skill should *predictably* diverge — its tokens vary, its behaviour doesn't.

The creation workflow lives in `SKILL.md`; this file is the diagnostic lens you apply when a skill underperforms, when reviewing a draft, or when auditing someone else's skill. Four axes, each with levers and failure modes. For every failure mode, the cure is named beside it.

This rubric is largely adapted from Matt Pocock's `writing-great-skills` skill and the talk that introduced it. Read it once at the start of a creation session, then reach for it whenever a skill isn't behaving.

---

## 1. Invocation — how the skill is reached

Two loads trade off. Pick the axis deliberately; don't default.

- **Model-invoked** (default): the `description` field sits in the agent's context every turn, so the agent can fire the skill on its own — and other skills can reach it. You can still type its name. Pays **context load**: tokens and attention spent on every turn, plus a triggering-variance tax (the model may choose not to invoke it even when it's the right call — which is why trigger-accuracy evals exist).
- **User-invoked** (`disable-model-invocation: true`): the description is stripped from the agent's reach; only the human typing its name can invoke it, and no other skill can fire it. Zero context load, but spends **cognitive load**: you are the index that must remember it exists and when to reach for it.

This is a real design philosophy, not a toggle of convenience:

- Bets on **model-invoked** (e.g. the Superpowers skill set): the agent gets the skill when it needs it; you accept the context load and commit to trigger-accuracy evaluation to keep the variance down.
- Bets on **user-invoked** (e.g. Matt Pocock's skill set): you keep the context window lean and *eliminate triggering-eval as a class of problem*, at the cost of holding the index in your head.

Pick model-invocation only when the agent must reach the skill on its own, or another skill must. If it only ever fires by hand, make it user-invoked and pay no context load.

**When user-invoked skills multiply past what you can remember**, that piled-up cognitive load is cured by a **router skill**: one user-invoked skill whose job is to name the others and when to reach for each. It can only hint — user-invoked skills have no description, so nothing but the human can fire them — but it gives you one skill to remember instead of many.

---

## 2. Information hierarchy — how content is arranged

A skill is built from two content types — **steps** (ordered actions) and **reference** (definitions, rules, facts consulted on demand). A skill can be all steps, all reference, or both. The core decision is which to use and how far down the **information hierarchy** each piece sits:

1. **In-skill step** — ordered action in `SKILL.md`, the primary tier. Each step ends on a **completion criterion** (below).
2. **In-skill reference** — definition or rule in `SKILL.md`, consulted on demand. A legitimately flat peer-set (e.g. every rule of a review on one rung) is a fine arrangement, not a smell.
3. **External reference** — pushed out of `SKILL.md` into a sibling file, reached by a **context pointer**, loaded only when the pointer fires.

**Progressive disclosure** is the move down the ladder. It is *not* primarily a token optimisation — it is how you protect the legibility of the top of `SKILL.md`. Mechanics: a linked `.md` file in the skill folder, named for what it holds, with a trigger condition that tells the agent when to load it ("Read `references/aws.md` if deploying to AWS").

The cleanest disclosure test is **branching**: a *branch* is a distinct way a skill can be invoked, taking a different path through it. Inline what *every* branch needs; push behind a pointer what only *some* branches reach.

- **One branch → inline.** A skill that always writes a PRD needs the PRD template every run; keep it in `SKILL.md`.
- **Multi-branch → disclose.** A skill that may *update a glossary*, *write an ADR*, or *do neither* has two-or-three branches. Each template belongs behind its own pointer, so a run that doesn't need it never loads it.

A **context pointer**'s *wording*, not its target, decides when — and how reliably — the agent reaches the material. A must-have target behind a weakly worded pointer is a variance bug: sharpen the wording first, and pull the material back inline only if sharpening fails.

**Co-location** is the within-file companion: keep a concept's definition, rules, and caveats under one heading rather than scattered, so reading one part brings its neighbours with it.

---

## 3. Steering — shaping runtime behaviour

The levers that move the agent toward predictable execution.

### Leading words

A **leading word** (literary theory: *Leitwort*) is a compact concept already living in the model's pretraining that the agent thinks with while running the skill. You repeat it as a token throughout the skill; the agent echoes it back in its reasoning traces, and that re-emphasis shapes behaviour. It encodes a principle in the fewest possible tokens by recruiting priors the model already holds.

The canonical example: agents code layer-by-layer — all the database models, then all the schemas, then all the endpoints, then all the frontend — never seeking feedback on a small slice first. Telling the agent "don't code layer by layer, do a small slice first" works weakly. Picking **`vertical slice`** as a leading word and using it throughout works much better: the term is already in pretraining, the agent knows what it means, and you can *see it working* — "we'll do this as a thin vertical slice" starts appearing in the reasoning traces, and the implementation plans get better.

Two properties make a leading word earn its repetitions:

- **Pretraining-resident.** Reach for an existing word first. A made-up word recruits no priors — you pay in definition tokens what a pretrained word gives free. (_`vertical slice`_, _`fog of war`_, _`tracer bullets`_, _`lesson`_, _`red`_ as in a red test.)
- **Observable in the trace.** If the agent isn't echoing the word back in its thinking, the word isn't landing. Try a stronger candidate, or coin one and define it clearly.

Leading words serve predictability twice. In the body they anchor *execution* — the same behaviour every time the concept appears. In the description they anchor *invocation* — when the same word lives in your prompts, docs, and codebase, the agent links that shared language to the skill and fires it more reliably. Word a description with the leading words you actually use when you want the skill.

English is a wide API. Try candidates, watch the traces, and ask the agent to help you find them — it is good at suggesting pretraining-resident phrasings.

### Completion criteria

Every step ends on a **completion criterion**: the condition that tells the agent the step is done. Two properties make it a lever:

- **Clarity** — can the agent tell done from not-done? A vague bound ("understanding reached") lets the agent declare done and slip to the next step.
- **Demand** — how much work it requires. "Every modified model accounted for" forces thorough work; "produce a change list" does not. This axis is *not* step-bound: a body of flat reference can carry an exhaustiveness bar ("every rule applied"), which is how a skill with no steps still drives thorough work.

The strongest criteria are both checkable and exhaustive.

### Legwork and the sequence cut

**Legwork** is the digging the agent does within a step — reading files, exploring the codebase, making changes. It lives below the step structure: never its own step, latent in the wording, controlled by the agent. You raise it with a leading word (_comprehensive_, _relentless_) or a demanding completion criterion.

The classic legwork failure is **plan mode**: two steps — *ask clarifying questions*, then *create a plan* — and the agent almost always underdoes the first because it can see the second. The cure is the **sequence cut**: split the run of steps into separate skills so the agent only sees one step at a time. (Matt's `grill-with-docs` → `2-prd` split exists for exactly this reason.) Hiding the future goal focuses the agent on the current phase. Use it sparingly — only when you observe the rush and the completion criterion is irreducibly fuzzy.

---

## 4. Pruning — keeping it lean

Each remedy paired with the failure it cures. Run these as a pass over the whole skill.

### Single source of truth ↔ Duplication

Each meaning in exactly one authoritative place, so a behaviour change is a one-place edit. **Duplication** is its violation: the same meaning in two places costs maintenance (change one, must change the others), tokens, and inflates a meaning's prominence past its real rank. Watch for it across reference material too — a "what is a test seam" note repeated in three spots is duplication.

### Relevance ↔ Sediment

A line is **relevant** if it still bears on what the skill does. Skills accrete **sediment** — stale layers that settle because adding feels safe and removing feels risky. The default fate of any skill without a pruning discipline. When `SKILL.md` is bloated, sediment is usually underneath; hunt for stale or irrelevant material and kill it dead.

### The no-op test ↔ No-ops

A **no-op** is an instruction that changes nothing because the model already does it by default — you pay load to tell the agent what it would do anyway. The test, run sentence by sentence: *if you deleted this line, would the agent's behaviour change?* If not, delete the whole sentence; don't trim words from it.

Worked example: a paragraph in an `implement` skill instructing the agent to write a long, detailed commit message. Delete the paragraph — the agent still writes one. It's a no-op; cut it.

A leading word too weak to beat the default is a no-op (_be thorough_ when the agent is already thorough-ish). The fix is a stronger word that passes the verdict (_relentless_), not a different technique. The no-op test is therefore also how you grade whether a leading word is earning its repetitions.

> Two people disagreeing over whether a line is a no-op disagree about the model's *default*. Settle it by running the skill, not by debate.

### Sprawl

A skill that is simply too long, even when every line is live and unique. Hurts readability (attention thins across the excess), maintainability, and token cost. **Size is a symptom, not a root cause** — when `SKILL.md` sprawls, hunt for duplication, sediment, or no-ops underneath. If everything genuinely earns its place, the cure is the ladder: push reference behind pointers, and split by branch or sequence so each path carries only what it needs.

---

## Quick diagnostic

When a skill misbehaves, walk this list before reaching for prose rewrites:

| Symptom | Likely failure mode | First move |
|---|---|---|
| Agent declares a step done too early | Premature completion | Sharpen the completion criterion; split only if fuzzy *and* you observe the rush |
| Agent doesn't do enough digging in a step | Thin legwork / premature completion | Demanding criterion, stronger leading word, or sequence cut |
| Agent ignores an instruction | No-op, or weak context pointer | Run the no-op test; sharpen the pointer's wording |
| Skill triggers on the wrong prompts | Description wording | Trigger-accuracy eval (`optimizing-descriptions.md`) |
| `SKILL.md` keeps growing | Sprawl, sediment, or duplication | Find the failure mode underneath; disclose or delete |
| Agent doesn't do what you want, period | Missing or weak leading word | Pick a pretraining-resident term; verify it appears in traces |
