#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read-only access to the ZCode session store (SQLite).

ZCode keeps every session — messages, tool calls, reasoning — in a single
SQLite database at ``~/.zcode/cli/db/db.sqlite`` (WAL mode), not in
per-session transcript files. Verified against schema written by zcode
0.16.x–0.17.0:

- ``session``: id, slug, title, directory (project cwd), parent_id,
  time_created/time_updated (ms epoch), time_archived, time_deleted.
  Subagent runs are ordinary session rows whose slug starts with
  ``sess_subagent``; forks and side-chats also carry parent_id but are
  user-facing, so subagents are excluded by slug, never by parent_id.
- ``message``: role (user/assistant), sequence, and ``data`` JSON carrying
  provenance under ``model.providerID`` / ``model.modelID``.
- ``part``: per-message content rows. ``data.type`` in text, reasoning,
  tool (single record per call: ``state.input`` arguments, ``state.output``
  result, ``state.status`` completed|error), step-start, step-finish,
  timeline, compaction, file.

Everything here is strictly read-only: connections are opened with
``mode=ro`` and pinned with ``PRAGMA query_only``. A live writer holds the
WAL, so a read-only open can fail when SQLite wants WAL recovery; the
caller-supplied warning hook is invoked and the open is retried with
``immutable=1`` rather than failing discovery outright.

Set ``ZCODE_DB`` to point the helpers at a different database file (tests
use this to inject fixtures).
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Sequence

import search_session as ss  # noqa: E402  (same directory)

ZCODE_DB_ENV = "ZCODE_DB"
SUBAGENT_SLUG_PREFIX = "sess_subagent"

# User-role text parts that zcode injects on its own (tool nudges, queued
# subagent/task notifications, harness context). Skipped when picking a
# *preview* so listings show what the human typed; content search still sees
# them, because search must stay faithful to the transcript.
PREVIEW_BOILERPLATE_PREFIXES = (
    "The TodoWrite tool",
    "The conversations tool",
    "<task-notification>",
    "<subagent-message>",
    "Caveat:",
    "Available agent types",
    "[Request interrupted",
)


def warn_noop(message: str) -> None:  # pragma: no cover - default hook
    pass


def db_path(home: Path | None = None) -> Path:
    override = os.environ.get(ZCODE_DB_ENV)
    if override:
        return Path(override)
    return (home or Path.home()) / ".zcode/cli/db/db.sqlite"


def connect(path: Path, warn: Callable[[str], None] = warn_noop) -> sqlite3.Connection:
    """Open the session store strictly read-only (mode=ro + query_only)."""
    uri = f"file:{path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.execute("PRAGMA query_only = 1")
        conn.execute("SELECT count(*) FROM session").fetchone()
        return conn
    except sqlite3.Error as error:
        # A live writer may hold the WAL; mode=ro then fails if recovery
        # would be needed. immutable=1 skips locking entirely (still no
        # writes) at the risk of a torn read — acceptable for discovery.
        warn(f"zcode db open needed immutable fallback ({path}: {error})")
        conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True, timeout=5.0)
        conn.execute("PRAGMA query_only = 1")
        conn.execute("SELECT count(*) FROM session").fetchone()
        return conn


def ms_to_iso(milliseconds: int | float | None) -> str:
    if not isinstance(milliseconds, (int, float)) or milliseconds <= 0:
        return ""
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).isoformat()


# --- Session rows ------------------------------------------------------------

@dataclass(frozen=True)
class SessionRow:
    id: str
    slug: str
    title: str
    directory: str
    time_created_ms: int
    time_updated_ms: int
    archived: bool
    subagent: bool


