---
name: create-project-agentsmd
description: >
  Generate a well-structured AGENTS.md (or CLAUDE.md, .cursorrules) instruction
  file for a project — encoding goals, shape, and stable project knowledge while
  avoiding volatile implementation specifics, so the file stays accurate as the
  codebase evolves. Invoke explicitly with /create-project-agentsmd.
license: Apache-2.0
metadata:
  version: "1.0"
  topic: agent-configuration
disable-model-invocation: true
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

## Stable Reference Facts Are Not Noise

"Implementation details" are things that change when you refactor — file paths, function names, current library versions. **Stable reference facts** are things the agent needs to know but cannot reliably discover from code. Don't conflate the two.

**Include stable reference facts:**

| Category | Examples |
|----------|----------|
| External data sources | CDN URLs, API endpoints, auth/CORS quirks, expected response formats |
| Data contracts | Database schemas, file formats, data shapes, field naming conventions |
| Domain vocabulary | What "trial" means here, what a "gap" represents, confidence level definitions |
| Workflows | Required commands, SQL queries that encode project-specific knowledge, multi-step procedures |
| Known gotchas | Non-obvious system behavior, historical surprises, pitfalls documented from past work |

These don't rot — CDN URLs and schemas change far less often than file locations. And even when they do change, having them documented means the next agent can find and update them instead of guessing.

**Cut volatile implementation details:**

| Category | Why cut |
|----------|---------|
| Exhaustive file trees | Discoverable with `ls`/`find` |
| Function/class names (unless public contracts) | Discoverable with `grep`, change on refactor |
| Line numbers | Rot immediately |
| Component inventories | Discoverable from file tree; current structure is temporary |
| "Currently implemented in X" notes | Will be wrong tomorrow |

**The litmus test:** Could the agent discover this from code alone? If yes, cut it. If no — or if discovery would be expensive enough that documenting it saves real time — keep it.

## File It, Don't Delete It

Cutting from AGENTS.md doesn't mean the knowledge should vanish. If something took real effort to figure out — an investigation, a comparison of approaches, a non-obvious gotcha — it has value. It just doesn't belong in a file injected into *every* agent interaction.

**File elsewhere when:**
- The context is useful but too niche for the root file (e.g., a specific subsystem's conventions)
- It's an explanation of *why* a decision was made, not a rule the agent needs to follow
- It documents a complex workflow that only matters in certain tasks
- It's a gotcha that's real but rare — worth knowing about, not worth taxing every interaction

**Where to file it:**
- `docs/adr/` (or `docs/decisions/`) for investigations and tradeoff analysis
- Subdirectory `AGENTS.md` (or `CLAUDE.md`) for per-directory rules
- `docs/agent-context/` or project `docs/` for anything the agent reads on demand

Reference the file from AGENTS.md with a one-liner. Most agents have a `read` tool — a path mention is enough to prompt them to load it.

```markdown
# AGENTS.md
## Architecture
Monorepo with event-driven backend. See `docs/adr/003-event-sourcing.md` for the rationale.
```

**The refined litmus test:** Two questions, not one:
1. Could the agent discover this from code alone? → If yes, cut it.
2. Would rediscovering it from scratch cost real time or risk getting it wrong? → If yes, file it — just not in the root AGENTS.md.

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

This doesn't mean "never include specifics." Stable reference facts like API endpoints, database schemas, and domain definitions belong in AGENTS.md — the agent can't infer them. The rule is: avoid coupling to *current implementation choices likely to change*, not *stable project knowledge.*

### ❌ Over-pruning until the file says nothing
The other extreme of including too much. If your AGENTS.md is just "write clean code, test things, follow conventions" — delete it. It's wasting tokens without guiding behavior.

But don't mistake *specific* for *volatile*. A note like "we use event sourcing because we need audit trails" is specific *and* stable. Cutting it because it's "too detailed" leaves the agent guessing at every architectural decision. If an investigation took real time, the answer belongs *somewhere* — even if it's not in the root file. See [File It, Don't Delete It](#file-it-dont-delete-it).

## Tool-Specific Adaptation

The same principles apply regardless of the file name. Adapt the output based on the target tool:

| Tool | File | Notes |
|------|------|-------|
| Pi | `AGENTS.md` | Walks up parent directories. No inline imports — reference files by path, agent reads on demand via `read` tool. |
| Cursor | `.cursorrules` | Keep to one file at root. |
| Generic | `AGENTS.md` | Widely recognized. Good default. |

If the user doesn't specify, produce `AGENTS.md` and note alternatives.

## Generating the File

1. **Scan** the project (or accept user-provided context)
2. **Fill** the structure above, omitting empty sections
3. **Review** every line: "Would the agent get this wrong without being told?" If no, cut it.
4. **Count** — if over 200 lines, cut more. Every line is a tax on every interaction.
5. **Write** the file to the project root (or wherever the target tool expects it)

## Maintaining the File

- **Update when patterns change, not when files move.** If you switch from REST to GraphQL, update the architecture section. If you rename a file, don't bother.

## Gotchas

- **Don't duplicate the README.** The agent can read it. AGENTS.md should contain things the README doesn't — operational rules, constraints, non-obvious conventions.
- **Don't try to be comprehensive.** A focused 50-line file outperforms a diffuse 300-line one. The agent has context limits and attention limits.
