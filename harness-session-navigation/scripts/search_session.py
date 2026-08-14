#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search normalized messages, thinking, and tool activity in one session.

Supports Pi, Command Code, and Freebuff local transcripts. Output is bounded;
complete message and tool payloads are never emitted.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

KINDS = ("user", "assistant", "thinking", "tool", "tool_call", "tool_result")
MAX_EVENT_CHARS = 10_000


@dataclass(frozen=True)
class Event:
    index: int
    kind: str
    timestamp: str
    message_id: str
    tool: str
    preview: str


def compact(value: object) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if value is None:
        return ""
    try:
        return " ".join(json.dumps(value, ensure_ascii=False, sort_keys=True).split())
    except (TypeError, ValueError):
        return clean(str(value))


def clean(value: str) -> str:
    return " ".join(value.split())


def block_text(block: object) -> str:
    if not isinstance(block, dict):
        return ""
    for key in ("text", "content", "output"):
        if key in block:
            return compact(block[key])
    return ""


def content_text(content: object) -> str:
    if isinstance(content, str):
        return clean(content)
    if not isinstance(content, list):
        return ""
    return clean(" ".join(block_text(block) for block in content if isinstance(block, dict) and block.get("type") == "text"))


def jsonl(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                print(f"warning: skipped invalid JSON at {path}:{line_number}: {error}", file=sys.stderr)
                continue
            if isinstance(value, dict):
                yield value


def make_event(index: int, kind: str, timestamp: object, message_id: object,
               tool: object, text: object) -> Event:
    # Bound retained payloads during parsing, not merely when rendering output.
    return Event(index, kind, compact(timestamp)[:100], compact(message_id)[:200],
                 compact(tool)[:100], compact(text)[:MAX_EVENT_CHARS])


def json_array(path: Path, chunk_size: int = 64 * 1024) -> Iterator[object]:
    """Incrementally decode a top-level JSON array without loading the file."""
    decoder = json.JSONDecoder()
    with path.open(encoding="utf-8") as handle:
        buffer = ""
        position = 0
        eof = False

        def fill() -> bool:
            nonlocal buffer, position, eof
            chunk = handle.read(chunk_size)
            if not chunk:
                eof = True
                return False
            buffer = buffer[position:] + chunk
            position = 0
            return True

        fill()
        while True:
            while position >= len(buffer) and fill():
                pass
            while position < len(buffer) and buffer[position].isspace():
                position += 1
            if position < len(buffer):
                break
            if eof:
                raise ValueError(f"empty JSON file: {path}")
        if buffer[position] != "[":
            raise ValueError(f"expected a JSON array in {path}")
        position += 1
        expecting_value = True
        while True:
            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position < len(buffer) or eof:
                    break
                fill()
            if position >= len(buffer):
                raise ValueError(f"unterminated JSON array in {path}")
            if buffer[position] == "]":
                return
            if not expecting_value:
                if buffer[position] != ",":
                    raise ValueError(f"expected ',' in JSON array in {path}")
                position += 1
                expecting_value = True
                continue
            try:
                value, end = decoder.raw_decode(buffer, position)
            except json.JSONDecodeError as error:
                if eof:
                    raise ValueError(f"invalid JSON in {path}: {error}") from error
                fill()
                continue
            position = end
            expecting_value = False
            yield value


def excerpt(text: str, query: str, limit: int) -> str:
    """Return a bounded excerpt, centering a query match when possible."""
    if len(text) <= limit:
        return text
    position = text.casefold().find(query) if query else 0
    if position < 0:
        position = 0
    start = max(0, position - limit // 3)
    end = min(len(text), start + limit)
    start = max(0, end - limit)
    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    body_limit = max(1, limit - len(prefix) - len(suffix))
    return prefix + text[start : start + body_limit] + suffix


def pi_events(path: Path) -> Iterator[Event]:
    index = 0
    for record in jsonl(path):
        if record.get("type") != "message":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        timestamp = message.get("timestamp") or record.get("timestamp")
        message_id = record.get("id")
        content = message.get("content")
        pending: list[tuple[str, object, object, object]] = []
        if role == "user":
            pending.append(("user", message_id, "", content_text(content)))
        elif role == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    pending.append(("assistant", message_id, "", block.get("text")))
                elif block.get("type") == "thinking":
                    pending.append(("thinking", message_id, "", block.get("thinking")))
                elif block.get("type") == "toolCall":
                    pending.append(("tool_call", block.get("id") or message_id,
                                    block.get("name"), block.get("arguments")))
        elif role == "toolResult":
            pending.append(("tool_result", message.get("toolCallId") or message_id,
                            message.get("toolName"), content_text(content)))
        elif role == "bashExecution":
            pending.append(("tool_result", message_id, "bash", message.get("output")))
        for kind, event_id, tool, text in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text)
            index += 1


def commandcode_events(path: Path) -> Iterator[Event]:
    index = 0
    for record in jsonl(path):
        role = record.get("role")
        content = record.get("content")
        timestamp = record.get("timestamp")
        message_id = record.get("id")
        pending: list[tuple[str, object, object, object]] = []
        if role == "user":
            pending.append(("user", message_id, "", content_text(content)))
        elif role == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    pending.append(("assistant", message_id, "", block.get("text")))
                elif block.get("type") == "reasoning":
                    pending.append(("thinking", message_id, "", block.get("text")))
                elif block.get("type") == "tool-call":
                    pending.append(("tool_call", block.get("toolCallId") or message_id,
                                    block.get("toolName"), block.get("input")))
        elif role == "tool" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool-result":
                    pending.append(("tool_result", block.get("toolCallId") or message_id,
                                    block.get("toolName"), block.get("output")))
        for kind, event_id, tool, text in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text)
            index += 1


