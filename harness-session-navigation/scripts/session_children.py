#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List the child agent sessions an orchestrator transcript observed or drove.

Herdr results in an orchestrator's tool output carry pane objects
(``{"agent": "devin", "agent_session": {"kind": "id", "value": ...},
"cwd": ..., "pane_id": ...}``). Each distinct agent becomes a child, resolved
to a transcript when possible:

- ``agent_session`` present → resolved by id or path (``resolution: agent_session``)
- absent (Claude panes usually) → transcripts of that harness whose recorded
  cwd equals the pane's cwd and whose activity overlaps the time the
  orchestrator saw the pane (``resolution: inferred``; every candidate listed)

``driven_calls`` counts the orchestrator's own tool calls that name the
child's pane id, terminal id, or session value; a pane that only appeared in
an ``agent list`` has 0. Read-only; never resumes anything.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import find_sessions  # noqa: E402  (same directory)
import search_session as ss  # noqa: E402  (same directory)
import session_cache  # noqa: E402  (same directory)

# Herdr agent label -> this skill's harness name.
AGENT_HARNESS = {
    "pi": "pi", "claude": "claude", "devin": "devin", "piz": "zcode", "zcode": "zcode",
    "command-code": "commandcode", "commandcode": "commandcode", "cmd": "commandcode",
    "freebuff": "freebuff",
}
_PANE_KEY = '"pane_id"'
_DECODER = json.JSONDecoder()
_PI_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})-(\d{3})Z_")


@dataclass
class Child:
    agent: str
    session_kind: str
    session_value: str
    cwd: str
    pane_ids: set[str] = field(default_factory=set)
    terminal_ids: set[str] = field(default_factory=set)
    first_seen_ms: float | None = None
    last_seen_ms: float | None = None
    first_seen_ref: str = ""
    observations: int = 0
    driven_calls: int = 0
    first_driven_ref: str = ""
    harness: str = ""
    resolution: str = "unresolved"
    session: dict[str, str] | None = None
    candidates: list[dict[str, str]] = field(default_factory=list)
    note: str = ""

    def key(self) -> tuple[str, ...]:
        if self.session_value:
            return (self.agent, self.session_value)
        terminal = min(self.terminal_ids) if self.terminal_ids else ""
        return (self.agent, terminal or min(self.pane_ids, default=""), self.cwd)

    def seen(self, at_ms: float | None, source_ref: str) -> None:
        self.observations += 1
        if at_ms is None:
            return
        if self.first_seen_ms is None or at_ms < self.first_seen_ms:
            self.first_seen_ms = at_ms
            self.first_seen_ref = source_ref
        if self.last_seen_ms is None or at_ms > self.last_seen_ms:
            self.last_seen_ms = at_ms


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def pane_objects(text: str) -> Iterable[dict[str, object]]:
    """Herdr pane/agent objects embedded anywhere in a tool result's text."""
    position = text.find(_PANE_KEY)
    seen_spans: list[tuple[int, int]] = []
    while position != -1:
        if not any(start <= position < end for start, end in seen_spans):
            brace = position
            for _ in range(30):  # innermost enclosing object is a few braces back at most
                brace = text.rfind("{", max(0, position - 4000), brace)
                if brace == -1:
                    break
                try:
                    value, end = _DECODER.raw_decode(text, brace)
                except json.JSONDecodeError:
                    continue
                if end > position and isinstance(value, dict) and "pane_id" in value:
                    seen_spans.append((brace, end))
                    yield value
                    break
        position = text.find(_PANE_KEY, position + len(_PANE_KEY))


def child_from_pane(pane: dict[str, object]) -> Child | None:
    agent = _text(pane.get("agent"))
    if not agent:
        return None  # a plain shell pane
    session = pane.get("agent_session")
    kind = value = ""
    if isinstance(session, dict):
        kind, value = _text(session.get("kind")), _text(session.get("value"))
    child = Child(agent, kind, value, _text(pane.get("cwd")))
    if _text(pane.get("pane_id")):
        child.pane_ids.add(_text(pane.get("pane_id")))
    if _text(pane.get("terminal_id")):
        child.terminal_ids.add(_text(pane.get("terminal_id")))
    return child


