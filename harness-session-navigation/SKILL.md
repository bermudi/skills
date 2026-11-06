---
name: harness-session-navigation
description: >
  Find, identify, resume, switch, branch or navigate sessions in Pi, Claude
  Code, Devin CLI, Command Code (`cmd`/`commandcode`), ZCode (`zcode`) or
  Freebuff; identify which harness owns an unknown session; search history by
  content, tool action or file edit; recover a session the picker can't find.
license: Apache-2.0
metadata:
  version: "1.5"
  topic: harness-sessions
---
# Harness Session Navigation

Use the harness's own picker first: it understands titles, project scope, hidden sessions and format changes better than filesystem guesses. Inspect files only when the picker can't answer.

## Route by intent

1. Identify the harness from the command, process or storage path; not every JSONL is a Pi session.
2. Establish the **project directory**: all six harnesses scope history by working directory or project. ZCode records the real cwd per session, so `--project` is reliable there (still a substring match).
3. Pick the operation: latest and the user wants it activated → continue; known session → resume by name/ID; unknown or ambiguous → picker/search; earlier point in one conversation → tree/rewind; keep the original before diverging → fork/clone.
4. Confirm the selection before working: session info command, or the title/ID and cwd from its listing. A continue command **activates** a session (it isn't read-only discovery), so list first when "latest" could be ambiguous.

## Quick reference

| Harness | Continue latest | Find/resume | Current session | Navigate or branch |
|---|---|---|---|---|
| Pi | `pi -c` | `pi -r`, `/resume`, `pi --session <path-or-id>` | `/session` | `/tree`, `/fork`, `/clone` |
| Claude Code | `claude -c` (cwd-scoped) | `claude -r [id-or-name]`, `/resume` | UUID in `~/.claude/projects/<slug>/<id>.jsonl` | `--fork-session` on resume; `/rewind` can restore files; no tree |
| Devin | `devin -c` | `devin -r [id]`, `devin list`, `/resume`, `/ls` | ID from listing/resume | No tree; `/new` starts fresh |
| Command Code | `cmd -c` | `cmd -r [name]`, `/resume`, `cmd --session <path-or-id>` | `/session-file` | `/tree`, `/rewind`, `/fork`, `/clone` |
| Freebuff | `freebuff --continue` | `/history`, `freebuff --continue <id>` | selected chat ID; local chat dir | No tree/fork; `/new` = separate chat |
| ZCode | `zcode -c` (cwd-scoped) | `zcode --resume <id>`; TUI `/resume [id]` (no id = latest in cwd) | ID from resume listing | `/fork`, `/rewind` (restores workspace files: not harmless); no tree |

`piz` (local thin-client fork of zcode) shares zcode's core and store: every zcode row applies, `piz --resume <id>` takes the same ids, and sessions can't (and needn't) be attributed to one frontend.

Read only the matching reference before giving commands or touching storage: [Pi](references/pi.md) · [Claude Code](references/claude.md) · [Devin](references/devin.md) · [Command Code](references/commandcode.md) · [Freebuff](references/freebuff.md) · [ZCode](references/zcode.md).

## Helper scripts

Read-only, bounded output, never resume or delete. Run from the skill directory with `uv run scripts/<name>.py`; each has `--help` with the full flags.

- **`search_sessions.py`**: content/tool search across **all** harnesses at once (ZCode via its SQLite store, subagent sessions excluded). Use before per-file `search_session.py`.
- **`find_sessions.py`**: list candidates by metadata and first-prompt preview (no content search). `--id <prefix>` answers "which harness owns this id?"; `--cache` makes warm reruns sub-second.
- **`inspect_session.py`**: metadata and prompt previews for one session; takes a path or any id/unique prefix.
- **`search_session.py`**: filter one transcript by event type, tool, args; `--extract` recovers e.g. every file path a session wrote; `--around L<n>` shows context around a hit's `source_ref`.
- **`session_children.py`**: child sessions an orchestrator drove through herdr (`--driven-only` drops panes that only appeared in a listing; `inferred` matches list every candidate).
- **`turn_usage.py`**: per-user-turn API calls, tool errors, output tokens, peak context, compactions for one Claude Code or Pi session.

```bash
uv run scripts/search_sessions.py --query 'webhook retries' --harness pi --harness devin --since 30d
uv run scripts/search_sessions.py --tool edit --tool-arg path=src/api/auth.py --since 90d   # which sessions/models changed a file
uv run scripts/search_sessions.py --regex 'wtf|why did you|not what i' --since 7d
uv run scripts/search_sessions.py --tool bash --query 'herdr agent wait' --with-result --since 7d
uv run scripts/find_sessions.py --id 1686b8b5 ; uv run scripts/find_sessions.py --here --limit 10
uv run scripts/search_session.py <id> --around L1520 --before 5 --after 10
```

Gotchas:
- **Read the coverage fields.** JSON carries `total_matches`, `returned`, `truncated`, `next_offset`, `warnings`, `hints` (what to narrow or raise), plus per-session `hits_capped`. `truncated: true` means not everything is shown; page with `--offset` (`--limit` ≤500). JSONL/TSV carry rows only; counts go to stderr.
- `--query` repeats to AND and matches full event text, tool names and full tool-call args; every word of a phrase must appear in one record, so multi-word queries scan fastest. A `--regex` (case-insensitive, ANDs with `--query`) with no literal on every branch forces a full parse (stderr says so). Full-history scans over gigabytes take about a minute: prefer `--since`.
- `--since` filters by transcript modification time, not event time (ZCode: recorded `time_updated`). `--project` filters the transcript's **path on disk**, not verified membership, and can't scope Devin's flat transcript dir by cwd: omit it for Devin unless the substring identifies a transcript. `--here` = `--project <cwd>`; a real path also matches slug-keyed harnesses (`--home-me-app--`).
- `--with-result` pairs each call with its result; `elapsed_source` is `recorded`, `timestamps` or `unknown` (Devin/Freebuff keep call and result in one step, so elapsed is never reported as 0).
- Devin discovery: `find_sessions.py --devin-source auto` uses `devin list --format json` only when scoped by `--project`/`--here` (directory-scoped), else scans `~/.local/share/devin/cli/transcripts/*.json`; `cli`/`disk` force one. Pass Devin transcript files directly to the inspect/search scripts.
- ZCode has no transcript file: pass a `sess_…` id (unique prefix OK).
- `turn_usage.py` counts per `message.id`: Claude writes one record per content block, each repeating the request's usage, so counting records inflates calls and tokens ~2×.
- Exit 3 = no matches (zero-hit searches still emit valid empty JSON); exit 2 = discovery/parse failure. Diagnostics go to stderr, data stays clean on stdout. `--type` and `--tool` repeat; tool calls and results are separate records (`--type tool` includes both); `--preview-chars` goes up to 100000 with `--extract`.
- Transcripts contain private prompts, source, tool output and credentials: the helpers return bounded excerpts; never print whole transcripts to identify a session.

If the user is present and a native picker answers more directly, use it.

## Finding workflow

**Project known:** run the picker from that exact directory, in a subshell if changing the caller's cwd would surprise: `(cd /path/to/project && pi -r)`, likewise `claude -r`, `devin list`, `cmd -r`. For Freebuff, launch normally and use `/history` (or `/chats`) in the active session; `freebuff --cwd <path> --continue` isn't discovery: it activates that project's latest chat.

**Only a phrase, date or task known:**
1. `search_sessions.py --query <phrase>` first, scoped with `--since`/`--harness`; for "which sessions changed file X" use `--tool edit --tool-arg path=<file>`.
2. For title/ID/project lookup use the picker or `find_sessions.py --cache`, preferring titles and first-prompt previews.
3. Return a small table: harness, title/preview, ID, project, last activity, and a resume command only when the project context is verified. Freebuff's on-disk key holds only a project basename, so its helper results deliberately omit a resume command.
4. More than one candidate left: ask the user. Never resume an arbitrary match and start modifying files.

**"Go back"** is four different operations: switch to another saved conversation; jump to an earlier message in one session tree; restore files as well as conversation; or branch and keep the original. Rewind can restore working files (Command Code `/rewind`, ZCode `/rewind`, Claude `/rewind`) while `/tree` only moves the conversation point. Clarify which, and never treat rewind as harmless browsing.

## Safety

- Default read-only. Listing, searching and resuming are separate from deleting, rewinding files or continuing agent work.
- Pi content search includes all recorded branches without labeling superseded ones: a historical statement isn't necessarily the final decision. For file edits, check the tool result before claiming the mutation succeeded.
- Never edit session databases, JSONL, metadata, checkpoints or sidecars. Never delete sessions without explicit confirmation; prefer the picker and recoverable deletion.
- Fork before an experiment when preserving the original matters.
- Resuming may restore or change model, permissions, cwd and context depending on harness and flags: verify before sending a task.

Done when the user has a verified active session ID/path, or a bounded candidate list with exact resume commands and enough evidence to choose.
