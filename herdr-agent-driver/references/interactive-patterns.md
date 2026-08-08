# Interactive Patterns — Devin, Pi, Codex, Command Code (Synthesized)

> **Synthesis of four TUI references for herdr drivers.**  Last distilled: 2026-05-13.
> Keep this lean: driver-relevant surface only — launch, modes, slash commands, session handling, keys, and what breaks automation.
>
> **Sources**
> - Devin — Essential Commands: <https://docs.devin.ai/cli/essential-commands>
> - Pi — Usage: <https://pi.dev/docs/latest/usage>
> - Codex — Developer Commands (CLI): <https://learn.chatgpt.com/docs/developer-commands?surface=cli>
> - Command Code — Interactive Mode: <https://commandcode.ai/docs/interactive-mode>
>
> Raw fetches saved to `research/` are not needed — this file is the curated driver view.
> For launch recipes (herdr `agent start` flags, resume, reporting) see **references/harness-recipes.md**.

---

## Why this exists

All four harnesses are **TUI-first**. You drive them inside a herdr pane, not by calling a JSON API. That means:

- You send keystrokes and slash commands, not just prompts.
- `Enter` often means *submit*, so multi-line pastes can split into two submits.
- Permission modes change what the agent can do without stopping for you.
- Sessions persist on disk; resuming restores model, context, and mode.
- The parent orchestrator never trusts the child's report — it verifies git state itself.

If you understand where the harnesses are the same, you can write one driving loop that works for all four and only varies the flags.

---

## At-a-glance matrix

| Concern | Devin (`devin`) | Pi (`pi`) | Codex (`codex`) | Command Code (`cmd`/`commandcode`) |
|---|---|---|---|---|
| **Launch** | `devin` (REPL), `devin -- prompt`, `devin -p "prompt"` (single-turn) | `pi`, `pi "prompt"`, `pi -p "prompt"` | `codex`, `codex "prompt"`, `codex exec "prompt"` (non-interactive) | `cmd`, `cmd -m <model>` |
| **File refs** | `@` — autocomplete, adds file as context | `@file` — fuzzy-search includes file; `Tab` completes paths | `@` — search & add path to prompt (TUI) | `@` anywhere — path autocomplete; also pulls `AGENTS.md` chain |
| **Bash escape** | Shell cmds run by agent; user doesn't send `!` | `!cmd` (output shown to model), `!!cmd` (hidden) | `!` in composer runs shell under approval/sandbox | `!cmd` at line start — runs shell, output joins session |
| **Permission cycle** | `Shift+Tab` cycles Normal→Accept Edits→Smart→Bypass→Autonomous; also `/mode <name>` and `/normal`, `/accept-edits`, `/smart`, `/bypass` | No built-in cycle; controlled by `--tools`, `--approve` trust, and tool allowlist | No single cycle; use `/permissions` picker (Auto / Read Only etc.) | `Shift+Tab` cycles default→auto-accept→plan→default; `bypass` joins as 4th rung with `--yolo`; `dont-ask` off-cycle; `/mode*` shorthands |
| **Session resume** | `devin -c` (continue), `devin -r [id]` (resume picker), `/resume`, `/continue`, `/ls` | `pi -c` / `pi -r`, `pi --session <id>`, `pi --fork <id>`, `/resume`, `/fork`, `/clone` | `codex resume [--last]`, `codex fork [--last]`, `/resume`, `/new`, `/fork`, `codex exec resume` | `--resume` / `--continue`, `/resume` (cold adopts model; in-TUI always adopts) |
| **Model switch** | `/model` selector; `--model` flag | `--model`, `--provider`, `--thinking`, `/model`, `--models` cycling | `/model`, `/fast`, `codex --model <id>`, `config.toml` | `/model` (becomes default for new sessions), `--model`/`-m` session override; `cmd --list-models`; resolution order flag > session pick > default |
| **Interrupt** | `Esc` or `Ctrl+C` | `Esc` aborts; `Alt+Up` restores queued msgs | `Esc` (herdr `send-keys esc`), queue `Tab`/`Enter` while working | `Esc` stops; `Esc Esc` rewinds (`/rewind`); `Ctrl+C` clears |
| **Newline** | `Shift+Enter` | `Shift+Enter` (or `Ctrl+Enter` on Windows Terminal) | `Shift+Enter` (or via composer) | `Shift+Enter` or `Ctrl+J` adds newline; `Enter` submits |
| **Paste >300 chars** | No collapse noted | No collapse noted | No collapse noted | Collapses to `[Text#N]` placeholder; disable via `collapsePastedText: false` in `~/.commandcode/config.json` |
| **External editor** | `Ctrl+G` | `Ctrl+G` (`$VISUAL`/`$EDITOR`) | `Ctrl+G` / `$EDITOR` via config | `Ctrl+G` uses `$EDITOR` (`code`, `vim`…) |
| **Context files** | Reads repo docs (AGENTS.md etc. per project) | Layers `AGENTS.md`/`CLAUDE.md` from `~/.pi` + parents + cwd; `AGENTS.override.md` replaces; `--no-context-files` disables | Reads `AGENTS.md` from workspace + `~/.codex/config.toml` | Reads `AGENTS.md` chain; `@` mention also pulls intermediate `AGENTS.md` |
| **Config trust** | Team Settings admin deny always wins | Trust prompt for project `.pi/` on first run; `--approve`/`--no-approve` overrides; `defaultProjectTrust` setting | `config.toml` + `-c key=value` overrides; `--strict-config` rejects unknown keys | `~/.commandcode/config.json` + `settings.json`; `keybindings.json` for shortcuts |

