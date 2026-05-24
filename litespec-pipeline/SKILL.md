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

### Creating the Zellij Session

Create a background zellij session for the review panes. The user can attach to watch live.

```bash
SESSION="review-<change-name>"
zellij attach "$SESSION" --create-background 2>/dev/null
export ZELLIJ_SESSION_NAME="$SESSION"
```

### Spawning Reviewers

Each reviewer gets its own named pane. Output is redirected to files for collection after completion.

```bash
mkdir -p /tmp/litespec-pipeline-<name>/reviews

# Spawn all three in parallel — each in its own pane
ZELLIJ_SESSION_NAME="$SESSION" zellij run -n "glm-5.1" --cwd "$(pwd)" -- \
  bash -c 'pi -p --provider zai --model glm-5.1 --no-session "Review litespec change '"'"'<name>'"'"'" > /tmp/litespec-pipeline-<name>/reviews/pi-glm-5.1.md 2>/tmp/litespec-pipeline-<name>/reviews/pi-glm-5.1.log; echo "DONE"' &
PID1=$!

ZELLIJ_SESSION_NAME="$SESSION" zellij run -n "deepseek" --cwd "$(pwd)" -- \
  bash -c 'pi -p --provider deepseek --model deepseek-v4-pro --no-session "Review litespec change '"'"'<name>'"'"'" > /tmp/litespec-pipeline-<name>/reviews/pi-deepseek-v4-pro.md 2>/tmp/litespec-pipeline-<name>/reviews/pi-deepseek-v4-pro.log; echo "DONE"' &
PID2=$!

ZELLIJ_SESSION_NAME="$SESSION" zellij run -n "kimi" --cwd "$(pwd)" -- \
  bash -c 'devin -p --model kimi-k2.6 -- "Review litespec change '"'"'<name>'"'"'" > /tmp/litespec-pipeline-<name>/reviews/devin-kimi-k2.6.md 2>/tmp/litespec-pipeline-<name>/reviews/devin-kimi-k2.6.log; echo "DONE"' &
PID3=$!

echo "Spawned: GLM=$PID1 DeepSeek=$PID2 Kimi=$PID3"
echo "Watch live: zellij attach $SESSION"
```

**The quoting is tricky.** The inner `bash -c '...'` needs the change name passed through. Use the `'"'"'` pattern for single quotes inside single quotes, or use double quotes for the outer layer. Test the command before running if unsure.

**Exact command reference (inside bash -c):**

| Reviewer | Command |
|---|---|
| GLM-5.1 | `pi -p --provider zai --model glm-5.1 --no-session "Review litespec change '<name>'"` |
| DeepSeek-V4-Pro | `pi -p --provider deepseek --model deepseek-v4-pro --no-session "Review litespec change '<name>'"` |
| Kimi-K2.6 | `devin -p --model kimi-k2.6 -- "Review litespec change '<name>'"` |

**devin requires `--` before the prompt.**

**pi requires `--provider` for zai models.**

### Waiting for Completion

`wait` does not work for zellij PIDs across bash invocations. Instead, poll pane status until all show `EXITED: true`:

```bash
# Poll until all reviewer panes have exited
while true; do
  RUNNING=$(ZELLIJ_SESSION_NAME="$SESSION" zellij action list-panes --json \
    | jq '[.[] | select(.title | test("glm|deepseek|kimi"))] | map(.exited) | sort | unique')
  if echo "$RUNNING" | grep -q 'true'; then
    # At least one pane is still running
    sleep 10
  else
    echo "All reviewers finished"
    break
  fi
done
```

Use a generous bash timeout (1200s+). Reviews take 15+ minutes.

### Checking Progress

While reviews are running, the user can attach: `zellij attach <session-name>`

The orchestrator can check status:

```bash
# See which panes are still running
ZELLIJ_SESSION_NAME="$SESSION" zellij action list-panes --state --command --tab

# Read a specific reviewer's screen
ZELLIJ_SESSION_NAME="$SESSION" zellij action dump-screen --pane-id <pane-id> | sed 's/\x1b\[[0-9;]*m//g'
```

A pane with `EXITED: true` has finished. A pane with a `running_command` is still going.

### Intervening on a Stuck Reviewer

If a reviewer is stuck (asking a question, hitting a prompt), send input via zellij:

```bash
# Send text to the pane
ZELLIJ_SESSION_NAME="$SESSION" zellij action write-chars --pane-id <pane-id> "continue"
ZELLIJ_SESSION_NAME="$SESSION" zellij action send-keys --pane-id <pane-id> "Enter"
```

### Collecting Results

```bash
ls -la /tmp/litespec-pipeline-<name>/reviews/*.md
```

If a file is empty or very short (<100 bytes), check the `.log` file. Report failures to the user — **do not investigate, do not try alternative models**.

### Re-Running a Failed Reviewer

Kill the old pane and re-run in the same session:

```bash
ZELLIJ_SESSION_NAME="$SESSION" zellij run -n "<name>" --cwd "$(pwd)" -- \
  bash -c '<command>; echo "DONE"' &
```

### Continuing a Timed-Out Reviewer

Each pane IS its session. To continue a reviewer, send `-c` to its pane:

```bash
# pi — continues the session in that pane
ZELLIJ_SESSION_NAME="$SESSION" zellij action write-chars --pane-id <pane-id> "pi -p --provider zai --model glm-5.1 -c --no-session"
ZELLIJ_SESSION_NAME="$SESSION" zellij action send-keys --pane-id <pane-id> "Enter"

# devin
ZELLIJ_SESSION_NAME="$SESSION" zellij action write-chars --pane-id <pane-id> "devin -p --model kimi-k2.6 -c"
ZELLIJ_SESSION_NAME="$SESSION" zellij action send-keys --pane-id <pane-id> "Enter"
```

No session ambiguity — each pane only has one session.

### Cleaning Up

```bash
# Kill the review session when done
ZELLIJ_SESSION_NAME="$SESSION" zellij action kill-session
```

### Consolidation

Once all reviews are collected, read every `.md` file in the reviews directory. Then read `references/consolidation.md` and follow its instructions to produce a consolidated meta-review.

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
| A reviewer fails (auth/error) | Report it, let user re-run or skip |
| All reviewers fail | **Stop immediately.** Report what failed and wait for the user. |
| Reviewer gets stuck (prompt/question) | Use `write-chars` + `send-keys` to respond, or report to user |
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
