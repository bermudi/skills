#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search normalized messages, thinking, and tool activity in one session.

Supports Pi, Command Code, Devin, and Freebuff local transcripts. Output is
bounded; complete message and tool payloads are never emitted.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

KINDS = ("user", "assistant", "thinking", "tool", "tool_call", "tool_result")
MAX_EVENT_CHARS = 10_000
OUTPUT_FIELDS = ("index", "kind", "timestamp", "message_id", "tool", "preview")
MAX_NORMAL_PREVIEW = 2_000
MAX_EXTRACT_PREVIEW = 100_000
MAX_EXTRACT_SOURCE = 200_000


@dataclass(frozen=True)
class Event:
    index: int
    kind: str
    timestamp: str
    message_id: str
    tool: str
    preview: str
    arguments: object | None = None


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
               tool: object, text: object, arguments: object | None = None) -> Event:
    # Bound retained payloads during parsing, not merely when rendering output.
    return Event(index, kind, compact(timestamp)[:100], compact(message_id)[:200],
                 compact(tool)[:100], compact(text)[:MAX_EVENT_CHARS], arguments)


def _ellipsize(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _preview_str(value: object, max_len: int) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = " ".join(value.split())
    else:
        text = compact(value)
    return _ellipsize(text, max_len)


def _fallback_preview(arguments: object) -> str:
    return _ellipsize(compact(arguments), 500)


def summarize_tool_call(function_name: object, arguments: object) -> str:
    """Return a compact, human-readable preview for a tool call."""
    name = str(function_name or "").casefold().strip()
    if not isinstance(arguments, dict) or not name:
        return _fallback_preview(arguments)

    def _get(*keys: str, max_len: int = 200) -> str | None:
        for key in keys:
            if key in arguments and arguments[key] is not None:
                preview = _preview_str(arguments[key], max_len)
                if preview:
                    return preview
        return None

    file_path = _get("file_path", "path", "paths")
    if (
        name
        in {
            "write",
            "edit",
            "read",
            "write_file",
            "write_files",
            "file_write",
            "edit_file",
            "str_replace",
            "read_file",
            "read_files",
            "file_read",
            "file_edit",
        }
        or name.startswith(("write_", "edit_", "read_"))
    ):
        if file_path:
            return file_path
        return _fallback_preview(arguments)

    if name == "run_subagent":
        title = _get("title", "task", max_len=200)
        profile = _get("profile", max_len=100)
        if title or profile:
            parts = []
            if title:
                parts.append(f"title: {title}")
            if profile:
                parts.append(f"profile: {profile}")
            return " ".join(parts)
        return _fallback_preview(arguments)

    if name in ("exec", "bash", "shell", "execute", "run_command", "run_shell", "command") or name.startswith(
        ("exec_", "run_")
    ):
        command = _get("command", "cmd", "script", max_len=300)
        workdir = _get("workdir", "cwd", max_len=200)
        if command:
            if workdir:
                return f"{command} (workdir: {workdir})"
            return command
        return _fallback_preview(arguments)

    if name == "grep":
        pattern = _get("pattern", "regex", max_len=300)
        path = _get("path", max_len=200)
        glob_pattern = _get("glob_pattern", max_len=200)
        if pattern:
            parts = [f"pattern: {pattern}"]
            if path:
                parts.append(f"path: {path}")
            if glob_pattern:
                parts.append(f"glob: {glob_pattern}")
            return " ".join(parts)
        return _fallback_preview(arguments)

    if name == "find_file_by_name":
        pattern = _get("pattern", max_len=300)
        path = _get("path", max_len=200)
        if pattern or path:
            parts = []
            if pattern:
                parts.append(f"pattern: {pattern}")
            if path:
                parts.append(f"path: {path}")
            return " ".join(parts)
        return _fallback_preview(arguments)

    if name == "web_search":
        query = _get("query", max_len=500)
        if query:
            return f"query: {query}"
        return _fallback_preview(arguments)

    if name in ("webfetch", "web_fetch"):
        url = _get("url", "uri", max_len=500)
        if url:
            return f"url: {url}"
        return _fallback_preview(arguments)

    if name == "skill":
        command = _get("command", max_len=300)
        skill = _get("skill", max_len=100)
        if command or skill:
            parts = []
            if command:
                parts.append(f"command: {command}")
            if skill:
                parts.append(f"skill: {skill}")
            return " ".join(parts)
        return _fallback_preview(arguments)

    if name == "todo_write":
        todos = arguments.get("todos")
        if isinstance(todos, list):
            return f"{len(todos)} todo(s)"
        return _fallback_preview(arguments)

    if name == "ask_user_question":
        questions = arguments.get("questions")
        if isinstance(questions, list):
            return f"{len(questions)} question(s)"
        return _fallback_preview(arguments)

    return _fallback_preview(arguments)


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
        pending: list[tuple[str, object, object, object, object | None]] = []
        if role == "user":
            pending.append(("user", message_id, "", content_text(content), None))
        elif role == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    pending.append(("assistant", message_id, "", block.get("text"), None))
                elif block.get("type") == "thinking":
                    pending.append(("thinking", message_id, "", block.get("thinking"), None))
                elif block.get("type") == "toolCall":
                    tool_name = block.get("name")
                    arguments = block.get("arguments")
                    pending.append(("tool_call", block.get("id") or message_id,
                                    tool_name, summarize_tool_call(tool_name, arguments), arguments))
        elif role == "toolResult":
            pending.append(("tool_result", message.get("toolCallId") or message_id,
                            message.get("toolName"), content_text(content), None))
        elif role == "bashExecution":
            pending.append(("tool_result", message_id, "bash", message.get("output"), None))
        for kind, event_id, tool, text, arguments in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text, arguments)
            index += 1