---

## Shared patterns to expect

These hold for **all four** and should shape your herdr loop:

1. **Slash menu on `/`** — type `/` at line start to open the ranked command palette. Up/Down moves, Enter runs, Tab/→ inserts with trailing space, Esc closes. Completion still works before queuing. In Codex, queued slash commands parse *when they run*, not when you queue them.
2. **`@` for files, `!` for shell** — across harnesses, `@` adds file context and `!` runs a shell line whose output the model sees. Prefer `herdr agent prompt` for agent turns; use `!` only for the human-style quick check.
3. **Permission modes hide behind `Shift+Tab`** — every harness offers a way to reduce approval prompts. For automation, **launch with the intended mode** (`--permission-mode accept-edits`, `-a on-request -s workspace-write`, `--yolo`) rather than cycling mid-session.
4. **Sessions are durable** — every harness saves to disk. Resume is cheaper than re-explaining context. Only resume when you want the old context; otherwise start fresh.
5. **`Esc` interrupts** — `herdr agent send-keys <name> esc` is the universal interrupt. `Ctrl+C` is the heavier fallback. After an interrupt, re-read state before prompting again.
6. **Multi-line is fragile** — pasting raw multi-line text into a TUI can fire `Enter` early. The safe path for long specs is: write to a file (`/tmp/task.md` or `TASK.md`), then prompt with `Read TASK.md. Implement only phase X.`
7. **Queuing exists** — Pi queues `Enter` (steer after tool loop) vs `Alt+Enter` (follow-up after all work); Codex queues via `Tab`; Command Code supports stashing via `Ctrl+S`. As a herdr driver, **do not queue** — wait for `idle` before sending the next prompt. Mid-`working` sends garble or queue depending on harness.

---

## Devin — Essential Commands (distilled)

### Starting

```bash
devin                             # interactive REPL, no prompt
devin -- your prompt here          # REPL with initial prompt (use -- so prompt isn't parsed as subcommand)
devin -p "prompt"                  # single-turn, no REPL: prints response, exits
devin -p -- prompt words here      # same, with -- separator
```

- `@` triggers file/dir autocomplete; selecting adds it as context.
- Paste images with `Ctrl+V` ( navigable with Left/Right, Backspace removes).
- If a shell command outlives the default wait, Devin moves it to background and reports wait time + background shell ID; it can check output later.

### Permission + agent modes

Five permission modes, plus three agent-modes (Normal, Plan, Ask):

- Permission: **Normal** (default, read-only auto-approves in cwd, writes/exec ask), **Accept Edits** (edits auto-approved, shell still asks — ` /accept-edits`), **Smart** (edits auto-approved, other actions judged by a fast model; package installs, mutating git, `rm`, `sudo`, cloud CLI always ask — `/smart` or `devin --permission-mode smart`), **Bypass** (all tools auto-approved — `/bypass` / `/yolo` / `devin --permission-mode bypass` — respects admin Team Settings deny/ask), **Autonomous** (only with `--sandbox` — shell auto-approved inside OS sandbox, edit/write still prompt, network filtered by sandbox domain lists; launched as `devin --sandbox --permission-mode autonomous`).
- Agent modes: `/plan`, `/ask <question>` (oneshot question without edits). Cycle via `Shift+Tab` or `/mode <name>` / `/mode` to show current.

**Bypass vs Autonomous**

|  | Bypass | Autonomous |
|---|---|---|
| Requires `--sandbox` | No | Yes (only there) |
| Shell | Auto-approved, unrestricted | Auto-approved, sandbox-contained |
| Edit/write tools | Auto-approved anywhere | Still prompt (scope grant expands sandbox) |
| Network | Unrestricted | Filtered by sandbox allow/deny |
| Respects admin Team Settings | Yes | Yes |

Pick Bypass when you trust the whole machine; pick `--sandbox` (Autonomous) when you want OS-enforced file/domain limits.

### Session history

```bash
devin -c              # continue most recent in cwd
devin --continue
devin -r              # picker for recent sessions
devin --resume
devin -r brisk-otter  # resume specific ID
```

Slash equivalents: `/resume`, `/resume <id>`, `/ls` (alias `/list-sessions`), `/ls --all`, `/continue`, `/rm-session <id>` (irreversible).

### Slash commands (grouped)

