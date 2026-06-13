# delegate — AI Subagents

Spawn subagents that run in parallel. Each gets independent context, model, tools, and system prompt. Results return to you.

> Loaded on demand from the `sub-tasks` skill. Read this before your first `delegate` call.

## Available Agents

Discover the agents available in *this* environment by calling `delegate({})` with no tasks — it prints a manual listing every agent with its model, tools, and description. **List first, then reference by name.**

Agents live in `.pi/agents/*.md` (project-local) and `~/.pi/agent/agents/` (global); project-local overrides global by name. A typical roster includes a read-only reviewer, a scout for codebase investigation, and a workhorse for mechanical bulk edits — but the exact names, models, and tool sets are per-install. Don't assume a named agent exists; the recipe examples below use illustrative names.

## Task Fields

| Field | What | Default |
|---|---|---|
| `prompt` | The task description. Required unless `resumeFrom` is set. | — |
| `agent` | Named agent from `.pi/agents/`. Overrides: `model`, `tools`, `thinking`, `systemPrompt` all work inline. | parent model |
| `systemPrompt` | Full system prompt. Required if no `agent`. | — |
| `model` | e.g. `anthropic/claude-sonnet-4`. | agent default → parent |
| `tools` | Array of tool names. **Only** `read`, `write`, `edit`, `bash` exist for subagents — MCP/extension tools are not available. | all four |
| `thinking` | `off`, `minimal`, `low`, `medium`, `high`, `xhigh`. | agent default → off |
| `skills` | Array of skill names to inject into the subagent's system prompt. | — |
| `cwd` | Working directory. Accepts absolute, relative, and `~` paths. | parent session cwd |
| `context` | `fresh` (clean) or `with-parent-transcript` (inject full conversation — expensive). | `fresh` |
| `sessionId` | Named persistent session. First call creates, subsequent reuse. | — |
| `resumeFrom` | Absolute path to a previous session `.jsonl`. Agent resumes with full history. | — |
| `action` | Per-task: `prompt` (default), `close` (tear down a pooled session), `list` (show active sessions). | `prompt` |

**Top-level delegate parameters** sit on the call itself, not inside `tasks[]`:

- `tasks` — the array of task objects above.
- `async` (boolean) — fire tasks in the background; returns a ticket ID immediately (see [Async Mode](#async-mode)).
- `action` + `ticket` — async ticket control, no `tasks` needed: `poll` (list all tickets, or check one via `ticket`), `cancel` (abort a running ticket).

Per-task `action` (`prompt` / `close` / `list`) and top-level `action` (`poll` / `cancel`) are different namespaces — don't mix them.

## Session Reuse (Multi-Turn)

Keep a subagent alive across multiple interactions:

```json
// Create and run
{ "tasks": [{ "prompt": "Investigate the auth module", "agent": "scout", "sessionId": "auth-research" }] }

// Continue the same agent
{ "tasks": [{ "prompt": "Now check the tests for that module", "sessionId": "auth-research" }] }

// Clean up
{ "tasks": [{ "sessionId": "auth-research", "action": "close" }] }
```

Pooled agents auto-close after 10 minutes of inactivity. Async tickets have a 30-minute hard timeout.

## Async Mode

Fire tasks in the background, keep working:

```json
delegate({ "async": true, "tasks": [{ "agent": "scout", "prompt": "Map the auth module" }] })
```

Returns a ticket ID immediately. Poll with:
- `delegate({ "action": "poll" })` — list all tickets
- `delegate({ "action": "poll", "ticket": "abc123" })` — check one
- `delegate({ "action": "cancel", "ticket": "abc123" })` — abort

Max 5 concurrent async tickets (default; configurable via `~/.pi/agent/delegate.json` → `maxAsyncTickets`). Completed tickets auto-deliver results.

## Handling Failures

When tasks fail, results include a `resumeFrom` path pointing to the failed session. Recover by resuming with a corrective prompt:

```json
{
  "tasks": [{
    "prompt": "Continue — the server is running on :3000, retry the failed request",
    "resumeFrom": "/home/user/.pi/agent/sessions/project/2026-01-01T12-00-00Z_abc123.jsonl"
  }]
}
```

Combine `resumeFrom` with `sessionId` to resume AND pool for further turns.

## `with-parent-transcript`

Injects your full conversation into the subagent. Token-expensive — only use when the subagent genuinely needs your entire context. For everything else, summarize what it needs in the `prompt`.

## Recipes

Examples use illustrative agent names (`reviewer`, `scout`, `workhorse`). Run `delegate({})` to see what's available in your env and substitute — or omit `agent` to inherit the parent model.

### Code Review

```json
{
  "tasks": [{
    "prompt": "Review src/handler.go:42-120 for race conditions and error handling gaps",
    "agent": "reviewer"
  }]
}
```

**DO:** Point at exact files/line ranges/diffs. State what to look for.
**DON'T:** Ask "also suggest fixes" (triggers overcorrection bias). Open-ended fishing. Vague "be thorough".

### Codebase Investigation

```json
{
  "tasks": [{
    "prompt": "Find all files related to authentication, trace how they connect, identify the middleware chain",
    "agent": "scout"
  }]
}
```

State the thoroughness you want in the prompt — e.g. key files only, follow imports (a sensible default), or trace all deps + tests + types.

### Parallel Swarm

```json
{
  "tasks": [
    { "prompt": "Review the API handlers for security issues", "agent": "reviewer" },
    { "prompt": "Map the database schema and trace all migrations", "agent": "scout" },
    { "prompt": "Research best practices for rate limiting in Go web services", "skills": ["web-content"] }
  ]
}
```

### Bulk Mechanical Work

```json
{
  "tasks": [{
    "prompt": "Rename getUserById to fetchUser in all files under src/. Update imports, exports, and test references.",
    "agent": "workhorse"
  }]
}
```

## When NOT to Delegate

- You can answer by reading one or two files directly.
- The question is trivial (typos, formatting).
- The user wants an explanation, not a critique.
- Tasks are tightly sequential (step B depends on step A's output).

## Gotchas

- Subagents are sandboxed to the four core tools (read, write, edit, bash). The `tools` field only accepts those names; MCP and extension tools are **never** available to subagents. Passing `skills` injects a skill's `SKILL.md` *instructions* into the system prompt (text) — it does not unlock extra tools.
- `delegate` is synchronous by default. Sync calls run at most **3 tasks at once** (the rest queue, not fail) — default ceiling, configurable via `~/.pi/agent/delegate.json` → `maxConcurrent`. `async: true` moves execution to the background so you keep working: up to 5 tickets run independently, each internally capped the same way.
- `with-parent-transcript` injects your *entire* conversation. A 50k-token session means the subagent starts 50k tokens deep.