def commandcode_events(path: Path) -> Iterator[Event]:
    index = 0
    for record in jsonl(path):
        role = record.get("role")
        content = record.get("content")
        timestamp = record.get("timestamp")
        message_id = record.get("id")
        pending: list[tuple[str, object, object, object, object | None]] = []
        if role == "user":
            pending.append(("user", message_id, "", content_text(content), None))
        elif role == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    pending.append(("assistant", message_id, "", block.get("text"), None))
                elif block.get("type") == "reasoning":
                    pending.append(("thinking", message_id, "", block.get("text"), None))
                elif block.get("type") == "tool-call":
                    tool_name = block.get("toolName")
                    arguments = block.get("input")
                    pending.append(("tool_call", block.get("toolCallId") or message_id,
                                    tool_name, summarize_tool_call(tool_name, arguments), arguments))
        elif role == "tool" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool-result":
                    pending.append(("tool_result", block.get("toolCallId") or message_id,
                                    block.get("toolName"), block.get("output"), None))
        for kind, event_id, tool, text, arguments in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text, arguments)
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
        pending: list[tuple[str, object, object, object, object | None]] = []
        if variant == "user":
            pending.append(("user", message_id, "", message.get("content"), None))
        elif variant == "ai":
            blocks = message.get("blocks")
            if not isinstance(blocks, list):
                text = compact(message.get("content"))
                if text:
                    pending.append(("assistant", message_id, "", text, None))
            else:
                for block in blocks:
                    if not isinstance(block, dict):
                        continue
                    kind = block.get("type")
                    if kind == "text":
                        event_kind = "thinking" if block.get("textType") == "reasoning" else "assistant"
                        pending.append((event_kind, message_id, "", block.get("content"), None))
                    elif kind == "tool":
                        tool_id = block.get("toolCallId") or message_id
                        tool_name = block.get("toolName")
                        arguments = block.get("input")
                        pending.append(("tool_call", tool_id, tool_name,
                                        summarize_tool_call(tool_name, arguments), arguments))
                        if "output" in block and block.get("output") is not None:
                            pending.append(("tool_result", tool_id, tool_name, block.get("output"), None))
        for kind, event_id, tool, text, arguments in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text, arguments)
            index += 1


