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

**DO NOT touch the skills inside .agents/skills/, .pi/skills/ or any other skill outside of this repository!!** Exception: entries under `~/.agents/skills/` that are symlinks back into this repo resolve here — but edit them via the repo path, never through the installed path, so the change shows up in `git status`.

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

**Keep descriptions lean.** The `description` is loaded into context *every single turn* so the agent can decide whether to trigger the skill. Bloat it and you pay that token cost forever, on every message, whether the skill fires or not.

## Deploying Skills

This repo is the **source of truth** for skills. We do NOT use the `skills` CLI to manage this repo's installs — installed copies are **plain symlinks** into this checkout (`~/.agents/skills/*`; `pi-docs` scoped to pi at `~/.pi/agent/skills/pi-docs`; external ones like `terminal-browser` and local-only ones like `filing-supervisor` stay tool-managed). The installed copy IS the working tree: **edits are live immediately**, no install/update step, nothing needs to "register" anywhere.

Git is history and CI only (skills-ref validation runs on push). Commit often; do not push without explicit permission.

New repo skills are NOT linked automatically (every install adds every-turn description cost); link deliberately:

```bash
./scripts/link-local-skills                 # dry run
./scripts/link-local-skills --apply         # (re)link; displaced copies go through `trash`
./scripts/link-local-skills --apply --skill <name>
```

`link-local-skills` only relinks installs stamped with our `github-repo` marker;
foreign installs (no marker, e.g. tool-shipped) link manually:
`trash ~/.agents/skills/<name> && ln -s "$PWD/<name>" ~/.agents/skills/<name>`

Warning: running `skills update -g` anyway can replace a symlink with a fresh directory copy — re-run `link-local-skills --apply` to repair, it detects and trashes displaced copies.

## Adopting a Skill

Two separate operations: **adopt** = move a skill into this repo as source of
truth (inert until installed — no context cost); **install** = link it into
`~/.agents/skills` so it works (see Deploying Skills above). Adopting does
NOT install. Install separately, deliberately, only when you want it live.

To adopt an upstream skill or standalone install:

1. Copy the skill directory in (usually just its `SKILL.md`).
2. Validate: `skills-ref validate ./<name>`
3. Commit here.
4. Add it to the Provenance table — including upstream, if any.

Adopt anything you expect to edit more than once. Leave one-off tool-managed
skills (e.g. `terminal-browser`) alone.

## Skill Provenance

Some skills are authored here from scratch; others were adapted from upstream sources and should be checked periodically for updates. `scripts/check-upstream.sh` body-diffs tracked skills against their upstream repos; local versions have diverged, so review diffs before merging anything upstream.

**Derived from upstream (track for updates):**

| Skill | Upstream | Notes |
|---|---|---|
| `content-retrieval` (LiteParse portion) | `run-llama/llamaparse-agent-skills` → former `skills/liteparse` | Consolidated skill is locally authored; only its LiteParse guide/search helper track upstream |
| `agent-browser` | `vercel-labs/agent-browser` → `skills/agent-browser` | Rewrote description + inlined workflow content; carries local agent-ff Firefox tooling under `scripts/` |
| `frontend-design` | `anthropics/skills` → `skills/frontend-design` | Adopted near-verbatim (Apache-2.0 LICENSE.txt included); license field set to SPDX identifier |
| `mcporter` | `steipete/clawdis` → `skills/mcporter` | Condensed upstream into a minimal stub |
| `skill-creator` | started from `anthropics/skills` → `skills/skill-creator` | **Owned here now** — substantially rewritten with its own eval tooling; no longer tracks upstream |
| `html-communication` | `plannotator/effective-html` → `skills/html` + sibling specialists | Consolidated the 6-skill collection (router + `design-artifact`, `html-wireframe`, `html-prototype`, `html-plan`, `html-diagram`) into one skill with specialized references; merged `design-artifact`+`creative-direction` and `html-diagram`+`diagrams` |

**Authored here (no upstream):**

`agent-memory-management`, `agent-observability`, `child-process-supervisor`, `create-project-agentsmd`, `create-subagents`, `litespec-pipeline`, `pass-cli`, `perspectives`, `pi-docs`, `plannotator` (adopted from a standalone install, then rewritten from the official docs at docs.plannotator.ai — owned here; docs can lag or lead the installed binary, trust `plannotator <cmd> --help` when they disagree). Binary-only install: `curl -fsSL https://plannotator.ai/install.sh | bash -s -- --minimal`. Never run `plannotator uninstall` — it would delete the `~/.agents/skills/plannotator` symlink into this repo along with the binary; check with `--dry-run` first. `herdr plugin uninstall` leaves the plugin's keybindings behind in `~/.config/herdr/config.toml` — remove those blocks by hand. No plannotator extensions are installed; last-message review for pi/devin/opencode runs through the herdr `prefix+shift+o` hook script with per-harness transcript extractors (`~/.config/herdr/scripts/plannotator-last.sh`) — adding a harness is one extractor function, not an upstream dependency. `PLANNOTATOR_BROWSER` points at a herdr side-pane wrapper., `poe-provider`, `pty-handling`, `terminal-sessions`.

`content-retrieval` also consolidates the locally authored former `document-ai`, `gh-repo-read`, `media`, `web-content`, and `youtube-transcript-extraction` skills; its LiteParse provenance is recorded above.

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

> **Ignore locally:** `disable-model-invocation: true` is intentional (pending [agentskills#105](https://github.com/agentskills/agentskills/issues/105)). `skills-ref` 0.1.0 reports it as `Unexpected fields` — ignore that error locally. CI patches `validator.py` to allow it. Do not remove the flag to make local validation pass.

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