def session_rows(conn: sqlite3.Connection, include_subagents: bool = False,
                 include_deleted: bool = False) -> list[SessionRow]:
    """Non-deleted sessions, newest last; subagents excluded unless asked."""
    sql = (
        "SELECT id, slug, title, directory, time_created, time_updated,"
        " time_archived IS NOT NULL, slug LIKE ?,"
        " (time_deleted IS NOT NULL) AS deleted"
        " FROM session"
        f"{' WHERE time_deleted IS NULL' if not include_deleted else ''}"
        " ORDER BY time_updated"
    )
    prefix = SUBAGENT_SLUG_PREFIX + "%"
    rows: list[SessionRow] = []
    for (sid, slug, title, directory, created, updated, archived, subagent,
         deleted) in conn.execute(sql, (prefix,)):
        if deleted and not include_deleted:
            continue
        if subagent and not include_subagents:
            continue
        rows.append(SessionRow(sid, slug or "", title or "", directory or "",
                               int(created or 0), int(updated or 0), bool(archived),
                               bool(subagent)))
    return rows


def resolve_session(conn: sqlite3.Connection, reference: str) -> SessionRow | None:
    """Resolve a full session id or an unambiguous id prefix."""
    reference = reference.strip()
    if not reference:
        return None
    rows = session_rows(conn, include_subagents=True, include_deleted=True)
    for row in rows:
        if row.id == reference:
            return row
    matches = [row for row in rows if row.id.startswith(reference)]
    return matches[0] if len(matches) == 1 else None


def first_user_texts(conn: sqlite3.Connection, session_id: str, limit: int = 1,
                     skip_boilerplate: bool = True) -> list[str]:
    """Earliest human-typed text parts of a session, bounded."""
    sql = (
        "SELECT p.data FROM part p JOIN message m ON m.id = p.message_id"
        " WHERE m.session_id = ? AND json_extract(m.data, '$.role') = 'user'"
        " AND json_extract(p.data, '$.type') = 'text'"
        " ORDER BY m.sequence, p.sequence LIMIT ?"
    )
    texts: list[str] = []
    for (raw,) in conn.execute(sql, (session_id, max(limit * 8, limit))):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        text = data.get("text") if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            continue
        if skip_boilerplate and text.lstrip().startswith(PREVIEW_BOILERPLATE_PREFIXES):
            continue
        texts.append(text)
        if len(texts) >= limit:
            break
    return texts


# --- Event projection ---------------------------------------------------------
# Emits ss.RawEvent tuples so every search helper shares one matcher.

def _model_fields(message_data: dict[str, object]) -> tuple[str, str]:
    model = message_data.get("model")
    provider = model_id = ""
    if isinstance(model, dict):
        raw = model.get("providerID")
        provider = raw if isinstance(raw, str) else ""
        raw = model.get("modelID")
        model_id = raw if isinstance(raw, str) else ""
    return model_id, provider


def zcode_row_events(message_data: dict[str, object],
                     part_data: dict[str, object],
                     message_id: str = "") -> list[ss.RawEvent]:
    """Project one (message, part) pair into normalized raw events."""
    time_field = message_data.get("time")
    timestamp = ms_to_iso(time_field.get("created") if isinstance(time_field, dict) else None)
    if not message_id:
        raw = part_data.get("messageID")
        message_id = raw if isinstance(raw, str) else ""
    model_id, provider = _model_fields(message_data)
    part_type = part_data.get("type")
    events: list[ss.RawEvent] = []
    if part_type == "text":
        text = part_data.get("text")
        if isinstance(text, str) and text.strip():
            role = message_data.get("role")
            kind = "user" if role == "user" else "assistant"
            events.append((kind, message_id, "", text, None, timestamp, model_id, provider))
    elif part_type == "reasoning":
        text = part_data.get("text")
        if isinstance(text, str) and text.strip():
            events.append(("thinking", message_id, "", text, None, timestamp, model_id, provider))
    elif part_type == "tool":
        raw_tool = part_data.get("tool")
        tool_name = raw_tool if isinstance(raw_tool, str) else ""
        raw_call_id = part_data.get("callID")
        call_id = raw_call_id if isinstance(raw_call_id, str) and raw_call_id else message_id
        state = part_data.get("state")
        arguments = state.get("input") if isinstance(state, dict) else None
        events.append(("tool_call", call_id, tool_name,
                       ss.summarize_tool_call(tool_name, arguments), arguments,
                       timestamp, model_id, provider))
        output = state.get("output") if isinstance(state, dict) else None
        if output is not None and not (isinstance(output, str) and not output.strip()):
            events.append(("tool_result", call_id, tool_name, output, None,
                           timestamp, model_id, provider))
    return events


