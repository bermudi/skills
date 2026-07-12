# Pi Subagents

> Sources: **`~/build/pi-delegate/`** ([github.com/bermudi/pi-delegate](https://github.com/bermudi/pi-delegate)) — the package this reference tracks. A *separate, unrelated* minimal package also named `pi-delegate` exists ([codeberg/drsh4dow](https://codeberg.org/drsh4dow/pi-delegate) · [npmjs](https://www.npmjs.com/package/pi-delegate)); this doc does not describe it. Other Pi subagent packages: [pi-subagents](https://www.npmjs.com/package/pi-subagents) · [pi-subagent (mjakl)](https://github.com/mjakl/pi-subagent) · [pi-sub-agent (HamdiMaz)](https://github.com/HamdiMaz/pi-sub-agent)

Pi's subagent story is **package-based**, not manifest-based like the other CLIs. You install an extension package that adds a delegation tool, and the package defines how subagents work. There is no single built-in subagent format — pick the package that matches your needs.

## The packages

| Package | Tool(s) | Approach |
|---|---|---|
| **`pi-delegate`** | `delegate` | Full-featured orchestrator: parallel tasks, named + built-in agents, persistent sessions, async tickets, resume, retries. One tool, report-only return |
| **`pi-subagents`** | `/run`, `/chain`, `/parallel` | Multi-agent: chains, parallel execution, saved workflows, built-in agent roster |
| **`pi-subagent`** (mjakl) | `subagent` | Named persistent sessions, auto-discovery, fresh or parent-snapshot context |
| **`pi-sub-agent`** (HamdiMaz) | `subagent` | Single/parallel/chain modes, bundled agent roster, project + user agent dirs |

The local **`pi-delegate`** (`~/build/pi-delegate/`) is the most capable and is the recommended default — it covers parallel tasks, named/built-in agents, persistent sessions, async background jobs, and resume in one tool. Use **`pi-subagents`** when you specifically want slash-command chains and saved `.chain.md`/`.chain.json` workflow *files* (which `pi-delegate` lacks). The other two are alternatives with different session models or bundled rosters.

---

## pi-delegate (recommended default)

`~/build/pi-delegate/` → [github.com/bermudi/pi-delegate](https://github.com/bermudi/pi-delegate). Extracted from `bermudi/agent-extensions` as a standalone repo and grown into a full orchestrator: parallel tasks, named agent profiles, persistent multi-turn sessions, async background tickets, session resume, per-model concurrency limits, and retries. Still one tool — `delegate` — and still report-only: the parent sees only each child's final message plus metadata (agent/model, duration, tokens, tool/error counts), never the child's intermediate exploration.

Call `delegate` with an empty `tasks` array to print the in-tool manual and the list of discovered agents.

### Install

Symlink the bundled entry into Pi's global extensions dir, then `/reload`:

```bash
ln -s "$PWD/delegate.bundle.ts" ~/.pi/agent/extensions/delegate.ts
```

(A separate, *unrelated* minimal package also named `pi-delegate` lives on npm — that's a different project. This reference tracks the local repo above.)

### Tool API: `delegate`

Top-level params:

| Param | Description |
|---|---|
| `tasks` | Array of task objects (below). Empty/omitted → print manual + agent list. |
| `async` | `true` → fire `tasks` in the background; returns a ticket id immediately. |
| `action` | `"poll"` / `"cancel"` for async tickets (top-level; no `tasks` needed). |
| `ticket` | Ticket id for `action: "poll"`/`"cancel"`. |

Per-task fields:

| Field | Default | Description |
|---|---|---|
| `prompt` | — | The task. Optional only when `resumeFrom` is set (defaults to a continuation prompt). |
| `agent` | inline | Named agent profile (see below). Inline fields override the agent's defaults. |
| `model` | parent | e.g. `anthropic/claude-sonnet-4`. Resolved by precedence (below). |
| `tools` | `*` | `*` = read/write/edit/bash (bash subsumes search); `ro` = read/grep/find/ls; or explicit names. Claude Code tool names auto-mapped; unmappable tools dropped. |
| `thinking` | agent's / `off` | `off` / `minimal` / `low` / `medium` / `high` / `xhigh`. |
| `systemPrompt` | agent's / parent's | Inline override. |
| `cwd` | parent cwd | Subagent working dir (settings + AGENTS.md resolution). Named-agent discovery is always parent-session-scoped regardless of per-task cwd. |
| `context` | `fresh` | `fresh`, or `with-parent-transcript` (injects the whole parent conversation — token-expensive, use deliberately). |
| `sessionId` | — | Name a persistent pooled agent. First use creates it; later calls reuse the same conversation. One task per session — duplicate `sessionId`s in one call are rejected. |
| `action` | `prompt` | Per-task: `prompt` / `close` (tear down a pooled session) / `list` (show active sessions). |
| `resumeFrom` | — | Absolute path to a previous session `.jsonl` to continue from. |

### Built-in agents

Seeded lowest in discovery, so any same-named user `.md` silently supersedes them:

| Agent | Tools | Thinking | Role |
|---|---|---|---|
| `scout` | `ro` | high | Map a code area — imports, call sites, key types — and hand a downstream agent a precise starting point |
| `reviewer` | `read`, `bash` | xhigh | Senior code reviewer; traces a concrete code path before flagging a finding |
| `workhorse` | `*` | xhigh | Mechanical execution — bulk edits, boilerplate, apply-this-everywhere |

### Agent discovery

First definition wins; later dirs cannot override. Built-ins are seeded last:

1. project `.pi/agents/*.md`
2. global `~/.pi/agent/agents/*.md`
3. global `~/.agents/*.md` (legacy)
4. project `.claude/agents/*.md` (Claude Code interchange)
5. global `~/.claude/agents/*.md`
6. built-ins (`scout`, `reviewer`, `workhorse`)

Agent files are Markdown with YAML-ish frontmatter:

```markdown
---
name: my-agent
description: What it does
model: anthropic/claude-haiku-4-5   # optional
thinking: low                        # off/minimal/low/medium/high/xhigh
tools: *                             # * = full agent; ro = read-only; omit to inherit *
---
You are a helpful agent...
```

### Sessions & async

- **Persistent sessions** (`sessionId`): the subagent stays alive in an in-memory pool for the duration of the Pi session. Same `sessionId` on later calls continues the conversation. Auto-closed after **10 min** idle. `action: "close"` tears one down; `action: "list"` shows active sessions.
- **Resume** (`resumeFrom`): rehydrate from a previous session `.jsonl` (absolute path). Combine with `sessionId` to resume *and* pool for further multi-turn use.
- **Async** (`async: true`): returns a ticket id immediately; the parent keeps working. `delegate({ action: "poll" })` lists tickets; `delegate({ action: "poll", ticket: "…" })` checks one; `delegate({ action: "cancel", ticket: "…" })` aborts. Results are delivered automatically on completion. Max **5** concurrent tickets; **30-min** hard timeout per ticket.

### Concurrency & config

Sync `delegate` runs at most `maxConcurrent` (default **3**) tasks at once — the rest queue, they don't fail. Tunables live in `~/.pi/agent/delegate.json`:

| Key | Default | Meaning |
|---|---|---|
| `maxConcurrent` | 3 | Sync ceiling on concurrent tasks |
| `maxAsyncTickets` | 5 | Max concurrent background tickets |
| `concurrency.default` | 3 | Per-model fallback limit |
| `concurrency.providers` | — | e.g. `{ "llamacpp": 2 }` |
| `concurrency.models` | — | keyed `provider/modelId` |
| `agent.default` | null | Global model override |
| `agent.<name>` | — | Per-agent model override |
| `retry.wholeTaskMaxRetries` | 3 | Whole-task transient-error retries after the first attempt |
| `retry.wholeTaskBaseDelayMs` | 1000 | Exponential-backoff base |

**Model precedence:** `task.model` → `agent.<name>` (config) → `agent.default` (config) → agent frontmatter `model` → parent session model.

### Behavior notes

- A child runs in an isolated context with its own system prompt, model, tools, and thinking level — fresh by default, or pooled (`sessionId`) / rehydrated (`resumeFrom`). Only the child's final message (+ metadata) returns to the parent.
- The default child toolset does **not** include `delegate`, so delegation is non-recursive by default.
- Children inherit all skills discovered in their `cwd` (per-task skill filtering is not supported — curate the cwd's skill set instead).
- `tasks` must be a real JSON array of objects, never a stringified array.

### When to use

- Parallelize independent investigation, review, or mechanical edits across many files/areas.
- Hand a fresh-context agent a focused sub-problem (scout an area, get an independent review, run a mechanical refactor).
- Run a long task in the background while the parent keeps working (`async`).
- Continue an interrupted/failed subagent from its session file (`resumeFrom`), or keep a specialist alive across turns (`sessionId`).

**Do not** use it as the default author of the final answer: the parent still synthesizes child reports and owns final validation. For slash-command chains and saved `.chain.md`/`.chain.json` workflow *files*, use `pi-subagents`.

---

## pi-subagents (chains, parallel, saved workflows)

Adds multi-agent orchestration: chains, parallel execution, saved workflows, background jobs.

### Built-in agents

| Agent | Role |
|---|---|
| `scout` | Quick read-only recon |
| `planner` | Reads and plans, does not edit |
| `reviewer` | Checks implementation against task/plan, tests, edge cases |
| `writer` | Edits files, validates, escalates unapproved decisions |
| `context-builder` | Gathers code context, writes handoff material (`context.md`, `meta-prompt.md`) |
| `oracle` | Second opinion — challenges assumptions, catches drift, no edits |
| `delegate` | Lightweight general delegate close to the parent session |

### Commands

| Command | Description |
|---|---|
| `/run [task]` | Run one agent |
| `/chain agent1 "task1" -> agent2 "task2"` | Run agents in sequence |
| `/chain scout "scan" -> (reviewer "A" \| reviewer "B") -> writer "fix"` | Chain with a static parallel group |
| `/parallel agent1 "task1" -> agent2 "task2"` | Run agents in parallel |
| `/run-chain -- <file>` | Launch a saved `.chain.md` or `.chain.json` workflow |
| `/subagents-doctor` | Setup diagnostics |
| `/subagents-models [agent]` | Show runtime model mapping |
| `/subagents-profiles` | List saved profiles from `~/.pi/agent/profiles/pi-subagents/` |

---

## pi-subagent (mjakl) — persistent named sessions

Each subagent runs in its own isolated `pi` process. Supports named persistent sessions so a specialist can continue across multiple turns.

Key fields:

| Field | Default | Description |
|---|---|---|
| `agent` | — | Required. Exact name of an available subagent. |
| `cwd` | Parent cwd | Working directory for this subagent process |
| `initialContext` | `"empty"` | `"empty"` = fresh child; `"parent"` = seed from parent session snapshot |
| `session` | — | Logical handle for a persistent child session |

If you have no agents yet, it creates a starter `explore` agent automatically. Customize agents only when you want different specialists.

---

## pi-sub-agent (HamdiMaz) — single/parallel/chain with bundled roster

Runs each delegated task in a separate `pi --mode json -p --no-session` subprocess. Bundles `scout`, `planner`, `worker`, `reviewer`, `debugger`, `verifier`, `security-auditor`, `docs-writer`, and `refactorer`.

Discovers user agents from `~/.pi/agent/agents/*.md` and project agents from `.pi/agents/*.md`. Provides `/sub-agent-settings` to view/edit each agent's model and thinking effort.

Tool modes (exactly one):

| Field | Applies to | Description |
|---|---|---|
| `agent` + `task` | Single | Agent name + task text |
| `tasks` | Parallel | Array of `{ agent, task, cwd? }` |
| `chain` | Chain | Array of `{ agent, task, cwd? }` steps (max 8); `{previous}` replaced with prior step's output |
| `agentScope` | All | `"user"` (default), `"project"`, or `"both"` |
| `confirmProjectAgents` | All | Default `true`; asks before running project-local agents |

---

## Choosing

- **Want one tool that does parallel tasks, named + built-in agents, persistent sessions, async tickets, and resume?** `pi-delegate` — the recommended default; it now covers most of the ground the other three were built for.
- **Need slash-command chains (`/chain`, `/parallel`) and saved `.chain.md`/`.chain.json` workflow *files*?** `pi-subagents` — the only one with first-class saved workflows.
- **Want a different persistent-session model or an auto-created starter agent?** `pi-subagent` (mjakl) — though `pi-delegate` also does pooled `sessionId` sessions now.
- **Want a different bundled roster plus a per-agent settings UI?** `pi-sub-agent` (HamdiMaz) — though `pi-delegate` ships `scout`/`reviewer`/`workhorse` built-ins and reads both `.pi/agents` and `.claude/agents`.
