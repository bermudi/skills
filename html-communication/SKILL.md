---
name: html-communication
description: >-
  Create or redesign self-contained single-file HTML artifacts — reports,
  explainers, presentations, landing pages, tools, wireframes, prototypes,
  plans, and diagrams. Use when HTML is the deliverable for any visual
  communication: a brief, mockup, roadmap, architecture diagram, data story,
  or mixed artifact. Routes internally to specialized references by form. Do
  not use for ordinary application implementation when a standalone HTML file
  is not the deliverable.
license: MIT
metadata:
  version: "1.0"
  topic: html-artifacts
---

# HTML Communication

Build one self-contained HTML file that makes the subject clearer, easier to use, or easier to understand. The standard is consistent care, not a consistent look. Do not reproduce a house palette, typography stack, card system, or layout from prior runs.

This is a single skill with an internal router. The form the artifact takes decides which specialized reference to load — there are no sibling skills to install.

## Route the request by form

Pick the narrowest reference that owns the **main review question** — the single question the viewer most needs the artifact to answer (e.g., "does this layout put the right things on the screen?" for a wireframe, "can a user complete this flow?" for a prototype). Load it before coding.

Requests can span forms. A second reference **materially applies** when it governs a distinct region or interaction the artifact actually contains — not one it merely could contain. Read every reference that materially applies.

When two references push different directions on the same element, the reference that owns the main review question wins on shared decisions; secondary references inform the regions they govern but yield on conflicts.

- **Visual direction still open** (palette, type, composition, theming, register) → read [`references/creative-direction.md`](references/creative-direction.md) before choosing any of the above. It does not replace the form-specific reference; it composes with it.
- **Wireframe** — structure, information hierarchy, navigation, or task flow still unsettled; intentionally low fidelity, possibly two or three layout directions → [`references/wireframes.md`](references/wireframes.md).
- **Prototype or mockup** — polished mockup or a working interactive flow; mockup is the static fidelity mode inside that reference → [`references/prototypes.md`](references/prototypes.md).
- **Plan** — roadmap, implementation sequence, or rollout document whose source commitments must remain easy to verify → [`references/plans.md`](references/plans.md).
- **Diagram** — relationships, sequence, topology, state, hierarchy, or system behavior are the main content → [`references/diagrams.md`](references/diagrams.md).
- **Report, brief, explainer, or deck** → [`references/documents-and-presentations.md`](references/documents-and-presentations.md).
- **Interface or tool** — editors, calculators, control panels people operate rather than read straight through → [`references/interfaces.md`](references/interfaces.md).
- **Quantitative charts, tables, metrics, or data story** → [`references/charts-and-data.md`](references/charts-and-data.md).

For mixed artifacts that do not have a clearer owner (a landing page, a data story with a tool, an explainer with a diagram), start with the closest form reference and pull in the others as needed.

## Read the room before designing

Inspect the user's request and any material they supplied. When working in a repository, look for its design language in `AGENTS.md`, `CLAUDE.md`, design-system documentation, tokens, existing components, and nearby artifacts.

Authority runs in this order:

1. The user's explicit visual and functional instructions.
2. The project's established design system and conventions.
3. The subject matter, audience, and purpose of this artifact.
4. Your own design judgment.

Before coding, settle five things in working notes:

- **Audience and job:** who will use this, and what should they understand or do?
- **Form:** document, presentation, interface, diagram, or data visualization.
- **Register:** quiet and workmanlike, polished and editorial, or intentionally expressive.
- **Fidelity:** whether to preserve the user's structure and wording or synthesize more freely.
- **Interaction:** what benefits from exploration, sequencing, filtering, or motion, if anything.

If the project already answers the visual questions, follow it. Otherwise read [`references/creative-direction.md`](references/creative-direction.md) before choosing the palette, type, composition, or motion.

## Build contract

These hold for every artifact regardless of form; the form-specific references add to them, never relax them.

- Produce one `.html` file with its essential CSS and JavaScript inline. It should work when opened directly, without a build step. Do not require a network connection unless the user permits external dependencies.
- Use real content. Do not fill prominent space with placeholder copy, decorative statistics, or controls that do nothing.
- Let content determine structure. A sequence should read in order; a comparison should make differences easy to scan; an interface should expose state and actions; a diagram should make relationships legible.
- Use semantic HTML, responsive layout, accessible contrast, visible keyboard focus, and reduced-motion handling. Make interactive elements work with a keyboard.
- Keep the page body free of accidental horizontal overflow. Put intentionally broad content in a contained scrolling or pannable region.
- Define a small set of CSS tokens for the chosen direction and use them consistently. Tokens are an implementation tool, not a predetermined palette.
- Treat motion as explanation or feedback. If removing an animation loses no meaning or useful feedback, remove it.
- Follow the user's or project's theme policy. When none exists, decide themes with this procedure:
  1. Does the concept depend on one visual world (e.g., the glow of an arcade cabinet, a letterpress invitation, a blueprint)? If yes, commit to a single theme and execute it fully — both modes would dilute it.
  2. Otherwise — utility artifacts, operational tools, documents, dashboards — support both light and dark. The dark counterpart is a real design pass, not a mechanical inversion; legibility and the accent must survive on either ground.
  3. When unsure, default to both. Single-theme is a verdict you reach, not a corner you forget.
- Never link webfonts from Google Fonts or any other font CDN — embed a custom face as a `@font-face` data URI instead, and only when its value justifies the file weight and its license permits it.

## Finish the work

Write the file to the requested location, or choose a clear filename in the current workspace. When browser tooling is available, open it and inspect a wide and narrow viewport. Exercise its controls, check the console, and fix clipping, overlap, illegible text, broken states, and accidental overflow. If browser tooling is unavailable, say which visual and interaction checks remain unverified instead of treating source inspection as a substitute.

Before delivery, run one originality check:

1. **Name a neighboring topic** — a different subject that would plausibly request the same artifact form (e.g., for a "CI pipeline dashboard," a neighbor is "incident dashboard"; for a "launch explainer," a neighbor is "feature explainer").
2. **State the visual concept in one sentence** using only design language, not the subject (e.g., "centered hero, three-card grid, indigo accent, Inter").
3. **Swap the subject.** If that sentence still describes the artifact unchanged, the direction is too generic.
4. **Revise until at least one element** — composition, type, color, imagery, or interaction — would not survive the swap because it references something specific to the actual subject. Name what changed.

The bar: the concept must lose something real when the subject changes. A palette swap alone does not count.

Return the absolute path and a short description of the artifact's visual and interaction choices.

### Optional: publish as a public page

Once the artifact is finished and delivered, ask the user whether they'd like to share it as a public page. If — and only if — they say yes, publish the file with the `tot` CLI (tot.page) and hand back the URL it prints:

```bash
tot path/to/artifact.html
```

If `tot` is not installed (`command -v tot` fails), tell the user and offer to install it. Install only on their explicit go-ahead:

```bash
npm install -g @plannotator/tot
```

Never publish or install without the user's explicit consent — a shared page is publicly accessible to anyone who has the link.
