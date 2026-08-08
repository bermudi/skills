# Devin CLI — Essential Commands (Driver Distillation)

> **Distilled from** <https://docs.devin.ai/cli/essential-commands> — 2026-05-13.
> For herdr launch & resume flags see **references/harness-recipes.md** and **references/interactive-patterns.md** (matrix + driving tips).

## Starting

By default Devin runs as a REPL (graphical TUI). Chat back and forth; watch actions live.

```bash
devin                            # REPL, no prompt
devin -- your prompt here        # REPL with initial prompt (use -- so prompt isn't parsed as subcommand)
devin -p "prompt"                # single-turn, no REPL: print to stdout and exit
devin -p -- prompt words here    # same, -- separator still works
```

- `@` opens file/dir autocomplete — picking adds it as context.
- Paste images with `Ctrl+V` (Left/Right to navigate, Backspace to remove).
- If a shell command outlives the default wait, Devin backgrounds it and reports wait time + shell ID; it continues work and checks output later.

## Permission modes

Devin has 5 permission modes + 3 agent-modes (Normal / Plan / Ask via `/plan` and `/ask`).

| Mode | How to enter | What it allows |
|---|---|---|
| **Normal** (default) | `/normal` or `/mode normal` | Auto-approves read-only tools in cwd; asks for writes/exec |
| **Accept Edits** | `/accept-edits` or `/mode accept-edits` | Edits in workspace auto-approved; shell still prompts. Most people live here. |
| **Smart** | `/smart` or `devin --permission-mode smart` | Like Accept Edits, plus a fast model judges every other action (shell, fetch, MCP). Clearly safe → auto-approved; unclear/risky (package installs, mutating git, rm, sudo, cloud CLI, sensitive files) still prompts. Rollout-gated; see Smart Mode docs. |
| **Bypass** | `/bypass` / `/yolo` / `/dangerous` or `devin --permission-mode bypass` | Auto-approves **all** tool calls (writes + shell). Respects admin Team Settings deny/ask. |
| **Autonomous** | `devin --sandbox --permission-mode autonomous` (only with `--sandbox`, auto-selected) | Shell auto-approved inside OS sandbox; file writes still prompt (scope grant expands sandbox). Network filtered by sandbox domain lists. |

**Bypass vs Autonomous** — both reduce prompts, different safety:

|  | Bypass | Autonomous |
|---|---|---|
| Requires `--sandbox` | No | Yes |
| Shell | Unrestricted auto-approved | Auto-approved, sandbox-contained |
| Edit/write | Auto-approved anywhere | Still prompts |
| Network | Unrestricted | Filtered by sandbox |
| Respects Team Settings | Yes | Yes |

Pick Bypass when you trust the whole machine; pick `--sandbox` (Autonomous) when you want OS-enforced file/domain limits.

Agent-modes: `/plan` enters Plan, `/ask <question>` asks without edits (oneshot).

## Session history

```bash
devin -c              # continue most recent in cwd
devin -r              # picker for recent sessions
devin -r brisk-otter  # resume specific ID
```

Slash equivalents: `/resume`, `/resume <id>`, `/ls` (`/list-sessions`), `/ls --all`, `/continue`, `/rm-session <id>` (irreversible).

## Slash commands

| Group | Command | Purpose |
|---|---|---|
| **Nav** | `/help` | Show all commands |
|  | `/exit` or `/quit` | Exit (also `exit`/`quit` without slash) |
|  | `/clear` or `/new` | Clear history, start fresh |
| **Modes** | `/mode` | Show current |
|  | `/mode <name>` | Switch `normal`/`accept-edits`/`smart`/`plan`/`bypass`/`autonomous` |
|  | `/normal`, `/accept-edits`, `/smart`, `/plan`, `/bypass` | Direct switches (`/yolo`, `/dangerous` alias bypass) |
|  | `/ask <q>` | Ask without edits |
| **Model** | `/model` | Show model selector |
| **Sessions** | `/resume`, `/ls`, `/continue`, `/rm-session` | As above |
| **Workspace** | `/workspace` (`/workspaces`) | List workspace dirs |
|  | `/add-dir <path>` | Add workspace root |
|  | `/undo-add-dir <path>` | Remove it |
| **Automation** | `/loop <prompt>` | Prompt → auto-review diff in loop (requires clean git) |
| **Extensibility** | `/hooks` | List loaded hooks (IDs, events, sources) |
| **System** | `/login`, `/logout` | Auth |
|  | `/update`, `/upgrade` | Update CLI / subscription |
|  | `/bug`, `/compact` | Report bug / force compaction |

## Keyboard shortcuts (essentials)

| Shortcut | Does |
|---|---|
| `Shift+Tab` | Cycle modes |
| `Ctrl+C` | Clear input or cancel agent |
| `Esc` | Cancel agent |
| `Shift+Enter` | Newline (multi-line) |
| `Ctrl+V` / `Shift+Insert` | Paste |
| `Ctrl+G` | External editor |
| `Ctrl+O` | Full-screen thinking trace |
| `@` | Mention file |

See full list at `https://docs.devin.ai/cli/reference/keyboard-shortcuts`.

## Herdr driver notes

- Launch: `herdr agent start devin-app --kind devin --pane <pane> -- --model swe-1.7` (herdr v0.8+ devin integration already defaults to `bypass` — don't add `--permission-mode`, it errors `cannot be used multiple times`; switch to `accept-edits`/`normal` later via `/mode` when `idle` if needed). For strict boundaries prefer one-turn prompts + `/new` over `/loop` (orchestrator-side loop; let parent enforce phase).
- Fresh context between phases: submit `/new`, wait for prompt, then next task. Or exit via `Ctrl+D` and relaunch.
- Mode `smart` is useful when you want helpful auto-approval without full bypass; verify it's available on the account first (`devin models` / Team Settings).
- SWE-1.7 is productive on scoped impl/tests but prone to scope expansion and weak self-review — verify claims.
