---
name: create-subagents
description: >
  Create custom subagents (a.k.a. custom agents, delegate agents) for coding agent
  CLIs. Use when the user asks to "create a subagent", "set up a custom agent",
  "add a reviewer agent", "configure delegation", or wants a specialized worker
  agent for Devin, Claude Code, OpenCode, Codex, AMP, Command Code, or Pi.
  Covers file format, location, frontmatter fields, tool restrictions, model
  selection, and system-prompt authoring for each CLI.
license: Apache-2.0
metadata:
  version: "1.0"
  topic: agent-configuration
---

# Create Subagents for Coding Agent CLIs

Custom subagents are specialized worker agents the main agent can delegate to. Each runs in its own context window with its own system prompt, tool set, and (often) model. They keep exploration, review, or niche workflows out of the main session's context.

This skill covers seven CLIs that all support custom subagents. They share the same shape — a **name**, a **description** (the triggering mechanism), a **system prompt**, **tool restrictions**, and an optional **model override** — but differ in file format, location, and field names.

## Step 1: Identify the target CLI

Ask or infer which CLI the user is targeting. Detect from project files when possible:

| Signal in the project | CLI |
|---|---|
| `.claude/`, `CLAUDE.md`, `claude` references | Claude Code |
| `.devin/`, `devin` references | Devin |
| `.opencode/`, `opencode.json` | OpenCode |
| `.codex/`, `codex` references | Codex |
| `.commandcode/` | Command Code |
| `amp` references, `@ampcode/plugin` | AMP |
| `.pi/`, `pi` references | Pi |

If unclear, ask: "Which agent CLI are you using — Claude Code, Devin, OpenCode, Codex, AMP, Command Code, or Pi?"

**Read the matching reference file for the exact file format, location, and frontmatter fields:**

- `references/claude-code.md` — Claude Code (`.claude/agents/*.md`, YAML frontmatter)
- `references/devin.md` — Devin (`.devin/agents/<name>/AGENT.md`, YAML frontmatter)
- `references/opencode.md` — OpenCode (`.opencode/agents/*.md` or `opencode.json`, YAML frontmatter)
- `references/codex.md` — Codex (`~/.codex/agents/*.toml` or `.codex/agents/*.toml`, TOML)
- `references/commandcode.md` — Command Code (`.commandcode/agents/*.md`, YAML frontmatter)
- `references/amp.md` — AMP (TypeScript plugin via `@ampcode/plugin`, programmatic)
- `references/pi.md` — Pi (npm extension package, e.g. `pi-delegate`; or `.pi/agents/*.md` with some packages)

## Step 2: Apply universal subagent design principles

These hold across every CLI. Get these right before worrying about field names.

### Scope narrowly

A subagent should own **one kind of job**. "Code reviewer" is good. "Reviews code, writes tests, and runs migrations" is three agents fighting in one file. If you can't describe the agent's job in one sentence, split it.

### The description is the trigger

In every CLI, the main agent reads the subagent's `description` to decide **when to delegate**. This is the highest-leverage field. Write it as guidance for the delegating agent, not marketing:

```
# Weak — doesn't tell the agent when to use it
A code review agent.

# Strong — names the trigger condition
Reviews uncommitted Go code for race conditions, error handling, and context
propagation. Use after writing or modifying concurrent code or before committing.
```

Include **when to use it**, not just what it does. Mention the specific contexts where delegation should fire.

### Match tools to the job

Restrict tools to the minimum the job needs. A read-only research agent that can write files will eventually write files. Restriction is a guardrail, not a limitation.

| Job | Tools |
|---|---|
| Codebase exploration / research | read, grep, glob (no write/edit) |
| Code review | read, grep, glob, exec (scoped to read-only commands like `git diff`) |
| Test running | read, grep, glob, exec (scoped to test commands) |
| Implementation | full tool access |

### Pick the model deliberately

Default to inheriting the parent's model. Override only when there's a reason:
- **Exploration / lookup** → a faster, cheaper model (e.g. Haiku, a mini variant). High volume, low stakes.
- **Review / critique / debugging** → a strong reasoning model. Low volume, high stakes.
- **Implementation** → inherit, or match the parent.

### Write a focused system prompt

The system prompt is the subagent's entire worldview — it does **not** inherit the parent's conversation or full system prompt. Tell it:

1. **Its role** — one line: "You are a security-focused code reviewer."
2. **Its scope** — what's in and out of bounds: "Inspect only the files named by the caller. Do not propose architectural changes."
3. **Its output format** — what to return: "Report findings as a list with severity, file:line, evidence, and suggested fix."
4. **Its constraints** — "Cite specific file paths and line numbers. Be concise."

Keep it short. A subagent with a 200-line system prompt will spend its context budget on instructions, not work.

## Step 3: Write the file

Using the format and location from the reference file, write the subagent definition. Concretely:

1. Choose **project scope** (shared via version control, recommended default) or **personal/global scope** (available everywhere, not shared).
2. Pick the filename — most CLIs derive the agent name from the filename or a `name` field.
3. Fill in the config fields the CLI expects (`name`, `description`, tools, model — but field names and format vary; Codex uses TOML, AMP is programmatic). See the reference file.
4. Write the system prompt as the markdown body (or `developer_instructions` for Codex, `instructions` for AMP).
5. Save to the correct directory.

See the reference file for a copy-pasteable template and the exact field names that CLI expects.

## Step 4: Verify

- Confirm the file is in the right location (wrong dir = silently not loaded).
- Restart the CLI if its docs say directory scanning only happens at startup (some watch for changes, some don't — the reference file notes this).
- Test delegation: ask the main agent to "use the <name> agent to <task>" or describe a task that matches the description.
- If it doesn't trigger, the description is usually the problem — make the trigger condition more explicit.

## Gotchas

- **Reserved names.** Several CLIs reserve built-in names (`explore`, `plan`, `general`, `review`, `worker`, `explorer`, `default`). A custom file with a reserved name is silently ignored or causes conflicts. Check the reference file's reserved-names list before naming.
- **`tools` vs `allowed-tools`.** Field names differ across CLIs (Claude Code uses `tools`, Devin uses `allowed-tools`). They're not interchangeable — use the one your CLI expects.
- **Background subagents can't prompt.** In CLIs with background mode (Devin, Claude Code), a background subagent that needs an unapproved tool will fail silently. Either pre-approve the tools or restrict to read-only.
- **Nesting is off by default.** Most CLIs disable subagent-spawning inside subagents to prevent unbounded fan-out. Don't assume a subagent can spawn its own subagents unless you explicitly enable it.
- **Codex uses TOML, not Markdown.** It's the odd one out — see `references/codex.md`.
- **AMP is programmatic.** Subagents are defined in a TypeScript plugin, not a markdown file — see `references/amp.md`.
- **Pi subagents come from extensions.** Pi's subagent model is package-based (`pi-delegate`, `pi-subagents`, `pi-subagent`); some packages also read `.pi/agents/*.md`. See `references/pi.md`.
