# Codex CLI — Developer Commands (Driver Distillation)

> **Distilled from** <https://learn.chatgpt.com/docs/developer-commands?surface=cli> — 2026-05-13. This is the OpenAI **Codex CLI** (`codex`), not Pi or Devin. Herdr kind `codex`.
> For launch recipes and herdr `agent start` flags see **references/harness-recipes.md**; for cross-harness patterns **references/interactive-patterns.md**.

## Global flags (base `codex`; most propagate to subcommands)

Precedence: `~/.codex/config.toml` < `-c key=value` (CLI, TOML-parsed). Add `--strict-config` to error on unknown fields.

| Flag | Values | Purpose |
|---|---|---|
| `--add-dir` | `path` (repeat) | Grant extra writable dirs alongside workspace |
| `-a/--ask-for-approval` | `untrusted\|on-request\|never` | When to pause for human approval |
| `-C/--cd` | `path` | Working dir before processing |
| `-c/--config` | `key=value` (repeat) | Inline config override |
| `--yolo` | (`--dangerously-bypass-approvals-and-sandbox`) | Bypass all approvals/sandbox — sandbox VM only |
| `--dangerously-bypass-hook-trust` | boolean | Run hooks without persisted trust (automation that vets hooks) |
| `--enable/--disable` | `feature` (repeat) | Force-enable/disable feature flag |
| `-i/--image` | `path[,path...]` (repeat/comma) | Attach images to first message |
| `--local-provider` | `lmstudio\|ollama` | Local provider for `--oss` |
| `-m/--model` | `string` (e.g. `gpt-5.6-terra`) | Override configured model |
| `--oss` | boolean | Use local open-source provider |
| `-p/--profile` | `string` | Layer `$CODEX_HOME/<profile>.config.toml` |
| `--remote` | `ws://\|wss://\|unix://` | Connect to remote app-server (supports `codex`, `resume`, `fork`, `archive`, `delete`, `unarchive`) |
| `--remote-auth-token-env` | `ENV_VAR` | Bearer token for `--remote` (`wss://` or local `ws://` only) |
| `-s/--sandbox` | `read-only\|workspace-write\|danger-full-access` | Sandbox policy for shell |
| `--search` | boolean | Live web search (`cached` is default) |
| `PROMPT` | `string` | Optional initial instruction; omit for empty TUI |

**TUI tip:** `codex --sandbox workspace-write -a on-request` is least-privilege for supervised repo work; avoid `--yolo` unless in a hardened VM.

## Subcommands

| Command | Maturity | Purpose |
|---|---|---|
| `codex` | Stable | Launch TUI (accepts global flags + `PROMPT`/images) |
| `codex app [PATH]` | Stable | Open ChatGPT desktop app (macOS opens path; Windows prints path) |
| `codex app-server --listen <url>` | Experimental | Local app-server (`stdio://`, `ws://IP:PORT`, `unix://[PATH]`, `off`); flags `--ws-auth`, `--ws-token-file`, `--code-mode-host` etc. |
| `codex apply <TASK_ID>` | Stable | Apply Codex cloud diff locally (`codex a` alias) |
| `codex archive/unarchive <SESSION>` | Stable | Archive/restore saved session |
| `codex cloud` / `cloud list` / `cloud exec` | Experimental | Browse/run cloud chats; `--env ENV_ID` required for exec, `--attempts 1-4`, `--json`, `--cursor`, `--limit` |
| `codex completion <shell>` | Stable | Shell completions (`bash\|zsh\|fish\|power-shell\|elvish`) |
| `codex debug …` | Experimental | `models`, `prompt-input`, `app-server send-message-v2` |
| `codex delete <SESSION> [--force]` | Stable | Permanent delete (`--force` only with UUID) |
| `codex doctor [--json --all]` | Stable | Diagnostic report |
| `codex exec [PROMPT]` (`codex e`) | Stable | Non-interactive run: `--json`, `--output-last-message`, `--sandbox`, `--yolo`, `--ephemeral`, `--oss`, `resume --last/--all` |
| `codex execpolicy check --rules <path>` | Experimental | Evaluate `.rules` decision → JSON |
| `codex features list/enable/disable` | Stable | Persist feature flags to `config.toml` |
| `codex fork [--last]` | Stable | Fork previous session into new chat |
| `codex login [--device-auth|--with-api-key|--with-access-token]` | Stable | Auth; `codex login status` exits 0 when logged in |
| `codex logout` | Stable | Clear creds |
| `codex mcp list/add/get/remove/login/logout` | Stable | Manage MCP servers (` -- <cmd>` for stdio, `--url` for HTTP, `--env`, `--oauth-*`) |
| `codex mcp-server` | Stable | Run Codex as MCP server over stdio |
| `codex plugin add/list/remove` + `marketplace` | Stable | Plugins from `owner/repo[@ref]` or local dirs; `--available --json` |
| `codex resume [--last --all]` | Stable | Resume by ID or most recent; honors `tui.resume_cwd` |
| `codex review --uncommitted|--base|--commit [PROMPT]` | Stable | Non-interactive review |
| `codex sandbox [--permission-profile]` | Stable | Run cmd under Codex sandbox (seatbelt/landlock/windows) |
| `codex update` | Stable | Self-update (release builds only) |

