---
name: review-panel
description: >
  Fan out a litespec change review to multiple AI coding agents (pi, devin, agent)
  with different models, collect their reports, and consolidate into a single
  meta-review. Triggers on: "review panel", "multi-review", "ensemble review",
  "fan out review", "run multiple reviewers", "consolidate reviews".
---

# Review Panel

Run N reviewers in parallel with different models, collect their structured review reports, and consolidate into one meta-review that captures the best insights from each.

## Prerequisites

- A litespec-initialized project (has `specs/` and `.agents/skills/`)
- At least one active change with artifacts
- The CLIs you want to use installed and authenticated (`pi`, `devin`, `agent`)

---

## Workflow

### 1. Detect Change

If the user provides a change name, use it. Otherwise auto-detect:

```bash
litespec list --changes --json
```

If there's only one active change, use it. If there are multiple, ask the user.

### 2. Configure Reviewers

Read `assets/default-panel.yaml` (resolved relative to this SKILL.md's directory) for the default reviewer lineup. Each entry has `tool` (pi | devin | agent), `model`, and optional `label`.

The user can override by:

- Creating `.review-panel.yaml` in the project root (takes precedence)
- Specifying in the prompt: "use pi with sonnet and devin with kimi"
- Asking to skip or add specific reviewers

When the user specifies overrides, use their lineup instead. When mixing, confirm the final lineup before proceeding.

### 3. Fan Out

Run `scripts/fan-out.sh` (resolved relative to this SKILL.md's directory) from the project root:

```bash
bash SKILL_DIR/scripts/fan-out.sh \
  --change <change-name> \
  --output /tmp/review-panel-<change-name> \
  --reviewer <tool>:<model> \
  --reviewer <tool>:<model> \
  ...
```

Replace `SKILL_DIR` with the directory containing this SKILL.md.

The script runs all reviewers in parallel. **Use a generous timeout** (600s+) on the bash call — each reviewer reads the entire change, loads skills, and produces a structured report.

If the script reports failures, note which reviewers failed but proceed with the available reviews. Don't abort the whole panel for one failure.

### 4. Read Outputs

Read every `.md` file in the output directory. Each file is a complete review report from one reviewer. The filename format is `<tool>-<model>.md`.

If a file is empty or very short (<100 bytes), treat it as a failed review. Note it in the consolidation.

### 5. Consolidate

Read `references/consolidation.md` and follow its instructions to merge the individual reviews into a single meta-review.

Produce the consolidated report in the output directory as `consolidated.md`.

### 6. Present & Act

Present the consolidated report to the user. Then offer:

- **Fix**: Feed the consolidated findings to a fix agent:
  ```bash
  pi -p --no-session "litespec-fix: Resolve the following consolidated review findings for change '<name>': <findings>"
  ```
  Or use `devin -p` or `agent -p` per user preference.
- **Re-review**: Run specific reviewers again if their output was unclear
- **Archive**: If the review is clean, suggest `litespec archive <name>`

---

## Consolidation-Only Mode

If the user already has review reports and just wants consolidation:

1. Ask for the file paths or directory containing the reports
2. Read all reports
3. Follow `references/consolidation.md`
4. Present the consolidated meta-review

Skip the fan-out step entirely.

---

## Fix Mode

If the user says "fix the findings" or "run the fix agent":

1. Confirm which findings to address (all, or specific ones)
2. Run the fix command with the user's preferred CLI
3. The fix agent follows the litespec-fix skill instructions — you don't need to supervise
4. After the fix completes, offer to re-run the review panel to verify

---

## Notes

- Each spawned CLI process runs in the project directory, so it auto-discovers the litespec skills from `.agents/skills/`
- The prompt sent to each reviewer is `"Review litespec change '<name>'"` — this triggers the `litespec-review` skill which handles mode detection (artifact / implementation / pre-archive) automatically
- Reviewers are independent — one failing doesn't affect the others
- The consolidation step is where the real value is: cross-referencing different models' perspectives catches blind spots that any single model would miss
