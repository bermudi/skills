# Harness launch recipes

Start recipes use an existing shell pane:

```bash
herdr agent start <unique-name> --kind <kind> --pane <pane-id> -- <harness-args...>
```

Herdr supplies the canonical executable; do not repeat it after `--`. Detection support requires the matching integration, for example `herdr integration install <claude|codex|opencode|pi|devin>`. Check with `herdr integration status`.

## Claude Code (`claude`)

```bash
--permission-mode acceptEdits                    # auto-accept file edits, still prompts for risky actions
--dangerously-skip-permissions                   # full autonomy — sandboxes only
--model sonnet -n my-session                     # model + display name
--add-dir ../shared                              # extra allowed directories
```

- Prefer submitting the initial task with `herdr agent prompt` after startup.
- Resume arguments: `-c` (last conversation in cwd) or `-r <session-id>`
- **Trust prompt:** interactive first run in an untrusted directory may show a workspace-trust dialog. Expect `blocked`; read `visible` and confirm once, or pre-trust the directory.
- Permission modes: `acceptEdits` | `auto` | `bypassPermissions` | `manual` | `dontAsk` | `plan`.

## Codex (`codex`)

```bash
-a on-request -s workspace-write                 # recommended: writable workspace, model asks when unsure
-a never -s workspace-write                      # no approval prompts, sandboxed to workspace
--dangerously-bypass-approvals-and-sandbox       # full autonomy — sandboxes only
-m gpt-5 -C ~/src/app                            # model + working root
```

- Prefer submitting the initial task with `herdr agent prompt` after startup.
- Resume arguments: `resume --last`
- Approval policies: `untrusted` | `on-request` | `never`. Sandbox: `read-only` | `workspace-write` | `danger-full-access`.
- `codex exec` is the non-interactive mode — do not use it for driven sessions; use the TUI.

## OpenCode (`opencode`)

```bash
# no arguments                                   # TUI in pane cwd
--auto                                           # auto-approve permissions (flag is documented as dangerous)
-m anthropic/claude-sonnet-4-5                   # provider/model
--agent build                                    # pick agent
```

- Continue/resume arguments: `-c` or `-s <session-id>`
- `opencode run <msg>` is non-interactive — not for driven sessions.

## Pi (`pi`)

```bash
# no arguments                                   # interactive, default provider
--model anthropic/claude-sonnet-4-5              # or --provider X --model Y; model:thinking works
-n my-session                                    # display name
--tools read,grep,find,ls,bash                   # tool allowlist (e.g. read-only reviews)
```

- Prefer submitting the initial task with `herdr agent prompt` after startup.
- Continue/resume arguments: `-c` or `-r`
- `pi -p` is non-interactive — not for driven sessions.

## Devin (`devin`)

```bash
herdr agent start devin-app --kind devin --pane <pane-id> -- --model swe-1.7 --permission-mode accept-edits
```

- Model selection: `--model <name>`; inspect available account models with `devin models`.
- Permission modes: `auto` (read-only auto-approval), `accept-edits`, `smart`, or `dangerous`. Prefer `accept-edits` for supervised repository work; `dangerous` is sandbox-only.
- Initial prompt can be supplied after `--` or via `--prompt-file`, but starting the TUI and using `herdr agent prompt` keeps orchestration consistent.
- Resume arguments: `-c` for the most recent conversation in the cwd, or `-r <session-id>` for a specific session.
- Fresh context: submit `/new`, wait for the new prompt, then submit the next task. Use this between implementation phases and between read-only review and review-fixing.
- `/loop` is an orchestrator-side command, not something the child model chooses. For strict phase/review boundaries, the parent should submit a normal one-turn prompt instead of invoking `/loop`, then exit Devin with Ctrl-D and relaunch the desired model.
- Observed SWE-1.7 profile: productive at tightly scoped implementation and tests, but prone to helpful scope expansion and insufficiently adversarial self-review. Treat its completion report and “unrelated/pre-existing” labels as unverified claims.

## Harnesses without a herdr integration (example: `cmd` / Command Code)

No official integration → state detection may be `unknown`. Two options:

**1. Launch with no-prompt flags and pattern-match output:**

```bash
# Unsupported harnesses cannot use `herdr agent start`; run them in an existing pane.
herdr pane run <pane_id> "cmd -t --auto-accept"  # or --yolo (full bypass)
herdr wait output <pane_id> --match "Press Esc twice" --timeout 120000
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
herdr agent send-keys <name> esc          # interrupt current generation (widely supported; verify per harness)
herdr agent send-keys <name> ctrl+c       # last resort
```

## Debugging detection

```bash
herdr agent explain <name> --verbose      # matched rule, evidence, evaluated-rules list
herdr agent read <name> --source detection # the exact snapshot the classifier sees
herdr server agent-manifests              # manifest source/version status
```
