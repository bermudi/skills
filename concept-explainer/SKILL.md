---
name: concept-explainer
description: >-
  Build a self-contained, interactive HTML "textbook chapter" that teaches a
  technical concept. Use when the user asks to understand, explain, walk
  through, or be taught how something works.
license: Apache-2.0
disable-model-invocation: true
metadata:
  version: "1.0"
---

# Concept Explainer

You are acting as a pedagogical designer and engineer. Your job is not to summarize 
the input — it is to build a durable *mental model* for the reader. Turn the input
into a single, self-contained, interactive HTML page that reads like a personalized 
textbook chapter.

If the user pastes code, a file, or a spec, treat it as the input to explain.

## Output

A single self-contained `.html` file saved to disk and opened in the browser (xdg-open).

**Start from the scaffold.** This skill ships `assets/template.html` (sitting
next to this `SKILL.md`). Copy it to your output location and fill it in
rather than hand-writing the page from scratch — the scaffold already provides
the quiz engine and a playground skeleton, which keeps the structure consistent
across runs. Read it before you start building.

## The five sections (the contract)

The page must contain these five sections, **in this order**, with these exact
headings. They are what make the output a "textbook chapter" instead of a blog
post — do not rename, reorder, or skip them.

1. **Background & Foundational Landscape** — Establish the groundwork *before*
   the change or the mechanics. Cover: the overarching **mental model** (what
   system/architecture this belongs to), the **prerequisites** the reader must
   know first (only genuine ones — if the concept stands alone, write "No
   prerequisites" rather than padding a list), and the **context** (where this
   sits in the broader project).
2. **Intuition Before Details** — Explain the *essence* before any syntax.
   Give the **core trick** (the elegant shortcut/pattern/metaphor), the
   **high-level goal** in plain, vivid English with an analogy ("think of this
   queue as a host at a busy restaurant…"), and the **expected outcome** (what
   the system should *feel* like once this is in place).
3. **The Micro-World (Interactive Playground)** — Embed a vanilla-JS +
   Tailwind (via CDN) widget the user can manipulate directly in the browser.
   It must visualize the concept's *state* and update as the user interacts
   (e.g. step an algorithm, change inputs and watch the output, toggle a
   behaviour). Keep it **minimal and focused on the one core mechanism** — do
   not clone the whole app or build a full UI.
4. **Literate Structural Breakdown** — Now walk the actual material (the code,
   diff, spec, or algorithm) in **pedagogical order** (simplest/foundational
   pieces first, building up to the orchestrators). Put prose and code
   side-by-side and explain the *story* — why each line, variable, or step
   exists. Code is illustration; the prose is the answer.
5. **The Speed Regulator (Quiz)** — A 5-question, medium-to-hard,
   **scenario-based** quiz (not trivia like "what is the variable called?").
   Ask "if state X changes to Y while condition Z holds, what happens?"
   Implement it with the scaffold's quiz engine: every option gets an
   explanation of why it is right or wrong, and a **Check Answers** control
   reveals scores + explanations.

## Process

1. **Pin the concept.** Identify the single core idea the reader must leave
   with. If the input is large, either ask which slice to focus on or pick the
   most concept-dense part — do not explain everything shallowly.
2. **Copy the scaffold** (`assets/template.html`) to `<output>.html` and fill
   the five sections. Reuse the built-in quiz engine and playground pattern.
3. **Build the playground** as a state-driven widget: define `state` → write
   `render(state)` → wire inputs to mutate `state` and re-render. Make it
   responsive and focused on the core mechanism.
4. **Write the quiz** via the `QUIZ` array in the scaffold: 5 scenario
   questions, 3–4 options each, the correct index, and an `explain` sentence
   per option.
5. **Save and open** the file; if the environment is headless, tell the user
   the path instead.

## Hard rules / gotchas

- **Self-contained:** all content and data are inline. Libraries only via CDN
  (Tailwind, optionally a charting lib). No `fetch()` to external data sources.
- Tailwind's CDN prints a "not for production" console warning on first open —
  that is expected and fine for a personal learning page.
- The five section headings are the contract. Renaming or skipping one breaks
  the structure that makes this a textbook chapter.
- **Prerequisites must be real.** Inventing prerequisites the reader doesn't
  need wastes their attention; if none are needed, say so plainly.
- **Quiz tests reasoning under changed conditions, not recall.** Every option
  needs an explanation, correct or not.
- Don't dump raw code as the explanation. The breakdown *interprets* it.

## Before you deliver (self-check)

- [ ] All five sections present and in order, with the exact headings?
- [ ] Playground has real interactivity (event handlers mutate visible state)?
- [ ] Quiz has 5 questions, each with per-option explanations, and Check Answers works?
- [ ] Opens in a browser with no broken dependencies (CDN only, no external data)?
- [ ] Intuition section is free of unexplained jargon?
