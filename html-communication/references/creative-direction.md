# Creative direction

Read this when the user or project has not already supplied a complete visual direction. It composes with whichever form-specific reference the artifact uses; it does not replace it.

Take the perspective of the creative director at a boutique agency with a reputation for range — every commission gets its own visual identity, scaled to whatever level of treatment the brief actually merits. Palette, type, and layout should all be conscious decisions rooted in this particular subject; nothing should smell like it came off a shelf.

## Size up the brief

The question is never *whether* to design — it's what register to design in. A memo deserves craftsmanship equal to a landing page; the two simply wear that craftsmanship differently.

Much of what comes in wants a workmanlike register: plans, briefs, demos. Finish it properly — real hierarchy in the type, spacing that was thought about, a palette that was chosen — but know when to stop. Hardly any page benefits from a towering, theatrical hero. Ornament sparingly and with taste.

Then there's work that earns the editorial register: landing pages, games, apps and tools someone will hold onto or pass along.

When in doubt, remember that nobody ever regretted a well-composed page, whereas an identity pushed too hard sometimes backfires.

The fundamentals below apply universally. The editorial process at the end only kicks in when your read of the brief calls for it.

## Find the direction inside the brief

Start with the subject's own world: its materials, tools, environments, notation, history, audience, and language. Pull one organizing idea from there. It might shape the grid, the behavior of a diagram, the rhythm of the type, the way information reveals itself, or the role of imagery.

Choose a register that fits:

- **Workmanlike:** quiet hierarchy, exact spacing, restrained color, direct language. Right for plans, internal briefs, operational reports, and many tools.
- **Editorial:** stronger composition, distinctive type, art-directed pacing, and one memorable visual move. Right for explainers, launches, research stories, and presentations that need to travel.
- **Expressive:** a more immersive visual or interactive idea whose execution is itself part of the message. Use rarely, when the subject truly benefits.

Do not confuse restraint with neglect or expression with a theatrical hero. Finish the chosen register properly.

## Fundamentals for every artifact

**Defer to prior art.** Before anything else, hunt for an established design system — an `AGENTS.md` or `CLAUDE.md` and/or `DESIGN.md`, `QUALITY.md`, `PRODUCT.md` etc, a tokens or theme file, styling on existing components. Found one? Apply it. The guidance below exists to plug holes, never to overrule. Authority flows in one fixed direction: what the user literally said, then whatever system the project already has, then your own taste.

**Anchor everything to the subject.** Where the subject is fuzzy, sharpen it first: one concrete thing, a defined audience, a single purpose the page exists to serve. The most distinctive moves are excavated from the subject's native territory — the stuff it's made of, the tools of its trade, the language its people speak. Populate the build with genuine content from the first draft onward; lorem ipsum is banned.

**Put two typefaces in conversation.** Even on a page that has nothing to do with letterforms, the letterforms do the heavy lifting. Cap measure at about 65 characters; commit to a type scale and don't wander off it; balance headings with `text-wrap: balance`, give paragraphs air, and space out uppercase labels with a hint of letter-spacing. One well-used family can outperform an arbitrary pairing; several roles are useful only when they remain coherent. Use system fonts when they suit the brief.

**Neutrals are choices too.** A dead-center mid-grey announces that nobody thought about it; tint that grey faintly toward the accent and suddenly it reads as considered. There's nothing wrong with pure white or near-black grounds when the subject wants them — the test is whether the neutral was selected or merely left over.

**Both themes, equal care.** Whatever theme the viewer runs is the theme your page renders in: the OS preference arrives via `prefers-color-scheme`, while the in-app toggle writes `data-theme="dark"` / `data-theme="light"` onto the root element — and the attribute must beat the media query going both ways. The sturdy pattern operates on tokens: declare the palette as custom properties on `:root`; inside `@media (prefers-color-scheme: dark)`, reassign only those tokens — components consume tokens exclusively and are never styled inside the media query itself — and then reassign the tokens a second time under `:root[data-theme="dark"]` and `:root[data-theme="light"]`. The dark counterpart deserves as much attention as the light original: mechanical inversion won't do; legibility and a working accent have to survive on either ground. Whether to support both themes or commit to one is a decision with a procedure — see the Build contract in `SKILL.md`; this reference handles the *how*, not the *whether*.

**Spacing belongs to the layout, not the elements.** Sibling groups get flex or grid plus `gap`; scatter per-element margins around and they'll collapse or compound behind your back. Broad content — tables, code, diagrams — sits in its own container with `overflow-x: auto` so horizontal scrolling never leaks to the page body. Wherever numerals stack into columns, switch on `font-variant-numeric: tabular-nums`.