def collect(events: Iterable[ss.Event]) -> tuple[dict[tuple[str, ...], Child], list[tuple[str, str]]]:
    children: dict[tuple[str, ...], Child] = {}
    calls: list[tuple[str, str]] = []  # (source_ref, searchable call text)
    for item in events:
        if item.kind == "tool_call":
            text = ss.compact(item.arguments) if item.arguments is not None else item.preview
            calls.append((item.source_ref, text))
            continue
        if item.kind != "tool_result" or _PANE_KEY not in item.preview:
            continue
        at_ms = ss.parse_time_ms(item.timestamp)
        for pane in pane_objects(item.preview):
            child = child_from_pane(pane)
            if child is None:
                continue
            existing = children.setdefault(child.key(), child)
            if existing is not child:
                existing.pane_ids |= child.pane_ids
                existing.terminal_ids |= child.terminal_ids
            existing.seen(at_ms, item.source_ref)
    return children, calls


def count_driven(children: Iterable[Child], calls: Sequence[tuple[str, str]]) -> None:
    for child in children:
        tokens = [token for token in (*child.pane_ids, *child.terminal_ids, child.session_value) if token]
        for source_ref, text in calls:
            if any(token in text for token in tokens):
                child.driven_calls += 1
                if not child.first_driven_ref:
                    child.first_driven_ref = source_ref


def iso(milliseconds: float | None) -> str:
    if milliseconds is None:
        return ""
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).isoformat()


def describe(candidate: find_sessions.Candidate) -> dict[str, str]:
    return {"harness": candidate.harness, "session_id": candidate.id, "source": candidate.source,
            "project": candidate.project, "title": candidate.title or candidate.preview[:80],
            "updated_at": candidate.updated_at, "resume_command": candidate.resume_command}


def start_ms(candidate: find_sessions.Candidate) -> float | None:
    """When a candidate session began: Pi's filename stamp, else its first timestamp."""
    path = Path(candidate.source)
    match = _PI_STAMP.match(path.name)
    if match:
        date, hour, minute, second, millis = match.groups()
        return ss.parse_time_ms(f"{date}T{hour}:{minute}:{second}.{millis}+00:00")
    if candidate.harness == "claude" and path.is_file():
        for record in find_sessions.iter_jsonl(path, max_lines=50):
            stamp = record.get("timestamp")
            if isinstance(stamp, str):
                return ss.parse_time_ms(stamp)
    return None


class Resolver:
    def __init__(self, home: Path, window_ms: float) -> None:
        self.home = home
        self.window_ms = window_ms
        self._candidates: list[find_sessions.Candidate] | None = None

    def candidates(self) -> list[find_sessions.Candidate]:
        if self._candidates is None:
            cache = session_cache.Cache.load(find_sessions.cache_path(self.home))
            try:
                self._candidates = find_sessions.gather(find_sessions.HARNESSES, "", "auto", self.home, cache)
            finally:
                try:
                    cache.save()
                except OSError as error:
                    print(f"warning: cannot write cache: {error}", file=sys.stderr)
        return self._candidates

    def resolve(self, child: Child) -> None:
        child.harness = AGENT_HARNESS.get(child.agent.casefold(), "")
        if not child.harness:
            child.note = f"agent {child.agent!r} is not a harness this skill reads"
            return
        if child.session_value:
            found = self.by_session(child)
            if found is not None:
                child.resolution, child.session = "agent_session", describe(found)
                return
            child.note = "agent_session value not found on disk; trying cwd + time window"
        self.infer(child)

    def by_session(self, child: Child) -> find_sessions.Candidate | None:
        if child.session_kind == "path":
            path = Path(child.session_value).expanduser()
            if path.is_file() and child.harness == "pi":
                return find_sessions.read_pi_candidate(path)
            if path.is_file() and child.harness == "claude":
                return find_sessions.read_claude_candidate(path)
            return None
        value = child.session_value.casefold()
        matches = [c for c in self.candidates() if c.harness == child.harness and c.id.casefold() == value]
        return matches[0] if len(matches) == 1 else None

    def infer(self, child: Child) -> None:
        if not child.cwd or child.first_seen_ms is None or child.last_seen_ms is None:
            child.note = (child.note + "; " if child.note else "") + "no cwd or timestamps to infer from"
            return
        low, high = child.first_seen_ms - self.window_ms, child.last_seen_ms + self.window_ms
        found: list[find_sessions.Candidate] = []
        for candidate in self.candidates():
            if candidate.harness != child.harness or candidate.project.rstrip("/") != child.cwd.rstrip("/"):
                continue
            updated = ss.parse_time_ms(candidate.updated_at)
            began = start_ms(candidate)
            if updated is not None and updated < low:
                continue  # finished before the orchestrator saw the pane
            if began is not None and began > high:
                continue  # started after the orchestrator last saw it
            found.append(candidate)
        found.sort(key=lambda c: c.updated_at)
        child.candidates = [describe(c) for c in found[:10]]
        if found:
            child.resolution = "inferred"
        if len(found) > 10:
            child.note = (child.note + "; " if child.note else "") + f"{len(found) - 10} more candidates not shown"


