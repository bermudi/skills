---
name: pi-docs
description: >
  Use when the user asks about pi itself — its SDK, extensions, themes, skills,
  TUI, prompt templates, keybindings, custom providers, models, or packages.
  Points the agent to pi's installed docs and examples.
---

Pi documentation:

- Pi is installed as a global npm package. Resolve its install root dynamically
  with `npm root -g` and append `@earendil-works/pi-coding-agent`. (On this
  machine that is `/home/daniel/.local/lib/node_modules/@earendil-works/pi-coding-agent`.)
- Main documentation: `…/README.md`
- Additional docs: `…/docs/`
- Examples: `…/examples/` (extensions, custom tools, SDK)
- When reading pi docs or examples, resolve `docs/...` under `…/docs/` and
  `examples/...` under `…/examples/`, not the current working directory.
- Topic → file map:
  - extensions → `docs/extensions.md`, `examples/extensions/`
  - themes → `docs/themes.md`
  - skills → `docs/skills.md`
  - prompt templates → `docs/prompt-templates.md`
  - TUI components → `docs/tui.md`
  - keybindings → `docs/keybindings.md`
  - SDK integrations → `docs/sdk.md`
  - custom providers → `docs/custom-provider.md`
  - adding models → `docs/models.md`
  - pi packages → `docs/packages.md`
- Read the relevant doc and examples fully and follow `.md` cross-references
  before implementing — pi's docs link to related pages that carry required
  detail (e.g., `tui.md` for TUI API details).
