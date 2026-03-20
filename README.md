# Skills Repository

A collection of [Agent Skills](https://agentskills.io) for extending AI agent capabilities.

## Strategy

Each skill lives on its own branch. This keeps skills isolated and makes it easy to:

- Review skills independently via PRs
- Test skills in isolation before merging
- Maintain version history per skill
- Delete or archive skills without affecting others

## Structure

```
skills/
├── main/           # Aggregation of all published skills
├── skill-name/     # Branch: contains skill directory
│   └── SKILL.md    # Required: metadata + instructions
│   ├── scripts/    # Optional: executable code
│   ├── references/ # Optional: documentation
│   └── assets/     # Optional: templates, resources
```

## Adding a Skill

1. Create a new branch from `main`: `git checkout -b skill-name`
2. Create the skill directory: `mkdir skill-name`
3. Write `skill-name/SKILL.md` with required frontmatter
4. Add any supporting files in `scripts/`, `references/`, `assets/`
5. Open a PR to merge into `main`

## Current Skills

See [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) for validation tool:

```bash
skills-ref validate ./skill-name
```
