# Wireframes

Read this when the artifact is a low-fidelity HTML wireframe testing information hierarchy, content, navigation, task flow, and responsive structure before visual design. The goal is to help reviewers decide what belongs on the screen and how the task should work — not to look like a finished product.

When the visual direction is also open, read [`creative-direction.md`](creative-direction.md) for subject-specific composition and hierarchy guidance without importing editorial polish. This reference's low-fidelity contract remains authoritative.

## Establish the review question

Read the conversation, supplied brief, and nearby project material before choosing a layout. Reuse the project's vocabulary, content model, and known product constraints.

Authority runs in this order:

1. The user's explicit instructions and accepted decisions.
2. The product's existing structure and terminology.
3. The user, task, and content being modeled.
4. Your own layout judgment.

Before coding, identify:

- the user and the job they need to complete;
- the screen or bounded flow under review;
- the information and actions the artifact must contain;
- the assumptions that can be made safely;
- the structural questions the wireframe should help answer.

Use real labels and representative content. Low fidelity is not permission to use anonymous boxes or lorem ipsum where wording affects the layout.

## Explore structure before style

When the layout is still unsettled, create two or three meaningfully different directions. Vary product decisions such as:

- navigation model;
- grouping and order;
- primary-action placement;
- content density;
- overview versus step-by-step flow;
- desktop-to-mobile reflow.

Do not call color changes or minor card rearrangements separate directions. Give each direction a short descriptive name and one sentence about its tradeoff.

Keep the directions in one HTML file when practical. Use a small, keyboard-operable selector so reviewers can compare them without opening several files. Preserve the same core content and task across directions. If the user has already chosen a structure, build that direction only.

## Keep the artifact intentionally unfinished

- Use a restrained grayscale palette, system type, plain borders, and simple blocks.
- Avoid brand colors, gradients, shadows, illustrations, decorative imagery, and polished component styling.
- Use limited radius and spacing. Enough order should be present to judge hierarchy, but not enough polish to invite a brand review.
- Show images or rich media as labeled placeholders unless the asset changes a structural decision.
- Add annotations only when they expose an assumption, open question, or behavior that cannot be shown directly.

The wireframe may still be well composed. Intentional unfinishedness is different from careless spacing, illegible type, or broken responsive behavior.

## Add only useful behavior

Use basic click-through behavior when it helps test navigation, disclosure, or a short task flow. Keep it immediate and plain.

- Make links, tabs, and next or back actions work when they are part of the review.
- Use native controls and visible keyboard focus.
- Do not build elaborate animation, persistence, simulated APIs, or production state management.
- Remove controls that have no review purpose, or label them clearly as out of scope.

## Build contract

- Deliver one self-contained `.html` file with essential CSS and JavaScript inline.
- Require no build tooling or external service.
- Use semantic landmarks, headings, lists, forms, and buttons.
- Make the layout useful at wide desktop and narrow mobile widths.
- Keep the page free of accidental horizontal overflow.
- Respect the source material. Do not invent extra product scope to fill space.

## Verify and hand off

Open the result at desktop and mobile widths. Check reading order, wrapping, overflow, focus visibility, and every implemented click path. Confirm that the directions remain structurally distinct at both sizes.

Return the absolute file path, the names and tradeoffs of the directions, and the visual decisions deliberately deferred to a later mockup or prototype.
