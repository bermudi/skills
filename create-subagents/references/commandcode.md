# Command Code Subagents

> Source: https://commandcode.ai/docs/core-concepts/custom-agents

Command Code custom agents are specialized **subagents** the main agent can delegate to. Each gets its own context window, system prompt, and tool set. Definitions are Markdown files with YAML front matter.

## File location

| Location | Scope |
|---|---|
| `.commandcode/agents/` in the current repo | Project (shared via VCS) |
| `~/.commandcode/agents/` | Personal (all projects on your machine) |

## Creating agents

Two paths:

1. **Interactive wizard**: run `/agents` in interactive mode → "Create new agent". Choose project or personal location, then either "Generate with Command Code" (describe the role, it drafts name/description/prompt) or "Manual configuration" (set fields yourself). Then select tools and save.
2. **Edit files directly** in `.commandcode/agents/` or `~/.commandcode/agents/`.

## File format

The filename is the agent identifier (e.g. `security-review.md` → agent `security-review`).

```markdown
---
name: "security-review"
description: "Use for dependency and secret-scanning review before release."
tools: "glob, grep, read_file, think"
---

You are a security-focused reviewer. Prioritize dependency risks, secrets in
code, and unsafe patterns. Be concise; cite file paths and lines.
```

### Frontmatter fields

| Field | Description |
|---|---|
| `name` | Identifier and filename (e.g. `security-review.md` → `security-review`) |
| `description` | Tells Command Code **when** to use this agent |
| `tools` | Comma-separated tool list, `"*"` for all tools, or a restricted (e.g. read-only) list |

## Built-in agents

`Explore` and `Plan` are always available as built-in defaults.

## Reserved names

Do **not** use these names for custom agents — they're reserved and custom files with them are ignored: `explore`, `plan`, `review`, `general`.

## Template: security reviewer

```markdown
---
name: "security-review"
description: "Use for dependency and secret-scanning review before release, or when touching auth, crypto, or input handling."
tools: "glob, grep, read_file, think"
---

You are a security-focused reviewer. Prioritize:
- Dependency risks (known CVEs, unmaintained packages)
- Secrets in code (API keys, tokens, credentials)
- Unsafe patterns (SQL injection, path traversal, deserialization)

Be concise; cite file paths and lines. Do not make changes.
```
