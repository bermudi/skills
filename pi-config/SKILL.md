---
name: pi-config
description: >
  Configure and customize the pi coding agent. Use when the user asks about
  pi settings, configuration, customization, keybindings, themes, extensions,
  skills, prompt templates, context files, providers, models, packages, or
  how to set up pi for a project. Also triggers on: "pi config", "pi settings",
  "configure pi", "customize pi", "pi setup", "how do I change X in pi",
  "pi keybindings", "pi AGENTS.md", "pi theme".
---

# Pi Configuration

Pi is configured through JSON files, context files, and a plugin system (extensions, skills, prompt templates, themes, packages). This skill is a curated index — it tells you which doc to read for each config question.

## Quick orientation

| What | Where |
|------|-------|
| All settings (JSON) | `~/.pi/agent/settings.json` (global), `.pi/settings.json` (project overrides) |
| Project instructions | `AGENTS.md` or `CLAUDE.md` (walked up from cwd) |
| System prompt override | `.pi/SYSTEM.md` (replace), `APPEND_SYSTEM.md` (augment) |
| Keybindings | `~/.pi/agent/keybindings.json` |
| Extensions | `~/.pi/agent/extensions/`, `.pi/extensions/` |
| Skills | `~/.pi/agent/skills/`, `~/.agents/skills/`, `.pi/skills/`, `.agents/skills/` |
| Prompt templates | `~/.pi/agent/prompts/`, `.pi/prompts/` |
| Themes | `~/.pi/agent/themes/`, `.pi/themes/` |
| Custom models | `~/.pi/agent/models.json` |

Use `/settings` in interactive mode for common options. Use `/hotkeys` to see current shortcuts.

## How to find the right doc

**Settings and tuneables** — Read `references/settings.md`.
**Customizing behavior (extensions, skills, themes, packages)** — Read `references/customization.md`.
**Providers, models, and auth** — Read `references/providers.md`.
**Keybindings and shortcuts** — Read `references/keybindings.md`.
**Context files (AGENTS.md, SYSTEM.md)** — Read `references/context-files.md`.

Each reference file summarizes the topic and links to the full pi docs on GitHub.

## Full docs

Complete pi documentation: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/index.md
