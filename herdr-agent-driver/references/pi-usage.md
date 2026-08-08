# Pi — Usage (Driver Distillation)

> **Distilled from** <https://pi.dev/docs/latest/usage> — 2026-05-13. Covers TUI layout, slash commands, sessions, context/trust, CLI flags.
> For launch recipes: **references/harness-recipes.md**. For cross-harness comparison: **references/interactive-patterns.md**.

## TUI layout (4 areas)

- **Startup header** — shortcuts, loaded context files, prompt templates, skills, extensions.
- **Messages** — user messages, assistant replies, tool calls/results, notifications, errors, extension UI.
- **Editor** — where you type; border color = thinking level; temporarily replaced by `/settings` or extension UI.
- **Footer** — cwd, session name, token/cache/cost/context usage, current model.

## Editor features

| Feature | How |
|---|---|
| File reference | `@` fuzzy-searches project files |
| Path completion | `Tab` |
| Multi-line | `Shift+Enter` (or `Ctrl+Enter` on Windows Terminal) |
| Copy last response | `Ctrl+X` (in `/tree`, copies selected message) |
| Images | `Ctrl+V`, `Alt+V` on Windows, or drag into terminal |
| Shell command | `!command` runs and sends output to model |
| Hidden shell | `!!command` runs without sending output to model |
| External editor | `Ctrl+G` opens `externalEditor` / `$VISUAL` / `$EDITOR` / Notepad / `nano` |

See `https://pi.dev/docs/latest/keybindings` for all shortcuts.

## Slash commands (type `/` to complete; extensions add custom, skills as `/skill:name`)

| Command | Purpose |
|---|---|
| `/login`, `/logout` | Manage OAuth / API-key credentials |
| `/llama` | Download/load llama.cpp router models |
| `/model`, `/scoped-models` | Switch / enable-disable models for `Ctrl+P` cycling |
| `/settings` | Thinking level, theme, message delivery, transport |
| `/resume` | Pick previous session |
| `/new` | Start new session |
| `/name <name>` | Set display name |
| `/session` | Show file, ID, messages, tokens, cost |
| `/tree` | Jump to any point and continue; can summarize abandoned branches |
| `/trust` | Save project trust to `~/.pi/agent/trust.json` (needs restart) |
| `/fork`, `/clone` | Fork from earlier user msg / duplicate active branch |
| `/compact [prompt]` | Manual compaction with optional instructions |
| `/copy`, `/export [file]`, `/import <file>`, `/share` | Copy last reply / export HTML-JSONL / import JSONL / gist share |
| `/reload`, `/hotkeys`, `/changelog`, `/quit` | Reload resources / show shortcuts / version history / quit |

## Message queuing (while agent is working)

- `Enter` — queues a steering message, delivered after current tool loop finishes.
- `Alt+Enter` — queues a follow-up, delivered after all work finishes.
- `Esc` — aborts and restores queued messages to editor.
- `Alt+Up` — retrieves queued messages back to editor.
- Configure via `steeringMode` / `followUpMode` in Settings. On Windows Terminal, `Alt+Enter` is fullscreen by default — remap per `terminal-setup` docs if needed.

**Driver rule:** don't queue mid-`working`. Wait for `idle` before sending next prompt; otherwise use `Esc` to interrupt first.

## Sessions on disk

Saved to `~/.pi/agent/sessions/`, organized by working directory.

```bash
pi -c                  # continue most recent
pi -r                  # browse picker
pi --no-session        # ephemeral, don't save
pi --name "my task"    # display name at startup
pi --session <path|id> # specific file / ID
pi --fork <path|id>    # fork into new file
```

Useful: `/session` shows current file/ID; `/tree` navigates the in-file session tree; `/compact` frees context. See `https://pi.dev/docs/latest/sessions` and `/compaction`.

## Context files

