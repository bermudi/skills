---
name: sub-tasks
description: >
  Delegate work to subagents and zellij panes — spawn parallel tasks, run code reviews,
  investigate codebases, launch long-running processes, drive external coding agents.
  Triggers on: "delegate", "subagent", "spawn", "in parallel", "review this", "scout",
  "investigate", "run in background", "zellij", "launch agent", "long-running",
  "code review", "multi-agent", "do these at the same time", "while that runs".
---

# Sub-Tasks: Multiplying Yourself

One agent, many hands. Use `delegate` for in-session parallelism (fast, structured, same process). Use zellij for long-running commands, interactive TUIs, and external coding agents (persistent, visible, cross-process).

Read `references/zellij-quickref.md` when orchestrating terminal panes, launching external agents, or running long-lived processes.

---

## Decision Tree

```
What are you doing?
│
├─ Single quick thing I can do myself → just do it
│
├─ Multiple independent things at once → delegate with multiple tasks
│
├─ Need specialist eyes (review, investigation, research)
│  └─ delegate with the right agent
│
├─ Long-running, needs monitoring, or interactive TUI
│  └─ zellij pane
│
├─ External coding agent (pi, claude, opencode in a terminal)
│  └─ zellij pane + drive it with write-chars/send-keys
│
└─ Multi-turn conversation with a subagent
   └─ delegate with sessionId
```

---

## The `delegate` Tool

Spawn subagents that run in parallel. Each gets independent context, model, tools, and system prompt. Results return to you.

### Available Agents

Agents live in `.pi/agents/*.md`. Project-local agents override global ones. Current roster:

| Agent | Model | Specialty | Tools |
|---|---|---|---|
| **reviewer** | deepseek-v4-pro | Code review: bugs, security, edge cases. Read-only. | read, bash |
| **scout** | deepseek-v4-flash | Codebase investigation: map architecture, trace imports. | read, bash |
| **workhorse** | deepseek-v4-pro | Mechanical execution: bulk edits, boilerplate, refactors. | all |

### Task Fields

| Field | What | Default |
|---|---|---|
| `prompt` | The task description. Required unless `resumeFrom` is set. | — |
| `agent` | Named agent from `.pi/agents/`. Overrides: `model`, `tools`, `thinking`, `systemPrompt` all work inline. | parent model |
| `systemPrompt` | Full system prompt. Required if no `agent`. | — |
| `model` | e.g. `anthropic/claude-sonnet-4`. | agent default → parent |
| `tools` | Array: `read`, `write`, `edit`, `bash`. | all four |
| `thinking` | `off`, `minimal`, `low`, `medium`, `high`, `xhigh`. | agent default → off |
| `skills` | Array of skill names to inject into the subagent's system prompt. | — |
| `cwd` | Working directory. Accepts absolute, relative, and `~` paths. | parent session cwd |
| `context` | `fresh` (clean) or `with-parent-transcript` (inject full conversation — expensive, use deliberately). | `fresh` |
| `sessionId` | Named persistent session. First call creates, subsequent reuse. | — |
| `resumeFrom` | Absolute path to a previous session `.jsonl`. Agent resumes with full history. | — |
| `action` | `prompt` (default), `close` (tear down session), `list` (show active). | `prompt` |

### Session Reuse (Multi-Turn)

Keep a subagent alive across multiple interactions:

```json
// Create and run
{ "prompt": "Investigate the auth module", "agent": "scout", "sessionId": "auth-research" }

// Continue the same agent
{ "prompt": "Now check the tests for that module", "sessionId": "auth-research" }

// Clean up
{ "sessionId": "auth-research", "action": "close" }
```

Pooled agents auto-close after 10 minutes of inactivity.

### Handling Partial Failures

When multiple tasks run in parallel, some may succeed and others fail. The delegate tool returns results for each task — errors include a `resumeFrom` path pointing to the failed session:

```json
// Result from a 3-task delegate where task 2 failed:
// Task 1: ✓ success
// Task 2: ✗ error — resumeFrom: /path/to/session.jsonl
// Task 3: ✓ success
```

Recovery pattern: read the successful results, then `resumeFrom` the failed one with a corrective prompt. You can also combine `resumeFrom` with `sessionId` to pool the recovered agent for further turns.

### Resuming Failed Sessions

Continue from where a failed/interrupted subagent left off:

```json
{
  "prompt": "Continue — the server is running on :3000",
  "resumeFrom": "/home/user/.pi/agent/sessions/project/2026-01-01T12-00-00Z_abc123.jsonl"
}
```

Combine with `sessionId` to resume AND pool for further turns.

### Async Mode

Fire tasks in the background, keep working:

```json
delegate({ "async": true, "tasks": [{ "agent": "scout", "prompt": "Map the auth module" }] })
```

Returns a ticket ID immediately. Poll with:
- `delegate({ "action": "poll" })` — list all tickets
- `delegate({ "action": "poll", "ticket": "abc123" })` — check one
- `delegate({ "action": "cancel", "ticket": "abc123" })` — abort

Max 5 concurrent async tickets. Completed tickets auto-deliver results.

