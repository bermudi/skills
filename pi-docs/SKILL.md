---
name: pi-docs
description: read only when the user asks about pi itself, its SDK, extensions, themes, skills, or TUI
---

Pi documentation:
- Pi is installed as a global npm package. Its install root is:
  `/home/daniel/.local/lib/node_modules/@earendil-works/pi-coding-agent`
- Main documentation: `…/README.md`
- Additional docs: `…/docs/`
- Examples: `…/examples/` (extensions, custom tools, SDK)
- When reading pi docs or examples, resolve docs/... under …/docs/ and examples/... under …/examples/, not the current working directory
- When asked about: extensions (docs/extensions.md, examples/extensions/), themes (docs/themes.md), skills (docs/skills.md), prompt templates (docs/prompt-templates.md), TUI components (docs/tui.md), keybindings (docs/keybindings.md), SDK integrations (docs/sdk.md), custom providers (docs/custom-provider.md), adding models (docs/models.md), pi packages (docs/packages.md)
- When working on pi topics, read the docs and examples, and follow .md cross-references before implementing
- Always read pi .md files completely and follow links to related docs (e.g., tui.md for TUI API details)
