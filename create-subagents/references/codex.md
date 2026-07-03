# Codex Subagents

> Source: https://developers.openai.com/codex/subagents

Codex is the odd one out: custom agents are **TOML files**, not Markdown. Codex only spawns subagents when you explicitly ask it to. Each subagent does its own model/tool work, so subagent workflows consume more tokens than single-agent runs.

## File location

| Location | Scope |
|---|---|
| `~/.codex/agents/<name>.toml` | Personal (all projects) |
| `.codex/agents/<name>.toml` | Project-scoped |

Each file defines one custom agent. Codex identifies the agent by its `name` field (matching filename to name is just convention). If a custom name matches a built-in (`explorer`, `worker`, `default`), the custom one takes precedence.

## File format (TOML)

```toml
name = "reviewer"
description = "PR reviewer focused on correctness, security, and missing tests."
model = "gpt-5.4"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Review code like an owner.
Prioritize correctness, security, behavior regressions, and missing test coverage.
Lead with concrete findings, include reproduction steps when possible, and avoid
style-only comments unless they hide a real bug.
"""
nickname_candidates = ["Atlas", "Delta", "Echo"]
```

### Required fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Agent name Codex uses when spawning/referring |
| `description` | Yes | Human-facing guidance for when Codex should use this agent |
| `developer_instructions` | Yes | Core instructions defining behavior (the "system prompt") |

### Optional fields (inherit from parent session if omitted)

| Field | Description |
|---|---|
| `nickname_candidates` | List of display nicknames for spawned instances |
| `model` | Model id |
| `model_reasoning_effort` | Reasoning effort |
| `sandbox_mode` | `read-only`, `workspace-write`, etc. |
| `mcp_servers` | MCP server config |
| `skills.config` | Skills config |

You can include other supported `config.toml` keys in a custom agent file — custom agents override the same settings as a normal Codex session config.

## Global settings (in `config.toml`)

```toml
[agents]
max_threads = 6           # concurrent open agent thread cap (default 6)
max_depth = 1             # nesting depth, root=0 (default 1)
job_max_runtime_seconds   # optional, per-worker timeout for CSV fan-out (default 1800)
```

Keep `max_depth` at the default unless you specifically need recursive delegation — raising it can cause fan-out that increases tokens, latency, and resource use.

## Built-in agents

| Agent | Purpose |
|---|---|
| `default` | General-purpose fallback |
| `worker` | Execution-focused: implementation and fixes |
| `explorer` | Read-heavy codebase exploration |

## Approvals and sandbox

Subagents inherit the current sandbox policy. In interactive CLI, approval requests can surface from inactive agent threads — the overlay shows the source thread label, press `o` to open it. In non-interactive flows, an action needing new approval fails and the error surfaces to the parent.

Codex reapplies the parent turn's live runtime overrides (`/permissions` changes, `--yolo`) when spawning a child, even if the custom agent file sets different defaults.

## Managing subagents

- `/agent` in the CLI to switch between active agent threads and inspect ongoing threads.
- Ask Codex directly to steer, stop, or close a running subagent.

## Template: PR review trio

Three focused agents that split review work:

`.codex/agents/pr-explorer.toml`:
```toml
name = "pr_explorer"
description = "Read-only codebase explorer for gathering evidence before changes are proposed."
model = "gpt-5.3-codex-spark"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
Stay in exploration mode.
Trace the real execution path, cite files and symbols, and avoid proposing fixes
unless the parent agent asks for them.
Prefer fast search and targeted file reads over broad scans.
"""
```

`.codex/agents/reviewer.toml`:
```toml
name = "reviewer"
description = "PR reviewer focused on correctness, security, and missing tests."
model = "gpt-5.4"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Review code like an owner.
Prioritize correctness, security, behavior regressions, and missing test coverage.
Lead with concrete findings, include reproduction steps when possible, and avoid
style-only comments unless they hide a real bug.
"""
```

Prompt that uses them: "Review this branch against main. Have pr_explorer map the affected code paths, reviewer find real risks."
