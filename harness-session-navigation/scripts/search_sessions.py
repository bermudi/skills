#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search message and tool content across ALL local sessions at once.

Discovers Pi, Devin, Command Code, and Freebuff transcripts on disk, applies a
cheap byte-level prefilter per line/file, and only parses content that could
match. Each matching session is reported with bounded excerpts, provenance
(model/provider/source position), and a resume command when one is safe.

Read-only: never prints complete transcripts and never resumes a session.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import search_session as ss  # noqa: E402  (same directory)

HARNESSES = ("pi", "devin", "commandcode", "freebuff")
PROJECTORS: dict[str, Callable[[dict[str, object]], list[ss.RawEvent]]] = {
    "pi": ss.pi_record_events,
    "commandcode": ss.commandcode_record_events,
}


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def iso_event_timestamp(raw: str) -> str:
    """Render compacted event timestamps: epoch digits become ISO, else passthrough."""
    text = raw.strip()
    if text.isdigit():
        value = int(text)
        if value > 10**12:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
        if value > 10**9:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
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


def enumerate_pi(home: Path) -> Iterator[FileEntry]:
    root = Path(os.environ.get("PI_CODING_AGENT_SESSION_DIR", home / ".pi/agent/sessions"))
    if not root.is_dir():
        return
    for path in root.rglob("*.jsonl"):
        yield FileEntry("pi", path, path.stat().st_size)


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


def build_needles(query: str, tools: Sequence[str], tool_args: Sequence[tuple[str, str]]) -> tuple[list[re.Pattern[bytes]], bool]:
    """Byte-level prefilter patterns. Returns (patterns, needs_full_parse).

    A needle is only usable as a byte pattern when it is ASCII; non-ASCII
    needles fall back to full parsing (JSON escaping makes byte matching
    unreliable for them).
    """
    texts = [query, *tools, *(value for _, value in tool_args)]
    patterns: list[re.Pattern[bytes]] = []
    non_ascii = False
    for text in texts:
        if not text:
            continue
        if not text.isascii():
            non_ascii = True
            continue
        variants = {text}
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        variants.add(escaped)
        for variant in variants:
            patterns.append(re.compile(re.escape(variant).encode(), re.IGNORECASE))
    return patterns, non_ascii and not patterns


def scan_jsonl_lines(path: Path, needles: list[re.Pattern[bytes]], parse_all: bool
                     ) -> Iterator[tuple[int, dict[str, object]]]:
    """Yield (line_number, record) for lines that pass the byte prefilter."""
    try:
        with path.open("rb") as handle:
            for line_number, raw in enumerate(handle, 1):
                if not parse_all:
                    if not any(needle.search(raw) for needle in needles):
                        continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    yield line_number, record
    except OSError as error:
        warn(f"cannot read {path}: {error}")


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


def resume_command(harness: str, path: Path, session_id: str) -> str:
    if harness == "pi":
        return shell_command("pi", "--session", str(path))
    if harness == "commandcode":
        return shell_command("cmd", "--session", str(path))
    if harness == "devin" and session_id:
        return shell_command("devin", "-r", session_id)
    # Freebuff's on-disk project key is only a basename, so a bare resume
    # command could target the wrong project; deliberately omitted.
    return ""


class Matcher:
    def __init__(self, args: argparse.Namespace) -> None:
        wanted = set(args.types or ss.KINDS)
        if "tool" in wanted:
            wanted.update(("tool_call", "tool_result"))
        self.wanted = wanted
        self.tools = {tool.casefold() for tool in args.tool}
        self.query = args.query.casefold().strip()
        self.tool_arg_filters = args.tool_arg

    def matches(self, item: ss.Event) -> bool:
        return ss.event_matches(item, self.wanted, self.tools, self.query, self.tool_arg_filters)


def collect_hits(entry: FileEntry, matcher: Matcher, needles: list[re.Pattern[bytes]],
                 parse_all: bool, max_hits: int, preview_chars: int) -> list[Hit]:
    hits: list[Hit] = []
    query = matcher.query

    def record_hit(item: ss.Event) -> bool:
        hits.append(Hit(
            kind=item.kind, tool=item.tool,
            timestamp=iso_event_timestamp(item.timestamp),
            model=item.model, provider=item.provider, source_ref=item.source_ref,
            excerpt=ss._event_preview(item, extract=False, query=query, max_chars=preview_chars),
        ))
        return len(hits) >= max_hits

    if entry.harness in PROJECTORS:
        projector = PROJECTORS[entry.harness]
        index = 0
        for line_number, record in scan_jsonl_lines(entry.path, needles, parse_all):
            for kind, event_id, tool, text, arguments, timestamp, model, provider in projector(record):
                item = ss.make_event(index, kind, timestamp, event_id, tool, text, arguments,
                                     model=model, provider=provider, source_ref=f"line {line_number}")
                index += 1
                if matcher.matches(item) and record_hit(item):
                    return hits
    else:
        # Devin and Freebuff files are small enough that a whole-file byte
        # prefilter plus a full parse of survivors beats line-level work.
        if not parse_all:
            try:
                data = entry.path.read_bytes()
            except OSError as error:
                warn(f"cannot read {entry.path}: {error}")
                return hits
            if not any(needle.search(data) for needle in needles):
                return hits
        stream = ss.devin_events(entry.path) if entry.harness == "devin" else ss.freebuff_events(entry.path)
        try:
            for item in stream:
                if matcher.matches(item) and record_hit(item):
                    return hits
        except (OSError, json.JSONDecodeError, ValueError) as error:
            warn(f"cannot parse {entry.path}: {error}")
    return hits