Pi layers `AGENTS.md` or `CLAUDE.md` from: `~/.pi/agent/AGENTS.md` → parent dirs walking up → cwd. If a dir contains `AGENTS.override.md`, that file replaces `AGENTS.md`/`CLAUDE.md` in that dir only. Disable with `--no-context-files` (`-nc`).

- **System prompt:** replace with `.pi/SYSTEM.md` (project) or `~/.pi/agent/SYSTEM.md` (global); append with `APPEND_SYSTEM.md` in either location.

Use context files for project conventions, commands, safety rules.

## Project trust

On interactive startup, if a project folder contains project-local settings/resources/skills and has no saved decision in `~/.pi/agent/trust.json`, Pi prompts to trust. Trusting allows loading `.pi/settings.json`, resources, installing packages, running project extensions. Before trust, only context files + global extensions + CLI `-e` extensions load.

Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) never prompt; they use `defaultProjectTrust` (`ask`/`always`/`never` in `~/.pi/agent/settings.json`). Override per-run with `--approve`/`-a` (trust) or `--no-approve`/`-na` (ignore). `/trust` writes `trust.json`; restart to apply. `pi config` / package commands use same flow, except `pi update` never prompts.

## Export / share

- `/export [file]` → HTML
- `/share` → private GitHub gist with HTML link
- Publish for research via `badlogic/pi-share-hf` (Hugging Face datasets).

## CLI reference (essential flags for driving)

```bash
pi [options] [@files...] [messages...]
```

**Package:** `pi install <src> [-l]`, `pi remove|uninstall <src> [-l]`, `pi update [src|self|pi]`, `pi update --all|--extensions|--models|--self|--extension <src>`, `pi list`, `pi config` (honor `--approve`/`--no-approve` except `update`).

**Modes:** default = TUI; `-p/--print` = print & exit (also merges piped stdin: `cat README.md | pi -p "Summarize"`); `--mode json` = JSON lines; `--mode rpc` = RPC over stdin/stdout; `--export <in> [out]` = HTML.

**Model:** `--provider <name>`, `--model <pattern>` (`provider/id` + optional `:thinking`), `--api-key`, `--thinking off|minimal|low|medium|high|xhigh|max`, `--models <patterns>` for `Ctrl+P` cycling, `--list-models [search]`.

**Session:** `-c/--continue`, `-r/--resume`, `--session <path|id>`, `--fork <path|id>`, `--session-dir <dir>`, `--no-session`, `--name/-n <name>`.

**Tools:** `--tools <list>`/`-t`, `--exclude-tools <list>`/`-xt`, `--no-builtin-tools`/`-nbt`, `--no-tools`/`-nt` (builtins: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`).

**Resources:** `-e/--extension <src>` (repeat), `--no-extensions`, `--skill <path>`, `--no-skills`, `--prompt-template <path>`, `--no-prompt-templates`, `--theme <path>`, `--no-themes`, `--no-context-files`/`-nc`. Combine `--no-*` with explicit loads to pin exactly what runs (e.g. `pi --no-extensions -e ./my-extension.ts`).

**Other:** `--system-prompt <text>`, `--append-system-prompt <text>`, `--tui-mode regular|fullscreen`, `--verbose`, `-a/--approve`, `-na/--no-approve`, `-h/--help`, `-v/--version`. Fullscreen scrolls inside viewport; `regular` uses terminal scrollback; Kitty image handling differs.

**File args:** `pi @prompt.md "Answer this"`, `pi -p @screenshot.png "What's in this image?"`.

**Examples:**

```bash
pi "List all .ts files in src/"                # interactive + prompt
pi -p "Summarize this codebase"                # non-interactive
cat README.md | pi -p "Summarize this text"    # piped stdin
pi --model openai/gpt-4o "Help me refactor"    # provider prefix
pi --model sonnet:high "Solve this"            # thinking shorthand
pi --tools read,grep,find,ls -p "Review"       # read-only
```

**Design note:** Pi keeps core small; workflow specifics (MCP, subagents, permission popups, plan mode, todos, background bash) are extensions/packages. Compose or use containers/tmux.