| Group | Command | What it does |
|---|---|---|
| **Nav** | `/help` | Show all commands |
|  | `/exit`, `/quit` | Exit app (also plain `exit`/`quit` without slash) |
|  | `/clear`, `/new` | Clear history, start fresh |
| **Modes** | `/mode` | Show current |
|  | `/mode <name>` | Switch `normal`, `accept-edits`, `smart`, `plan`, `bypass`, `autonomous` |
|  | `/normal`, `/accept-edits`, `/smart`, `/plan`, `/bypass` | Direct switches (`/yolo` alias for bypass) |
|  | `/ask <q>` | Oneshot question, no edits |
| **Model** | `/model` | Model selector |
| **Sessions** | `/resume`, `/ls`, `/continue`, `/rm-session` | As above |
| **Workspace** | `/workspace` | List dirs (`/workspaces` alias) |
|  | `/add-dir <path>`, `/undo-add-dir <path>` | Add/remove workspace root |
| **Automation** | `/loop <prompt>` | Run prompt then auto-review diff in loop (requires clean git) |
| **Extensibility** | `/hooks` | List loaded hooks (IDs, events, source paths) |
| **Account** | `/login`, `/logout`, `/update`, `/upgrade`, `/bug`, `/compact` | Auth, update, report bug, force compaction |

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Shift+Tab` | Cycle modes |
| `Ctrl+C` | Clear input, or cancel running agent |
| `Esc` | Cancel running agent |
| `Shift+Enter` | Newline (multi-line input) |
| `Ctrl+V` / `Shift+Insert` | Paste |
| `Ctrl+G` | External editor |
| `Ctrl+O` | Full-screen thinking trace |
| `@` | Mention files |
| `/help` etc. | Slash palette |

**Herdr tip:** Launch Devin as `herdr agent start devin-app --kind devin --pane <pane_id> -- --model swe-1.7` (herdr v0.8+ devin integr. already injects `bypass` — don't add `--permission-mode`, or you get `cannot be used multiple times`; switch via `/mode` when `idle` if you need stricter). For strict phase boundaries, prefer one-turn prompts and fresh context (`/new`) over `/loop`, which is orchestrator-side.

---

## Pi — Usage (distilled)

### TUI layout (4 areas)

- **Startup header** — shortcuts, loaded context files, prompt templates, skills, extensions
- **Messages** — user msgs, assistant replies, tool calls/results, notifications, errors, extension UI
- **Editor** — typing area; border color = thinking level; temporarily replaced by `/settings` or extension UI
- **Footer** — cwd, session name, token/cache/cost/context usage, model

### Editor features

| Feature | How |
|---|---|
| File reference | `@` fuzzy-search project files |
| Path completion | `Tab` |
| Multi-line | `Shift+Enter` (or `Ctrl+Enter` on Windows Terminal) |
| Copy last response | `Ctrl+X` (in `/tree`, copies selected msg) |
| Images | `Ctrl+V`, `Alt+V` on Windows, or drag in |
| Shell command | `!command` — runs and sends output to model |
| Hidden shell | `!!command` — runs without sending output |
| External editor | `Ctrl+G` — respects `externalEditor` / `$VISUAL` / `$EDITOR` / Notepad / `nano` |
| Queued msgs | `Enter` = steer after tool loop; `Alt+Enter` = follow-up after all work; `Esc` = abort + restore queue; `Alt+Up` = retrieve queued → editor |

Configure queuing via `steeringMode` / `followUpMode` in Settings (`/settings`).

### Slash commands (type `/` to complete; skills as `/skill:name`)

| Command | Purpose |
|---|---|
| `/login`, `/logout` | OAuth / API-key creds |
| `/llama` | llama.cpp router models |
| `/model`, `/scoped-models` | Switch / enable/disable models for `Ctrl+P` cycling |
| `/settings` | Thinking level, theme, delivery, transport |
| `/resume` | Pick previous session |
| `/new` | New session |
| `/name <name>` | Display name |
| `/session` | Show file, ID, msgs, tokens, cost |
| `/tree` | Jump to any point, continue from there; can summarize abandoned branches |
| `/trust` | Save project trust to `~/.pi/agent/trust.json` (needs restart) |
| `/fork`, `/clone` | Fork from earlier msg / duplicate active branch |
| `/compact [prompt]` | Manual compaction with optional instructions |
| `/copy`, `/export [file]`, `/import <file>`, `/share` | Clipboard / HTML-JSONL export / gist share |
| `/reload`, `/hotkeys`, `/changelog`, `/quit` | Reload resources / show shortcuts / version history / quit |

### Sessions on disk

Saved to `~/.pi/agent/sessions/`, organized by cwd.

```bash
pi -c                  # continue most recent
pi -r                  # browse picker
pi --no-session        # ephemeral, don't save
pi --name "my task"    # display name at startup
pi --session <path|id> # specific file/ID
pi --fork <path|id>    # fork into new file
```

Use `/session` to see current file/ID; `/tree` for in-file navigation; `/compact` to free context.

### Context files

Pi layers `AGENTS.md` or `CLAUDE.md` from: `~/.pi/agent/AGENTS.md` → parent dirs walking up → cwd. If a dir has `AGENTS.override.md`, that file replaces `AGENTS.md`/`CLAUDE.md` in that dir only.

Disable with `--no-context-files` (`-nc`). Use for project conventions, commands, safety rules.

- **System prompt:** replace with `.pi/SYSTEM.md` (project) or `~/.pi/agent/SYSTEM.md` (global); append with `APPEND_SYSTEM.md` in either location.

### Project trust

On interactive startup, if a project folder contains project-local settings/resources/skills and has no saved decision in `~/.pi/agent/trust.json`, pi prompts to trust. Trusting allows loading `.pi/settings.json`, `.pi` resources, installing project packages, executing project extensions. Before trust, only context files + global extensions + CLI `-e` extensions load.

Non-interactive (`-p`, `--mode json`, `--mode rpc`) never prompts; it uses `defaultProjectTrust` (`ask`/`always`/`never` in `~/.pi/agent/settings.json`). Override per-run with `--approve`/`-a` (trust) or `--no-approve`/`-na` (ignore). `/trust` writes `trust.json`; restart to apply. `pi config` / package cmds use same flow, except `pi update` never prompts.

### CLI reference (driver-relevant flags)

```bash
pi [options] [@files...] [messages...]
```

**Package:**
`pi install <src> [-l]`, `pi remove|uninstall <src> [-l]`, `pi update [src|self|pi]`, `pi update --all|--extensions|--models|--self|--extension <src>`, `pi list`, `pi config` (all honor `--approve`/`--no-approve` except `update`).

**Modes:**
- default = interactive TUI
- `-p, --print` = print & exit; also merges piped stdin: `cat README.md | pi -p "Summarize"`
- `--mode json` = JSON lines per event; `--mode rpc` = stdin/stdout RPC; `--export <in> [out]` = HTML export

**Model:**
`--provider <name>` (anthropic/openai/google…), `--model <pattern>` (supports `provider/id` and `:thinking`), `--api-key`, `--thinking off|minimal|low|medium|high|xhigh|max`, `--models <patterns>` for `Ctrl+P` cycling, `--list-models [search]`

**Session:**
`-c/--continue`, `-r/--resume`, `--session <path|id>`, `--fork <path|id>`, `--session-dir <dir>`, `--no-session`, `--name/-n <name>`

**Tools:**
`--tools <list>` / `-t`, `--exclude-tools <list>` / `-xt`, `--no-builtin-tools` / `-nbt`, `--no-tools` / `-nt` (builtins: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`)

