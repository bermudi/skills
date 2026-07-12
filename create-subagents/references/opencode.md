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
| `model` | `provider/model-id`, e.g. `anthropic/claude-sonnet-4-20250514`, `opencode/gpt-5.1-codex` (Zen). Subagents inherit the invoking primary agent's model if omitted. |
| `temperature` | 0.0–1.0. Lower = more focused. Defaults: 0 for most models, 0.55 for Qwen. |
| `prompt` | System prompt file (`{file:./path}`), or use the markdown body. Path is relative to the config file's location. |
| `permission` | Object of permission keys → `allow`/`deny`/`ask` (or glob maps). See **Permission details** below. |
| `steps` | Max agentic iterations before forced text-only response. When the limit is hit, the agent gets a system prompt instructing it to summarize work and list remaining tasks. |
| `top_p` | Top-p sampling (0.0–1.0). Alternative to temperature. |
| `color` | Hex (`#FF5733`) or theme (`primary`, `secondary`, `accent`, `success`, `warning`, `error`, `info`). |
| `hidden` | `true` to hide a subagent from `@` autocomplete. Hidden agents can still be invoked by the model via the Task tool if permissions allow. |
| `disable` | `true` to disable the agent entirely. |
| `tools` | Deprecated — use `permission` instead. `true` = `{"*": "allow"}`, `false` = `{"*": "deny"}`. Supports wildcards (e.g. `mymcp_*: false` to disable a whole MCP server). |

Any **other** key is passed through directly to the provider as a model option (e.g. `reasoningEffort: "high"`, `textVerbosity: "low"` for OpenAI reasoning models). These are provider-specific.

## Permission details

Each permission key is `allow` / `ask` / `deny`. `read`, `edit`, `glob`, `grep`, `list`, `bash`, `task`, `external_directory`, `lsp`, and `skill` also accept an object of glob/pattern → action for fine-grained control; the rest take the shorthand action only.

| Key | Tools it gates |
|---|---|
| `read` | `read` |
| `edit` | `write`, `edit`, `apply_patch` |
| `glob` | `glob` |
| `grep` | `grep` |
| `list` | `list` |
| `bash` | `bash` |
| `task` | `task` (subagent invocation) |
| `external_directory` | Any tool reading/writing files outside the project worktree |
| `todowrite` | `todowrite`, `todoread` |
| `webfetch` | `webfetch` |
| `websearch` | `websearch` |
| `lsp` | `lsp` |
| `skill` | `skill` |
| `question` | `question` |
| `doom_loop` | Recovery prompts when an agent appears stuck |

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

`permission.task` (glob patterns, last match wins) controls which subagents an agent can invoke via the Task tool:

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

A `deny` removes the subagent from the Task tool description entirely, so the model won't attempt to invoke it. Users can still invoke any subagent directly via `@` regardless of task permissions.

## Built-in agents

**Primary**: `build` (default, all tools), `plan` (restricted — file edits and bash default to `ask`).

**Subagents**: `general` (full tools except todo, multi-step tasks), `explore` (fast read-only codebase search), `scout` (read-only external docs/dependency research — clones deps into OpenCode's managed cache).

Hidden system agents: `compaction`, `title`, `summary` (auto-run, not selectable).

## Reserved names

`build`, `plan`, `general`, `explore`, `scout`, `compaction`, `title`, `summary`. Avoid colliding with these.

## Usage

- Primary agents: `Tab` to cycle (or your `switch_agent` keybind).
- Subagents: invoked automatically by primary agents based on description, or manually via `@general help me search for this function`.
- Navigate child sessions: `session_child_first` (default `<Leader>+Down`), `session_child_cycle` (Right) / `session_child_cycle_reverse` (Left), `session_parent` (Up).
- `opencode agent create` — interactive command that walks through scope, description, prompt, and permissions (anything unselected is denied), then writes the markdown file for you.

## Model ids

Format is `provider/model-id`. Examples: `anthropic/claude-sonnet-4-20250514`, `anthropic/claude-haiku-4-20250514`, `opencode/gpt-5.1-codex` (via [OpenCode Zen](https://opencode.ai/docs/zen)).

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

In `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
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
