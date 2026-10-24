---
name: harness-session-navigation
description: >
  Use this skill when finding, identifying, resuming, switching, branching, or
  navigating sessions in Pi, Devin CLI, Command Code (`cmd`/`commandcode`),
  ZCode (`zcode`), or Freebuff, when identifying which of those harnesses
  owns an unknown coding session, or when searching session history — by
  content, tool actions, or file edits — across one or all of them. Covers
  project scoping, IDs, transcript locations, pickers, trees, forks, and safe
  read-only recovery when the normal picker cannot find it.
license: Apache-2.0
metadata:
  version: "1.1"
  topic: harness-sessions
---
# Harness Session Navigation

Use the harness's own session picker first. It understands titles, project
scope, hidden sessions, and format changes better than filesystem guesses.
Inspect files only when the picker cannot answer the question.

## Route by intent

1. Identify the harness from the command, process, or storage path. Do not
   assume every JSONL file is a Pi session.
2. Establish the **project directory**. Pi, Devin, Command Code, ZCode, and
   Freebuff all scope normal history discovery by working directory or project.
   ZCode records each session's working directory in its store — a real cwd,
   not a transcript-path inference — so `--project` substring scoping is
   reliable there (still a substring match, not equality).
3. Choose the operation:
   - latest session, and the user explicitly wants it activated → continue command
   - known session → resume by name or ID
   - unknown or ambiguous session → open/search the picker
   - earlier point in one conversation → tree/rewind when supported
   - preserve the original before diverging → fork/clone when supported
4. Confirm the selected session before doing work: use the harness's session
   info command, or report the title/ID and working directory shown by its
   listing. A continue command activates a session; it is not read-only
   discovery, so list first when “latest” could be ambiguous.

## Quick reference

| Harness | Continue latest | Find/resume | Current session | Navigate or branch |
|---|---|---|---|---|
| Pi | `pi -c` | `pi -r`, `/resume`, `pi --session <path-or-id>` | `/session` | `/tree`, `/fork`, `/clone` |
| Devin | `devin -c` | `devin -r [id]`, `devin list`, `/resume`, `/ls` | session ID shown by listing/resume | No Pi-style tree command; start fresh with `/new` |
| Command Code | `cmd -c` | `cmd -r [name]`, `/resume`, `cmd --session <path-or-id>` | `/session-file` | `/tree`, `/rewind`, `/fork`, `/clone` |
| Freebuff | `freebuff --continue` | `/history`, `freebuff --continue <id>` | selected chat ID; local chat directory if needed | No tree/fork interface; `/new` starts a separate chat |
| ZCode | `zcode -c` (cwd-scoped) | `zcode --resume <id>`; TUI `/resume [id]` (omit id = latest in cwd) | session ID from resume listing | `/fork`, `/rewind` (checkpoint restore); no tree view. `/rewind` can restore workspace files — not harmless browsing |

`piz` (the local thin-client fork of zcode) drives the same shared core and
records into the same store — every zcode row below is findable as-is, and
`piz --resume <id>` accepts the same ids. The core stamps `zcode-agent` on
both, so sessions cannot be attributed to one frontend and don't need to be.

Read only the matching reference before giving commands or inspecting storage:

- [Pi](references/pi.md)
- [Devin](references/devin.md)
- [Command Code](references/commandcode.md)
- [Freebuff](references/freebuff.md)
- [ZCode](references/zcode.md)

## Helper scripts

The helpers are read-only, emit bounded structured output, and never resume or
delete sessions:

- `scripts/search_sessions.py` — search message and tool content across
  **all** local sessions at once (Pi, Devin, Command Code, Freebuff, ZCode): the
  one-place search. Byte-prefilters each transcript, parses only what could
  match, and returns per-session grouped hits with bounded excerpts,
  provenance (model/provider/source position), and a resume command where
  safe. ZCode is queried through its SQLite store instead of files; its
  subagent sessions are excluded as noise. Use it before running
  `search_session.py` over individual files.
  - `--query` matches full event text, tool names, and full tool-call
    arguments; `--tool edit --tool-arg path=AGENTS.md` answers "which
    sessions — and which models — changed a file"
  - scope with `--harness` (repeatable), `--since 30d`, `--project
    <path-substring>`; a full-history scan over gigabytes can take a minute,
    so prefer `--since` when recency bounds the question
  - `--since` filters by transcript modification time, not event time — for
    zcode it uses the session's recorded `time_updated`, which is real
    activity time. `--project` filters the transcript's path on disk, not
    verified project membership; it cannot scope Devin's flat transcript
    directory by cwd. Omit that filter for Devin unless the substring
    identifies a transcript. ZCode's `--project` matches against the
    session's recorded working directory — a case-insensitive substring like
    everywhere else, but on the real cwd rather than an inferred path.
  - the byte prefilter is conservative: Unicode, escaped text, and tool
    summaries may require extra parsing rather than risk missing a match
  - exit 3 means no matches; zero-hit searches still emit valid empty JSON
- `scripts/find_sessions.py` — list/filter candidate sessions across
  harnesses by metadata and first-prompt previews (no content search).
  `--cache` memoizes extraction in
  `${XDG_CACHE_HOME:-~/.cache}/session-navigation/` keyed by file
  mtime/size, including changes to or creation of optional metadata sidecars:
  a cold scan of thousands of transcripts drops to a warm rerun in well under
  a second. Cache format changes cause a rebuild automatically.
  For Devin, `--devin-source` controls
  discovery: `auto` (default) tries `devin list --format json`, then falls back
  to scanning `~/.local/share/devin/cli/transcripts/*.json`; `cli` forces the
  CLI only; `disk` forces the transcript scan only. When a transcript exists on
  disk, the `source` field is the transcript path and `preview` is the first
  user prompt.
- `scripts/inspect_session.py` — inspect one Pi, Command Code, Devin,
  Freebuff, or ZCode session, returning metadata and a limited number of user
  prompt previews. For Devin, pass the transcript file from
  `~/.local/share/devin/cli/transcripts/<session-id>.json`. Devin output also
  includes `tool_call_summary` (counts by tool name), `files_touched` (paths
  from write/edit calls, capped at 50), `duration`, `step_counts`, and
  `final_metrics` when present. For ZCode, pass a session id (`sess_…`, unique
  prefix allowed) — no transcript file exists; output includes
  `tool_call_summary`, `files_touched`, and `duration_seconds`.
- `scripts/search_session.py` — normalize and filter one local transcript by
  `user`, `assistant`, `thinking`, `tool`, `tool_call`, or `tool_result`;
  optionally filter exact tool names and preview text. Supports Pi, Command
  Code, Devin, Freebuff, and ZCode (pass a `sess_…` id or unique prefix;
  looked up read-only in the zcode store). `--query` matches full event text and full
  tool-call arguments before any display truncation, so matches deep inside
  long messages or `edit`/`write` payloads are found. Output rows carry
  `model`, `provider`, and `source_ref` (line/step position) for
  attribution. Tool-call previews are smart summaries (file
  paths for write/edit, commands for exec, queries for web_search, etc.)
  instead of raw argument dumps; when the query matches the arguments but
  not the summary, the excerpt falls back to the arguments so the hit stays
  visible. `--tool-arg key=value` filters by argument
  content (case-insensitive partial match). `--extract` with
  `--extract-field <name>` pulls plain-text values from tool-call arguments —
  e.g., recovering all file paths written by a session.

Run them from the skill directory with `uv`:

```bash
uv run scripts/search_sessions.py --query 'webhook retries' --harness pi --harness devin --since 30d
uv run scripts/search_sessions.py --tool edit --tool-arg path=src/api/auth.py --since 90d
uv run scripts/search_sessions.py --query kwin --project skills --format tsv
uv run scripts/find_sessions.py --harness pi --query webhook --cache
uv run scripts/find_sessions.py --harness devin --devin-source disk --limit 10
uv run scripts/find_sessions.py --harness devin --project /path/to/repo --format tsv
uv run scripts/inspect_session.py /path/to/session.jsonl --max-prompts 3
uv run scripts/inspect_session.py ~/.local/share/devin/cli/transcripts/brawny-relish.json
uv run scripts/search_session.py /path/to/session.jsonl --type user --query migration
uv run scripts/search_session.py /path/to/session.jsonl --type tool --tool bash --limit 20
uv run scripts/search_session.py ~/.local/share/devin/cli/transcripts/brawny-relish.json --type tool_call --tool write
uv run scripts/search_session.py ~/.local/share/devin/cli/transcripts/brawny-relish.json --tool write --extract --extract-field file_path
uv run scripts/search_session.py ~/.local/share/devin/cli/transcripts/brawny-relish.json --type tool_call --tool-arg file_path=html-communication
```

