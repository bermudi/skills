---
name: create-project-agentsmd
description: >
  Generate a well-structured AGENTS.md (or CLAUDE.md, .cursorrules, copilot-instructions.md)
  instruction file for a project. Use when the user asks to "create an AGENTS.md", "set up
  agent instructions", "write a CLAUDE.md", "add project context for AI", "generate instruction
  file", or mentions configuring any AI coding agent's behavior for their project. Produces
  instruction files that encode goals and shape — not implementation details — so they stay
  accurate as the codebase evolves.
license: Apache-2.0
metadata:
  version: "1.0"
  topic: agent-configuration
---

# Create Project AGENTS.md

Generate a project instruction file (AGENTS.md, CLAUDE.md, etc.) that encodes **shape and intent**, not implementation specifics. The goal is a file that stays useful for months without constant updating.

## Core Principle: Goals Over Mechanism

A good instruction file tells the agent *what matters and why*, not *how everything is wired*. Implementation details rot fast — directory structures change, files move, function signatures evolve. But the project's goals, constraints, and quality standards remain stable.

**Encode things that change slowly. Let the code document things that change fast.**

```
# ❌ Stale in a week
All API routes are in src/api/routes/. Use express.Router().
The auth middleware is in src/middleware/auth.ts and uses JWT with RS256.

# ✅ Useful for months
API routes follow REST conventions. Auth is required on all mutating endpoints.
When adding endpoints, match the patterns of nearby files — the codebase is the source of truth.
```

## Before Writing

### 1. Scan the project

Read enough to understand:

- **What it does** (README, package.json, pyproject.toml, Cargo.toml — whatever's at the root)
- **Stack and tooling** (languages, frameworks, build tools, test runners)
- **Project layout** at a glance (top-level dirs, not file-by-file)
- **Existing conventions** (lint configs, tsconfig, CI files — these already enforce things, don't duplicate)

Don't read every file. You're looking for *shape*, not specifics. If the user gives you context directly, use that and skip the scan.

### 2. Ask about gaps

If you can't determine these from scanning, ask:

- **Who uses this?** (internal tool? public API? library?)
- **What's the deployment model?** (serverless? containers? monolith?)
- **Any non-obvious constraints?** (compliance, performance SLAs, cost budgets)
- **Tool-specific preferences?** (which agent(s) will consume this file?)

Don't ask questions the code already answers.

## Structure

Use this skeleton, omitting sections that don't apply. Keep the whole file under **200 lines**. Every line costs tokens on every request — be ruthless.

```markdown
# AGENTS.md

## Project
1-3 sentences. What this is, who it's for, what it does. Not a marketing blurb — just enough for the agent to orient.

## Stack
Table or short list. Languages, frameworks, key libraries, package manager, runtime.
Only list what the agent might not infer from the code. "TypeScript with Bun" is useful.
"Node.js with npm" is usually obvious.

## Architecture
Broad shapes, not file paths. "Monorepo with apps/ and packages/" or "SPA frontend
calling REST API backed by PostgreSQL." The agent can `ls` to find specifics.
If there's a key architectural decision that's non-obvious (e.g., event sourcing,
CQRS, microservices), mention it with *why*, not *how*.

## Conventions
Things the agent should know that aren't enforced by tooling. For example:
- "Tests live alongside source files, not in a separate test/ directory"
- "API errors use a consistent envelope: { error: { code, message } }"
- "Database queries go through the data layer, never raw SQL in route handlers"

Only list conventions that the agent would reasonably get wrong without being told.
If ESLint/Prettier/Ruff already enforce it, don't restate it here.

## Workflow
How to build, test, and run. Just the commands — the agent doesn't need paragraphs
about what each does. If there's a non-obvious step (e.g., "must run migrations before
tests"), mention it.

## Constraints & Red Lines
Hard rules. Things that must never happen. Security boundaries, compliance requirements,
destructive operations that require confirmation. Be specific.
"Never exfiltrate secrets" is universal — omit unless you have project-specific additions.
"Never modify files in generated/" is project-specific — include it.

## Quality Bar
What "done" means here. Not generic best practices — the project's specific standards.
If there aren't any beyond "tests pass and linter is clean", omit this section entirely.
```

## Anti-Patterns to Avoid

### ❌ File paths and function names
These change. The agent can discover them by reading the code.

### ❌ Things tooling already enforces
If your linter catches unused imports, don't list it. If your CI runs type checking, don't say "type check before committing."

### ❌ Generic advice
"Write clean code." "Handle errors properly." "Follow best practices." — useless to every agent. They all do this by default. Your file should only contain things the agent would *get wrong* without being told.

### ❌ Long prose paragraphs
Agents parse bullet points and short sections more reliably. Use tables for structured data. Use bullets for rules. Use code blocks for commands and patterns. Keep prose to 1-3 sentences per section intro.

### ❌ Implementation-specific rules when abstract ones suffice
```
# ❌ Breaks when you migrate to Drizzle
All database queries use Prisma Client. Models are defined in prisma/schema.prisma.

# ✅ Survives migration
Database access goes through an ORM/data layer — never raw SQL in route handlers.
Check the existing code for the current query patterns.
```

## Tool-Specific Adaptation

The same principles apply regardless of the file name. Adapt the output based on the target tool:

| Tool | File | Notes |
|------|------|-------|
| Claude Code | `CLAUDE.md` | Supports hierarchy — root + per-directory. Use `@path/to/file.md` for imports. |
| GitHub Copilot | `.github/copilot-instructions.md` | Use `applyTo` in `.github/instructions/*.md` for path-scoped rules. |
| Cursor | `.cursorrules` | Keep to one file at root. |
| Cline | `.clinerules/*.md` | Supports conditional `paths:` frontmatter. Split by topic. |
| OpenHands | `.openhands/microagents/` | Use repo microagents for always-active rules, knowledge for trigger-based. |
| Generic | `AGENTS.md` | Widely recognized. Good default. |

If the user doesn't specify, produce `AGENTS.md` and note alternatives.

## Generating the File

1. **Scan** the project (or accept user-provided context)
2. **Fill** the structure above, omitting empty sections
3. **Review** every line: "Would the agent get this wrong without being told?" If no, cut it.
4. **Count** — if over 200 lines, cut more. Every line is a tax on every interaction.
5. **Write** the file to the project root (or wherever the target tool expects it)

## Gotchas

- **Don't duplicate the README.** The agent can read it. AGENTS.md should contain things the README doesn't — operational rules, constraints, non-obvious conventions.
- **Don't try to be comprehensive.** A focused 50-line file outperforms a diffuse 300-line one. The agent has context limits and attention limits.
- **Update when patterns change, not when files move.** If you switch from REST to GraphQL, update the architecture section. If you rename a file, don't bother.
- **HTML comments are hidden from some agents.** In Claude Code, `<!-- -->` in CLAUDE.md is stripped before injection. Don't put rules in comments.
