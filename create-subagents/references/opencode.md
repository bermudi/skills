# OpenCode Subagents

> Source: https://opencode.ai/docs/agents/

OpenCode has two agent types: **primary agents** (main assistants, switch with `Tab`) and **subagents** (invoked by primary agents or via `@mention`). Custom subagents use `mode: subagent`.

## File location

| Location | Scope |
|---|---|
| `.opencode/agents/<name>.md` | Per-project |
| `~/.config/opencode/agents/<name>.md` | Global |

The markdown filename becomes the agent name. `review.md` → `review` agent.

You can also configure agents in `opencode.json` (JSON format) instead of markdown files.

## File format (markdown)

```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash: deny
---

You are in code review mode. Focus on:

- Code quality and best practices
- Potential bugs and edge cases
- Performance implications
- Security considerations

Provide constructive feedback without making direct changes.
```

### Frontmatter fields

`description` is **required**.

| Field | Description |
|---|---|
| `description` | Required. What the agent does and when to use it. |
| `mode` | `primary` or `subagent`. Use `subagent` for delegation. |
| `model` | Provider/model id, e.g. `anthropic/claude-sonnet-4-20250514` |
| `temperature` | 0.0–1.0. Lower = more focused. |
| `prompt` | System prompt (or use the markdown body) |
| `permission` | Object: `edit`, `bash` each `allow`/`deny`/`ask` |
| `max_steps` | Max agent steps |
| `disable` | `true` to disable |
| `hidden` | `true` to hide from UI |
| `color` | Display color |
| `top_p` | Top-p sampling |
| `tools` | Deprecated — use `permission` instead |
| `task_permissions` | Per-task permission overrides |

## Built-in agents

**Primary**: `build` (default, all tools), `plan` (restricted, edit/bash set to `ask`).

**Subagents**: `general` (full tools except todo, multi-step tasks), `explore` (read-only codebase search), `scout` (read-only external docs/dependency research — clones deps into a managed cache).

Hidden system agents: `compaction`, `title`, `summary` (auto-run, not selectable).

## Usage

- Primary agents: `Tab` to cycle.
- Subagents: invoked automatically by primary agents based on description, or manually via `@general help me search for this function`.
- Navigate child sessions: `session_child_first` (default `<Leader>+Down`), `session_child_cycle` (Right/Left), `session_parent` (Up).

## Reserved names

`build`, `plan`, `general`, `explore`, `scout`, `compaction`, `title`, `summary`.

## Template: code reviewer subagent

```markdown
---
description: Reviews code for security, performance, and maintainability. Use after writing or modifying code, or before committing.
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash: ask
---

You are a code reviewer. Focus on security, performance, and maintainability.

For each issue:
- Explain the problem
- Show the current code with file:line
- Provide an improved version

Do not make direct changes.
```

## JSON config alternative

```json
{
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices and potential issues",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "You are a code reviewer. Focus on security, performance, and maintainability.",
      "permission": {
        "edit": "deny"
      }
    }
  }
}
```