**Resources:**
`-e/--extension <src>` (repeatable), `--no-extensions`, `--skill <path>`, `--no-skills`, `--prompt-template <path>`, `--no-prompt-templates`, `--theme <path>`, `--no-themes`, `--no-context-files`/`-nc`; combine `--no-*` with explicit loads to pin exactly what runs (e.g. `pi --no-extensions -e ./my-extension.ts`).

**Other:**
`--system-prompt <text>`, `--append-system-prompt <text>`, `--tui-mode regular|fullscreen`, `--verbose`, `-a/--approve`, `-na/--no-approve`, `-h/--help`, `-v/--version`. Fullscreen vs regular affects transcript scrolling and Kitty image rendering.

**File args & examples:**
`pi @prompt.md "Answer this"`, `pi -p @screenshot.png "What's in this image?"`, `pi --model openai/gpt-4o --tools read,grep,find,ls -p "Review"` etc. See Jina markdown for full list.

**Design principle:** Pi keeps core small; workflow specifics (MCP, subagents, permission popups, plan mode, todos, background bash) are extensions/packages. You can compose them or use containers/tmux.

---

## Codex — Developer Commands (distilled, CLI surface = TUI + exec)

> This is the OpenAI **Codex CLI** (`codex` on `learn.chatgpt.com`), not Pi or Devin. Herdr kind `codex`.

### Global flags (base `codex` command; most propagate)

`--add-dir <path>` (repeat), `-a/--ask-for-approval untrusted|on-request|never`, `-C/--cd <path>`, `-c/--config key=value` (TOML), `--yolo` (`--dangerously-bypass-approvals-and-sandbox`), `--oss` + `--local-provider lmstudio|ollama`, `-m/--model <id>`, `-p/--profile <name>`, `-s/--sandbox read-only|workspace-write|danger-full-access`, `--search` (live web), `-i/--image <path>` (comma or repeat), `--remote ws://|wss://|unix://` + `--remote-auth-token-env`, `--enable/--disable <feature>`, `PROMPT` optional.

Precedence: `~/.codex/config.toml` < `-c key=value` (CLI). Add `--strict-config` to error on unknown config fields.

### Subcommands (maturity)

