#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search message and tool content across ALL local sessions at once.

Discovers Pi, Claude Code, Devin, Command Code, and Freebuff transcripts on disk, applies a
cheap byte-level prefilter per line/file, and only parses content that could
match. Each matching session is reported with bounded excerpts, provenance
(model/provider/source position), and a resume command when one is safe.

Read-only: never prints complete transcripts and never resumes a session.
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import re
import shlex
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import claude_sessions  # noqa: E402  (same directory)
import scoping  # noqa: E402  (same directory)
import search_session as ss  # noqa: E402  (same directory)
import zcode_store  # noqa: E402  (same directory)

HARNESSES = ("pi", "claude", "devin", "commandcode", "freebuff", "zcode")
Projector = Callable[[dict[str, object]], list[ss.RawEvent]]
# Factories, because some projectors carry per-file state (Claude pairs
# tool_result events to their tool_use name).
PROJECTOR_FACTORIES: dict[str, Callable[[], Projector]] = {
    "pi": lambda: ss.pi_record_events,
    "claude": ss.claude_projector,
    "commandcode": lambda: ss.commandcode_record_events,
}


WARNINGS = 0  # diagnostics emitted this run; reported so partial coverage is visible


def warn(message: str) -> None:
    global WARNINGS
    WARNINGS += 1
    print(f"warning: {message}", file=sys.stderr)


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def iso_event_timestamp(raw: str) -> str:
    """Render compacted event timestamps: epoch digits become ISO, else passthrough."""
    text = raw.strip()
    if text.isdigit():
        value = int(text)
        try:
            if value > 10**12:
                return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
            if value > 10**9:
                return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            pass  # out of datetime's range: report the raw digits, never crash a search
        return text
    return text


def shell_command(*arguments: str) -> str:
    return " ".join(shlex.quote(argument) for argument in arguments)


@dataclass(frozen=True)
class FileEntry:
    harness: str
    path: Path
    size: int


@dataclass
class Hit:
    kind: str
    tool: str
    timestamp: str
    model: str
    provider: str
    source_ref: str
    excerpt: str
    paired: dict[str, object] = field(default_factory=dict)  # --with-result fields


@dataclass
class SessionMatch:
    harness: str
    path: Path
    size: int
    updated_at: str
    session_id: str = ""
    project: str = ""
    title: str = ""
    resume_command: str = ""
    hits: list[Hit] = field(default_factory=list)
    hits_capped: bool = False  # stopped at --max-hits; more may exist


def enumerate_pi(home: Path) -> Iterator[FileEntry]:
    root = Path(os.environ.get("PI_CODING_AGENT_SESSION_DIR", home / ".pi/agent/sessions"))
    if not root.is_dir():
        return
    for path in root.rglob("*.jsonl"):
        yield FileEntry("pi", path, path.stat().st_size)


def enumerate_claude(home: Path) -> Iterator[FileEntry]:
    for path in claude_sessions.transcripts(home):
        yield FileEntry("claude", path, path.stat().st_size)


def enumerate_devin(home: Path) -> Iterator[FileEntry]:
    root = home / ".local/share/devin/cli/transcripts"
    if not root.is_dir():
        return
    for path in root.glob("*.json"):
        if path.name.startswith("."):
            continue
        yield FileEntry("devin", path, path.stat().st_size)


def enumerate_commandcode(home: Path) -> Iterator[FileEntry]:
    root = home / ".commandcode/projects"
    if not root.is_dir():
        return
    for path in root.glob("*/*.jsonl"):
        if any(path.name.endswith(suffix) for suffix in (".checkpoints.jsonl", ".prompts.jsonl")):
            continue
        yield FileEntry("commandcode", path, path.stat().st_size)


def enumerate_freebuff(home: Path) -> Iterator[FileEntry]:
    root = home / ".config/manicode/projects"
    if not root.is_dir():
        return
    for path in root.glob("*/chats/*/chat-messages.json"):
        yield FileEntry("freebuff", path, path.stat().st_size)


