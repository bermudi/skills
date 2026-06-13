---
name: sub-tasks
description: >
  Delegate work to subagents or drive terminal sessions for concurrent/durable
  execution. Use when spawning parallel AI tasks, running several subagents
  at once, or driving interactive programs and waiting for their output.
---

# Sub-Tasks: Multiplying Yourself

Two mechanisms, one routing rule: **if it needs *thinking*, use `delegate`. If it needs a *terminal*, use `boo`.**

| Mechanism | What it does | Use for |
|---|---|---|
| **`delegate` tool** | Spawn AI subagents with their own context, model, and tools | Code review, investigation, parallel coding tasks, research |
| **`boo` CLI** | Drive terminal sessions — send input, read output, wait for conditions | Builds, REPLs, TUIs, servers, interactive CLI programs |

## Decision Tree

```
What are you doing?
│
├─ Single quick thing I can do myself → just do it
│
├─ Multiple independent AI tasks at once → delegate
│
├─ Need specialist eyes (review, investigation) → delegate with the right agent
│
├─ Multi-turn conversation with a subagent → delegate with sessionId
│
├─ Run a build/test/server and read output → boo
│
├─ Drive an interactive program (REPL, TUI, prompts) → boo
│
└─ Multiple terminal tasks in parallel → boo (multiple sessions)
```

## Read the matching reference before you act

Both tools have non-obvious behavior that will bite you. On your first action with either tool, read its reference first — not as background, but before you spawn or drive anything.

- **delegate** → `references/delegate.md`. Two sharp edges to know up front: subagents are sandboxed to the four core tools (read, write, edit, bash) — MCP/extension tools are silently unavailable; and concurrency has hard ceilings (3 concurrent sync tasks, 5 async tickets). The reference covers task fields, session reuse, async, failure recovery, and recipes.
- **boo** → `references/boo.md`. Two sharp edges to know up front: `send --text` is literal — no implicit Enter, no shell escaping — and `wait`/`peek` match the *rendered screen*, not scrollback. The reference covers the command set, core loop, recipes, and gotchas.
