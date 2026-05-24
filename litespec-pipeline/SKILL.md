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

Each step can run independently or as part of the full pipeline. The user controls which steps to run.

## Prerequisites

- A litespec-initialized project (has `specs/` and `.agents/skills/`)
- At least one active change with artifacts
- The CLIs you want to use installed and authenticated (`pi`, `devin`, `agent`)
- Resolve all script/reference/asset paths against this SKILL.md's directory

---

## Configuration

Read `assets/default-panel.yaml` for the default configuration.

**Only the review step fans out to multiple models.** Apply and fix both use `agent --model auto` — a single model, no fan-out.

**Do not change models unless the user explicitly asks.** The default lineup is fixed — no swapping, no "similar model" substitutions, no guessing. If the user doesn't specify models, use the defaults.

Override by creating `.litespec-pipeline.yaml` in the project root (takes precedence), or by specifying in the prompt. Only then may you use different models.

---

## Step 1: Detect Change

If the user provides a change name, use it. Otherwise auto-detect:

```bash
litespec list --changes --json
```

One active change → use it. Multiple → ask the user. None → tell them to create one first.

---

## Step 2: Apply Phases

**When to run:** User says "apply", "implement", "pipeline", "ship". Or tasks.md has unchecked boxes.

Run `scripts/apply-phases.sh` from the project root:

```bash
bash SKILL_DIR/scripts/apply-phases.sh \
  --change <name> \
  --tool <tool:model> \
  --output /tmp/litespec-pipeline-<name>/apply
```

Examples: `--tool agent:auto`, `--tool pi:sonnet-4`.

The script loops: checks for unchecked tasks, runs the apply tool, repeats. It stops when:
- All tasks are checked ✅
- Progress stalls (unchecked count doesn't decrease) — agent hit a pause condition
- Max iterations reached (default: 15)

**If the script reports a stall**, read the last output file to understand what blocked the agent. Present the blocker to the user — don't try to unstick it yourself. Common reasons: unclear task, design issue discovered, artifact changes needed.

**If the user wants to apply manually** (review each phase themselves), skip this step.

---

## Step 3: Review Panel

**When to run:** User says "review", "review panel", "fan out". Or apply completed and user wants pre-archive review.

Run `scripts/fan-out.sh` from the project root:

```bash
bash SKILL_DIR/scripts/fan-out.sh \
  --change <name> \
  --output /tmp/litespec-pipeline-<name>/reviews \
  --reviewer pi:glm-5.1:zai \
  --reviewer pi:deepseek-v4-pro:deepseek \
  --reviewer devin:kimi-k2.6
```

The reviewer spec format is `tool:model[:provider]`. The `:provider` suffix is for `pi` when model name resolution is ambiguous. Read `assets/default-panel.yaml` for the correct specs.

**Before fanning out**, verify each tool works by running a trivial test command. If a tool fails auth or isn't installed, report it immediately and **do not attempt workarounds** — tell the user which tools failed and wait for them to fix it.

If some reviewers fail at runtime, note which ones but proceed with available reviews.

If all reviewers fail, **stop immediately**. Do not investigate, do not try alternative models, do not explore. Report what failed and wait for the user.

### Consolidation

Read every `.md` file in the reviews output directory. Then read `references/consolidation.md` and follow its instructions to produce a consolidated meta-review.

Write the consolidated report as `consolidated.md` in the reviews directory.

Present the consolidated report to the user.

### Consolidation-Only Mode

If the user already has review reports and just wants consolidation:
1. Ask for the file paths or directory
2. Read all reports
3. Follow `references/consolidation.md`
4. Present the meta-review

---

## Step 4: Fix

**When to run:** User says "fix", "fix the findings", "address the review". After consolidation when findings exist.

Feed the consolidated findings to the fix agent:

```bash
agent -p --model auto --trust "litespec-fix: Resolve the following consolidated review findings for change '<name>': $(cat /tmp/litespec-pipeline-<name>/reviews/consolidated.md)"
```

The fix agent auto-discovers the `litespec-fix` skill from the project's `.agents/skills/`.

**After the fix completes**, offer to re-run the review panel (or a single reviewer) to verify. Don't auto-re-review — the user decides.

---

## Step 5: Archive

**When to run:** User says "archive", "ship it", and the review is clean (or user accepts remaining findings).

```bash
litespec archive <name>
```

Present the archive output. Suggest committing.

---

## Pipeline Shorthand

When the user says "pipeline <name>" or "ship <name>" without specifying steps, run the full sequence:

1. **Apply** all phases (Step 2)
2. **Review panel** (Step 3)
3. **Present** consolidated findings — **STOP HERE** and wait for user approval
4. **Fix** if user approves (Step 4)
5. **Re-review** with a single reviewer if user wants verification
6. **Archive** when user is satisfied (Step 5)

**Never archive without explicit user approval.** The pipeline pauses after consolidation for human judgment.

---

## Handling Failures

| Failure | Action |
|---|---|
| Apply stalls | Read last output, present blocker to user |
| A reviewer fails | Note it, proceed with available reviews |
| All reviewers fail | **Stop immediately.** Do not investigate, do not try alternative models, do not explore. Report what failed and wait for the user. |
| Fix fails to compile | Report the failure, don't loop — let user decide |
| User interrupts | Summarize progress so far, note what remains |

---

## Output Convention

All pipeline outputs go under `/tmp/litespec-pipeline-<change-name>/`:

```
/tmp/litespec-pipeline-<name>/
├── apply/
│   ├── phase-1.md          # Agent output from phase 1 apply
│   ├── phase-2.md          # Agent output from phase 2 apply
│   └── ...
└── reviews/
    ├── pi-glm-5.1.md       # Individual review report
    ├── pi-deepseek-v4-pro.md
    ├── devin-kimi-k2.6.md
    └── consolidated.md     # Meta-review
```

If the user re-runs, clean the relevant subdirectory first or use a fresh one.