ENUMERATORS: dict[str, Callable[[Path], Iterator[FileEntry]]] = {
    "pi": enumerate_pi,
    "claude": enumerate_claude,
    "devin": enumerate_devin,
    "commandcode": enumerate_commandcode,
    "freebuff": enumerate_freebuff,
}


def parse_since(value: str) -> float:
    """Cutoff epoch seconds: '30d'/'12h'/'4w'/'6mo'/'1y' or an ISO date/datetime."""
    text = value.strip().lower()
    match = re.fullmatch(r"(\d+)(h|d|w|mo|y)", text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        seconds = {"h": 3600, "d": 86_400, "w": 7 * 86_400, "mo": 30 * 86_400, "y": 365 * 86_400}[unit]
        return time.time() - amount * seconds
    try:
        parsed = datetime.fromisoformat(text.replace("z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"invalid --since value: {value!r} (use e.g. 30d, 12h, 4w, 6mo, 1y, or 2026-10-01)"
        ) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


# Non-ASCII characters whose casefold/lower/upper contains ASCII (ſ -> s,
# K (Kelvin) -> k, ß -> ss, ﬁ -> fi, ...). Only these, or a JSON \u escape,
# can put an ASCII anchor into decoded, case-folded text without it being
# in the raw bytes. test_fold_to_ascii_set_is_complete recomputes the set.
FOLDS_TO_ASCII = "\u00df\u0130\u0131\u0149\u017f\u01f0\u1e96\u1e97\u1e98\u1e99\u1e9a\u1e9e\u212a\ufb00\ufb01\ufb02\ufb03\ufb04\ufb05\ufb06"  # escaped: editors and tools NFKC-normalize U+212A to K


def _fold_letters(char: str) -> set[str]:
    return {letter.lower() for form in (char.casefold(), char.lower(), char.upper())
            for letter in form if letter.isascii()}


def relevant_folds(words: Iterable[str]) -> list[bytes]:
    """UTF-8 of the folding characters that could supply a letter of an anchor.

    ſ only matters to an anchor containing 's'; for 'herdr' only ẖ does.
    """
    letters = {letter for word in words for letter in word.lower()}
    return [char.encode() for char in FOLDS_TO_ASCII if _fold_letters(char) & letters]
# A JSON \u escape matters only if it decodes to printable ASCII or to one of
# the folding characters; control escapes (\u001b in ANSI tool output) and
# other non-ASCII text cannot form an ASCII word.
_UNICODE_ESCAPE = re.compile(
    rb"\\u(?:00[2-7][0-9a-f]|" + b"|".join(f"{ord(char):04x}".encode() for char in FOLDS_TO_ASCII) + rb")",
    re.IGNORECASE)

# Tool summaries can contain words not present in the encoded arguments (e.g.
# "workdir" synthesized from a "cwd" key, or a todo count). Tool-call records
# must be projected whenever an anchor could come from that synthetic text.
TOOL_MARKERS = (b'"toolCall"', b'"tool-call"', b'"tool_calls"', b'"tool"')


def _could_be_synthetic(word: str) -> bool:
    return word.isdigit() or any(word in label for label in ss.SUMMARY_LABELS)
_WORD = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class Prefilter:
    """A conservative byte-level test: False only when a record cannot match.

    ``groups`` is an AND of OR-groups of lower-cased ASCII words. Every word of
    a ``--query`` phrase is its own group (the phrase's event lives in one
    record, so all its words do); a regex alternation is one group; repeated
    ``--tool`` names are one group. Rejecting a record needs no group satisfied
    by any escape/fold/marker route that decoding could open up.
    """
    groups: list[tuple[bytes, ...]]
    markers: list[re.Pattern[bytes]] = field(default_factory=list)
    tool_lines: bool = True  # parse every tool-call record (anchors may be synthetic)
    folds: list[bytes] = field(default_factory=lambda: [char.encode() for char in FOLDS_TO_ASCII])

    @property
    def words(self) -> list[bytes]:
        return sorted({word for group in self.groups for word in group})

    @property
    def parse_all(self) -> bool:
        # Type-only, empty, punctuation-only, and non-ASCII-only filters have
        # no safe anchor. They must parse, not reject, every candidate record.
        return not self.groups

    def might_match(self, raw: bytes, lowered: bytes | None = None, markers: bool = True) -> bool:
        """``lowered`` is ``raw.lower()`` when the caller already has it.

        ``markers=False`` tests a whole file: structural markers only admit
        lines of files that already hold an anchor elsewhere (a Claude result
        is named by its tool_use line), so they never rescue a whole file.
        """
        if self.parse_all:
            return True
        # Cheap substring tests gate the slower checks: most lines have neither.
        if b"\\u" in raw and _UNICODE_ESCAPE.search(raw):
            return True
        if self.folds and not raw.isascii() and any(fold in raw for fold in self.folds):
            return True
        if self.tool_lines and any(marker in raw for marker in TOOL_MARKERS):
            return True
        if lowered is None:
            lowered = raw.lower()
        if all(any(word in lowered for word in group) for group in self.groups):
            return True
        return markers and any(marker.search(raw) for marker in self.markers)

    def with_markers(self, *patterns: bytes) -> "Prefilter":
        return Prefilter(self.groups, [*self.markers, *(re.compile(p) for p in patterns)],
                         self.tool_lines, self.folds)


def _longest_word(text: str) -> str:
    words = _WORD.findall(text) if text.isascii() else []
    return max(words, key=len) if words else ""


def _op_name(op: object) -> str:
    return str(getattr(op, "name", op))


def _sequence_anchors(items: Iterable[object]) -> frozenset[str] | None:
    """Words one of which every match of this parsed regex sequence contains."""
    best: frozenset[str] | None = None
    run: list[str] = []

    def consider(candidate: frozenset[str] | None) -> None:
        nonlocal best
        if not candidate:
            return
        score = (min(len(word) for word in candidate), -len(candidate))
        if best is None or score > (min(len(word) for word in best), -len(best)):
            best = candidate

    def flush() -> None:
        word = _longest_word("".join(run))
        if word:
            consider(frozenset({word}))
        run.clear()

    for item in items:
        if not (isinstance(item, tuple) and len(item) == 2):
            return None
        op, value = item
        name = _op_name(op)
        if name == "LITERAL" and isinstance(value, int):
            run.append(chr(value))
            continue
        flush()
        if name == "SUBPATTERN" and isinstance(value, tuple):
            consider(_sequence_anchors(value[-1]))
        elif name == "ATOMIC_GROUP":
            consider(_sequence_anchors(value))
        elif name in ("MAX_REPEAT", "MIN_REPEAT", "POSSESSIVE_REPEAT") and isinstance(value, tuple) \
                and isinstance(value[0], int) and value[0] >= 1:
            consider(_sequence_anchors(value[2]))
        elif name == "ASSERT" and isinstance(value, tuple):
            consider(_sequence_anchors(value[1]))  # positive lookaround text is still present
        elif name == "BRANCH" and isinstance(value, tuple):
            alternatives = [_sequence_anchors(branch) for branch in value[1]]
            if alternatives and all(alternatives):
                consider(frozenset().union(*(a for a in alternatives if a)))
    flush()
    return best


def regex_anchor_words(pattern: re.Pattern[str]) -> frozenset[str] | None:
    """ASCII words one of which any match must contain, or None if unknown."""
    try:
        parser = importlib.import_module("re._parser")
        parsed = parser.parse(pattern.pattern, pattern.flags)
        return _sequence_anchors(list(parsed))
    except Exception:  # private-module drift must cost speed, never matches
        return None


def _ascii_words(text: str) -> list[str]:
    return _WORD.findall(text) if text.isascii() else []


def build_prefilter(text_filter: ss.TextFilter, tools: Sequence[str],
                    tool_args: Sequence[tuple[str, str]]) -> Prefilter:
    """Necessary anchors from every filter, as AND-of-OR groups.

    A phrase need not appear literally in JSON (whitespace is normalized after
    decoding, text blocks are joined), but each of its words must.
    """
    groups: set[tuple[str, ...]] = set()
    for text in (*text_filter.terms, *(value for _, value in tool_args)):
        groups.update((word.lower(),) for word in _ascii_words(text.strip()))
    tool_words = [_longest_word(tool.strip()) for tool in tools]
    if tool_words and all(tool_words):
        groups.add(tuple(sorted({word.lower() for word in tool_words})))
    for pattern in text_filter.patterns:
        anchors = regex_anchor_words(pattern)
        if anchors:
            groups.add(tuple(sorted({word.lower() for word in anchors})))
    words = {word for group in groups for word in group}
    return Prefilter([tuple(word.encode() for word in group) for group in sorted(groups)],
                     tool_lines=any(_could_be_synthetic(word) for word in words),
                     folds=relevant_folds(words))


def pi_session_metadata(path: Path) -> tuple[str, str, str]:
    """Session id, project cwd, and title from the head of a Pi session file."""
    session_id = path.stem.rsplit("_", 1)[-1]
    project = ""
    title = ""
    try:
        with path.open(encoding="utf-8") as handle:
            for count, line in enumerate(handle):
                if count >= 20:
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("type") == "session":
                    value = record.get("id")
                    if isinstance(value, str) and value:
                        session_id = value
                    value = record.get("cwd")
                    if isinstance(value, str):
                        project = " ".join(value.split())[:500]
                elif record.get("type") == "session_info":
                    value = record.get("name")
                    if isinstance(value, str) and value and not title:
                        title = " ".join(value.split())[:200]
    except OSError as error:
        warn(f"cannot read {path}: {error}")
    return session_id, project, title


def claude_session_metadata(path: Path) -> tuple[str, str, str]:
    meta = claude_sessions.read_meta(path)
    return meta.session_id, meta.cwd, meta.title


def commandcode_session_metadata(path: Path) -> tuple[str, str, str]:
    session_id = path.stem
    project = path.parent.name
    title = ""
    meta_path = path.with_name(f"{session_id}.meta.json")
    if meta_path.is_file():
        try:
            value = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("title"), str):
                title = " ".join(value["title"].split())[:200]
        except (OSError, json.JSONDecodeError):
            pass
    return session_id, project, title


def resume_command(harness: str, path: Path, session_id: str, project: str = "") -> str:
    if harness == "pi":
        return shell_command("pi", "--session", str(path))
    if harness == "claude":
        return claude_sessions.resume_command(session_id, project)
    if harness == "commandcode":
        return shell_command("cmd", "--session", str(path))
    if harness == "devin" and session_id:
        return shell_command("devin", "-r", session_id)
    if harness == "zcode" and session_id:
        return shell_command("zcode", "--resume", session_id)
    # Freebuff's on-disk project key is only a basename, so a bare resume
    # command could target the wrong project; deliberately omitted.
    return ""


class Matcher:
    def __init__(self, args: argparse.Namespace) -> None:
        self.wanted = ss.wanted_kinds(args.types)
        self.tools = {tool.casefold() for tool in args.tool}
        self.text = ss.TextFilter.build(args.query, getattr(args, "regex", ()) or ())
        self.tool_arg_filters = args.tool_arg

    @property
    def query(self) -> ss.TextFilter:
        return self.text

    def matches(self, item: ss.Event) -> bool:
        return ss.event_matches(item, self.wanted, self.tools, self.text, self.tool_arg_filters)


# Result records, per harness, so --with-result can find a call's outcome
# even when the result line itself holds none of the search words.
RESULT_MARKERS = (rb'"toolResult"', rb'"type":\s*"tool_result"', rb'"tool-result"', rb'"bashExecution"')


class HitCollector:
    """Keep the first ``max_hits`` matching events of one transcript and, with
    pairing on, keep reading only until their tool results are found."""

    def __init__(self, matcher: Matcher, max_hits: int, preview_chars: int, with_result: bool) -> None:
        self.matcher = matcher
        self.max_hits = max_hits
        self.preview_chars = preview_chars
        self.events: list[ss.Event] = []
        self.pairer = ss.Pairer(preview_chars) if with_result else None

    @property
    def full(self) -> bool:
        return len(self.events) >= self.max_hits

    @property
    def done(self) -> bool:
        return self.full and (self.pairer is None or not self.pairer.pending())

    def needs_line(self, raw: bytes) -> bool:
        """After the hit cap, only lines naming a still-pending call id matter."""
        if self.pairer is None:
            return False
        return any(call_id.encode() in raw for call_id in self.pairer.pending_ids())

    def add(self, item: ss.Event) -> bool:
        """Consume one event; True once nothing more is needed from this file."""
        if self.pairer is not None:
            self.pairer.observe(item)
        if not self.full and self.matcher.matches(item):
            self.events.append(item)
            if self.pairer is not None:
                self.pairer.want(item)
        return self.done

    def hits(self) -> list[Hit]:
        out: list[Hit] = []
        for item in self.events:
            out.append(Hit(
                kind=item.kind, tool=item.tool,
                timestamp=iso_event_timestamp(item.timestamp),
                model=item.model, provider=item.provider, source_ref=item.source_ref,
                excerpt=ss._event_preview(item, extract=False, query=self.matcher.text,
                                          max_chars=self.preview_chars),
                paired=self.pairer.fields(item) if self.pairer is not None else {},
            ))
        return out


def collect_hits(entry: FileEntry, matcher: Matcher, prefilter: Prefilter,
                 max_hits: int, preview_chars: int, with_result: bool = False) -> list[Hit]:
    collector = HitCollector(matcher, max_hits, preview_chars, with_result)
    if with_result and "tool_result" in matcher.wanted and not prefilter.tool_lines:
        # A result hit reports its call, so call records must be read too.
        prefilter = Prefilter(prefilter.groups, prefilter.markers, True, prefilter.folds)
    if entry.harness in PROJECTOR_FACTORIES:
        projector = PROJECTOR_FACTORIES[entry.harness]()
        if entry.harness == "claude" and not prefilter.parse_all and (
                "tool_result" in matcher.wanted or with_result):
            # tool_result lines carry no tool name. Always read tool_use lines
            # so the name is known, and with a --tool filter read the result
            # lines too, since they can't contain the filter word.
            prefilter = prefilter.with_markers(rb'"type":\s*"tool_use"')
            if matcher.tools and "tool_result" in matcher.wanted:
                prefilter = prefilter.with_markers(rb'"type":\s*"tool_result"')
        # Stream lines: transcripts reach hundreds of MiB, and a whole-file
        # copy (plus a lower-cased one) costs more under memory pressure than
        # the per-line test it would save.
        try:
            with entry.path.open("rb") as handle:
                for line_number, raw in enumerate(handle, 1):
                    if collector.full:
                        if not collector.needs_line(raw):
                            continue
                    elif not prefilter.might_match(raw) and not collector.needs_line(raw):
                        continue
                    try:
                        record = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(record, dict):
                        continue
                    for raw_event in projector(record):
                        item = ss.event_from_raw(0, raw_event, f"line {line_number}")
                        if collector.add(item):
                            return collector.hits()
        except OSError as error:
            warn(f"cannot read {entry.path}: {error}")
            return collector.hits()
        return collector.hits()
    else:
        # Devin and Freebuff files are small enough that a whole-file byte
        # prefilter plus a full parse of survivors beats line-level work.
        if not prefilter.parse_all:
            try:
                data = entry.path.read_bytes()
            except OSError as error:
                warn(f"cannot read {entry.path}: {error}")
                return []
            if not prefilter.might_match(data, markers=False):
                return []
        try:
            stream = ss.devin_events(entry.path) if entry.harness == "devin" else ss.freebuff_events(entry.path)
            for item in stream:
                if collector.add(item):
                    break
        except (OSError, json.JSONDecodeError, ValueError) as error:
            warn(f"cannot parse {entry.path}: {error}")
    return collector.hits()


def finalize_session(entry: FileEntry, hits: list[Hit]) -> SessionMatch:
    result = SessionMatch(harness=entry.harness, path=entry.path, size=entry.size,
                          updated_at=iso_mtime(entry.path))
    if entry.harness == "pi":
        result.session_id, result.project, result.title = pi_session_metadata(entry.path)
    elif entry.harness == "claude":
        result.session_id, result.project, result.title = claude_session_metadata(entry.path)
    elif entry.harness == "commandcode":
        result.session_id, result.project, result.title = commandcode_session_metadata(entry.path)
    elif entry.harness == "devin":
        try:
            data = json.loads(entry.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("session_id"), str):
                result.session_id = data["session_id"]
        except (OSError, json.JSONDecodeError):
            pass
    else:  # freebuff: .../projects/<project>/chats/<chat-id>/chat-messages.json
        result.session_id = entry.path.parent.name
        result.project = entry.path.parents[2].name if len(entry.path.parents) >= 3 else ""
    result.resume_command = resume_command(entry.harness, entry.path, result.session_id, result.project)
    result.hits = hits
    return result


def sql_needle(text_filter: ss.TextFilter, tools: Sequence[str],
               tool_args: Sequence[tuple[str, str]]) -> str:
    """A conservative SQL LIKE anchor mirroring build_prefilter's logic.

    The longest ASCII word of the filters must appear literally (modulo
    letter case) in a matching part's JSON. A regex contributes only when one
    word is required on every path (an alternation cannot be one LIKE).
    Unicode-only or empty filters get no anchor and force a full scan.
    """
    candidates = [_longest_word(text.strip())
                  for text in (*text_filter.terms, *tools, *(value for _, value in tool_args))]
    for pattern in text_filter.patterns:
        anchors = regex_anchor_words(pattern)
        if anchors and len(anchors) == 1:
            candidates.extend(anchors)
    return max(candidates, key=len, default="")


def search_zcode(args: argparse.Namespace, home: Path, matcher: Matcher,
                 max_hits: int, preview_chars: int) -> list[SessionMatch]:
    """Query the zcode SQLite store directly instead of scanning files.

    ``--since`` maps to session time_updated (real activity time, not file
    mtime) and ``--project`` matches the session's recorded directory, so
    zcode project scoping is exact rather than a path-substring guess.
    """
    db = zcode_store.db_path(home)
    if not db.is_file():
        # Not installed is not partial coverage: plain note, not a counted warning.
        print(f"note: zcode session store not found at {db}; skipping harness", file=sys.stderr)
        return []
    try:
        conn = zcode_store.connect(db, warn)
    except (sqlite3.Error, OSError) as error:
        warn(f"cannot open zcode session store ({db}): {error}")
        return []
    since_ms = int(args.since * 1000) if args.since is not None else None
    needle = sql_needle(matcher.text, args.tool, args.tool_arg)
    collectors: dict[str, HitCollector] = {}
    meta: dict[str, zcode_store.SessionRow] = {}
    try:
        for row, message_data, part_data, message_id, message_sequence, part_sequence in \
                zcode_store.matching_part_rows(conn, needle, since_ms, args.project):
            collector = collectors.setdefault(
                row.id, HitCollector(matcher, max_hits, preview_chars, args.with_result))
            meta.setdefault(row.id, row)
            if collector.done:
                continue
            # A zcode tool part holds both the call and its output, so
            # pairing never needs rows beyond the matching one.
            for raw_event in zcode_store.zcode_row_events(message_data, part_data, message_id):
                collector.add(ss.event_from_raw(0, raw_event, f"msg {message_sequence} part {part_sequence}"))
    finally:
        conn.close()
    size = db.stat().st_size
    matches: list[SessionMatch] = []
    for row_id, collector in collectors.items():
        session_row = meta.get(row_id)
        if session_row is None or not collector.events:
            continue
        matches.append(SessionMatch(harness="zcode", path=db, size=size,
                                    updated_at=zcode_store.ms_to_iso(session_row.time_updated_ms),
                                    session_id=session_row.id, project=session_row.directory,
                                    title=" ".join(session_row.title.split())[:200],
                                    resume_command=resume_command("zcode", db, session_row.id),
                                    hits=collector.hits(), hits_capped=collector.full))
    return matches


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search message and tool content across all local sessions (Pi, Claude Code, Devin, Command Code, Freebuff, ZCode).",
        epilog=("Examples:\n"
                "  uv run scripts/search_sessions.py --query obelisk\n"
                "  uv run scripts/search_sessions.py --query 'auth bug' --harness pi --harness devin --since 30d\n"
                "  uv run scripts/search_sessions.py --tool edit --tool-arg path=AGENTS.md   # who changed a file\n"
                "  uv run scripts/search_sessions.py --type user --query kwin --project skills --format tsv\n"
                "  uv run scripts/search_sessions.py --query herdr --query 'agent wait' --tool bash --with-result\n"
                "  uv run scripts/search_sessions.py --type user --regex 'wtf|why did you|not what i' --since 30d"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--harness", action="append", choices=("all", *HARNESSES), default=[],
                        help="Restrict to a harness; repeat to combine (default: all)")
    ss.add_text_filter_args(parser)
    parser.add_argument("--type", dest="types", action="append", choices=ss.KINDS,
                        help="Event type; repeat to combine. 'tool' includes calls and results")
    parser.add_argument("--tool", action="append", default=[], help="Exact tool name; repeat to combine")
    parser.add_argument("--tool-arg", action="append", default=[],
                        help="Filter tool calls by key=value in arguments; repeat to combine (partial match for strings)")
    parser.add_argument("--project", default="",
                        help="Case-insensitive substring the transcript path must contain (a real path also "
                             "matches slug-keyed harnesses). Same meaning as find_sessions.py")
    parser.add_argument("--here", action="store_true", help="Shorthand for --project <current directory>")
    parser.add_argument("--since", type=parse_since, default=None,
                        help="Only sessions modified since: 30d, 12h, 4w, 6mo, 1y, or an ISO date")
    parser.add_argument("--limit", type=int, default=20, help="Maximum sessions returned (1-500; default: 20)")
    parser.add_argument("--offset", type=int, default=0,
                        help="Matching sessions to skip, newest first (default: 0); page with next_offset")
    parser.add_argument("--with-result", action="store_true",
                        help="Pair tool_call hits with their result (preview, is_error, elapsed_ms) "
                             "and tool_result hits with their call")
    parser.add_argument("--max-hits", type=int, default=3,
                        help="Excerpts kept per session (1-20; default: 3)")
    parser.add_argument("--preview-chars", type=int, default=300,
                        help="Characters per excerpt (20-2000; default: 300)")
    parser.add_argument("--format", choices=("json", "jsonl", "tsv"), default="json")
    args = parser.parse_args(argv)
    if args.here:
        if args.project:
            parser.error("--here and --project are mutually exclusive")
        args.project = str(Path.cwd())
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if args.offset < 0:
        parser.error("--offset must be non-negative")
    ss.compile_regexes(parser, args)
    if not 1 <= args.max_hits <= 20:
        parser.error("--max-hits must be between 1 and 20")
    if not 20 <= args.preview_chars <= 2000:
        parser.error("--preview-chars must be between 20 and 2000")
    for i, pair in enumerate(args.tool_arg):
        if "=" not in pair:
            parser.error(f"--tool-arg must be key=value: {pair}")
        key, value = pair.split("=", 1)
        args.tool_arg[i] = (key, value.casefold())
    return args


def run(args: argparse.Namespace, home: Path) -> int:
    global WARNINGS
    WARNINGS = 0
    selected = list(HARNESSES) if not args.harness or "all" in args.harness else list(dict.fromkeys(args.harness))
    matcher = Matcher(args)
    prefilter = build_prefilter(matcher.text, args.tool, args.tool_arg)
    parse_all = prefilter.parse_all

    file_harnesses = [harness for harness in selected if harness != "zcode"]
    entries: list[FileEntry] = []
    for harness in file_harnesses:
        entries.extend(ENUMERATORS[harness](home))
    if args.since is not None:
        entries = [entry for entry in entries if entry.path.stat().st_mtime >= args.since]
    if args.project:
        entries = [entry for entry in entries if scoping.project_matches(args.project, str(entry.path))]

    total_bytes = sum(entry.size for entry in entries)
    scope = ", ".join(selected)
    if "zcode" in selected:
        scope += " (zcode queries its SQLite session store directly)"
    print(f"searching {len(entries)} files ({total_bytes / 2**20:.1f} MiB) across {scope}"
          + ("; no text needle, full-parsing every file" if parse_all else ""), file=sys.stderr)

    matches: list[SessionMatch] = []
    if "zcode" in selected:
        matches.extend(search_zcode(args, home, matcher, args.max_hits, args.preview_chars))
    started = time.monotonic()
    for entry in entries:
        hits = collect_hits(entry, matcher, prefilter, args.max_hits, args.preview_chars, args.with_result)
        if hits:
            match = finalize_session(entry, hits)
            match.hits_capped = len(hits) >= args.max_hits
            matches.append(match)
    elapsed_s = time.monotonic() - started
    matches.sort(key=lambda match: match.updated_at, reverse=True)
    total_matches = len(matches)
    matches = matches[args.offset: args.offset + args.limit]
    end = args.offset + len(matches)
    truncated = end < total_matches
    capped = sum(1 for match in matches if match.hits_capped)
    hints: list[str] = []
    if truncated:
        hints.append(f"{total_matches - end} more matching sessions not shown: continue with --offset {end}, "
                     "raise --limit (max 500), or narrow with --since/--project/--harness/--tool")
    if capped:
        hints.append(f"{capped} session(s) stopped at --max-hits {args.max_hits} and may have more hits: "
                     "raise --max-hits or open one with search_session.py")
    if WARNINGS:
        hints.append(f"{WARNINGS} warning(s) on stderr (unreadable files or skipped stores): coverage may be partial")
    shown = f"{len(matches)} of {total_matches}" if truncated or args.offset else f"{len(matches)}"
    print(f"{shown} session(s) matched in {elapsed_s:.1f}s", file=sys.stderr)
    for hint in hints:
        print(f"note: {hint}", file=sys.stderr)

    def session_dict(match: SessionMatch) -> dict[str, object]:
        return {
            "harness": match.harness,
            "session_id": match.session_id,
            "project": match.project,
            "title": match.title,
            "path": str(match.path),
            "updated_at": match.updated_at,
            "resume_command": match.resume_command,
            "hits_capped": match.hits_capped,
            "hits": [hit_dict(hit) for hit in match.hits],
        }

    if args.format == "json":
        summary: dict[str, object] = {
            "harnesses": selected, "files_scanned": len(entries),
            "total_matches": total_matches, "offset": args.offset, "returned": len(matches),
            "truncated": truncated}
        if truncated:
            summary["next_offset"] = end
        json.dump({**summary, "warnings": WARNINGS, "hints": hints,
                   "sessions": [session_dict(match) for match in matches]},
                  sys.stdout, indent=2, ensure_ascii=False)
        print()
    elif args.format == "jsonl":
        for match in matches:
            print(json.dumps(session_dict(match), ensure_ascii=False))
    else:
        columns = ["harness", "session_id", "project", "path", "updated_at", "resume_command",
                   "kind", "tool", "timestamp", "model", "provider", "source_ref", "excerpt"]
        if args.with_result:
            columns.extend(ss.PAIR_TSV_FIELDS)
        writer = csv.DictWriter(sys.stdout, fieldnames=columns, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for match in matches:
            for hit in match.hits:
                row = {"harness": match.harness, "session_id": match.session_id,
                       "project": match.project, "path": str(match.path),
                       "updated_at": match.updated_at, "resume_command": match.resume_command,
                       **hit_dict(hit), **ss.pair_tsv_fields(hit.paired)}
                writer.writerow(row)
    return 0 if matches else 3

def hit_dict(hit: Hit) -> dict[str, object]:
    row: dict[str, object] = {name: value for name, value in vars(hit).items() if name != "paired"}
    row.update(hit.paired)
    return row


def main(argv: Sequence[str] | None = None) -> int:
    return run(parse_args(argv or sys.argv[1:]), Path.home())


if __name__ == "__main__":
    raise SystemExit(main())
