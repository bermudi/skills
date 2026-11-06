---
name: create-project-agentsmd
description: >
  Generate a well-structured AGENTS.md (or CLAUDE.md, .cursorrules) instruction
  file for a project — encoding goals, shape, and stable project knowledge while
  avoiding volatile implementation specifics, so the file stays accurate as the
  codebase evolves. Invoked explicitly.
license: Apache-2.0
metadata:
  version: "1.1"
  topic: agent-configuration
disable-model-invocation: true
---

# Create Project AGENTS.md

Write an instruction file that encodes **what matters and why**, not how everything is wired, so it stays useful for months. **Encode what changes slowly; let the code document what changes fast.**

```
# ❌ Stale in a week
All API routes are in src/api/routes/. The auth middleware is in src/middleware/auth.ts and uses JWT with RS256.

# ✅ Useful for months
API routes follow REST conventions. Auth is required on all mutating endpoints.
When adding endpoints, match nearby files; the codebase is the source of truth.
```

## What goes in

**Litmus test: could the agent discover this from the code cheaply? If yes, cut it. If no, or discovery is expensive enough that writing it down saves real time, keep it.** Specific is not volatile: "we use event sourcing because we need audit trails" is both specific and stable.

**Keep stable reference facts** (the agent can't infer them; they change far less than file locations):
- external data sources: URLs, endpoints, auth/CORS quirks, response formats
- data contracts: schemas, file formats, field naming
- domain vocabulary (what "trial" or "gap" means here)
- required commands and project-specific multi-step procedures
- known gotchas and historical surprises

**Cut volatile detail:** exhaustive file trees, function/class names (except public contracts), line numbers, component inventories, "currently implemented in X" notes, current test counts. Prefer rules that survive a migration ("database access goes through the data layer, never raw SQL in route handlers") over ones that name the current tool.

## Where each item belongs

1. **Omit** if cheap and safe to rediscover from code or tooling.
2. **Root file** if the agent needs it before deciding what to inspect, or missing it risks wrong behavior, compatibility breakage, data loss or big wasted work. Frequency isn't the test: a rare, high-consequence gotcha belongs in root.
3. **Scoped doc** (subdirectory `AGENTS.md`, `docs/adr/` for investigations and tradeoffs, `docs/agent-context/`) if it matters only to one subsystem or uncommon task, and the root file carries an explicit trigger. A passive "see docs/foo.md" gets ignored; say *when* it must be read:

```markdown
## Debug Logging
Before changing debug logging, frontmatter preservation, or upstream-sync behavior, read `docs/fork-changes.md`.
```

Don't delete hard-won knowledge (an investigation, a comparison, a gotcha) just because it doesn't belong in a file injected into every interaction: file it somewhere it can be found.

Example, a fork-specific section: source files and function names → omit or scoped; test counts and instrumented call sites → omit; "apparently-dead plumbing is kept for upstream compatibility" → root; known limitations that change implementation decisions → root; config contract (env-var precedence, redaction guarantees) → root, or a mandatory subsystem doc behind a "before changing…" trigger; historical investigation → scoped.

## Before writing

**Scan** just for shape: what it does (README, manifest), stack and tooling, top-level layout, existing conventions (lint, tsconfig, CI already enforce things; don't duplicate). Skip the scan if the user supplies context. **Ask only what the code can't answer:** who uses it, deployment model, non-obvious constraints (compliance, SLAs, cost), and which agent tool consumes the file.

## Structure

Omit sections that don't apply. Aim for 50–150 lines; 200 is a review signal, never a reason to drop contracts, warnings or compatibility knowledge.

```markdown
# AGENTS.md
## Project       1–3 sentences: what, for whom. No marketing.
## Stack         Only what isn't inferable ("TypeScript with Bun" yes, "Node with npm" usually no).
## Architecture  Broad shapes, not paths. Non-obvious decisions (event sourcing, CQRS) with why, not how.
## Conventions   What the agent would get wrong untold and tooling doesn't enforce ("tests live beside source", "errors use { error: { code, message } }").
## Workflow      Build/test/run commands; non-obvious steps ("migrate before tests").
## Constraints & Red Lines   Project-specific hard rules ("never modify generated/"). Omit universals like "never leak secrets".
## Quality Bar   Only if "done" means more than tests + linter. Otherwise omit.
```

## Anti-patterns

- Paths and function names; things lint/CI already enforce; generic advice ("write clean code"): every agent does these anyway.
- Long prose. Use bullets, tables for structured data, code blocks for commands; 1–3 sentence section intros.
- Over-pruning until nothing is left: a file that is just "write clean code, follow conventions" should be deleted.
- Duplicating the README. A focused 50-line file beats a diffuse 300-line one.

## Tool targets

Pi: `AGENTS.md`, walks up parent dirs, no inline imports (reference by path; the agent reads on demand). Cursor: `.cursorrules`, one file at root. Default: `AGENTS.md`, noting alternatives.

## Generating and maintaining

1. Scan (or take user context), fill the structure, then review every line: "would the agent get this wrong without being told?" If not, cut it.
2. Over ~200 lines: look for duplication, discoverable inventories, and material with a clear task-specific home. Write to the project root (or where the tool expects it).
3. Update when patterns change (REST → GraphQL), not when files move.

**Revising an existing file:** classify each substantive item as keep-in-root, move-to-scoped, or omit. Preserve non-obvious contracts, warnings, compatibility constraints and known limitations by default; detail isn't evidence of unimportance. When in doubt, keep it in root and add a trigger reference to the scoped detail.