def devin_events(path: Path) -> Iterator[Event]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object in {path}")
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ValueError(f"no steps array in {path}")
    index = 0
    for step in steps:
        if not isinstance(step, dict):
            continue
        source = step.get("source")
        timestamp = step.get("timestamp")
        step_id = step.get("step_id")
        message = step.get("message")
        pending: list[tuple[str, object, object, object, object | None]] = []
        if source == "user" and isinstance(message, str) and message.strip():
            pending.append(("user", step_id, "", message, None))
        elif source == "agent":
            if isinstance(message, str) and message.strip():
                pending.append(("assistant", step_id, "", message, None))
            reasoning = step.get("reasoning_content")
            if isinstance(reasoning, str) and reasoning.strip():
                pending.append(("thinking", step_id, "", reasoning, None))
            tool_calls = step.get("tool_calls")
            if isinstance(tool_calls, list):
                for call in tool_calls:
                    if not isinstance(call, dict):
                        continue
                    tool_name = call.get("function_name", "")
                    call_id = call.get("tool_call_id") or step_id
                    arguments = call.get("arguments")
                    pending.append(("tool_call", call_id, tool_name,
                                    summarize_tool_call(tool_name, arguments), arguments))
            observation = step.get("observation")
            if isinstance(observation, dict):
                results = observation.get("results")
                if isinstance(results, list):
                    for result in results:
                        if not isinstance(result, dict):
                            continue
                        call_id = result.get("source_call_id") or step_id
                        pending.append(("tool_result", call_id, "", result.get("content"), None))
        for kind, event_id, tool, text, arguments in pending:
            yield make_event(index, kind, timestamp, event_id, tool, text, arguments)
            index += 1


def detect(path: Path) -> str:
    if path.is_dir() and (path / "chat-messages.json").is_file():
        return "freebuff"
    if path.name in ("chat-meta.json", "chat-messages.json"):
        return "freebuff"
    if path.suffix == ".json" and not path.name.startswith("."):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "steps" in value and "session_id" in value:
            return "devin"
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
                "  uv run scripts/search_session.py chat-dir --type assistant --offset 20 --format jsonl\n"
                "  uv run scripts/search_session.py devin.json --tool write --extract --preview-chars 50000\n"
                "  uv run scripts/search_session.py devin.json --tool write --extract --extract-field file_path\n"
                "  uv run scripts/search_session.py devin.json --type tool_call --tool-arg file_path=foo"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="Pi/Command Code JSONL, Devin transcript JSON, or Freebuff chat directory/file")
    parser.add_argument("--harness", choices=("auto", "pi", "commandcode", "devin", "freebuff"), default="auto")
    parser.add_argument("--type", dest="types", action="append", choices=KINDS,
                        help="Event type; repeat to combine. 'tool' includes calls and results")
    parser.add_argument("--tool", action="append", default=[], help="Exact tool name; repeat to combine")
    parser.add_argument("--tool-arg", action="append", default=[],
                        help="Filter tool calls by key=value in arguments; repeat to combine (partial match for strings)")
    parser.add_argument("--query", default="", help="Case-insensitive text search in preview and tool name")
    parser.add_argument("--offset", type=int, default=0, help="Matching records to skip (default: 0)")
    parser.add_argument("--limit", type=int, default=20, help="Maximum records (1-500; default: 20)")
    parser.add_argument("--preview-chars", type=int, default=300,
                        help="Characters per result (default: 300; max 2000, or 100000 with --extract)")
    parser.add_argument("--extract", action="store_true",
                        help="Emit full tool-call arguments in the preview field")
    parser.add_argument("--extract-field",
                        help="With --extract, emit only this argument field as plain text, one value per line")
    parser.add_argument("--format", choices=("json", "jsonl", "tsv"), default="json")
    args = parser.parse_args(argv)
    if not args.source.exists():
        parser.error(f"source does not exist: {args.source}")
    if args.offset < 0:
        parser.error("--offset must be non-negative")
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if args.extract_field:
        args.extract = True
    for i, pair in enumerate(args.tool_arg):
        if "=" not in pair:
            parser.error(f"--tool-arg must be key=value: {pair}")
        key, value = pair.split("=", 1)
        args.tool_arg[i] = (key, value.casefold())
    max_preview = MAX_EXTRACT_PREVIEW if args.extract else MAX_NORMAL_PREVIEW
    if not 20 <= args.preview_chars <= max_preview:
        parser.error(f"--preview-chars must be between 20 and {max_preview}")
    return args


