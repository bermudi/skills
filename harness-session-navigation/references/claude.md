# Claude Code sessions

`claude` scopes `--continue` to the current directory (per `claude --help`).
Launch from the target project, or use the helper's `cd … && claude --resume`.

## Find and resume

```bash
claude -c                       # latest conversation in this directory
claude -r                       # interactive picker (optional search term: claude -r foo)
claude -r <session-id-or-name>  # resume by UUID or name
claude -r <id> --fork-session   # resume into a NEW session id; original untouched
claude -n "name"                # name a new session (easier to find later)
```

Inside Claude Code: `/resume` opens the picker; `/rewind` (double `Esc`)
restores conversation and/or files — it can overwrite working files, so it is
a mutating recovery operation, not browsing. There is no tree view; fork with
`--fork-session` before risky alternatives.

Unverified: whether `--resume <id>` from a different directory finds a
session from another project. The helpers therefore emit
`cd <cwd> && claude --resume <id>` using the cwd recorded in the transcript.

## Storage and fallback inspection

```text
${CLAUDE_CONFIG_DIR:-~/.claude}/projects/<slug>/<session-id>.jsonl
```

- `<slug>` is the project path with `/` (and `.`) turned into `-`. It is
  **lossy** (`-home-daniel-build-skills` can't distinguish `build-skills` from
  `build/skills`); trust the `cwd` field on records, which the helpers use.
- `<session-id>/` sibling directories hold `tool-results/` spill files, not
  transcripts. Helpers glob only `<slug>/*.jsonl`. Subagent transcripts: none
  seen in the local store (unverified layout), so none are excluded or parsed.
- `~/.claude/sessions/` holds live-process IPC files with tokens — **do not
  read it**; it is not session history.

One JSON record per line; `type` selects the shape:

| `type` | Used for |
|---|---|
| `user` | `message.content` is a string (typed prompt) or blocks: `text`, `tool_result` (`tool_use_id`, `content`). `isMeta: true` = injected caveats, skipped |
| `assistant` | `message.model`, blocks `text` / `thinking` / `tool_use` (`id`, `name`, `input`); observed one block per record |
| `ai-title` | `aiTitle`, rewritten repeatedly — last wins. `custom-title` (`/rename`) is expected but unverified; the helper reads it too |
| `system`, `attachment`, `mode`, `permission-mode`, `last-prompt`, `file-history-*`, `api-request*`, … | bookkeeping; ignored by search |

`tool_result` blocks carry only `tool_use_id`; the helpers pair it with the
earlier `tool_use` so result events carry the tool name and `--tool Bash
--type tool_result` works. (A result whose call isn't in the same transcript
keeps an empty `tool`.)
Records carry `cwd`, `gitBranch`, `sessionId`, `version`, `timestamp`.

Never edit transcripts. `--no-session-persistence` runs leave no transcript.

```bash
scripts/find_sessions.py --harness claude --query webhook
scripts/search_sessions.py --harness claude --tool Edit --tool-arg file_path=AGENTS.md --since 30d
scripts/inspect_session.py ~/.claude/projects/<slug>/<id>.jsonl
```