def _iter_rows(conn: sqlite3.Connection, session_id: str) -> Iterator[tuple[dict[str, object], dict[str, object], str, int, int]]:
    sql = (
        "SELECT m.data, p.data, m.id, m.sequence, p.sequence"
        " FROM message m JOIN part p ON p.message_id = m.id"
        " WHERE m.session_id = ?"
        " ORDER BY m.sequence, p.sequence, p.time_created"
    )
    for raw_message, raw_part, message_id, message_sequence, part_sequence in conn.execute(sql, (session_id,)):
        try:
            message_data = json.loads(raw_message)
            part_data = json.loads(raw_part)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(message_data, dict) and isinstance(part_data, dict):
            yield message_data, part_data, str(message_id or ""), int(message_sequence or 0), int(part_sequence or 0)


def zcode_events(conn: sqlite3.Connection, session_id: str) -> Iterator[ss.Event]:
    """Full normalized event stream for one zcode session."""
    index = 0
    for message_data, part_data, message_id, message_sequence, part_sequence in _iter_rows(conn, session_id):
        for kind, event_id, tool, text, arguments, timestamp, model, provider in zcode_row_events(
                message_data, part_data, message_id):
            yield ss.make_event(index, kind, timestamp, event_id, tool, text, arguments,
                                model=model, provider=provider,
                                source_ref=f"msg {message_sequence} part {part_sequence}")
            index += 1


def zcode_session_events(db: Path, reference: str,
                         warn: Callable[[str], None] = warn_noop) -> Iterator[ss.Event]:
    """Resolve a session id/prefix and stream its events, closing the store."""
    conn = connect(db, warn)
    try:
        row = resolve_session(conn, reference)
        if row is None:
            raise ValueError(f"no zcode session matches {reference!r} in {db}")
        yield from zcode_events(conn, row.id)
    finally:
        conn.close()


# --- Search support -----------------------------------------------------------

def matching_part_rows(conn: sqlite3.Connection, needle: str,
                       since_ms: int | None = None,
                       project_substr: str = "",
                       include_subagents: bool = False
                       ) -> Iterator[tuple[SessionRow, dict[str, object], dict[str, object], str, int, int]]:
    """Yield (session, message, part, message_id, seqs) pairs whose raw part
    JSON could contain ``needle`` (SQL LIKE prefilter), newest sessions first.

    An empty needle yields every part of every candidate session: callers use
    it for type-only searches where Python-side matching decides.
    """
    conditions = ["s.time_deleted IS NULL"]
    params: list[object] = []
    if not include_subagents:
        conditions.append("s.slug NOT LIKE ?")
        params.append(SUBAGENT_SLUG_PREFIX + "%")
    if since_ms is not None:
        conditions.append("s.time_updated >= ?")
        params.append(since_ms)
    if project_substr:
        conditions.append("lower(s.directory) LIKE ?")
        params.append(f"%{project_substr.casefold()}%")
    if needle:
        # Mirrors the byte prefilter's contract: only reject a row when
        # decoding cannot introduce a match. ASCII-case-insensitive LIKE can
        # miss (a) JSON \uXXXX escapes of ASCII letters and (b) non-ASCII
        # text whose casefold maps onto the needle (ſ -> s, ß -> ss), so
        # either shape is accepted and Python matching decides.
        conditions.append("(lower(p.data) LIKE ? OR p.data LIKE ? OR p.data GLOB '*[^ -~]*')")
        params.append(f"%{needle.casefold()}%")
        params.append("%\\u%")
    sql = (
        "SELECT s.id, s.slug, s.title, s.directory, s.time_created, s.time_updated,"
        " s.time_archived IS NOT NULL, m.data, p.data, m.id, m.sequence, p.sequence"
        " FROM part p"
        " JOIN message m ON m.id = p.message_id"
        " JOIN session s ON s.id = m.session_id"
        " WHERE " + " AND ".join(conditions) +
        " ORDER BY s.time_updated DESC, m.sequence, p.sequence"
    )
    for (sid, slug, title, directory, created, updated, archived,
         raw_message, raw_part, message_id, message_sequence, part_sequence) in conn.execute(sql, params):
        try:
            message_data = json.loads(raw_message)
            part_data = json.loads(raw_part)
        except (json.JSONDecodeError, TypeError):
            continue
        if not (isinstance(message_data, dict) and isinstance(part_data, dict)):
            continue
        row = SessionRow(sid, slug or "", title or "", directory or "",
                         int(created or 0), int(updated or 0), bool(archived), False)
        yield row, message_data, part_data, str(message_id or ""), int(message_sequence or 0), int(part_sequence or 0)