## `codex exec` (non-interactive, CI-friendly)

```bash
codex exec --sandbox workspace-write --json --output-last-message out.md "Implement phase 2, verify, commit"
codex exec resume --last "Follow-up: address review comments"
```

- `--ephemeral` = no rollout files; `--skip-git-repo-check` outside git; `-o` writes final message for scripts; `--output-schema <json>` validates shape; `--ignore-rules`/`--ignore-user-config` for hermetic runs.

## Slash commands inside the TUI (type `/`; `Tab` queues, `Enter` injects while working)

| Command | Purpose |
|---|---|
| `/permissions` | Approval policy picker (Auto / Read Only / custom profiles) |
| `/ide` | Pull open files/selection from IDE |
| `/keymap` | Remap TUI shortcuts → `tui.keymap` |
| `/vim` | Toggle Vim mode |
| `/setup-default-sandbox`, `/sandbox-add-read-dir` | Windows elevated sandbox |
| `/agent`, `/subagents` | Switch active agent thread |
| `/apps`, `/plugins`, `/hooks`, `/mcp`, `/memories`, `/skills`, `/import` | Browse connectors/plugins/hooks/MCP/memory/skills; import Claude Code artifacts |
| `/clear` | Clear terminal + start fresh chat |
| `/rename <name>` | Rename chat |
| `/archive`, `/delete` | Archive/delete & exit (prefer CLI `codex archive/delete`) |
| `/compact` | Summarize to free tokens |
| `/copy` (`Ctrl+O`) | Copy last completed output |
| `/diff` | Git diff incl. untracked (driver should use `git diff` directly) |
| `/exit`, `/quit` | Exit |
| `/experimental` | Toggle Network proxy / Prevent sleep (restart) |
| `/approve` | Retry one auto-review denial |
| `/model` | Pick model + reasoning effort (`/status` to verify) |
| `/fast` | Toggle Fast tier (only if catalog advertises it) |
| `/plan [prompt]` | Enter plan mode, propose execution plan |
| `/goal <obj>` / `/goal edit|pause|resume|clear` | Persistent task goal ≤4000 chars |
| `/personality` | Style `friendly`/`pragmatic`/`none` |
| `/ps`, `/stop` (`/clean`) | Show/stop background terminals (when `unified_exec`) |
| `/fork` | Fork current chat into new ID |
| `/app` | Continue in ChatGPT desktop app |
| `/side`, `/btw` | Ephemeral side chat (parent status still shown) |
| `/raw [on|off]` | Toggle raw scrollback (`Alt+R`) |
| `/resume`, `/new [name]` | Resume picker / new chat in same session (`/new` keeps view, `/clear` clears) |
| `/review` | Working-tree review (uses `review_model`) |
| `/status` | Show model, approval, writable roots, tokens, remote addr |
| `/usage [daily|weekly|cumulative]` | Token usage + earned resets |
| `/debug-config` | Config layer diagnostics |
| `/statusline`, `/title` | Pick footer/title items → `tui.status_line` / `tui.terminal_title` |
| `/theme`, `/pets` | Syntax theme / terminal pet |
| `/init` | Generate `AGENTS.md` scaffold |
| `/help`, `/bug`, `/feedback`, `/logout` | Help / report / send feedback / sign out |
| `@` mention, `!` shell | `@` file adds context; `!` runs shell under approval/sandbox |

**Workflow snippets:**

- **Model:** `/model` → pick `gpt-5.6-luna/terra` → `/status` confirms.
- **Fast:** `/fast` on/off (persists; footer via `/statusline`).
- **Plan:** `/plan Propose a migration…` (unavailable while working).
- **Goal:** `/goal Finish migration…` → `/goal pause/resume/clear`.
- **Blocked:** `/approve` retries one denied action; else answer via `herdr agent prompt`.

## App-server (for local protocol clients)

`codex app-server --listen ws://IP:PORT|unix://[PATH]|stdio://` keeps JSONL-over-stdio by default (`--stdio` alias). WebSocket auth via `--ws-auth capability-token|signed-bearer-token` + `--ws-token-file`/`--ws-token-sha256` or signed JWT claims. `--code-mode-host wss://…/host` connects outbound to remote host.

## Herdr driver notes

- Prefer `herdr agent start codex-app --kind codex --pane <pane> -- -a on-request -s workspace-write` over `--yolo`. Add `--add-dir` for extra writable roots.
- Use `codex exec --json` only for CI outside herdr; inside herdr drive the TUI and use `herdr wait`/`agent read`.
- For unattended cloud, `codex cloud exec --env ENV_ID --attempts 2 "task"` then `codex apply <TASK_ID>` to apply diff.
