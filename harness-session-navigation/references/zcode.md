# ZCode (`zcode`)

ZCode (Z.AI's coding CLI, tested against 0.16.x–0.17.0) is the odd one out:
it keeps **every session in one SQLite database**, not in transcript files.

- Store: `~/.zcode/cli/db/db.sqlite` (WAL mode; `-wal`/`-shm` siblings)
- Tables that matter:
  - `session` — `id` (`sess_<uuid>`), `slug`, `title`, `directory` (the
    project cwd), `parent_id`, `time_created`/`time_updated` (ms epoch),
    `time_archived`, `time_deleted`
  - `message` — role (`user`/`assistant`), `sequence`, `data` JSON with
    provenance under `model.providerID` / `model.modelID`
  - `part` — per-message content; `data.type` is `text`, `reasoning`, `tool`
    (one record per call: `state.input` arguments, `state.output` result),
    `step-start`, `step-finish`, `timeline`, `compaction`, `file`

## There is no archive directory

"Archived" is just a `time_archived` flag on the session row; deleted sessions
get `time_deleted`. If a conversation is missing from the picker, query the
store — the helpers do exactly that. Subagent runs are ordinary session rows
whose slug starts with `sess_subagent`; there are usually many per real
session, so the helpers **exclude them by default** (forks and side-chats also
carry `parent_id` but remain listed — the slug is the discriminator, never
`parent_id`).

## Commands

| Intent | Command |
|---|---|
| Continue latest in this directory | `zcode -c` |
| Resume by id | `zcode --resume sess_<uuid>` |
| Resume in TUI (omit id = latest in cwd) | `/resume [sessionId]` |
| Fresh session | `/new` |
| Branch from checkpoint | `/fork [latest|checkpointId]` |
| Restore workspace files | `/rewind [latest|checkpointId]` — changes files on disk, not just conversation state; never treat as harmless browsing |
| Compact context | `/compact [instructions]` |

ZCode has no tree view of a session's branches like Pi's `/tree`.

## Helper coverage

All four helpers accept ZCode. Because there are no transcript files, they
query the store **strictly read-only** (`mode=ro` + `query_only`; a WAL held
by a live writer falls back to `immutable=1` with a stderr warning):

- `find_sessions.py --harness zcode` — title, first real prompt (zcode-injected
  boilerplate like TodoWrite nudges and `<task-notification>` blocks is
  skipped for previews), exact project directory, `zcode --resume <id>`
- `search_sessions.py --harness zcode` — SQL LIKE prefilter that mirrors the
  byte prefilter's contract (rows containing `\uXXXX` escapes or any
  non-ASCII text are accepted and matched after decode), provenance from the
  message's model record, `--since` maps to session `time_updated`,
  `--project` matches the recorded directory exactly
- `search_session.py sess_<id-or-prefix>` — full event stream of one session,
  unique id prefixes allowed
- `inspect_session.py sess_<id-or-prefix>` — metadata, prompt previews,
  `tool_call_summary`, `files_touched`, `duration_seconds`

Set `ZCODE_DB=/path/to/db.sqlite` to point the helpers at a different store.

## Cautions

- Never write to the store; a live zcode process owns the WAL. The helpers
  open read-only and never resume or delete anything.
- `~/.zcode/v2/` holds credentials (`credentials.json`) — nothing in this
  skill ever reads that directory.
- Schema verified against zcode 0.16.5–0.17.0. If a future version moves or
  reshapes the tables, expect `find_*`/`search_*` zcode results to vanish (an
  unreadable store is skipped with a warning, never fatal) — re-check
  `sqlite3 'file:~/.zcode/cli/db/db.sqlite?mode=ro' '.schema session'`.