def child_dict(child: Child) -> dict[str, object]:
    return {
        "agent": child.agent, "harness": child.harness,
        "agent_session": ({"kind": child.session_kind, "value": child.session_value}
                          if child.session_value else None),
        "cwd": child.cwd, "pane_ids": sorted(child.pane_ids), "terminal_ids": sorted(child.terminal_ids),
        "first_seen": iso(child.first_seen_ms), "last_seen": iso(child.last_seen_ms),
        "first_seen_ref": child.first_seen_ref, "observations": child.observations,
        "driven_calls": child.driven_calls, "first_driven_ref": child.first_driven_ref,
        "resolution": child.resolution, "session": child.session, "candidates": child.candidates,
        "note": child.note,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List child agent sessions an orchestrator transcript observed or drove via herdr.",
        epilog=("Examples:\n"
                "  uv run scripts/session_children.py ~/.pi/agent/sessions/<slug>/<file>.jsonl\n"
                "  uv run scripts/session_children.py 01a19b3a --driven-only --format tsv\n"
                "  uv run scripts/session_children.py <claude-id> --window-minutes 30"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="Orchestrator transcript path or session id (unique prefix)")
    parser.add_argument("--harness", default="auto",
                        choices=("auto", "pi", "claude", "commandcode", "devin", "freebuff", "zcode"))
    parser.add_argument("--driven-only", action="store_true",
                        help="Only children the orchestrator's own tool calls named (driven_calls > 0)")
    parser.add_argument("--window-minutes", type=float, default=10.0,
                        help="Slack around first/last sighting when inferring by cwd (default: 10)")
    parser.add_argument("--no-resolve", action="store_true",
                        help="Skip mapping children to transcripts (no session discovery scan)")
    parser.add_argument("--format", choices=("json", "tsv"), default="json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        source, harness, events = ss.open_events(args.source, args.harness)
        children, calls = collect(events)
    except (OSError, json.JSONDecodeError, ValueError, sqlite3.Error, LookupError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    found = list(children.values())
    count_driven(found, calls)
    if args.driven_only:
        found = [child for child in found if child.driven_calls]
    if not args.no_resolve:
        resolver = Resolver(Path.home(), args.window_minutes * 60_000)
        for child in found:
            resolver.resolve(child)
        # An orchestrator usually lists its own pane too; drop that self-sighting.
        own = str(Path(str(source)).resolve()) if Path(str(source)).exists() else str(source)
        found = [child for child in found if not (child.session and (
            child.session.get("source") in (own, str(source)) or child.session.get("session_id") == str(source)))]
    found.sort(key=lambda child: (-child.driven_calls, child.first_seen_ms or 0.0))
    print(f"{len(found)} child agent(s) in {harness} transcript {source} "
          f"({sum(1 for c in found if c.driven_calls)} driven)", file=sys.stderr)
    rows = [child_dict(child) for child in found]
    if args.format == "json":
        json.dump({"source": str(source), "harness": harness, "total": len(rows), "children": rows},
                  sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        columns = ("agent", "harness", "resolution", "session_id", "source", "cwd", "pane_ids",
                   "first_seen", "last_seen", "observations", "driven_calls", "note")
        writer = csv.DictWriter(sys.stdout, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for child, row in zip(found, rows):
            target = child.session or (child.candidates[0] if len(child.candidates) == 1 else None)
            writer.writerow({
                "agent": child.agent, "harness": child.harness, "resolution": child.resolution,
                "session_id": target.get("session_id", "") if target else "",
                "source": target.get("source", "") if target else f"{len(child.candidates)} candidates",
                "cwd": child.cwd, "pane_ids": ",".join(sorted(child.pane_ids)),
                "first_seen": row["first_seen"], "last_seen": row["last_seen"],
                "observations": child.observations, "driven_calls": child.driven_calls, "note": child.note,
            })
    return 0 if found else 3


if __name__ == "__main__":
    raise SystemExit(main())