def freebuff_events(path: Path) -> Iterator[Event]:
    chat_dir = path if path.is_dir() else path.parent
    messages_path = chat_dir / "chat-messages.json"
    index = 0
    for message in json_array(messages_path):
        if not isinstance(message, dict):
            continue
        variant = message.get("variant")
        timestamp = message.get("timestamp")
        message_id = message.get("id")
        pending: list[tuple[str, object, object, object]] = []
        if variant == "user":
            pending.append(("user", message_id, "", message.get("content")))
        elif variant == "ai":
            blocks = message.get("blocks")
            if not isinstance(blocks, list):
                text = compact(message.get("content"))
                if text:
                    pending.append(("assistant", message_id, "", text))
            else:
                for block in blocks:
                    if not isinstance(block, dict):
                        continue
                    kind = block.get("type")
                    if kind == "text":
                        event_kind = "thinking" if block.get("textType") == "reasoning" else "assistant"
                        pending.append((event_kind, message_id, "", block.get("content")))
                    elif kind == "tool":
                        tool_id = block.get("toolCallId") or message_id
                        tool_name = block.get("toolName")
                        pending.append(("tool_call", tool_id, tool_name, block.get("input")))
                        if "output" in block and block.get("output") is not None:
                            pending.append(("tool_result", tool_id, tool_name, block.get("output")))
        for kind, event_id, tool, text in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text)
            index += 1


def detect(path: Path) -> str:
    if path.is_dir() and (path / "chat-messages.json").is_file():
        return "freebuff"
    if path.name in ("chat-meta.json", "chat-messages.json"):
        return "freebuff"
    if path.name.endswith((".checkpoints.jsonl", ".prompts.jsonl")):
        raise ValueError("pass the main Command Code <session-id>.jsonl, not a sidecar")
    first = next(jsonl(path), None)
    if first and first.get("type") == "session":
        return "pi"
    if first and ("sessionId" in first or first.get("role") in ("user", "assistant", "tool")):
        return "commandcode"
    raise ValueError("could not identify the session format")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter bounded user, assistant, thinking, and tool events in one local session.",
        epilog=("Examples:\n"
                "  uv run scripts/search_session.py session.jsonl --type user --query migration\n"
                "  uv run scripts/search_session.py session.jsonl --type tool --tool bash --limit 20\n"
                "  uv run scripts/search_session.py chat-dir --type assistant --offset 20 --format jsonl"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="Pi/Command Code JSONL or Freebuff chat directory/file")
    parser.add_argument("--harness", choices=("auto", "pi", "commandcode", "freebuff"), default="auto")
    parser.add_argument("--type", dest="types", action="append", choices=KINDS,
                        help="Event type; repeat to combine. 'tool' includes calls and results")
    parser.add_argument("--tool", action="append", default=[], help="Exact tool name; repeat to combine")
    parser.add_argument("--query", default="", help="Case-insensitive text search in preview and tool name")
    parser.add_argument("--offset", type=int, default=0, help="Matching records to skip (default: 0)")
    parser.add_argument("--limit", type=int, default=20, help="Maximum records (1-500; default: 20)")
    parser.add_argument("--preview-chars", type=int, default=300, help="Characters per result (20-2000; default: 300)")
    parser.add_argument("--format", choices=("json", "jsonl", "tsv"), default="json")
    args = parser.parse_args(argv)
    if not args.source.exists():
        parser.error(f"source does not exist: {args.source}")
    if args.offset < 0:
        parser.error("--offset must be non-negative")
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if not 20 <= args.preview_chars <= 2000:
        parser.error("--preview-chars must be between 20 and 2000")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        harness = detect(args.source) if args.harness == "auto" else args.harness
        if harness == "pi":
            events = pi_events(args.source)
        elif harness == "commandcode":
            events = commandcode_events(args.source)
        else:
            events = freebuff_events(args.source)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    wanted = set(args.types or KINDS)
    if "tool" in wanted:
        wanted.update(("tool_call", "tool_result"))
    tools = {tool.casefold() for tool in args.tool}
    query = args.query.casefold().strip()
    total_matches = 0
    page: list[Event] = []
    try:
        for item in events:
            if item.kind not in wanted:
                continue
            if tools and item.tool.casefold() not in tools:
                continue
            if query and query not in f"{item.tool} {item.preview}".casefold():
                continue
            if args.offset <= total_matches < args.offset + args.limit:
                page.append(item)
            total_matches += 1
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    rows = [{**asdict(item), "preview": excerpt(item.preview, query, args.preview_chars)} for item in page]

    if args.format == "json":
        json.dump({"harness": harness, "total_matches": total_matches, "offset": args.offset,
                   "limit": args.limit, "events": rows}, sys.stdout, indent=2)
        print()
    elif args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    else:
        fields = list(Event.__dataclass_fields__)
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 3 if total_matches == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