def _tool_arg_matches(arguments: object, filters: list[tuple[str, str]]) -> bool:
    if not isinstance(arguments, dict):
        return False
    for key, expected in filters:
        if key not in arguments:
            return False
        if expected == "":
            continue
        actual = arguments[key]
        if isinstance(actual, str):
            actual_str = " ".join(actual.split())
        else:
            actual_str = compact(actual)
        if expected not in actual_str.casefold():
            return False
    return True


def _extract_field_lines(value: object, max_len: int) -> Iterator[str]:
    if value is None:
        return
    if isinstance(value, list):
        for element in value:
            if isinstance(element, str):
                yield _ellipsize(" ".join(element.split()), max_len)
            else:
                yield _ellipsize(compact(element), max_len)
        return
    if isinstance(value, str):
        yield _ellipsize(" ".join(value.split()), max_len)
        return
    yield _ellipsize(compact(value), max_len)


def _event_preview(item: Event, extract: bool, query: str, max_chars: int) -> str:
    if extract and item.kind == "tool_call":
        raw = compact(item.arguments)
        if len(raw) > MAX_EXTRACT_SOURCE:
            raw = raw[: MAX_EXTRACT_SOURCE - 1] + "…"
        return excerpt(raw, query, max_chars)
    return excerpt(item.preview, query, max_chars)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        harness = detect(args.source) if args.harness == "auto" else args.harness
        if harness == "pi":
            events = pi_events(args.source)
        elif harness == "commandcode":
            events = commandcode_events(args.source)
        elif harness == "devin":
            events = devin_events(args.source)
        else:
            events = freebuff_events(args.source)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    wanted = set(args.types or KINDS)
    if "tool" in wanted:
        wanted.update(("tool_call", "tool_result"))
    if args.extract:
        if args.types and not any(t in ("tool", "tool_call") for t in args.types):
            print("warning: --extract only emits tool_call events", file=sys.stderr)
        wanted = {"tool_call"}
    tools = {tool.casefold() for tool in args.tool}
    query = args.query.casefold().strip()
    tool_arg_filters = args.tool_arg
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
            if tool_arg_filters and not _tool_arg_matches(item.arguments, tool_arg_filters):
                continue
            if args.extract_field:
                if not isinstance(item.arguments, dict) or args.extract_field not in item.arguments:
                    continue
            if args.offset <= total_matches < args.offset + args.limit:
                page.append(item)
            total_matches += 1
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.extract_field:
        for item in page:
            value = item.arguments[args.extract_field]
            for line in _extract_field_lines(value, args.preview_chars):
                print(line)
        return 3 if total_matches == 0 else 0

    rows = []
    for item in page:
        preview = _event_preview(item, args.extract, query, args.preview_chars)
        row = {field: getattr(item, field) for field in OUTPUT_FIELDS}
        row["preview"] = preview
        rows.append(row)

    if args.format == "json":
        json.dump({"harness": harness, "total_matches": total_matches, "offset": args.offset,
                   "limit": args.limit, "events": rows}, sys.stdout, indent=2)
        print()
    elif args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 3 if total_matches == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
