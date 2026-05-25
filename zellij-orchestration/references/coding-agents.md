# Coding Agent CLI Reference

Quick reference for launching and driving coding agents from the command line. Useful when orchestrating agents via zellij panes.

## Common Patterns

All these agents share a few conventions:
- `-p` / `--print` for non-interactive mode (process prompt, print result, exit)
- `-c` / `--continue` to resume last session
- `-r` / `--resume` to resume a specific session
- `--model` to override the model

---

## pi

```
pi [options] [messages...]
```

| Flag | Effect |
|---|---|
| `-p, --print` | Non-interactive: process and exit |
| `-c, --continue` | Resume previous session |
| `-r, --resume` | Select session to resume interactively |
| `--session <path\|id>` | Use specific session (partial UUID works) |
| `--fork <path\|id>` | Fork session into new session |
| `--no-session` | Ephemeral, don't save |
| `--model <pattern>` | Model pattern or `provider/id` |
| `--provider <name>` | Provider name |
| `--thinking <level>` | off, minimal, low, medium, high, xhigh |
| `--skill <path>` | Load a skill |
| `-e <path>` | Load an extension |
| `-nt` | Disable all tools |
| `-t <tools>` | Tool allowlist |
| `--mode <mode>` | Output: text (default), json, rpc |
| `--system-prompt <text>` | Override system prompt |
| `--append-system-prompt <text>` | Append to system prompt |
| `--no-context-files` | Skip AGENTS.md / CLAUDE.md discovery |
| `@<file>` | Include file in initial message |

Examples:
```bash
pi "list all .ts files"                          # interactive with prompt
pi -p "list all .ts files"                       # non-interactive
pi -c "what did we discuss?"                     # continue session
pi --model sonnet:high "solve this"              # model + thinking
pi --no-tools "just answer questions"            # no tool access
pi @prompt.md @image.png "what color is the sky" # with file context
```

---

## Claude (claude)

```
claude [options] [prompt]
```

| Flag | Effect |
|---|---|
| `-p, --print` | Non-interactive: print response and exit |
| `-c, --continue` | Resume last conversation |
| `-r, --resume [id]` | Resume by session ID or interactive picker |
| `--model <model>` | Model alias or full name (e.g. `sonnet`, `opus`) |
| `--effort <level>` | low, medium, high, xhigh, max |
| `--output-format <fmt>` | text, json, stream-json (with `-p`) |
| `--max-budget-usd <n>` | Cap spending (with `-p`) |
| `--system-prompt <text>` | Override system prompt |
| `--append-system-prompt <text>` | Append to system prompt |
| `--dangerously-skip-permissions` | Bypass all permission checks |
| `--permission-mode <mode>` | acceptEdits, auto, bypassPermissions, default, dontAsk, plan |
| `--allowedTools <tools>` | Tool allowlist |
| `--disallowedTools <tools>` | Tool denylist |
| `-w, --worktree [name]` | Create git worktree for session |
| `--mcp-config <file>` | Load MCP servers |
| `-n, --name <name>` | Session display name |
| `--bare` | Minimal mode: skip hooks, LSP, plugins, etc. |
| `--json-schema <schema>` | Validate output against JSON Schema |

Examples:
```bash
claude                                    # interactive
claude -p "fix the bug in main.ts"        # non-interactive
claude -c                                 # continue
claude --model opus --effort high "plan"  # model + effort
claude --dangerously-skip-permissions     # no permission prompts
claude -p --output-format json "list deps" # structured output
```

---

## Cursor Agent (agent)

```
agent [options] [prompt...]
```

| Flag | Effect |
|---|---|
| `-p, --print` | Non-interactive: print to console |
| `--output-format <fmt>` | text, json, stream-json (with `-p`) |
| `--continue` | Continue previous session |
| `--resume [chatId]` | Resume specific chat |
| `--model <model>` | Model to use (e.g. `gpt-5`, `sonnet-4`) |
| `--mode <mode>` | plan (read-only), ask (Q&A) |
| `--plan` | Shorthand for `--mode=plan` |
| `-f, --force` | Auto-approve unless explicitly denied |
| `--yolo` | Alias for `--force` |
| `--trust` | Trust workspace (with `-p` only) |
| `--workspace <path>` | Workspace directory |
| `-w, --worktree [name]` | Git worktree |
| `--sandbox <mode>` | enabled, disabled |

Examples:
```bash
agent                            # interactive
agent -p "list files"            # non-interactive
agent --plan "analyze the code"  # read-only planning
agent --force "make changes"     # auto-approve
```

---

## OpenCode (opencode)

```
opencode [options] [project]       # TUI (default)
opencode run [message..]           # Non-interactive run
opencode serve                     # Headless server
```

### `opencode run` (non-interactive)

| Flag | Effect |
|---|---|
| `-m, --model <provider/model>` | Model to use |
| `-c, --continue` | Resume last session |
| `-s, --session <id>` | Resume specific session |
| `--fork` | Fork on resume |
| `--agent <name>` | Agent to use |
| `--format <fmt>` | default, json |
| `-f, --file <files>` | Attach files |
| `--title <title>` | Session title |
| `--variant <level>` | Reasoning effort (high, max, minimal) |

### `opencode serve` (headless)

| Flag | Effect |
|---|---|
| `--port <n>` | Listen port (default: random) |
| `--hostname <host>` | Listen host (default: 127.0.0.1) |

Examples:
```bash
opencode                                  # interactive TUI
opencode run "list all .ts files"         # non-interactive
opencode run --format json "list deps"    # structured output
opencode serve --port 4096                # headless server
opencode run --attach http://localhost:4096 "do stuff"  # attach to server
```

---

## Devin (devin)

```
devin [options] [-- <prompt>...]
```

| Flag | Effect |
|---|---|
| `-p, --print [prompt]` | Non-interactive: process and exit |
| `-c, --continue` | Resume last conversation |
| `-r, --resume [id]` | Resume specific session |
| `--model <model>` | Model to use |
| `--prompt-file <file>` | Load prompt from file |
| `--permission-mode <mode>` | auto (read-only), dangerous (all) |
| `--sandbox` | Sandbox exec-tool processes |
| `--config <path>` | Override config file |
| `--agent-config <file>` | Declarative agent config (JSON/YAML) |

Subcommands: `auth`, `mcp`, `rules`, `skills`, `cloud`, `list`, `sandbox`, `acp`

Examples:
```bash
devin -- "fix the bug"                # interactive
devin -p "list all .ts files"         # non-interactive
devin -p --permission-mode dangerous  # auto-approve all
devin -c                              # continue
```

---

## Quick Comparison

| | Non-interactive | Resume | Worktree | JSON output | Permission bypass |
|---|---|---|---|---|---|
| **pi** | `-p` | `-c`, `-r` | — | `--mode json` | `-nt` / `-t` |
| **claude** | `-p` | `-c`, `-r` | `-w` | `--output-format json` | `--dangerously-skip-permissions` |
| **agent** | `-p` | `--continue`, `--resume` | `-w` | `--output-format json` | `-f` / `--yolo` |
| **opencode** | `run` | `-c`, `-s` | — | `--format json` | — |
| **devin** | `-p` | `-c`, `-r` | — | — | `--permission-mode dangerous` |
