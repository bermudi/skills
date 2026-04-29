# AGENTS.md

## What This Is

A monorepo of [Agent Skills](https://agentskills.io) — self-contained prompt packages that extend AI agent capabilities. Each skill is a directory with a `SKILL.md` as its entry point.

## Repository Layout

Skills live as top-level directories.

```
skill-name/
├── SKILL.md          # Required: frontmatter + instructions
├── scripts/          # Optional: executable tooling the agent runs during tasks
├── references/       # Optional: deep-dive docs (progressive disclosure)
├── evals/            # Optional: evals.json test cases
├── assets/           # Optional: templates, resources
└── research/         # Optional: gitignored research artifacts (probes, raw data, etc.)
```

**DO NOT touch the skills inside .agents/skills/ or .pi/skills/**

## SKILL.md Format

YAML frontmatter followed by Markdown content:

```yaml
---
name: kebab-case-name       # required, max 64 chars
description: >               # required, max 1024 chars, no angle brackets
  When to trigger this skill.
license: Apache-2.0          # optional
metadata:                    # optional
  version: "3.1"
  topic: context-engineering
---

Skill instructions in Markdown...
```

Allowed frontmatter keys: `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`.

## Deploying Skills

This repo is the **source of truth** for skills. 

**`skills` detects changes via git state, not filesystem mtime.** You must `git add && git commit` before `skills update -g` will pick up your edits. Pushing ensures remote mirrors stay in sync too.

## Validation

Uses [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) (the official reference validator). CI runs on every push.

```bash
# Install once
uv tool install git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref

# Validate a single skill
skills-ref validate ./skill-name

# Validate all skills
for dir in */; do [ -f "${dir}SKILL.md" ] && skills-ref validate "${dir}"; done
```

For trigger accuracy testing (spawns `claude -p` subprocesses):

```bash
uv run python skill-creator/scripts/run_eval.py ./skill-name
```

## Research Artifacts

When building a skill, you'll often produce one-off research files — API probes, benchmark scripts, raw result JSON, investigation reports. These are **not** part of the published skill and should live in a gitignored `research/` directory:

```
skill-name/research/.gitignore   # ignores everything except itself
```

```gitignore
*
!.gitignore
```

**Why not `scripts/`?** `scripts/` is for reusable tools the agent runs during task execution. Research artifacts are tools *you* used to produce the skill's content — the agent should never discover and run them. Keep the skill root clean.