| Command | Maturity | When |
|---|---|---|
| `codex` (no subcommand) | Stable | Launch TUI (interactive) |
| `codex app [PATH]` | Stable | Open ChatGPT desktop app |
| `codex app-server --listen <url>` | Experimental | Local app-server (stdio/ws/unix) for clients |
| `codex apply <TASK_ID>` | Stable | Apply Codex cloud diff locally |
| `codex archive <SESSION>` / `unarchive` | Stable | Archive/restore saved session |
| `codex cloud [--env ENV_ID]` + `cloud list`/`exec` | Experimental | Browse/run cloud chats; `--attempts 1-4`, `--json` |
| `codex completion <shell>` | Stable | Generate bash/zsh/fish/powershell completions |
| `codex debug …` | Experimental | `app-server send-message-v2`, `models`, `prompt-input` |
| `codex delete <SESSION> [--force]` | Stable | Permanent delete (--force only with UUID) |
| `codex doctor [--json --all]` | Stable | Diagnostic report |
| `codex exec [PROMPT]` (`codex e`) | Stable | Non-interactive run: `--json`, `--sandbox`, `--yolo`, `-o <file>`, `--output-schema`, resume |
| `codex execpolicy check --rules <path>` | Experimental | Evaluate `.rules` decision |
| `codex features list/enable/disable` | Stable | Persist feature flags to `config.toml` |
| `codex fork [--last]` | Stable | Fork session into new chat |
| `codex login [--device-auth|--with-api-key|--with-access-token]` | Stable | Auth; `codex login status` exits 0 when logged in |
| `codex logout` | Stable | Clear creds |
| `codex mcp list|add|get|remove|login|logout` | Stable | Manage MCP servers (stdio ` -- <cmd>` vs `--url https://…`) |
| `codex mcp-server` | Stable | Run Codex as MCP server over stdio |
| `codex plugin add|list|remove` + `marketplace add|list|remove|upgrade` | Stable | Marketplace `owner/repo[@ref]` / local dir |
| `codex resume [--last --all]` | Stable | Resume by ID or most recent; `tui.resume_cwd` controls cwd prompt |
| `codex review --uncommitted|--base|--commit <SHA> [PROMPT]` | Stable | Non-interactive review |
| `codex sandbox [--permission-profile]` | Stable | Run cmd under same sandbox Codex uses (seatbelt/landlock/windows) |
| `codex update` | Stable | Self-update (release builds) |

**Driver tip:** For supervised repo work, prefer `codex --sandbox workspace-write -a on-request` (safe) over `--yolo`. Use `codex exec --json --output-last-message out.md "task"` in CI, then `codex exec resume --last "follow-up"` to continue. Add `--add-dir` to grant extra writable roots rather than `danger-full-access`.

### Slash commands inside the TUI (type `/` and Tab-queuing supported)

Codex ships 40+ in-TUI slashes. While working, `Tab` queues a slash for next turn; `Enter` injects into current turn.

| Command | Purpose | When driver cares |
|---|---|---|
| `/permissions` | Set approval policy (Auto / Read Only / custom profiles) | Prefer launch flags; use slash only to tighten mid-session |
| `/ide` | Pull open files/selection from IDE | `herdr agent prompt` usually instead |
| `/keymap` | Remap TUI shortcuts → `config.toml` `tui.keymap` | Avoid remapping in driven panes |
| `/vim` | Toggle Vim mode in composer | Rare for driving |
| `/setup-default-sandbox`, `/sandbox-add-read-dir <abs path>` | Windows elevated sandbox | Only on Windows |
| `/agent`, `/subagents` | Switch active agent thread | Use when forking subagents |
| `/apps`, `/plugins`, `/hooks`, `/mcp`, `/memories`, `/skills`, `/import` | Browse connectors/plugins/hooks/MCP/memory/skills; import Claude Code artifacts | Treat as setup steps |
| `/clear` | Clear terminal + start fresh chat | Driver should use `/new` instead for clean history without clearing view |
| `/rename <name>` | Rename chat | Useful for `herdr agent rename` naming |
| `/archive`, `/delete` | Archive/delete current session & exit | Driver uses `codex archive/delete` CLI instead |
| `/compact` | Summarize chat to free tokens | Call after long runs |
| `/copy` (`Ctrl+O`) | Copy last completed output to clipboard | Not needed in herdr (use `agent read`) |
| `/diff` | Show git diff incl. untracked | Driver should use `git diff` directly for verification |
| `/exit`, `/quit` | Exit CLI | Driver uses pane close |
| `/experimental` | Toggle Network proxy etc. | Restart needed |
| `/approve` | Retry one auto-review denial | Handle blocked states directly |
| `/model` | Pick active model & reasoning effort | Sets model for session; verify via `/status` |
| `/fast` | Toggle Fast service tier (catalog-driven) | Only if model advertises Fast |
| `/plan [prompt]` | Enter plan mode, propose execution plan | Use before implementation when you want a plan artifact |
| `/goal <obj>` / `/goal edit|pause|resume|clear|view` | Persistent task goal ≤4000 chars | Goal stays attached across turns |
| `/personality` | Style: `friendly`/`pragmatic`/`none` | Only if model supports |
| `/ps`, `/stop` (`/clean` alias) | Show/stop background terminals (when `unified_exec` in use) | Prefer `herdr pane read` + `herdr wait output` for background cmds |
| `/fork` | Fork current chat into new ID | Alternative to `codex fork` CLI |
| `/app` | Continue session in ChatGPT desktop app (macOS/Windows) | Not for herdr |
| `/side`, `/btw` | Ephemeral side chat (focused detour; parent status still shown) | Avoid in strictly bounded driving |
| `/raw [on|off]` | Toggle raw scrollback (`Alt+R`, `tui.raw_output_mode`) | Use for copy-friendly output |
| `/resume`, `/new [name]` | Resume picker / start new chat in same CLI session | `/new` keeps terminal view; `/clear` clears it |
| `/review` | Working-tree review (behavior changes + missing tests; uses `review_model`) | Run after implementation, then `/diff` |
| `/status` | Show model, approval, writable roots, tokens, remote addr | Confirm where you are |
| `/usage [daily|weekly|cumulative]` | Token usage + earned resets | From inside TUI |
| `/debug-config` | Config layer diagnostics | Debug why effective setting ≠ `config.toml` |
| `/statusline`, `/title` | Pick footer/title items → `tui.status_line` / `tui.terminal_title` | Footer includes model/context/limits/git/tokens |
| `/theme` | Syntax theme → `tui.theme` | Cosmetic |
| `/pets`, `/pet` | Terminal pet → persists | Cosmetic |
| `/raw`, `/copy`, `/diff` | See above | — |
| `/init` | Generate `AGENTS.md` scaffold | Run once to bootstrap instructions |
| `/help`, `/bug`, `/feedback`, `/logout` | Help, report bug, send feedback, sign out | — |
| `@` file mention | `@` then path | Adds file as prompt context |
| `!` shell | `!` prefix runs shell under approval/sandbox | Quick checks |

