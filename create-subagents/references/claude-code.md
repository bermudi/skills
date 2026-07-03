# Claude Code Subagents

> Source: https://code.claude.com/docs/en/sub-agents

Claude Code subagents are Markdown files with YAML frontmatter. The body becomes the system prompt.

## File location

| Location | Scope | Priority |
|---|---|---|
| Managed settings dir | Organization-wide (admin-deployed) | 1 (highest) |
| `--agents` CLI flag (JSON) | Current session only | 2 |
| `.claude/agents/` | Current project (commit to VCS) | 3 |
| `~/.claude/agents/` | All your projects (personal) | 4 |
| Plugin's `agents/` dir | Where plugin is enabled | 5 (lowest) |

Project subagents (`.claude/agents/`) are the recommended default — share them with your team via version control. Claude Code scans recursively, so subfolders are fine. Identity comes from the `name` field, not the path.

Claude Code **watches** `.claude/agents/` and `~/.claude/agents/` for changes (no restart needed), except: a scope's first agent file in a new `agents/` dir requires a restart, and `--disable-slash-commands` sessions don't watch.

## File format

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices. Use after writing or modifying code.
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

### Frontmatter fields

Only `name` and `description` are required.

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique id, lowercase + hyphens. Filename doesn't have to match. |
| `description` | Yes | When Claude should delegate to this subagent |
| `tools` | No | Allowlist of tools. Inherits all if omitted. |
| `disallowedTools` | No | Denylist, removed from inherited/specified tools |
| `model` | No | `sonnet`, `opus`, `haiku`, `fable`, full model ID, or `inherit` (default) |
| `permissionMode` | No | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | No | Max agentic turns before stopping |
| `skills` | No | Skills to preload into context at startup |
| `mcpServers` | No | MCP servers available to this subagent (inline defs or name refs) |
| `hooks` | No | Lifecycle hooks scoped to this subagent |
| `memory` | No | Persistent memory scope: `user`, `project`, or `local` |
| `background` | No | `true` to always run as background task |
| `effort` | No | `low`, `medium`, `high`, `xhigh`, `max` (model-dependent) |
| `isolation` | No | `worktree` to run in a temporary git worktree |
| `color` | No | Display color: red, blue, green, yellow, purple, orange, pink, cyan |
| `initialPrompt` | No | Auto-submitted as first user turn when run as main session agent |

### Tool restrictions

Subagents inherit the main conversation's tools by default. These are **never** available to subagents: `AskUserQuestion`, `EnterPlanMode`, `ExitPlanMode` (unless `permissionMode: plan`), `ScheduleWakeup`, `WaitForMcpServers`.

Use `tools` as an allowlist or `disallowedTools` as a denylist. If both set, `disallowedTools` applies first. Both accept MCP patterns: `mcp__<server>` or `mcp__<server>__*`; `mcp__*` in denylist removes all MCP tools.

To restrict which subagents an agent can spawn (when running as main thread via `claude --agent`): `tools: Agent(worker, researcher), Read, Bash`.

### Model resolution

Order: `CLAUDE_CODE_SUBAGENT_MODEL` env var → per-invocation `model` param → frontmatter `model` → main conversation's model. As of v2.1.198, subagents inherit the main conversation's extended-thinking config.

## Built-in subagents

Claude Code ships with Explore (read-only codebase search), Plan (research for plan mode), and general-purpose (full tools). Explore and Plan skip CLAUDE.md and git status to stay fast. To disable built-ins: `CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS=1` (Explore+Plan only) or `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1` (all, in non-interactive/SDK). Block specific ones via `permissions.deny`.

## Reserved names

`Explore`, `Plan`, `general-purpose`, `statusline-setup`, `claude-code-guide`. A user/project subagent named `Explore` **overrides** the built-in (define `model: haiku` to keep it cheap).

## Template: read-only reviewer

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities, unsafe patterns, and secrets. Use before commits or when touching auth, crypto, or input handling.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You are a security-focused code reviewer. Inspect only the files and
concerns named by the caller.

For each finding, report:
- Severity (critical / high / medium / low)
- File path and line number
- The vulnerable code
- A suggested fix

Do not make changes. Cite specific locations.
```

## Template: implementation agent with worktree isolation

```markdown
---
name: feature-implementer
description: Implements a well-specified feature in an isolated worktree. Use when the task is clearly scoped and you want changes isolated from the working tree.
model: inherit
isolation: worktree
---

You are a feature implementation agent. Implement exactly what is asked,
no more. Run the relevant tests before reporting done.
```
