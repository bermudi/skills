---
name: litespec-pipeline
description: >
  Automate the full litespec change pipeline: apply all implementation phases,
  fan out multi-model review, consolidate findings, fix issues, and archive.
  Triggers on: "pipeline", "ship this change", "run the pipeline",
  "apply and review", "full pipeline on", "apply all phases",
  "ensemble review", "fan out review", "review panel", "consolidate reviews".
---

# Litespec Pipeline

Orchestrate the full litespec change lifecycle across multiple AI coding agents:
**apply phases → multi-model review → consolidate → fix → archive.**

## Configuration

Read `assets/default-panel.yaml` for the default reviewer lineup.

**Only the review step fans out to multiple models.** Apply and fix both use `agent --model auto`.

**Do not change models unless the user explicitly asks.** The default lineup is fixed — no swapping, no "similar model" substitutions. Override by creating `.litespec-pipeline.yaml` in the project root.

---

## Step 1: Detect Change

```bash
litespec list --changes --json
```

One active change → use it. Multiple → ask the user.

---

## Step 2: Apply Phases

```bash
bash SKILL_DIR/scripts/apply-phases.sh \
  --change <name> --tool agent:auto \
  --output /tmp/litespec-pipeline-<name>/apply
```

Stops when all tasks checked, stalled, or max iterations (15). If stalled, present the blocker to the user — don't try to unstick it.

---

## Step 3: Review Panel

```bash
bash SKILL_DIR/scripts/review-panel.sh --change <name>
```

Replace `SKILL_DIR` with the directory containing this SKILL.md.

This script:
1. Creates a zellij session named `review-<change>`
2. Spawns each reviewer in its own named pane (reads config for lineup)
3. Polls until all panes finish
4. Prints a status report: ✓ for each reviewer that produced output, ✗ for failures

**To watch live:** `zellij attach review-<change>` in another terminal.

**To run with a custom config:** `bash scripts/review-panel.sh --change <name> --config .litespec-pipeline.yaml`

**To keep the session alive after completion:** add `--no-cleanup`.

### Per-Reviewer Session Directories

Each pi reviewer gets `--session-dir <outdir>/sessions/<name>`. This makes `-c` continuation unambiguous — it only finds that reviewer's session.

### Re-Running a Failed Reviewer

```bash
ZELLIJ_SESSION_NAME="review-<change>" zellij run -n "<name>" --cwd "$(pwd)" -- \
  bash -c "<command>; echo DONE"
```

### Continuing a Timed-Out Reviewer

```bash
# Continue glm — only finds glm's session in its dedicated dir
pi -p --provider zai --model glm-5.1 --session-dir /tmp/litespec-pipeline-<name>/sessions/GLM-5.1 -c

# Continue deepseek
pi -p --provider opencode-go --model deepseek-v4-pro --session-dir /tmp/litespec-pipeline-<name>/sessions/DeepSeek-V4-Pro -c

# Continue devin
devin -p --model kimi-k2.6 -c
```

### Consolidation

Once all reviews are collected:

```bash
ls -la /tmp/litespec-pipeline-<name>/reviews/
```

Read every `.md` file, then read `references/consolidation.md` and produce `consolidated.md`.

---

## Step 4: Fix

```bash
agent -p --model auto --trust "litespec-fix: Resolve the following consolidated review findings for change '<name>': $(cat /tmp/litespec-pipeline-<name>/reviews/consolidated.md)"
```

---

## Step 5: Archive

```bash
litespec archive <name>
```

Present the archive output. Suggest committing.

---

## Pipeline Shorthand

"pipeline <name>" or "ship <name>" → apply → review → **STOP for approval** → fix → re-review if requested → archive.

**Never archive without explicit user approval.**

---

## Handling Failures

| Failure | Action |
|---|---|
| Apply stalls | Read last output, present blocker |
| A reviewer fails | Report it, let user re-run or skip |
| All reviewers fail | Stop immediately, report |
| Fix fails | Report, don't loop |
| User interrupts | Summarize progress |