Tool calls and tool results are separate records; `--type tool` includes both.
Repeat `--type`, `--tool`, or `--tool-arg` to combine filters. Use `--offset`
for pagination and `--preview-chars` to adjust bounded snippets. With
`--extract`, `--preview-chars` can be raised up to 100000 to retrieve full
tool-call arguments. Exit code `3` means no candidates/events matched. Exit
code `2` means discovery or parsing failed; when cross-harness discovery
cannot query Devin via CLI, it falls back to disk rather than failing.
Diagnostics go to stderr; JSON/JSONL/TSV data stays clean on stdout.
Use the native interactive picker instead when the user is present and a picker
can answer the question more directly.

## Finding workflow

### When the project is known

Run the picker from that exact directory. If changing the caller's shell would
be surprising, use a subshell:

```bash
(cd /path/to/project && pi -r)
(cd /path/to/project && devin list)
(cd /path/to/project && cmd -r)
```

For Freebuff, launch it normally in the known project and use `/history` (or
`/chats`) inside the already-active session. Running `freebuff --cwd
/path/to/project --continue` is not read-only discovery: it immediately
activates that project's latest chat.

### When only a phrase, date, or task is known

1. Search content across all sessions first:
   `scripts/search_sessions.py --query <phrase>` — scope with `--since` or
   `--harness` when a full-history scan is more than the question needs. For
   "which sessions changed file X", use the action form
   `--tool edit --tool-arg path=<file>`. Session transcripts can contain
   private prompts, source code, tool output, and credentials; the helpers
   return bounded excerpts, never whole transcripts.
2. If content search is the wrong tool (title/ID/project lookup), use the
   built-in picker/list; prefer titles and first-prompt previews.
3. `scripts/find_sessions.py --cache` lists candidates by metadata cheaply;
   the harness's own picker may still be more direct when the user is
   present.
4. Return a small candidate table: harness, title/preview, ID, project, last
   activity, and a resume command only when the required project context is
   verified. Freebuff's on-disk key contains only a project basename, so its
   helper results deliberately omit a resume command rather than claiming an
   ambiguous command is exact.
5. If more than one candidate remains, ask the user to choose. Do not resume an
   arbitrary match and begin modifying files.

### When the user says “go back”

Clarify whether they mean:

- switch to a different saved conversation;
- jump to an earlier message while retaining one session tree;
- restore files as well as conversation state; or
- branch safely and keep the original untouched.

These are different operations. In particular, Command Code `/rewind` can
restore working files, while `/tree` changes the active conversation point.
Never treat rewind as harmless browsing.

## Safety rules

- Default to read-only discovery. Listing, searching, and resuming are separate
  from deleting, rewinding files, or continuing agent work.
- Never print whole transcripts merely to identify a session. Extract the
  smallest useful metadata or prompt preview.
- Pi content search includes all recorded branches; it does not yet label
  superseded branches. A historical statement is not necessarily the final
  decision. For file edits, inspect the corresponding tool result before
  claiming the mutation succeeded.
- Do not edit session databases, JSONL, metadata, checkpoint, or sidecar files.
- Do not delete sessions without explicit confirmation. Prefer the harness's
  picker and trash/recoverable deletion where available.
- Fork before an experiment when the harness supports it and preserving the
  original matters.
- Resuming may restore or change model, permissions, cwd, and context depending
  on the harness and launch flags. Verify the relevant state before sending a
  task.

## Completion signal

A session-navigation task is complete when the user has either:

- a verified active session and its ID/path, or
- a bounded candidate list with exact resume commands and enough evidence to
  choose safely.
