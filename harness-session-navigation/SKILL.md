---
name: harness-session-navigation
description: >
  Use this skill when finding, identifying, resuming, switching, branching, or
  navigating sessions in Pi, Devin CLI, Command Code (`cmd`/`commandcode`), or
  Freebuff, or when identifying which of those harnesses owns an unknown coding
  session. Covers project scoping, IDs, transcript locations, pickers, trees,
  forks, and safe read-only recovery when the normal picker cannot find it.
license: Apache-2.0
metadata:
  version: "1.0"
  topic: harness-sessions
---
# Harness Session Navigation

Use the harness's own session picker first. It understands titles, project
scope, hidden sessions, and format changes better than filesystem guesses.
Inspect files only when the picker cannot answer the question.

## Route by intent

1. Identify the harness from the command, process, or storage path. Do not
   assume every JSONL file is a Pi session.
2. Establish the **project directory**. Pi, Devin, Command Code, and Freebuff
   all scope normal history discovery by working directory or project.
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

Read only the matching reference before giving commands or inspecting storage:

- [Pi](references/pi.md)
- [Devin](references/devin.md)
- [Command Code](references/commandcode.md)
- [Freebuff](references/freebuff.md)

## Helper scripts

The helpers are read-only, emit bounded structured output, and never resume or
delete sessions:

- `scripts/find_sessions.py` — list/filter candidates across harnesses. It uses
  metadata and first-prompt previews; for Devin it calls the official
  `devin list --format json` interface.
- `scripts/inspect_session.py` — inspect one Pi/Command Code transcript or
  Freebuff chat directory, returning metadata and a limited number of user
  prompt previews.
- `scripts/search_session.py` — normalize and filter one local transcript by
  `user`, `assistant`, `thinking`, `tool`, `tool_call`, or `tool_result`;
  optionally filter exact tool names and preview text. It supports Pi, Command
  Code, and Freebuff. Devin has no local transcript/export interface in this
  skill, so do not scrape its private database for message bodies.

Run them from the skill directory with `uv`:

```bash
uv run scripts/find_sessions.py --harness pi --query 'webhook retries'
uv run scripts/find_sessions.py --harness devin --project /path/to/repo --format tsv
uv run scripts/inspect_session.py /path/to/session.jsonl --max-prompts 3
uv run scripts/search_session.py /path/to/session.jsonl --type user --query migration
uv run scripts/search_session.py /path/to/session.jsonl --type tool --tool bash --limit 20
```

Tool calls and tool results are separate records; `--type tool` includes both.
Repeat `--type` or `--tool` to combine filters. Use `--offset` for pagination
and `--preview-chars` to adjust bounded snippets. Exit code `3` means no
candidates/events matched. Exit code `2` means discovery or parsing failed;
when cross-harness discovery cannot query Devin, it fails rather than returning
an incomplete result. Diagnostics go to stderr; JSON/JSONL/TSV data stays clean
on stdout.
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

1. Search the built-in picker/list first; prefer titles and first-prompt
   previews over transcript content.
2. Widen to other projects only if no match appears.
3. If disk search is necessary, run `scripts/find_sessions.py` before writing
   ad-hoc shell pipelines. Search metadata or filenames before full transcripts.
   Session transcripts can contain private prompts, source code, tool output,
   and credentials.
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
