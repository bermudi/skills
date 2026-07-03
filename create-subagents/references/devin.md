# Devin Subagents

> Source: https://docs.devin.ai/cli/subagents

Devin subagents are defined as `AGENT.md` files inside a named directory under `agents/`. The directory name becomes the profile identifier.

## File location

| Location | Scope |
|---|---|
| `.devin/agents/<name>/AGENT.md` | Project-specific |
| `.agents/agents/<name>/AGENT.md` | Project-specific (alt path) |
| `~/.config/devin/agents/<name>/AGENT.md` | Global (Linux/macOS) |
| `%APPDATA%\devin\agents\<name>\AGENT.md` | Global (Windows) |

## File format

```markdown
---
name: reviewer
description: Reviews code changes for correctness and style
model: sonnet
allowed-tools:
  - read
  - grep
  - glob
  - exec
permissions:
  allow:
    - Exec(git diff)
    - Exec(git log)
  deny:
    - write
    - edit
---

You are a code review subagent. Your job is to review code changes
thoroughly and report findings back to the parent agent.

Focus on:
1. Correctness — logic errors, edge cases, off-by-one mistakes
2. Security — potential vulnerabilities
3. Style — consistency with the rest of the codebase
4. Performance — obvious inefficiencies

Always cite specific file paths and line numbers in your findings.
```

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | directory name | Profile identifier (must not conflict with built-ins) |
| `description` | string | none | Shown to agent when selecting a profile |
| `model` | string | default subagent model | Override the model |
| `allowed-tools` | list | all tools | Restrict tools. Cannot grant `ask_user_question` (always withheld). |
| `permissions` | object | inherit | `allow`, `deny`, `ask` overrides |
| `max-nesting` | integer | none | Override max nesting depth (lets this subagent spawn its own subagents) |

## Built-in profiles

| Profile | Tool access |
|---|---|
| `subagent_explore` | Read-only codebase tools + web search; cannot edit or fetch arbitrary URLs |
| `subagent_general` | Full tool access (foreground) or pre-approved tools only (background) |

The agent auto-selects a profile by task. Custom profiles appear alongside built-ins. Custom profiles conflicting with `subagent_explore` / `subagent_general` are skipped with a warning.

## Foreground vs background

- **Foreground**: runs inline, parent pauses, you approve/deny tool calls.
- **Background**: runs in parallel, parent continues, unapproved tools auto-denied. Switch with `Ctrl+B` (background a foreground one) or `f` in the subagent panel (foreground a background one).

Background subagents **cannot prompt for new permissions**. If a background subagent fails on a denied tool, resume it in the foreground to approve.

## Nesting

By default subagents cannot spawn subagents — `run_subagent` and `read_subagent` are disabled inside subagents. A custom profile can opt in via `max-nesting: 3` (allows the chain root→child→grandchild→stops).

## Importing from Claude Code

Devin also imports `.claude/agents/*.md` — each becomes a subagent profile. Claude Code uses `tools` instead of `allowed-tools`; both formats are supported.

## Reserved names

`subagent_explore`, `subagent_general`.

## Template: read-only research agent

```markdown
---
name: researcher
description: Deep codebase research and architecture analysis
model: sonnet
allowed-tools:
  - read
  - grep
  - glob
---

You are a research subagent specializing in codebase exploration.

Your job is to thoroughly investigate a topic and report back with:
- Relevant files and their purposes
- Architecture patterns and dependencies
- Code flow traces with specific line references

Be exhaustive — search broadly and follow references.
```

## Template: test runner

```markdown
---
name: test-runner
description: Runs tests and reports results
allowed-tools:
  - read
  - grep
  - glob
  - exec
permissions:
  allow:
    - Exec(npm run test)
    - Exec(cargo nextest)
    - Exec(pytest)
---

You are a test runner subagent. Run the relevant test suites and report:
- Which tests passed and failed
- Failure messages and stack traces
- Suggestions for fixing failures
```