def finalize_session(entry: FileEntry, hits: list[Hit]) -> SessionMatch:
    result = SessionMatch(harness=entry.harness, path=entry.path, size=entry.size,
                          updated_at=iso_mtime(entry.path))
    if entry.harness == "pi":
        result.session_id, result.project, result.title = pi_session_metadata(entry.path)
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
    result.resume_command = resume_command(entry.harness, entry.path, result.session_id)
    result.hits = hits
    return result


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search message and tool content across all local sessions (Pi, Devin, Command Code, Freebuff).",
        epilog=("Examples:\n"
                "  uv run scripts/search_sessions.py --query obelisk\n"
                "  uv run scripts/search_sessions.py --query 'auth bug' --harness pi --harness devin --since 30d\n"
                "  uv run scripts/search_sessions.py --tool edit --tool-arg path=AGENTS.md   # who changed a file\n"
                "  uv run scripts/search_sessions.py --type user --query kwin --project skills --format tsv"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--harness", action="append", choices=("all", *HARNESSES), default=[],
                        help="Restrict to a harness; repeat to combine (default: all)")
    parser.add_argument("--query", default="", help="Case-insensitive text search over full event text, tool names, and tool-call arguments")
    parser.add_argument("--type", dest="types", action="append", choices=ss.KINDS,
                        help="Event type; repeat to combine. 'tool' includes calls and results")
    parser.add_argument("--tool", action="append", default=[], help="Exact tool name; repeat to combine")
    parser.add_argument("--tool-arg", action="append", default=[],
                        help="Filter tool calls by key=value in arguments; repeat to combine (partial match for strings)")
    parser.add_argument("--project", default="",
                        help="Case-insensitive substring the transcript path must contain (e.g. project directory)")
    parser.add_argument("--since", type=parse_since, default=None,
                        help="Only sessions modified since: 30d, 12h, 4w, 6mo, 1y, or an ISO date")
    parser.add_argument("--limit", type=int, default=20, help="Maximum sessions returned (1-100; default: 20)")
    parser.add_argument("--max-hits", type=int, default=3,
                        help="Excerpts kept per session (1-20; default: 3)")
    parser.add_argument("--preview-chars", type=int, default=300,
                        help="Characters per excerpt (20-2000; default: 300)")
    parser.add_argument("--format", choices=("json", "jsonl", "tsv"), default="json")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
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
    selected = list(HARNESSES) if not args.harness or "all" in args.harness else list(dict.fromkeys(args.harness))
    matcher = Matcher(args)
    needles, needs_full_parse = build_needles(args.query, args.tool, args.tool_arg)
    parse_all = needs_full_parse

    entries: list[FileEntry] = []
    for harness in selected:
        entries.extend(ENUMERATORS[harness](home))
    if args.since is not None:
        entries = [entry for entry in entries if entry.path.stat().st_mtime >= args.since]
    if args.project:
        needle_path = args.project.casefold()
        entries = [entry for entry in entries if needle_path in str(entry.path).casefold()]

    total_bytes = sum(entry.size for entry in entries)
    print(f"searching {len(entries)} files ({total_bytes / 2**20:.1f} MiB) across {', '.join(selected)}"
          + ("; no text needle, full-parsing every file" if parse_all else ""), file=sys.stderr)

    matches: list[SessionMatch] = []
    files_read = 0
    for entry in entries:
        hits = collect_hits(entry, matcher, needles, parse_all, args.max_hits, args.preview_chars)
        if hits:
            files_read += 1
            matches.append(finalize_session(entry, hits))
    matches.sort(key=lambda match: match.updated_at, reverse=True)
    matches = matches[: args.limit]

    print(f"{len(matches)} session(s) matched", file=sys.stderr)

    def session_dict(match: SessionMatch) -> dict[str, object]:
        return {
            "harness": match.harness,
            "session_id": match.session_id,
            "project": match.project,
            "title": match.title,
            "path": str(match.path),
            "updated_at": match.updated_at,
            "resume_command": match.resume_command,
            "hits": [vars(hit) for hit in match.hits],
        }

    if args.format == "json":
        json.dump({"harnesses": selected, "files_scanned": len(entries),
                   "sessions": [session_dict(match) for match in matches]},
                  sys.stdout, indent=2, ensure_ascii=False)
        print()
    elif args.format == "jsonl":
        for match in matches:
            print(json.dumps(session_dict(match), ensure_ascii=False))
    else:
        columns = ("harness", "session_id", "project", "path", "updated_at", "resume_command",
                   "kind", "tool", "timestamp", "model", "provider", "source_ref", "excerpt")
        writer = csv.DictWriter(sys.stdout, fieldnames=columns, delimiter="\t",
                                               lineterminator="\n")
        writer.writeheader()
        for match in matches:
            for hit in match.hits:
                row = {"harness": match.harness, "session_id": match.session_id,
                       "project": match.project, "path": str(match.path),
                       "updated_at": match.updated_at, "resume_command": match.resume_command,
                       **vars(hit)}
                writer.writerow(row)
    return 0 if matches else 3

def main(argv: Sequence[str] | None = None) -> int:
    return run(parse_args(argv or sys.argv[1:]), Path.home())


if __name__ == "__main__":
    raise SystemExit(main())
