# ZCode Subagents

> Sources:
> - https://zcode.z.ai/en/docs/subagents (public docs)
> - `zcode-guide` plugin's `zcode-configuration-guide` and `diagnosing-plugins` skills (authoritative, shipped with the client)

ZCode (the official harness for GLM-5.2) ships with built-in **general-purpose** and **Explore** subagents and supports **user-level custom subagents** (Beta). Custom subagents are created from the Settings UI; ZCode writes each one as a Markdown file under `~/.zcode/agents/` and the runtime loads it on the next run.

## File location

| Location | Scope | Status |
|---|---|---|
| `~/.zcode/agents/<name>.md` | Personal / global (all workspaces on this machine) | Written by the Settings UI; runtime loads it on next run (per public docs) |
| Plugin manifest `agents` field | Project (shared via plugin) | **Recorded but not executed** in the current runtime — see note below |

> **User-level only via Settings.** The Settings UI manages global subagents under `~/.zcode/agents/`. There is no project/workspace-level subagent directory creatable from Settings, and `~/.zcode/agents/` is **not** listed among ZCode's documented file-configurable resources (skills, commands, MCP, hooks, plugins, AGENTS.md). Subagents are managed through **Settings → Subagents**, not by editing a config file the way MCP or hooks are.

### Plugin-bundled subagents — caveat

The public Plugin docs page describes an `agents` plugin component ("Subagents registered together with the plugin"). However, the official `diagnosing-plugins` skill (shipped in the `zcode-guide` plugin) lists `agents` under **"Recorded but not executed"** manifest fields. This means a plugin's `agents` field is currently parsed into the manifest but **not actually loaded** as runnable subagents by the runtime. Treat plugin-bundled subagents as not-yet-functional until you see them appear under **Settings → Subagents → Plugin subagents** after enabling a plugin. Do not rely on it as a way to ship subagents with a repo today.

## Creating subagents

**Use the Settings UI — it is the only supported authoring path.** The on-disk frontmatter schema for `~/.zcode/agents/<name>.md` is **not publicly documented**, and none of ZCode's configuration/diagnostic skills describe it. Hand-editing the file is unsupported; if you do it, you are guessing at the schema and should verify the subagent loads in **Settings → Subagents** after restarting the Agent runtime.

1. Open **Settings → Subagents → New** (top-right).
2. Fill in the fields (below).
3. Save. ZCode writes `~/.zcode/agents/<name>.md` and loads it on the next run.

## Fields (from the Settings UI)

| Field | Description |
|---|---|
| **Name** | Identifier, e.g. `code-reviewer`. Must not reuse a built-in name (`general-purpose`, `Explore`). |
| **Color** | Identity marker in the list/conversation; not a status. |
| **Model** | "Inherit default" (follow the primary Agent's current model) or a specific model. |
| **Description** | Shown to the primary Agent — it decides **when** to delegate based on this text. The highest-leverage field; write the trigger condition, not marketing. |
| **Available tools** | "All permissions by default" inherits every tool, or "Custom tools" checked one by one. Writable tools (`Bash`, `Edit`, `Write`) are flagged when restricting. |
| **System prompt** | The subagent's role, boundaries, and rules — its runtime system prompt. |

## Built-in subagents

| Subagent | Tool access |
|---|---|
| `general-purpose` | All tools — read, edit, run commands. Default for broad, self-contained work. |
| `Explore` | Read-only — read, glob, grep, regex content search, known-URL fetch / web search. No create/modify/move/delete. |

The primary Agent auto-selects a subagent by task. Custom subagents appear alongside the built-ins.

## Reserved names

`general-purpose` and `Explore` are built-in, read-only, and cannot be edited, deleted, or reused as a custom name.

## Execution model

- **Foreground only.** Subagents run in the foreground — when several are launched together they run in parallel, and the main task waits for all to finish before continuing. Background execution is not available yet.
- No background-mode "unapproved tool auto-deny" footgun to worry about, but also no way to keep working while a subagent runs.

## Invoking a custom subagent

Once enabled, either let the Agent pick it automatically from the description, or reference it with `@<name>` in the chat box.

## Hand-editing `~/.zcode/agents/<name>.md` (unsupported, best-effort)

If you must hand-edit instead of using the Settings UI, the only documented shape ZCode publishes for Markdown extension files is the **skill** format (`name` + `description` in YAML frontmatter, body as instructions). The subagent on-disk schema is not published, so the minimal guess below uses that shape plus the system prompt as the body. **The `model` and tool-restriction UI fields have no documented on-disk key names** — do not assume `model:` or `tools:` work; configure those in the UI after creating the file. Verify the subagent appears and is correctly configured in **Settings → Subagents** before relying on it.

```markdown
---
name: code-reviewer
description: Reviews uncommitted code for correctness, security, and missing tests before commit.
---

You are a code review subagent. Inspect only the files named by the caller.
Report findings as a list with severity, file:line, evidence, and suggested fix.
Do not make changes.
```

> If hand-editing produces a subagent that doesn't load or is missing its model/tool settings, delete the file and recreate it through **Settings → Subagents → New**. That is the supported path.

## Template: read-only security reviewer (via Settings UI)

Create via **Settings → Subagents → New** with:

- **Name**: `security-reviewer`
- **Description**: `Use before commit or release to scan for secrets, unsafe patterns (SQL injection, path traversal, deserialization), and dependency risks. Read-only.`
- **Model**: Inherit default
- **Available tools**: Custom — `Read`, `Grep`, `Glob` only (leave `Bash`/`Edit`/`Write` unchecked)
- **System prompt**:

```
You are a security-focused reviewer. Prioritize:
- Secrets in code (API keys, tokens, credentials)
- Unsafe patterns (SQL injection, path traversal, unsafe deserialization)
- Dependency risks (known CVEs, unmaintained packages)

Inspect only the files named by the caller. Be concise; cite file paths and
line numbers. Do not make changes.
```

## Template: test runner (via Settings UI)

- **Name**: `test-runner`
- **Description**: `Runs the project's test suites (npm test, cargo nextest, pytest) and reports pass/fail with failure messages and stack traces.`
- **Model**: Inherit default
- **Available tools**: Custom — `Read`, `Grep`, `Glob`, `Bash` (leave `Edit`/`Write` unchecked)
- **System prompt**:

```
You are a test runner subagent. Run the relevant test suites and report:
- Which tests passed and failed
- Failure messages and stack traces
- A concise suggestion for each failure

Do not modify source files.
```
