# AGENTS.md

## What This Is

A meta-skill — it generates instruction files (AGENTS.md, CLAUDE.md, .cursorrules, etc.) for other projects. The skill itself is a single `SKILL.md` with no scripts, no references, no evals.

## Skill Design

The skill's core principle is **goals over mechanism**: tell agents what matters and why, not how things are wired. Implementation details rot; project intent endures.

The output is always under 200 lines. Every line is a tax on every agent interaction — ruthlessness is a feature.

## Validation

```bash
skills-ref validate ./create-project-agentsmd
```

## Changing This Skill

- The entire skill lives in `SKILL.md`. That's the only file to edit.
- After editing: `git add && git commit`, then `skills update -g`.
- The structure section (the markdown skeleton) is the skill's most valuable part — changes there ripple into every file the skill generates. Be deliberate.
- Anti-patterns are as important as the template — don't trim them to save lines, they prevent the most common mistake (over-specific instruction files that rot in a week).

## Quality Bar

- If the generated skeleton has a section that applies to fewer than 20% of projects, cut it.
- If an anti-pattern duplicates what linters/formatters already enforce, cut it.
- Tool-specific adaptation table should cover the 5 most popular agents, no more.
