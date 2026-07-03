# Pi Subagents

> Sources: https://codeberg.org/drsh4dow/pi-delegate , https://www.npmjs.com/package/pi-delegate , https://www.npmjs.com/package/pi-subagents , https://github.com/mjakl/pi-subagent , https://github.com/HamdiMaz/pi-sub-agent

Pi's subagent story is **package-based**, not manifest-based like the other CLIs. You install an extension package that adds a delegation tool, and the package defines how subagents work. There is no single built-in subagent format — pick the package that matches your needs.

## The packages

| Package | Tool(s) | Approach |
|---|---|---|
| **`pi-delegate`** | `delegate` | Minimal: one tool, fresh in-memory child, returns only the final report |
| **`pi-subagents`** | `/run`, `/chain`, `/parallel` | Multi-agent: chains, parallel execution, saved workflows, built-in agent roster |
| **`pi-subagent`** (mjakl) | `subagent` | Named persistent sessions, auto-discovery, fresh or parent-snapshot context |
| **`pi-sub-agent`** (HamdiMaz) | `subagent` | Single/parallel/chain modes, bundled agent roster, project + user agent dirs |

If you just want clean delegation with no workflow engine, use **`pi-delegate`**. If you want chains, parallel fan-out, or saved workflows, use **`pi-subagents`**. The other two are alternatives with persistent sessions or bundled agents.

---

## pi-delegate (recommended default)

Minimal by design: one tool (`delegate`), one job — keep the main context clean.

### Install

```bash
pi install npm:pi-delegate
```

### Tool API: `delegate`

| Parameter | Description |
|---|---|
| `task` | The task for the child agent |
| `effort` | Optional `fast` / `balanced` / `smart` (default `balanced`; callers should choose explicitly) |

The child uses the **active parent model** by default. `effort` only selects the thinking level:

| effort | thinking |
|---|---|
| `fast` | `low` |
| `balanced` | `medium` |
| `smart` | `high` |

- `fast` → scouting, repo mapping, docs/API lookup, quick read-only recon.
- `smart` → review, critique, debugging, ambiguous design, high-risk reasoning.
- `balanced` → moderate investigation or exceptional write-capable child implementation.

### Behavior

- Fresh in-memory child session, parent cwd, project context files loaded via Pi's normal resource discovery.
- Recursive delegation tools are **disabled inside the child**.
- Parallel execution — multiple `delegate` calls in one agent turn run concurrently.
- 15-minute internal timeout.
- The main agent never sees the child's intermediate exploration — only the concise final report plus metadata (model/effort, duration, tool/error counts, usage).
- Normal Pi tools are available to the child, **including write-capable tools**. Keep implementation/final validation in the parent by default; delegate write-capable child tasks only when explicit or exceptional. Callers must avoid conflicting concurrent delegated writes.
- Parent-facing delegation policy is tool-owned (via the `delegate` tool description/snippet/guidelines); the package does not append a separate parent system prompt.

### When to use

- Scan a code area without filling the main context.
- Research a library/API and report the answer.
- Get an explicitly requested independent/fresh review.
- Investigate noisy failures and report evidence.

**Do not** use it as a workflow engine or default implementation worker. The parent owns implementation, final validation, and the final answer. For chains, background jobs, worktrees, or agent management, use a purpose-built workflow package like `pi-subagents`.

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

- **Just want clean side-thread delegation?** `pi-delegate`.
- **Need chains, parallel fan-out, or saved workflows?** `pi-subagents`.
- **Want persistent named sessions across turns?** `pi-subagent` (mjakl).
- **Want a bundled roster + project/user agent dirs?** `pi-sub-agent` (HamdiMaz).
