# MiMo Code Subagents

> Source: https://mimo.xiaomi.com/mimocode/agents

MiMo Code has two agent types: **primary agents** (main assistants, switch with `Tab`) and **subagents** (invoked by primary agents or via `@mention`). Custom subagents use `mode: subagent`.

## File location

| Location | Scope |
|---|---|
| `.mimocode/agents/<name>.md` | Per-project |
| `~/.config/mimocode/agents/<name>.md` | Global |

The markdown filename becomes the agent name. `review.md` → `review` agent.

You can also configure agents in `mimocode.json` (JSON format) instead of markdown files.

## File format (markdown)

```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: mimo/mimo-v2.5-pro
temperature: 0.1
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "git log*": allow
    "grep *": allow
  webfetch: deny
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
| `mode` | `primary`, `subagent`, or `all` (default `all`). Use `subagent` for delegation. |
| `model` | `provider/model-id`, e.g. `mimo/mimo-v2.5-pro` (MiMo Platform). If omitted, primary agents use the globally-configured model and subagents inherit the invoking primary agent's model. |
| `temperature` | 0.0–1.0. Lower = more focused. Defaults: 0 for most models, 0.55 for Qwen. |
| `prompt` | System prompt file (`{file:./path}`), or use the markdown body. Path is relative to the config file's location. |
| `permission` | Object: `edit`, `bash`, `webfetch` each `allow`/`deny`/`ask`. `bash` accepts glob patterns. |
| `permission.task` | Glob patterns controlling which subagents this agent can invoke via the Task tool. Last matching rule wins. |
| `steps` | Max agentic iterations before forced text-only response (legacy `maxSteps` is deprecated). |
| `tools` | Deprecated — use `permission` instead. `true` = `{"*": "allow"}`, `false` = `{"*": "deny"}`. Supports wildcards (`mymcp_*: false`). |
| `top_p` | Top-p sampling (0.0–1.0). |
| `color` | Hex (`#FF5733`) or theme (`primary`, `secondary`, `accent`, `success`, `warning`, `error`, `info`). |
| `hidden` | `true` to hide from `@` autocomplete (subagents only). Hidden agents can still be invoked by the model via the Task tool. |
| `disable` | `true` to disable the agent entirely. |

Any **other** key is passed through to the provider as a model option (e.g. `reasoningEffort: "high"`, `textVerbosity: "low"` for OpenAI reasoning models). These are provider-specific.

## Permission details

`permission.bash` takes a glob map; the **last matching rule wins**, so put `"*": ask` first and specific rules after:

```json
{
  "permission": {
    "bash": {
      "*": "ask",
      "git status *": "allow"
    }
  }
}
```

`permission.task` (glob patterns, last match wins):

```json
{
  "permission": {
    "task": {
      "*": "deny",
      "orchestrator-*": "allow",
      "code-reviewer": "ask"
    }
  }
}
```

A `deny` removes the subagent from the Task tool description entirely. Users can still invoke any subagent directly via `@` regardless of task permissions.

## Built-in agents

**Primary**: `build` (default, all tools), `plan` (restricted — file edits and bash default to `ask`).

**Subagents**: `general` (full tools except todo, multi-step tasks), `explore` (read-only codebase search).

Hidden system agents: `compaction`, `title`, `summary` (auto-run, not selectable).

## Reserved names

`build`, `plan`, `general`, `explore`, `compaction`, `title`, `summary`. The docs state built-ins can be customized via config — they don't document what happens when a custom file uses a built-in name, so avoid colliding.

## Usage

- Primary agents: `Tab` to cycle (or your `switch_agent` keybind).
- Subagents: invoked automatically by primary agents based on description, or manually via `@general help me search for this function`.
- Navigate child sessions: `session_child_first` (default `<Leader>+Down`), `session_child_cycle` (Right/Left), `session_parent` (Up).
- `mimo agent create` — interactive command that walks through scope, description, prompt, and tools, then writes the markdown file for you.

## Model ids

Format is `provider/model-id`. Run `mimo models` to list available models. MiMo Platform example: `mimo/mimo-v2.5-pro`.

## Template: code reviewer subagent

```markdown
---
description: Reviews code for security, performance, and maintainability. Use after writing or modifying code, or before committing.
mode: subagent
model: mimo/mimo-v2.5-pro
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

In `mimocode.json`:

```json
{
  "$schema": "https://mimo.xiaomi.com/mimocode/config.json",
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices and potential issues",
      "mode": "subagent",
      "model": "mimo/mimo-v2.5-pro",
      "prompt": "You are a code reviewer. Focus on security, performance, and maintainability.",
      "permission": {
        "edit": "deny"
      }
    }
  }
}
```