**Workflow snippets (driver-relevant):**

- **Set model:** `/model` → pick `gpt-5.6-luna/terra` → confirm via `/status`.
- **Fast toggle:** `/fast` on/off (persists; footer item via `/statusline`).
- **Plan:** `/plan Propose a migration…` (unavailable while working); use `/plan` to propose before implementation.
- **Goal:** `/goal Finish migration…` to attach persistent objective; `/goal pause/resume/clear`.
- **Blocked:** `/approve` retries one denied action under current policy; else answer via `herdr agent prompt`.

---

## Command Code — Interactive Mode (distilled)

### Surface

Three prefixes change what input does:

| Type | Result |
|---|---|
| `/` at start | Slash menu — built-in, custom ` $ARGUMENTS`, skill, mod commands; ranked: names starting with query > names containing > description |
| `!` at start | Bash mode: line runs as shell, command+output joins session |
| `@` anywhere | File-path autocomplete; mentioned file becomes context; also pulls any `AGENTS.md` between file's dir and project root (see Memory) |

Five keys per session:

| Key | Action |
|---|---|
| `Shift+Tab` | Cycle permission: `default → auto-accept → plan → default` (`Alt+M` fallback on Windows) |
| `Esc` | Stop what's running |
| `Esc Esc` | Rewind to previous checkpoint (`/rewind`) |
| `Ctrl+O` | Toggle full tool output |
| `Ctrl+G` | Open prompt in `$EDITOR` (`code`/`vim`/`nano`/…) |

` /hotkeys` shows every shortcut (incl. overrides); `/help` is the short list.

### Slash menu mechanics

Rows ranked as you type. `↑/↓` move, `Enter` runs, `Tab`/`→` inserts with trailing space for args, `Esc` closes. Full catalog at `/reference/slash-commands` (60+ commands; `$ARGUMENTS` templating for custom).

### Model picking

`/model` switches model for running session **and becomes default for new sessions** (next `cmd` starts there). Existing sessions keep their model until you switch them.

`--model` / `-m` is a **session-scoped** override — does not change saved default; cleared by an explicit `/model` pick or a `/resume` switch. Unknown IDs rejected; `cmd --list-models` enumerates all. Catalog at `/reference/cli/models`.

Resolution order for requests:

1. `--model` flag (until cleared by `/model` or conversation switch)
2. Model picked via `/model` this session, or adopted from resumed conversation
3. Default (last `/model` pick snapshotted at session start → built-in default)

