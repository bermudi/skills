# Harness launch recipes

All recipes go after `herdr agent start <unique-name> [--workspace ID] [--no-focus] -- `.

Detection support requires the matching integration: `herdr integration install <claude|codex|opencode|pi>`. Check with `herdr integration status`.

## Claude Code (`claude`)

```bash
-- claude --permission-mode acceptEdits          # auto-accept file edits, still prompts for risky actions
-- claude --dangerously-skip-permissions         # full autonomy — sandboxes only
-- claude --model sonnet -n my-session           # model + display name
-- claude --add-dir ../shared                    # extra allowed directories
```

- Initial prompt: positional arg, e.g. `-- claude "Fix the flaky test in auth/"`
- Resume: `-- claude -c` (last conversation in cwd) or `-- claude -r <session-id>`
- **Trust prompt:** interactive first run in an untrusted directory may show a workspace-trust dialog. Expect `blocked`; read `visible` and confirm once, or pre-trust the directory.
- Permission modes: `acceptEdits` | `auto` | `bypassPermissions` | `manual` | `dontAsk` | `plan`.

## Codex (`codex`)

```bash
-- codex -a on-request -s workspace-write        # recommended: writable workspace, model asks when unsure
-- codex -a never -s workspace-write             # no approval prompts, sandboxed to workspace
-- codex --dangerously-bypass-approvals-and-sandbox   # full autonomy — sandboxes only
-- codex -m gpt-5 -C ~/src/app                   # model + working root
```

- Initial prompt: positional, `-- codex "Refactor the parser"`
- Resume: `-- codex resume --last`
- Approval policies: `untrusted` | `on-request` | `never`. Sandbox: `read-only` | `workspace-write` | `danger-full-access`.
- `codex exec` is the non-interactive mode — do not use it for driven sessions; use the TUI.

## OpenCode (`opencode`)

```bash
-- opencode                                      # TUI in cwd (or: opencode /path/to/project)
-- opencode --auto                               # auto-approve permissions (flag is documented as dangerous)
-- opencode -m anthropic/claude-sonnet-4-5       # provider/model
-- opencode --agent build                        # pick agent
```

- Continue/resume: `-- opencode -c` or `-- opencode -s <session-id>`
- `opencode run <msg>` is non-interactive — not for driven sessions.

## Pi (`pi`)

```bash
-- pi                                            # interactive, default provider
-- pi --model anthropic/claude-sonnet-4-5        # or --provider X --model Y, supports model:thinking shorthands
-- pi -n my-session                              # display name
-- pi --tools read,grep,find,ls,bash             # tool allowlist (e.g. read-only-ish reviews)
```

- Initial prompt: positional, `-- pi "List all .ts files in src/"`
- Continue/resume: `-- pi -c` or `-- pi -r`
- `pi -p` is non-interactive — not for driven sessions.

## Harnesses without a herdr integration (example: `cmd` / Command Code)

No official integration → state detection may be `unknown`. Two options:

**1. Launch with no-prompt flags and pattern-match output:**

```bash
herdr agent start cmd-a --workspace <ws_id> --no-focus -- cmd -t --auto-accept   # or --yolo (full bypass)
herdr wait output <pane_id> --match "Press Esc twice" --timeout 120000           # booted
herdr wait output <pane_id> --match "some completion marker" --regex --timeout 1800000
```

**2. Report state from harness hooks** using the pane's own environment (`HERDR_PANE_ID` is set inside herdr panes):

```bash
herdr pane report-agent "$HERDR_PANE_ID" --source cmd-hook --agent cmd --state working --seq 1
herdr pane report-agent "$HERDR_PANE_ID" --source cmd-hook --agent cmd --state idle    --seq 2
```

States: `idle|working|blocked|unknown`. Use increasing `--seq` so stale reports are ignored. This gives the pane a real agent identity usable by `agent wait`/`agent get`.

## Interrupt / steering keys (all harnesses)

```bash
herdr pane send-keys <pane_id> esc        # interrupt current generation (widely supported; verify per harness)
herdr pane send-keys <pane_id> ctrl+c     # last resort
```

## Debugging detection

```bash
herdr agent explain <name> --verbose      # matched rule, evidence, evaluated-rules list
herdr agent read <name> --source detection # the exact snapshot the classifier sees
herdr server agent-manifests              # manifest source/version status
```