def tool_activity_summary(conn: sqlite3.Connection, session_id: str,
                          files_cap: int = 50) -> dict[str, object]:
    """Bounded tool-call summary: counts by tool plus files touched."""
    counts: dict[str, int] = {}
    files: list[str] = []
    for message_data, part_data, _message_id, _msg_seq, _part_seq in _iter_rows(conn, session_id):
        if part_data.get("type") != "tool":
            continue
        tool_name = part_data.get("tool")
        tool_name = tool_name if isinstance(tool_name, str) else "?"
        counts[tool_name] = counts.get(tool_name, 0) + 1
        state = part_data.get("state")
        if not isinstance(state, dict):
            continue
        arguments = state.get("input")
        if not isinstance(arguments, dict):
            continue
        for key in ("file_path", "path", "notebook_path"):
            value = arguments.get(key)
            if isinstance(value, str) and value and value not in files:
                files.append(value)
                break
        else:
            continue
        if len(files) >= files_cap:
            break
    note = f"capped at {files_cap}" if len(files) >= files_cap else ""
    return {"tool_call_summary": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "files_touched": files, "files_touched_note": note}


def inspect(conn: sqlite3.Connection, reference: str,
            max_prompts: int, preview_chars: int, source: str) -> dict[str, object]:
    """Bounded inspection of one zcode session."""
    row = resolve_session(conn, reference)
    if row is None:
        raise ValueError(f"no zcode session matches {reference!r}")
    count_sql = ("SELECT count(*), min(time_created), max(time_created)"
                 " FROM message WHERE session_id = ?")
    messages, first_ms, last_ms = conn.execute(count_sql, (row.id,)).fetchone()
    prompts = [ss.clean(text)[:preview_chars]
               for text in first_user_texts(conn, row.id, limit=max_prompts)]
    info: dict[str, object] = {
        "harness": "zcode",
        "id": row.id,
        "title": ss.clean(row.title)[:200],
        "project": row.directory,
        "archived": row.archived,
        "subagent": row.subagent,
        "message_records": int(messages or 0),
        "duration_seconds": round((int(last_ms or 0) - int(first_ms or 0)) / 1000, 1) or 0,
        "user_prompt_previews": prompts,
        "resume_command": f"zcode --resume {row.id}",
        "source": source,
    }
    info.update(tool_activity_summary(conn, row.id))
    return info


def iter_candidates(db: Path, warn: Callable[[str], None] = warn_noop
                    ) -> tuple[sqlite3.Connection, list[SessionRow]]:
    conn = connect(db, warn)
    return conn, session_rows(conn)
