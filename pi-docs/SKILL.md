---
name: pi-docs
description: >
  Use when the user asks about pi itself — its SDK, extensions, themes, skills,
  TUI, prompt templates, keybindings, custom providers, models, or packages.
  Points to pi's installed docs and examples.
---

Pi is a managed install (not npm). Docs root:
`~/.pi/agent/install/releases/<version>/node_modules/@earendil-works/pi-coding-agent`. Resolve `<version>` with `pi --version` or `ls ~/.pi/agent/install/releases`. Launcher: `~/.pi/agent/bin/pi` (linked from `~/bin/pi`); update with `pi update`.

Under the root: `README.md`, `docs/`, `examples/` (extensions, custom tools, SDK). Resolve `docs/...` and `examples/...` there, not against the CWD.

| Topic | Read |
|---|---|
| extensions | `docs/extensions.md`, `examples/extensions/` |
| themes | `docs/themes.md` |
| skills | `docs/skills.md` |
| prompt templates | `docs/prompt-templates.md` |
| TUI components | `docs/tui.md` |
| keybindings | `docs/keybindings.md` |
| SDK | `docs/sdk.md` |
| custom providers | `docs/custom-provider.md` |
| models | `docs/models.md` |
| packages | `docs/packages.md` |

Read the relevant doc fully and follow its `.md` cross-references before implementing; linked pages carry required detail (e.g. `tui.md` for TUI APIs).
