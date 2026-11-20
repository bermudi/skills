# Skills Repository

A monorepo of [Agent Skills](https://agentskills.io). This repo is the source of
truth; installs are plain symlinks into it. Full conventions (authoring format,
deploy, adopt-vs-install, provenance) live in [AGENTS.md](AGENTS.md).

## Structure

```
skills/
├── skill-name/
│   ├── SKILL.md    # Required: frontmatter + instructions
│   ├── scripts/    # Optional: executable tooling the agent runs
│   ├── references/ # Optional: deep-dive docs (progressive disclosure)
│   ├── assets/     # Optional: templates, resources
│   └── research/   # Optional: gitignored one-off research artifacts
└── scripts/        # Repo tooling (symlink repair, upstream checks)
```

Flat `main` history — one branch, no per-skill branches.

## Adding a Skill

1. Create `skill-name/SKILL.md` with the required frontmatter.
2. Validate: `skills-ref validate ./skill-name`
3. Commit to `main`. Adapted from upstream? Add a row to the Provenance
   table in AGENTS.md.
4. Install deliberately (adopting does NOT install — every install adds
   always-on description cost):
   ```bash
   ln -s "$PWD/skill-name" ~/.agents/skills/skill-name
   ln -sfn "$(readlink -f ~/.agents/skills/skill-name)" ~/.claude/skills/skill-name
   ```

## Validation

CI runs [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref)
validation on every push.

```bash
skills-ref validate ./skill-name
```