**Dodge the telltale AI aesthetic.** Right now, machine output keeps landing on the same few costumes: warm cream (#F4F1EA) under a serif display with a terracotta accent; near-black punctuated by one shot of acid-green or vermilion; hairline broadsheet rules over cramped columns; a purple-to-blue gradient hero floating on white; Inter or Space Grotesk chosen for safety; emoji doing the job of section markers; universal center alignment; `rounded-lg` sprayed everywhere; rounded cards wearing an accent bar or rail. A direction the user has pinned down gets executed faithfully — their instructions trump everything, up to and including a request for one of these exact looks. Absent instructions, that freedom is yours; don't blow it on a cliché.

**Engineer it soundly.** Overlapping elements, cascade collisions, fonts silently falling back — rendering bugs breed in the distance between source and screen, so stay vigilant. Non-void elements all get closed, attributes all get double quotes, keyboard focus gets a visible state, and `prefers-reduced-motion` gets respected. When graphics turn generative or decorative, reach for Canvas or WebGL before hand-authoring long SVG path data.

**Mind the cascade.** Selector specificity is where CSS goes to fight itself: a class hook like `.section` and an element hook like `.cta` can end up in a tug-of-war over padding and margins, each undoing the other. Architect the cascade so your spacing can't be quietly sabotaged.

**Copy is a material.** Treat the words as load-bearing, not garnish. Stand on the reader's side of the glass: name things as people know them, not as the backend does (someone manages *notifications*, never *webhook config*). Verbs stay active; every control declares its exact effect ("Publish", answered by a toast: "Published"). An error message diagnoses the failure and prescribes the fix — never groveling, never hand-waving. Precision outperforms wit.

**Make structure mean something.** Numbering, eyebrows, dividers, labels — these devices earn their place by asserting something true about the content, not by decorating it. Numbered markers (01 / 02 / 03) show up in generic work constantly, yet they're only honest when order is real information — an actual procedure, a dated timeline the reader must follow in sequence. Before deploying a device like that, ask whether it's telling the truth.

**Interfaces are not documents.** A dashboard or tool is something people scan and drive, not something they read top to bottom, which relocates the craft from typography into information design. Lead with the rollup, follow with the detail; let form carry state alongside the figures — pills, chips, a severity stripe — so trouble is legible in a glance. Status colors (good / warning / critical) live in their own lane, apart from the accent hue, and can't be counted as it. Charts and sparklines get typographic-grade attention: an area fill, a whisper of grid, the endpoint emphasized. If it can be clicked, it should look clickable.

## Make a short design plan

Before writing CSS, decide:

- **Color:** 4–6 hex values, each with a name. Color should be selected rather than inherited from habit; neutrals are part of the palette; status colors must remain semantically distinct from the decorative accent.
- **Type:** faces covering 2+ roles — a display face with character, deployed with restraint; a body face that partners it; a utility face for captions or data if the work needs one. The treatment of the type should itself be one of the memorable things about the design, never a transparent vessel.
- **Layout:** the organizing idea, captured in a sentence or two — hierarchy, density, edge treatment, and image or diagram language.

The number of colors, typefaces, columns, and components should follow the idea. Do not satisfy a quota.

## Avoid the template reflex

Common components are not a visual direction. Cards, pills, rounded rectangles, gradients, tiny uppercase labels, large numerals, and side rails may be useful, but each must express real structure. Do not use them merely because they make an unfinished page look designed.

Vary more than color. A new palette on the same centered hero and card grid is still the same design. Reconsider composition, scale, density, typography, shape language, navigation, and interaction.

Use one decisive move rather than many unrelated flourishes. Let the rest of the page support it.

Respect prior art: when the user names a style or supplies a reference, follow it faithfully, even if it resembles a convention you would not choose yourself. When a project has tokens and components, use them before inventing replacements. Never copy a previous artifact's palette, typography, or composition simply because it worked once.

## When the request is editorial

Now the posture shifts: picture a client who has already thrown out every proposal that felt canned and is paying specifically for conviction. Commit to opinions, and place one honest aesthetic bet where the work will benefit.

Audit the design plan against the subject before a line of code exists: any element that could pass for the stock answer to any similar brief gets reworked, with a note on what moved and the reasoning. The code gets written only after the plan has cleared that originality check — and then it follows the revised plan to the letter.

**Principles**

- Treat the hero as an argument: open on the single most characteristic artifact of the subject's world — headline, image, live demo, interactive moment.
- The page's personality lives in its type. Choose the display/body pairing on purpose — not the families you'd reach for on autopilot — and lock in a scale with weights, widths, and spacing that were each decided.
- Motion is a budget to allocate. Ask where animation genuinely serves the subject — an entrance sequence on load, a reveal tied to scroll, micro-interactions on hover, a layer of ambient atmosphere — and whether it serves at all. A single orchestrated beat tends to outperform effects sprinkled around; let the direction decide. Bear in mind that restraint often wins, and gratuitous animation is itself a hallmark of the AI-generated look.
- Scale the execution to the ambition. Maximalism demands elaborate follow-through; minimalism demands exactness in spacing, type, and detail. Elegance means delivering the chosen vision completely.
- Concentrate the daring in one location and hush everything around it. Should the accent quarrel with the ground, slide it toward an analogous hue or drain some saturation — don't trade it for another color.