**Resuming restores model transiently** (doesn't rewrite default; banner and requests stay in sync):

- **Cold `--resume`/`--continue`** (fresh process): adopts saved conversation's model, unless same command also passes `--model X` (which wins).
- **In-TUI `/resume`**: always adopts jumped-into conversation's model, even over launch `--model` or prior `/model`.

### Permission modes

`Shift+Tab` cycles `default → auto-accept → plan → default`. With `--yolo`, cycle gains `bypass` as 4th rung: `plan → bypass → default`.

Two modes off-cycle:
- `dont-ask` — from settings or `--permission-mode dont-ask`; `Shift+Tab` from it goes to `auto-accept`.
- `bypass` — only via `--yolo`.

Jump directly via `/mode` or shorthands `/mode:default`, `/mode:auto-accept`, `/mode:plan`. Guide at `/permissions` covers rule syntax and decision ladder.

### Pasting

Paste >300 chars collapses to `[Text#N]` for readability; full text still submits, and `Ctrl+G` opens real prompt in editor. To inline raw instead, set in `~/.commandcode/config.json`:

```json
{ "collapsePastedText": false }
```

Top-level key (alongside `theme`, `compactMode`). Legacy fallback `input.collapsePastedText` in `settings.json` honored only if top-level absent.

### Keybindings — all remappable via `~/.commandcode/keybindings.json`

File is optional; missing/typoed lines fall back to defaults; bad entry never breaks the rest. `/reload` applies edits mid-session. Earlier short names (`cursorUp`, `expandTools`) auto-mapped to dotted IDs.

**How a binding is written:** `modifier+key` (`ctrl+a`, `alt+left`, `shift+enter`); multi-mods allowed, order irrelevant. Modifiers: `ctrl`/`control`, `shift`, `alt`/`option`/`opt`/`meta`. Keys: letters/digits/symbols or named keys `up/down/left/right/home/end/pageup/pagedown/enter/return/escape/esc/tab/space/backspace/delete/insert` (case-insensitive). Value can be single string or list; `[]` unbinds.

**Coverage:** Remapping live today for: Moving cursor, word/line deletion, whole `/tree` navigator, and `app.permission.cycle`, `app.tools.expand`, `app.model.select`, `app.todos.toggle`. Rest listed for reference; custom bindings "on the way". `backspace` stays fixed.

| Action | Default | Does |
|---|---|---|
| **Moving cursor** |  |  |
| `tui.editor.cursorLeft` | `left` | Char left |
| `tui.editor.cursorRight` | `right` | Char right |
| `tui.editor.cursorUp` | `up` | Line up |
| `tui.editor.cursorDown` | `down` | Line down |
| `tui.editor.cursorWordLeft` | `alt+left`, `ctrl+left`, `alt+b` | Word back |
| `tui.editor.cursorWordRight` | `alt+right`, `ctrl+right`, `alt+f` | Word forward |
| `tui.editor.cursorLineStart` | `home`, `ctrl+a` | Line start |
| `tui.editor.cursorLineEnd` | `end`, `ctrl+e` | Line end |
| **Editing** |  |  |
| `tui.editor.deleteCharBackward` | `backspace` | Char behind |
| `tui.editor.deleteCharForward` | `delete` | Char ahead |
| `tui.editor.deleteWordBackward` | `ctrl+w`, `alt+backspace` | Word behind |
| `tui.editor.deleteToLineStart` | `ctrl+u` | To line start |
| `tui.editor.deleteToLineEnd` | `ctrl+k` | To line end |
| **Composing** |  |  |
| `tui.input.newLine` | `shift+enter`, `ctrl+j` | Newline not submit |
| `tui.input.submit` | `enter` | Send |
| **Session** |  |  |
| `app.permission.cycle` | `shift+tab`, `alt+m` | Cycle permission |
| `app.tools.expand` | `ctrl+o` | Full tool output |
| `app.model.select` | `alt+p` | Quick model picker (`option+p` macOS) |
| `app.todos.toggle` | `ctrl+x` | Todo manager (`/todos` overlay) |
| `app.editor.external` | `ctrl+g` | `$EDITOR` |
| `app.input.stash` | `ctrl+s` | Stash/restore prompt |
| `app.interrupt` | `escape` | Stop |
| `app.clipboard.pasteImage` | `ctrl+v` | Paste image |
| **`/tree` browser** |  |  |
| `app.tree.foldOrPrevBranch` | `alt+left`, `shift+tab`, `ctrl+left` | Fold / jump prev branch |
| `app.tree.unfoldOrNextBranch` | `alt+right`, `tab`, `ctrl+right` | Unfold / jump next branch |
| `app.tree.label` | `shift+l` | Edit entry label |
| `app.tree.labelTime` | `shift+t` | Toggle label timestamps |
| `app.tree.filter.default` | `ctrl+d` | Default view |
| `app.tree.filter.noTools` | `ctrl+t` | Hide tool rows |
| `app.tree.filter.userOnly` | `ctrl+u` | User msgs only |
| `app.tree.filter.labeledOnly` | `ctrl+l` | Labeled only |
| `app.tree.filter.all` | `ctrl+a` | Show every entry |
| `app.tree.filter.cycle` | `ctrl+o` | Cycle filter forward |
| `app.tree.filter.cycleBack` | `shift+ctrl+o` | Cycle filter back |

**Fixed (not remappable):**

| Key | Where | Does |
|---|---|---|
| `Ctrl+E` (`Ctrl+Y` in VS Code-family terminals) | Permission prompt | Explain pending shell command in plain English (controlled by On-demand explanations in `/config` General) |
| `Ctrl+E` / `Ctrl+Y` | Transcript on | Toggle limited/full transcript (permission prompt takes priority) |

VS Code-based terminals claim `Ctrl+E`, so `cmd` uses `Ctrl+Y` — see IDE Integration docs.

**Further reading:** Slash Commands, Plan Mode, Sessions & Checkpoints (`/rewind`, `/tree`, `/fork`), IDE Integration.

---

## Herdr driving implications (read this)

What changes when you drive these harnesses from a parent via `herdr`:

### Do

- **Launch with least-privilege auto-approval.** Examples:
  ```bash
  herdr agent start devin-app --kind devin --pane <pane> -- --model swe-1.7  # herdr v0.8+ devin = bypass by default; don't add --permission-mode
  herdr agent start pi-app    --kind pi    --pane <pane> -- --model anthropic/claude-sonnet-4-5 --thinking medium
  herdr agent start codex-a   --kind codex --pane <pane> -- -a on-request -s workspace-write
  herdr pane run <pane> "cmd -t --auto-accept"  # unsupported kind via pane run
  ```
  Update `harness-recipes.md` for per-kind flags.

- **Wait for `idle`/`done` before prompting.** Never assume the child finished because your tool call returned; `herdr agent wait <name> --until idle --until done --until blocked --timeout 1200000` is the gate. On timeout or interrupt, re-read: `herdr agent get` + `herdr agent read --source visible`.

- **Use `agent prompt`, not raw pane typing, for turns.** `herdr agent prompt <name> "text"` submits via the integration; verify via state change or `agent read`. Only use `herdr pane run <pane> "text"` or `send-keys enter` for slash commands where submission via prompt is unreliable (e.g., harness slash widgets).

- **Write long prompts to a file.** All four harnesses can misinterpret multi-line pasted text as two submits. `echo "Full task..." > TASK.md` then `herdr agent prompt <name> "Read TASK.md. Do only step 2, verify, commit, stop."` avoids the trap.

- **Reset context at phase boundaries.** Devin `/new`, Pi `/new`/`/compact`, Codex `/new` or new session, Command Code `/rewind` or new session. Stale context makes agents defend earlier mistakes and blur scope.

- **Verify, don't trust.** After `idle`/`done`, read diff and commits yourself (`git status --short --branch`, `git diff --check`, `git show --stat HEAD`) and rerun relevant tests. Labels like "unrelated/pre-existing" need evidence.

### Don't

- **Don't drive via `codex exec`, `pi -p`, `devin -p` inside a pane.** Those are non-interactive modes for CI/scripts outside herdr. Inside herdr you want the interactive TUI plus `agent prompt`.

- **Don't spam slash commands to bypass supervision.** `/bypass`, `--yolo`, `/dangerous` remove the human from the loop. Reserve for sandboxes. Prefer `accept-edits` / `workspace-write` + explicit `blocked` handling.

- **Don't queue mid-`working`.** Pi and Codex both queue inputs if you send while working; Command Code stashes. Either way you lose determinism. Interrupt first (`send-keys esc`), confirm `idle`, then prompt.

- **Don't infer pane IDs.** Always parse `pane_id`/`workspace_id` from JSON responses (`herdr workspace create`, `herdr pane split`). Closed IDs aren't reused; moved panes get new IDs.

- **Don't forget `--no-focus`.** When orchestrating multiple panes, `herdr pane split --no-focus` and `herdr workspace create --no-focus` avoid stealing focus from the driver.

### Handling `blocked`

1. `herdr agent read <name> --source visible --lines 80` — see the actual prompt (permission, question, selector).
2. Choose minimally: `herdr agent send-keys <name> enter` (accept default) / `down enter` / answer text via `herdr agent prompt <name> "yes, proceed"` .
3. If irresolvable, escalate: `herdr notification show "… blocked" --body "…" --sound request`.

For harnesses without integration (`unknown` state), either launch with `--auto-accept`/`--yolo` and `herdr wait output --match` on a completion marker, or have the pane report state via `herdr pane report-agent "$HERDR_PANE_ID" --source hook --agent <kind> --state <idle|working|blocked> --seq N`.

---

## Related herdr recipes

- **Launch & resume per harness:** `references/harness-recipes.md` — exact `herdr agent start` flags, continue/resume (`-c`/`-r` vs `--resume` vs `/resume`), cold vs in-TUI model adoption.
- **Troubleshooting detection:** `herdr agent explain <target> --verbose`, `herdr agent read --source detection`, `herdr server agent-manifests`.

## Deep dives

- Pi keybindings & terminal setup: `https://pi.dev/docs/latest/keybindings` and `/terminal-setup`
- Pi sessions/compaction: `https://pi.dev/docs/latest/sessions` and `/compaction`
- Codex config: `https://learn.chatgpt.com/codex/config-file/config-basic` and `config-advanced`
- Codex AGENTS.md: `https://learn.chatgpt.com/codex/agent-configuration/agents-md`
- Command Code permissions decision table: `https://commandcode.ai/docs/permissions`
- Command Code slash commands & plan/sessions: `https://commandcode.ai/docs/reference/slash-commands`, `/plan-mode`, `/sessions`

