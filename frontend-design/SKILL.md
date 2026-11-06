---
name: frontend-design
description: >
  Distinctive visual design when building or reshaping UI: aesthetic
  direction, typography, avoiding templated defaults.
license: Apache-2.0
---

# Frontend Design

Aim for a distinct visual identity specific to this brief, not a cliché or template. Make opinionated choices on palette, type and layout, and take aesthetic risk when justified. The brief's own words always win, even when they ask for one of the looks listed below.

## Ground it in the subject

If the brief doesn't say what the product is, propose one concrete subject, audience and primary job, and confirm. Use anything you know of the client's context. Distinctive choices come from the subject's industry, materials and vernacular (a toy for 8–11 year olds and a dashboard for financial analysts look nothing alike); use real content throughout.

## Principles

- **Hero:** open with the most characteristic thing in the subject's world, in whatever form fits (headline, image, animation, live demo, interaction). A big number + small label + stats + gradient accent is the default; use it only if it's truly best.
- **Type carries personality.** One family or two, clearly distinct if two. Pick faces deliberately, not your usual defaults, and set a real type scale (weights, widths, spacing, per *The Elements of Typographic Style*). Type used as a visual element is an active part of the design.
- Line length under 80 characters (serif may run a bit longer, with slightly more line-height than sans).
- **Typographic tells of a generated page, avoid:** accenting one word in a headline (italic/bold/colour), ALL CAPS labels, needless labels above content.
- **Structure is information.** Outlines, borders, numbering, eyebrows, dividers and labels should encode something about the content. Numbered markers (01 / 02 / 03) only for real sequences.
- **Motion:** non-user-triggered motion sparingly, to draw attention: one orchestrated page-load or reveal beats scattered effects (fade-and-slide-up on every section and hover transitions on every card read as AI-generated). Motion that answers a user action and shows what changed is welcome.
- Placeholder copy can make a design feel as templated as the layout; see Writing.

## Process: plan, review against the brief, build, critique

Current AI-generated design clusters on:
1. Warm cream background (~#F4F1EA), high-contrast serif display, terracotta/clay accent (~#D97757, Claude's own accent, so on a user's brief it reads as a tell).
2. Near-black background with one acid-green or vermilion accent.
3. Broadsheet layout: hairline rules, zero radius, dense newspaper columns.
4. SaaS-card kit: identical rounded cards, one radius for everything, the same soft grey shadow, gradient washes as decoration.
5. Template chrome: tracked-out ALL-CAPS eyebrow above every heading; middle-dot meta strings ('A · B · C'); 'WORD — fragment' labels; tinted near-black (#0B0B0B, #111) for black; monospace small data labels; '→' on every link and button.

Each is legitimate for some briefs but a default, not a choice. Where the brief leaves an axis free, don't spend it on these.

**Pass 1, plan:** a compact token system: colour (4–6 named hex values), type (faces and roles), layout (one-sentence concepts and ASCII wireframes to compare; state alignment), principles (what makes this page unique).
**Review the plan against the brief** before building: if any part is what you'd produce for any similar prompt, revise it and say what changed and why.
**Pass 2, build** to the revised plan. Mind CSS specificity: type-based classes (`.section`) and element selectors (`.cta`) cancel each other, notably on section padding/margin.

## Restraint and self-critique

Spend boldness in one place: one memorable element, everything around it quiet; cut decoration that doesn't serve the brief (Chanel: remove one accessory before leaving). Quality floor, unannounced: responsive to mobile, visible keyboard focus, reduced-motion respected, accessible, harmonious colour. Critique as you build; take screenshots if you can.

## Writing

Words exist to make the design easier to understand and use. Write from the user's side: name things by what they understand (they manage notifications, not webhook config), say what something does rather than selling it, specific beats clever. Active voice; a CTA says what happens ("Save changes", not "Submit"); an action keeps one name through the flow (Publish → "Published"). Errors say what went wrong and how to fix it, never apologise or stay vague; an empty screen invites action. Plain verbs, sentence case, no filler; each element does one job.
