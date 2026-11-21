---
name: create-project-agentsmd
description: >
  Generate or revise a project AGENTS.md encoding goals, shape
  and stable knowledge, not volatile implementation details.
license: Apache-2.0
metadata:
  version: "1.2"
  topic: agent-configuration
disable-model-invocation: true
---

# Create Project AGENTS.md

Write an instruction file that encodes **what matters and why**, not how everything is wired, so it stays useful for months. **Encode what changes slowly; let the code document what changes fast.**

```text
# ❌ Stale in a week
All API routes are in src/api/routes/. The auth middleware is in src/middleware/auth.ts and uses JWT with RS256.

# ✅ Useful for months
API routes follow REST conventions. Auth is required on all mutating endpoints.
When adding endpoints, match nearby files; the codebase is the source of truth.
```

## What goes in

**Litmus test:** would the agent get this wrong without being told, or spend meaningful time rediscovering it? If no, cut it. Specific is not volatile: "we use event sourcing because we need audit trails" is both specific and stable.

**Keep stable reference facts:**
- external data sources: URLs, endpoints, auth/CORS quirks, response formats
- data contracts: schemas, file formats, field naming
- domain vocabulary: put project-specific terms in `GLOSSARY.md` at repo root if the repo uses one (or create it when project jargon accumulates); otherwise keep a short list in root `AGENTS.md`
- required commands and project-specific multi-step procedures
- known gotchas and historical surprises

**Cut volatile or redundant detail:** exhaustive file trees, function/class names (except public contracts), line numbers, component inventories, "currently implemented in X" notes, current test counts, anything lint/CI already enforces, and generic advice ("write clean code"). Prefer rules that survive a migration ("database access goes through the data layer, never raw SQL in route handlers") over ones naming the current tool.

## Where each item belongs

1. **Omit** if it fails the litmus test.
2. **Root file** if the agent needs it before deciding what to inspect, or missing it risks wrong behavior, compatibility breakage, data loss or big wasted work. Frequency isn't the test: a rare, high-consequence gotcha belongs in root.
3. **Scoped doc** (subdirectory `AGENTS.md`, `docs/adr/` for investigations and tradeoffs, `docs/agent-context/`) if it matters only to one subsystem or uncommon task, and the root file carries an explicit trigger. A passive "see docs/foo.md" gets ignored; say *when* it must be read:

```markdown
## Debug Logging
Before changing debug logging, frontmatter preservation, or upstream-sync behavior, read `docs/fork-changes.md`.
```

Don't delete hard-won knowledge (an investigation, a comparison, a gotcha) just because it doesn't belong in root: file it somewhere findable.

Example — classifying a fork-specific section:

| Item | Placement |
|---|---|
| Source files, function names, test counts, instrumented call sites | Omit (or scoped) |
| "Apparently-dead plumbing is kept for upstream compatibility" | Root |
| Known limitations that change implementation decisions | Root |
| Config contract (env-var precedence, redaction guarantees) | Root, or scoped behind a "before changing…" trigger |
| Historical investigation / comparison | Scoped (`docs/adr/`) |

## Before writing

**Scan** just for shape: what it does (README, manifest), stack and tooling, top-level layout, existing conventions (lint, tsconfig, CI, `GLOSSARY.md`). Skip the scan if the user supplies context. **Ask only what the code can't answer:** who uses it, deployment model, non-obvious constraints (compliance, SLAs, cost), and which agent harness consumes the file.

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

- Long prose. Use bullets, tables for structured data, code blocks for commands; 1–3 sentence section intros.
- Over-pruning until nothing is left: a file that is just "write clean code, follow conventions" should be deleted.
- Duplicating the README. A focused 50-line file beats a diffuse 300-line one.

## Tool targets

- **Default (`AGENTS.md`):** read by Pi, Codex, Devin, T3, and modern Cursor (walks up parent dirs; no inline imports — reference scoped docs by path with triggers). `AGENTS.local.md` holds personal/harness overrides when supported.
- **Claude Code:** keep personal instructions in the global `~/.claude/CLAUDE.md` and project instructions in `AGENTS.md`. Use Claude Code's `AGENTS.md` fallback rather than creating a project `CLAUDE.md`, import stub, or symlink.
- **Forks:** if upstream already ships an `AGENTS.md`, keep it as the project entry point. Preserve upstream guidance and make only the changes the fork needs.
- **Cursor (scoped rules):** `.cursor/rules/*.mdc` for glob-scoped rules; legacy `.cursorrules` only if the repo already uses it.

## Generating and maintaining

1. Scan (or take user context), fill the structure, then apply the litmus test to every line.
2. Over ~200 lines: look for duplication, discoverable inventories, and material with a clear task-specific home. Write to the project root (or where the tool expects it).
3. Update when patterns change (REST → GraphQL), not when files move.

**Revising an existing file:** classify each substantive item as keep-in-root, move-to-scoped, or omit. Preserve non-obvious contracts, warnings, compatibility constraints and known limitations by default; detail isn't evidence of unimportance. When in doubt, keep it in root and add a trigger reference to the scoped detail.