### `with-parent-transcript`

Injects your full conversation into the subagent. Token-expensive — only use when the subagent genuinely needs your entire context (e.g., it needs to understand a long debugging session). For everything else, summarize what it needs in the `prompt`.

---

## Delegation Recipes

### Code Review

```json
{
  "tasks": [{
    "prompt": "Review src/handler.go:42-120 for race conditions and error handling gaps",
    "agent": "reviewer"
  }]
}
```

**DO:**
- Point at exact files, line ranges, or a git diff
- State what to look for (bugs, security, edge cases, spec compliance)
- Include the spec or expected behavior if reviewing for correctness

**DON'T:**
- Ask the reviewer to "also suggest fixes" — this triggers overcorrection bias (models reject correct code up to 3× more when asked to propose fixes)
- Ask "is there anything else wrong?" — open-ended fishing generates noise
- Vague directives like "be thorough" — increase false negatives without improving true positives
- Request review AND implementation in the same task — the reviewer's job is to find bugs, not fix them

The reviewer agent has structured reasoning, anti-pattern guards, and evidence requirements built in. Don't override its system prompt.

### Codebase Investigation

```json
{
  "tasks": [{
    "prompt": "Find all files related to authentication, trace how they connect, identify the middleware chain",
    "agent": "scout"
  }]
}
```

Specify thoroughness in the prompt:
- **Quick**: Targeted lookups, key files only
- **Medium**: Follow imports, read critical sections (default)
- **Thorough**: Trace all dependencies, check tests and types

The scout returns structured findings (file list with line ranges, key code snippets, architecture map) that you can use without re-reading everything yourself.

### Parallel Swarm

Multiple independent tasks at once — the full Kage Bunshin:

```json
{
  "tasks": [
    { "prompt": "Review the API handlers for security issues", "agent": "reviewer" },
    { "prompt": "Map the database schema and trace all migrations", "agent": "scout" },
    { "prompt": "Research best practices for rate limiting in Go web services", "skills": ["web-content"] }
  ]
}
```

All three run simultaneously. You get three structured results back.

### Bulk Mechanical Work

```json
{
  "tasks": [{
    "prompt": "Rename getUserById to fetchUser in all files under src/. Update imports, exports, and test references.",
    "agent": "workhorse"
  }]
}
```

For well-defined, repetitive tasks. The workhorse is thorough but not a decision-maker — give it precise instructions.

### Context Inheritance

When a subagent needs to see your conversation:

```json
{
  "tasks": [{
    "prompt": "Apply the same pattern we just discussed to the remaining CRUD endpoints",
    "context": "with-parent-transcript",
    "agent": "workhorse"
  }]
}
```

Expensive but sometimes necessary. Prefer summarizing what it needs in the prompt instead.

---

## When to Use Zellij Instead

| Use case | Use |
|---|---|
| Multiple independent reads/edits/analyses | `delegate` |
| Code review or investigation | `delegate` with agent |
| Long-running build, server, test suite | zellij pane |
| Driving an interactive coding agent (pi, claude, etc.) | zellij pane |
| Process that needs monitoring or human takeover | zellij pane |
| One-shot agent command with file output | zellij `run -- bash -c 'agent -p "..." > /tmp/out.txt'` |

Read `references/zellij-quickref.md` for the full zellij command reference (session management, pane operations, driving coding agents, monitoring scripts).

### Quick Zellij Pattern

```bash
# Create headless session
SESSION="task-$(date +%s)"
zellij attach "$SESSION" --create-background 2>/dev/null
zellij list-sessions | grep -qx "$SESSION" || { echo "Session creation failed"; exit 1; }
export ZELLIJ_SESSION_NAME="$SESSION"

# Launch a process
PANE=$(zellij run -n "build" -- make test)

# Check on it later
zellij action dump-screen -p "$PANE" | sed 's/\x1b\[[0-9;]*m//g'

# Launch a coding agent and send it a prompt
PANE=$(zellij run -n "pi" -- pi --extension roundtable)
# Wait for prompt, then:
zellij action write-chars -p "$PANE" "implement the auth middleware"
zellij action send-keys -p "$PANE" "Enter"
```

---

## When NOT to Delegate

- You can answer by reading one or two files directly — don't spawn a scout to do what a single `read` handles.
- The question is trivial (typos, formatting) — inline review is faster than the overhead of a subagent.
- The user wants an explanation, not a critique — just explain it.
- The user wants fixes, not findings — delegate to a workhorse, not a reviewer.
- Tasks are tightly sequential (step B depends on step A's output) — delegate the whole thing to one agent or do it yourself.

## Gotchas

**Delegate:**
- Subagents only have the core tools (read, write, edit, bash). They don't inherit your MCP tools or skills unless you specify `skills` in the task.
- `delegate` is synchronous by default — all tasks must complete before you get results. Use `async: true` to fire-and-forget.
- `with-parent-transcript` injects your *entire* conversation. A 50k-token session means the subagent starts 50k tokens deep. Use sparingly.

**Zellij:** see full gotchas in `references/zellij-quickref.md`.
