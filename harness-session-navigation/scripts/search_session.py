#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Search normalized messages, thinking, and tool activity in one session.

Supports Pi, Claude Code, Command Code, Devin, Freebuff, and ZCode sessions. ZCode has no
transcript files: pass a session id (``sess_…``, unique prefix allowed) and it
is read — strictly read-only — from the zcode SQLite store.
``--query`` matches against full message text and full tool-call arguments
before any display truncation; output excerpts are bounded. Complete payloads
are never emitted wholesale.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Iterator, NamedTuple, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import claude_sessions  # noqa: E402  (same directory)
import find_sessions  # noqa: E402  (same directory)
import zcode_store  # noqa: E402  (same directory)

KINDS = ("user", "assistant", "thinking", "tool", "tool_call", "tool_result")
MAX_NORMAL_PREVIEW = 2_000
MAX_EXTRACT_PREVIEW = 100_000
OUTPUT_FIELDS = ("index", "kind", "timestamp", "message_id", "tool", "preview",
                 "model", "provider", "source_ref")


@dataclass(frozen=True)
class Event:
    index: int
    kind: str
    timestamp: str
    message_id: str
    tool: str
    preview: str
    arguments: object | None = None
    model: str = ""
    provider: str = ""
    source_ref: str = ""
    # tool_result only, when the harness records them.
    is_error: bool | None = None
    duration_ms: int | None = None


class RawEvent(NamedTuple):
    """One normalized event before it gets an index and a source reference."""
    kind: str
    event_id: object
    tool: object
    text: object
    arguments: object | None
    timestamp: object
    model: object
    provider: object
    is_error: object = None
    duration_ms: object = None


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


def jsonl(path: Path) -> Iterator[tuple[int, dict[str, object]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                print(f"warning: skipped invalid JSON at {path}:{line_number}: {error}", file=sys.stderr)
                continue
            if isinstance(value, dict):
                yield line_number, value


def make_event(index: int, kind: str, timestamp: object, message_id: object,
               tool: object, text: object, arguments: object | None = None,
               model: object = "", provider: object = "",
               source_ref: str = "", is_error: object = None,
               duration_ms: object = None) -> Event:
    # Matching must see the complete text. Bound excerpts only when rendering;
    # cutting retained text here silently turns deep matches into false negatives.
    return Event(index, kind, compact(timestamp)[:100], compact(message_id)[:200],
                 compact(tool)[:100], compact(text), arguments,
                 compact(model)[:200], compact(provider)[:100], source_ref,
                 is_error if isinstance(is_error, bool) else None,
                 int(duration_ms) if isinstance(duration_ms, (int, float))
                 and not isinstance(duration_ms, bool) and duration_ms >= 0 else None)


def event_from_raw(index: int, raw: RawEvent, source_ref: str) -> Event:
    return make_event(index, raw.kind, raw.timestamp, raw.event_id, raw.tool, raw.text,
                      raw.arguments, model=raw.model, provider=raw.provider,
                      source_ref=source_ref, is_error=raw.is_error, duration_ms=raw.duration_ms)


def raw_events(stream: Iterable[tuple[str, Iterable[RawEvent]]]) -> Iterator[Event]:
    """Index (source_ref, projected events) pairs into one Event stream."""
    index = 0
    for source_ref, projected in stream:
        for raw in projected:
            yield event_from_raw(index, raw, source_ref)
            index += 1


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


# Words summarize_tool_call writes itself; every other summary word is copied
# from the arguments. search_sessions' byte prefilter relies on this split
# (test_summary_words_come_from_arguments_or_labels keeps it honest).
SUMMARY_LABELS = ("title", "profile", "workdir", "pattern", "path", "glob", "query",
                  "url", "command", "skill", "todo", "question", "s")


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


def excerpt(text: str, query: "str | re.Pattern[str] | None", limit: int) -> str:
    """Return a bounded excerpt, centering a query (or regex) match when possible."""
    if len(text) <= limit:
        return text
    if isinstance(query, re.Pattern):
        match = query.search(text)
        return _window(text, match.start() if match else 0, limit)
    if not query:
        return _window(text, 0, limit)
    folded = text.casefold()
    position = max(0, folded.find(query))
    if len(folded) != len(text):
        # casefold can expand characters (ß -> ss). Its offsets are not
        # original-text offsets; map the hit back before selecting a window.
        folded_offset = 0
        for original_offset, char in enumerate(text):
            folded_offset += len(char.casefold())
            if folded_offset > position:
                position = original_offset
                break
    return _window(text, position, limit)


def _window(text: str, position: int, limit: int) -> str:
    # Reserve marker space before selecting the window. Trimming afterwards
    # can cut the end of a query that sits at the very end of a long payload.
    window = max(1, limit - 2)
    start = max(0, position - window // 3)
    end = min(len(text), start + window)
    start = max(0, end - window)
    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


# --- Per-record projectors -------------------------------------------------
# Shared by this script's event streams and by search_sessions.py, which scans
# many files and only parses lines that pass a cheap byte-level prefilter.

def pi_record_events(record: dict[str, object]) -> list[RawEvent]:
    if record.get("type") != "message":
        return []
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    role = message.get("role")
    timestamp = message.get("timestamp") or record.get("timestamp")
    message_id = record.get("id")
    model = message.get("model")
    provider = message.get("provider")
    content = message.get("content")
    events: list[RawEvent] = []
    if role == "user":
        events.append(RawEvent("user", message_id, "", content_text(content), None, timestamp, model, provider))
    elif role == "assistant" and isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                events.append(RawEvent("assistant", message_id, "", block.get("text"), None, timestamp, model, provider))
            elif block.get("type") == "thinking":
                events.append(RawEvent("thinking", message_id, "", block.get("thinking"), None, timestamp, model, provider))
            elif block.get("type") == "toolCall":
                tool_name = block.get("name")
                arguments = block.get("arguments")
                events.append(RawEvent("tool_call", block.get("id") or message_id, tool_name,
                               summarize_tool_call(tool_name, arguments), arguments, timestamp, model, provider))
    elif role == "toolResult":
        events.append(RawEvent("tool_result", message.get("toolCallId") or message_id,
                               message.get("toolName"), content_text(content), None, timestamp, model, provider,
                               message.get("isError"), message.get("durationMs")))
    elif role == "bashExecution":
        events.append(RawEvent("tool_result", message_id, "bash", message.get("output"), None, timestamp, model, provider))
    return events


def claude_projector() -> Callable[[dict[str, object]], list[RawEvent]]:
    """A per-file projector that names ``tool_result`` events.

    Claude's result blocks carry only ``tool_use_id``; the name lives on the
    earlier ``tool_use`` block. Use one projector per transcript.
    """
    names: dict[str, str] = {}

    def project(record: dict[str, object]) -> list[RawEvent]:
        return claude_record_events(record, names)

    return project


def claude_record_events(record: dict[str, object],
                         tool_names: dict[str, str] | None = None) -> list[RawEvent]:
    kind = record.get("type")
    if kind not in ("user", "assistant") or record.get("isMeta"):
        return []
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    timestamp = record.get("timestamp")
    message_id = record.get("uuid")
    model = message.get("model")
    events: list[RawEvent] = []
    if kind == "user":
        if isinstance(content, str):
            events.append(RawEvent("user", message_id, "", content, None, timestamp, None, None))
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    events.append(RawEvent("user", message_id, "", block.get("text"), None, timestamp, None, None))
                elif block.get("type") == "tool_result":
                    use_id = block.get("tool_use_id")
                    name = tool_names.get(use_id, "") if tool_names is not None and isinstance(use_id, str) else ""
                    events.append(RawEvent("tool_result", use_id or message_id, name,
                                           content_text(block.get("content")), None, timestamp, None, None,
                                           block.get("is_error")))
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                events.append(RawEvent("assistant", message_id, "", block.get("text"), None, timestamp, model, None))
            elif block.get("type") == "thinking":
                events.append(RawEvent("thinking", message_id, "", block.get("thinking"), None, timestamp, model, None))
            elif block.get("type") == "tool_use":
                tool_name = block.get("name")
                arguments = block.get("input")
                if tool_names is not None and isinstance(block.get("id"), str) and isinstance(tool_name, str):
                    tool_names[block["id"]] = tool_name
                events.append(RawEvent("tool_call", block.get("id") or message_id, tool_name,
                               summarize_tool_call(tool_name, arguments), arguments, timestamp, model, None))
    return events


def commandcode_record_events(record: dict[str, object]) -> list[RawEvent]:
    role = record.get("role")
    content = record.get("content")
    timestamp = record.get("timestamp")
    message_id = record.get("id")
    events: list[RawEvent] = []
    if role == "user":
        events.append(RawEvent("user", message_id, "", content_text(content), None, timestamp, None, None))
    elif role == "assistant" and isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                events.append(RawEvent("assistant", message_id, "", block.get("text"), None, timestamp, None, None))
            elif block.get("type") == "reasoning":
                events.append(RawEvent("thinking", message_id, "", block.get("text"), None, timestamp, None, None))
            elif block.get("type") == "tool-call":
                tool_name = block.get("toolName")
                arguments = block.get("input")
                events.append(RawEvent("tool_call", block.get("toolCallId") or message_id, tool_name,
                               summarize_tool_call(tool_name, arguments), arguments, timestamp, None, None))
    elif role == "tool" and isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool-result":
                events.append(RawEvent("tool_result", block.get("toolCallId") or message_id,
                               block.get("toolName"), block.get("output"), None, timestamp, None, None))
    return events


def freebuff_message_events(message: dict[str, object]) -> list[RawEvent]:
    variant = message.get("variant")
    timestamp = message.get("timestamp")
    message_id = message.get("id")
    events: list[RawEvent] = []
    if variant == "user":
        events.append(RawEvent("user", message_id, "", message.get("content"), None, timestamp, None, None))
    elif variant == "ai":
        blocks = message.get("blocks")
        if not isinstance(blocks, list):
            text = compact(message.get("content"))
            if text:
                events.append(RawEvent("assistant", message_id, "", text, None, timestamp, None, None))
        else:
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                kind = block.get("type")
                if kind == "text":
                    event_kind = "thinking" if block.get("textType") == "reasoning" else "assistant"
                    events.append(RawEvent(event_kind, message_id, "", block.get("content"), None, timestamp, None, None))
                elif kind == "tool":
                    tool_id = block.get("toolCallId") or message_id
                    tool_name = block.get("toolName")
                    arguments = block.get("input")
                    events.append(RawEvent("tool_call", tool_id, tool_name,
                                   summarize_tool_call(tool_name, arguments), arguments, timestamp, None, None))
                    if "output" in block and block.get("output") is not None:
                        events.append(RawEvent("tool_result", tool_id, tool_name, block.get("output"), None, timestamp, None, None))
    return events


def devin_step_events(step: dict[str, object]) -> list[RawEvent]:
    source = step.get("source")
    timestamp = step.get("timestamp")
    step_id = step.get("step_id")
    message = step.get("message")
    model = step.get("model_name")
    events: list[RawEvent] = []
    if source == "user" and isinstance(message, str) and message.strip():
        events.append(RawEvent("user", step_id, "", message, None, timestamp, model, "devin"))
    elif source == "agent":
        if isinstance(message, str) and message.strip():
            events.append(RawEvent("assistant", step_id, "", message, None, timestamp, model, "devin"))
        reasoning = step.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            events.append(RawEvent("thinking", step_id, "", reasoning, None, timestamp, model, "devin"))
        tool_calls = step.get("tool_calls")
        if isinstance(tool_calls, list):
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                tool_name = call.get("function_name", "")
                call_id = call.get("tool_call_id") or step_id
                arguments = call.get("arguments")
                events.append(RawEvent("tool_call", call_id, tool_name,
                               summarize_tool_call(tool_name, arguments), arguments, timestamp, model, "devin"))
        observation = step.get("observation")
        if isinstance(observation, dict):
            results = observation.get("results")
            if isinstance(results, list):
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    call_id = result.get("source_call_id") or step_id
                    events.append(RawEvent("tool_result", call_id, "", result.get("content"), None, timestamp, model, "devin"))
    return events


# --- Event streams over whole files ----------------------------------------

def pi_events(path: Path) -> Iterator[Event]:
    return raw_events((f"line {n}", pi_record_events(r)) for n, r in jsonl(path))


def commandcode_events(path: Path) -> Iterator[Event]:
    return raw_events((f"line {n}", commandcode_record_events(r)) for n, r in jsonl(path))


def claude_events(path: Path) -> Iterator[Event]:
    project = claude_projector()
    return raw_events((f"line {n}", project(r)) for n, r in jsonl(path))


def freebuff_events(path: Path) -> Iterator[Event]:
    chat_dir = path if path.is_dir() else path.parent
    messages_path = chat_dir / "chat-messages.json"
    return raw_events((f"item {i}", freebuff_message_events(m))
                      for i, m in enumerate(json_array(messages_path)) if isinstance(m, dict))


def devin_events(path: Path) -> Iterator[Event]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object in {path}")
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ValueError(f"no steps array in {path}")
    return raw_events((f"step {i}", devin_step_events(step))
                      for i, step in enumerate(steps) if isinstance(step, dict))


# --- Matching ---------------------------------------------------------------

def event_haystack(item: Event) -> str:
    """Full text a --query should match against, before any display truncation."""
    parts = [item.tool, item.preview]
    if item.kind == "tool_call" and item.arguments is not None:
        parts.append(compact(item.arguments))
    return " ".join(part for part in parts if part)


@dataclass(frozen=True)
class TextFilter:
    """AND of case-insensitive substrings (``--query``) and regexes (``--regex``).

    Every term and every pattern must match the same event's full text.
    """
    terms: tuple[str, ...] = ()
    patterns: tuple[re.Pattern[str], ...] = ()

    @classmethod
    def build(cls, queries: str | Sequence[str] | None = None,
              regexes: Sequence[str | re.Pattern[str]] = ()) -> "TextFilter":
        if isinstance(queries, str):
            queries = [queries]
        terms = tuple(term for term in (query.casefold().strip() for query in queries or ()) if term)
        patterns = tuple(regex if isinstance(regex, re.Pattern) else re.compile(regex, re.IGNORECASE)
                         for regex in regexes)
        return cls(terms, patterns)

    def __bool__(self) -> bool:
        return bool(self.terms or self.patterns)

    def matches(self, text: str) -> bool:
        if self.terms:
            folded = text.casefold()
            if any(term not in folded for term in self.terms):
                return False
        return all(pattern.search(text) for pattern in self.patterns)

    @property
    def focus(self) -> "str | re.Pattern[str] | None":
        """What a bounded excerpt should centre on."""
        if self.terms:
            return self.terms[0]
        return self.patterns[0] if self.patterns else None


def as_filter(query: "str | TextFilter | None") -> TextFilter:
    return query if isinstance(query, TextFilter) else TextFilter.build(query)


def event_matches(item: Event, wanted: set[str], tools: set[str],
                  query: "str | TextFilter", tool_arg_filters: list[tuple[str, str]]) -> bool:
    if item.kind not in wanted:
        return False
    if tools and item.tool.casefold() not in tools:
        return False
    if tool_arg_filters and not tool_arg_matches(item.arguments, tool_arg_filters):
        return False
    text_filter = as_filter(query)
    if text_filter and not text_filter.matches(event_haystack(item)):
        return False
    return True


# --- Call/result pairing ----------------------------------------------------

def parse_time_ms(value: str) -> float | None:
    """Epoch milliseconds from an ISO timestamp or epoch digits; None if unknown."""
    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        number = int(text)
        if number > 10**12:
            return float(number)
        return float(number * 1000) if number > 10**9 else None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None  # a naive timestamp's zone is a guess; refuse to subtract it
    return parsed.timestamp() * 1000


def elapsed(call: Event, result: Event) -> tuple[int | None, str]:
    """(milliseconds, source). Source is recorded|timestamps|unknown.

    A harness-recorded duration wins. Otherwise subtract timestamps, but only
    when call and result live in different records: Devin and Freebuff store
    both in one step/item, whose single timestamp says nothing about runtime.
    """
    if result.duration_ms is not None:
        return result.duration_ms, "recorded"
    if call.source_ref == result.source_ref:
        return None, "unknown"
    start, end = parse_time_ms(call.timestamp), parse_time_ms(result.timestamp)
    if start is None or end is None or end < start:
        return None, "unknown"
    return int(end - start), "timestamps"


class Pairer:
    """Pair tool calls with their results by call id, within one transcript.

    Results always follow their call, so a result row's call is known when the
    row is collected; a call row's result is attached once the stream reaches it.
    """

    def __init__(self, preview_chars: int) -> None:
        self.preview_chars = preview_chars
        self.calls: dict[str, Event] = {}
        self.results: dict[str, Event] = {}
        self.wanted: set[str] = set()

    def observe(self, item: Event) -> None:
        call_id = item.message_id
        if not call_id:
            return
        if item.kind == "tool_call" and call_id not in self.calls:
            # Keep a light copy: arguments can be megabytes of edit payload.
            self.calls[call_id] = Event(item.index, item.kind, item.timestamp, call_id, item.tool,
                                        item.preview[:2000], None, item.model, item.provider,
                                        item.source_ref)
        elif item.kind == "tool_result" and call_id in self.wanted and call_id not in self.results:
            self.results[call_id] = Event(item.index, item.kind, item.timestamp, call_id, item.tool,
                                          item.preview[:max(4000, self.preview_chars * 2)], None,
                                          item.model, item.provider, item.source_ref,
                                          item.is_error, item.duration_ms)

    def want(self, item: Event) -> None:
        if item.kind == "tool_call" and item.message_id:
            self.wanted.add(item.message_id)

    def pending(self) -> bool:
        return any(call_id not in self.results for call_id in self.wanted)

    def pending_ids(self) -> set[str]:
        return {call_id for call_id in self.wanted if call_id not in self.results}

    def fields(self, item: Event) -> dict[str, object]:
        """Extra row fields: ``result`` for a call row, ``call`` for a result row."""
        if item.kind == "tool_call":
            result = self.results.get(item.message_id)
            if result is None:
                return {"result": None}
            milliseconds, source = elapsed(item, result)
            return {"result": {
                "preview": excerpt(result.preview, None, self.preview_chars),
                "is_error": result.is_error, "elapsed_ms": milliseconds, "elapsed_source": source,
                "timestamp": result.timestamp, "source_ref": result.source_ref,
            }}
        if item.kind == "tool_result":
            call = self.calls.get(item.message_id)
            if call is None:
                return {"call": None, "is_error": item.is_error,
                        "elapsed_ms": item.duration_ms,
                        "elapsed_source": "recorded" if item.duration_ms is not None else "unknown"}
            milliseconds, source = elapsed(call, item)
            return {"call": {"tool": call.tool, "preview": excerpt(call.preview, None, self.preview_chars),
                             "timestamp": call.timestamp, "source_ref": call.source_ref},
                    "is_error": item.is_error, "elapsed_ms": milliseconds, "elapsed_source": source}
        return {}


def pair_tsv_fields(fields: dict[str, object]) -> dict[str, object]:
    """Flatten Pairer.fields for TSV: one paired preview plus error/elapsed."""
    other = fields.get("result", fields.get("call"))
    if "result" in fields:
        info = other if isinstance(other, dict) else {}
        return {"is_error": info.get("is_error"), "elapsed_ms": info.get("elapsed_ms"),
                "paired_preview": info.get("preview", "")}
    info = other if isinstance(other, dict) else {}
    return {"is_error": fields.get("is_error"), "elapsed_ms": fields.get("elapsed_ms"),
            "paired_preview": info.get("preview", "")}


PAIR_TSV_FIELDS = ("is_error", "elapsed_ms", "paired_preview")


# --- Position-based context --------------------------------------------------

_REF_RE = re.compile(r"^\s*(?:(L|line|step|item|msg|#)\s*)?(\d+)(?:\s*part\s*(\d+))?\s*$", re.IGNORECASE)
_SOURCE_RE = re.compile(r"^(line|step|item|msg) (\d+)(?: part (\d+))?$")


def parse_position(text: str) -> tuple[str, tuple[int, ...]]:
    """'L120', 'line 120', '120', 'step 4', 'item 2', 'msg 3 part 1', '#57' (event index)."""
    match = _REF_RE.match(text)
    if not match:
        raise ValueError(f"cannot parse position {text!r}: use L<line>, step <n>, item <n>, "
                         "msg <n> [part <n>], or #<event index>")
    unit = (match.group(1) or "line").lower()
    unit = {"l": "line", "#": "index"}.get(unit, unit)
    numbers = (int(match.group(2)),) + ((int(match.group(3)),) if match.group(3) else ())
    return unit, numbers


def source_position(item: Event) -> tuple[str, tuple[int, ...]] | None:
    match = _SOURCE_RE.match(item.source_ref)
    if not match:
        return None
    return match.group(1), tuple(int(group) for group in match.groups()[1:] if group is not None)


def context_window(events: Iterable[Event], reference: str, wanted: set[str],
                   before: int, after: int,
                   pairer: Pairer | None = None) -> tuple[list[Event], set[int]]:
    """Events around a source position: (window, indexes of anchor events).

    The anchor is the first wanted event at or after the position; every
    wanted event from that same source record is an anchor too.
    """
    unit, numbers = parse_position(reference)
    preceding: collections.deque[Event] = collections.deque(maxlen=before)
    window: list[Event] = []
    anchors: set[int] = set()
    anchor_ref: str | None = None
    following = 0

    def results_pending() -> bool:
        return pairer is not None and any(
            e.kind == "tool_call" and e.message_id and e.message_id not in pairer.results for e in window)

    for item in events:
        if item.kind not in wanted:
            if pairer is not None:
                pairer.observe(item)
            continue
        if anchor_ref is None:
            if unit == "index":
                reached = item.index >= numbers[0]
            else:
                position = source_position(item)
                if position is None or position[0] != unit:
                    found = position[0] if position else item.source_ref
                    raise ValueError(f"this transcript records positions as '{found} <n>', not '{unit}'")
                reached = position[1] >= numbers
            if not reached:
                # A call in the look-behind may get its result at or after the anchor.
                preceding.append(item)
                if pairer is not None:
                    pairer.want(item)
                    pairer.observe(item)
                continue
            anchor_ref = item.source_ref
            window.extend(preceding)
        if unit != "index" and item.source_ref == anchor_ref and following == 0:
            anchors.add(item.index)
        elif unit == "index" and not anchors:
            anchors.add(item.index)
        elif following >= after:
            if pairer is not None:
                pairer.observe(item)
            if not results_pending():
                break
            continue
        else:
            following += 1
        window.append(item)
        if pairer is not None:
            pairer.want(item)
            pairer.observe(item)
    return window, anchors


def looks_like_zcode_id(source: object) -> bool:
    """zcode ids are sess_<uuid>; some core-internal rows use session_<hex>.
    The not-a-file guard keeps real paths winning over id-shaped strings."""
    if not isinstance(source, str) or Path(source).exists():
        return False
    return source.startswith(("sess_", "session_"))


def detect(path: Path) -> str:
    if looks_like_zcode_id(str(path)):
        return "zcode"
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
    first = next(jsonl(path), (0, None))[1]
    if first and first.get("type") == "session":
        return "pi"
    if claude_sessions.looks_like_claude(path, first):
        return "claude"
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
                "  uv run scripts/search_session.py devin.json --type tool_call --tool-arg file_path=foo\n"
                "  uv run scripts/search_session.py s.jsonl --tool bash --query 'herdr agent' --with-result\n"
                "  uv run scripts/search_session.py s.jsonl --type user --regex 'wtf|why did you'\n"
                "  uv run scripts/search_session.py s.jsonl --around L1520 --before 5 --after 10"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="Transcript path (Pi/Claude Code/Command Code JSONL, Devin JSON, Freebuff chat dir/file), or a session id from any harness (unique prefix allowed)")
    parser.add_argument("--harness", choices=("auto", "pi", "claude", "commandcode", "devin", "freebuff", "zcode"), default="auto")
    parser.add_argument("--type", dest="types", action="append", choices=KINDS,
                        help="Event type; repeat to combine. 'tool' includes calls and results")
    parser.add_argument("--tool", action="append", default=[], help="Exact tool name; repeat to combine")
    parser.add_argument("--tool-arg", action="append", default=[],
                        help="Filter tool calls by key=value in arguments; repeat to combine (partial match for strings)")
    add_text_filter_args(parser)
    parser.add_argument("--with-result", action="store_true",
                        help="Pair each tool_call row with its result (preview, is_error, elapsed_ms) "
                             "and each tool_result row with its call")
    parser.add_argument("--result-chars", type=int, default=300,
                        help="Characters of the paired call/result preview (20-2000; default: 300)")
    parser.add_argument("--around", metavar="POS",
                        help="Show events around a position instead of searching: L<line>, step <n>, "
                             "item <n>, msg <n> [part <n>] (from source_ref), or #<event index>")
    parser.add_argument("--before", type=int, default=5, help="With --around: events before (default: 5)")
    parser.add_argument("--after", type=int, default=10, help="With --around: events after (default: 10)")
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
    if not args.source.exists() and args.harness != "zcode" \
            and not looks_like_zcode_id(str(args.source)) \
            and not find_sessions.looks_like_session_id(str(args.source)):
        parser.error(f"source does not exist: {args.source} (pass a transcript path or a session id)")
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
    if not 20 <= args.result_chars <= MAX_NORMAL_PREVIEW:
        parser.error(f"--result-chars must be between 20 and {MAX_NORMAL_PREVIEW}")
    compile_regexes(parser, args)
    if args.around is not None:
        conflicts = [flag for flag, used in (("--query", args.query), ("--regex", args.regex),
                                             ("--tool", args.tool), ("--tool-arg", args.tool_arg),
                                             ("--offset", args.offset), ("--extract", args.extract)) if used]
        if conflicts:
            parser.error(f"--around shows a position, not search results; drop {', '.join(conflicts)} "
                         "(use --type to choose which kinds appear)")
        try:
            parse_position(args.around)
        except ValueError as error:
            parser.error(str(error))
        if not (0 <= args.before <= 200 and 0 <= args.after <= 200):
            parser.error("--before/--after must be between 0 and 200")
    elif "--before" in argv or "--after" in argv:
        parser.error("--before/--after need --around")
    return args


def add_text_filter_args(parser: argparse.ArgumentParser) -> None:
    """--query/--regex, shared with search_sessions.py."""
    parser.add_argument("--query", action="append", default=[],
                        help="Case-insensitive substring of full event text, tool names, and tool-call "
                             "arguments; repeat to require all (AND)")
    parser.add_argument("--regex", action="append", default=[],
                        help="Python regex over the same text (case-insensitive unless (?-i)); "
                             "repeat to require all; combines with --query by AND")


def compile_regexes(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    compiled: list[re.Pattern[str]] = []
    for pattern in args.regex:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error as error:
            parser.error(f"invalid --regex {pattern!r}: {error}")
    args.regex = compiled


def tool_arg_matches(arguments: object, filters: list[tuple[str, str]]) -> bool:
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


# Backwards-compatible private name used by older callers.
_tool_arg_matches = tool_arg_matches


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


def _event_preview(item: Event, extract: bool, query: "str | TextFilter | re.Pattern[str] | None",
                   max_chars: int) -> str:
    focus = query.focus if isinstance(query, TextFilter) else query
    if extract and item.kind == "tool_call":
        raw = compact(item.arguments)
        return excerpt(raw, focus, max_chars)
    if item.kind == "tool_call" and item.arguments is not None:
        # The summary preview may not contain the query even when the full
        # arguments do; fall back to an excerpt of the arguments so the hit is
        # visible evidence, not a bare file path.
        summary = excerpt(item.preview, focus, max_chars)
        if focus and not _contains(summary, focus):
            raw = compact(item.arguments)
            return excerpt(raw, focus, max_chars)
        return summary
    return excerpt(item.preview, focus, max_chars)


def _contains(text: str, focus: "str | re.Pattern[str]") -> bool:
    if isinstance(focus, re.Pattern):
        return focus.search(text) is not None
    return focus in text.casefold()


def open_events(source: Path, harness: str = "auto") -> tuple[Path, str, Iterator[Event]]:
    """Resolve a path or session id and return (source, harness, event stream)."""
    if not source.exists() and harness != "zcode" and not looks_like_zcode_id(str(source)):
        source = find_sessions.resolve_source(source)
    if harness == "auto":
        harness = detect(source)
    if harness == "zcode":
        return source, harness, zcode_store.zcode_session_events(zcode_store.db_path(), str(source))
    streams: dict[str, Callable[[Path], Iterator[Event]]] = {
        "pi": pi_events, "claude": claude_events, "commandcode": commandcode_events,
        "devin": devin_events, "freebuff": freebuff_events,
    }
    return source, harness, streams[harness](source)


def wanted_kinds(types: Sequence[str] | None) -> set[str]:
    wanted = set(types or KINDS)
    if "tool" in wanted:
        wanted.update(("tool_call", "tool_result"))
    return wanted


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        args.source, harness, events = open_events(args.source, args.harness)
    except (OSError, json.JSONDecodeError, ValueError, sqlite3.Error, LookupError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    wanted = wanted_kinds(args.types)
    if args.extract:
        if args.types and not any(t in ("tool", "tool_call") for t in args.types):
            print("warning: --extract only emits tool_call events", file=sys.stderr)
        wanted = {"tool_call"}
    tools = {tool.casefold() for tool in args.tool}
    text_filter = TextFilter.build(args.query, args.regex)
    tool_arg_filters = args.tool_arg
    pairer = Pairer(args.result_chars) if args.with_result else None
    total_matches = 0
    page: list[Event] = []
    anchors: set[int] = set()
    try:
        if args.around is not None:
            page, anchors = context_window(events, args.around, wanted, args.before, args.after, pairer)
            total_matches = len(page)
        else:
            for item in events:
                if pairer is not None:
                    pairer.observe(item)
                if not event_matches(item, wanted, tools, text_filter, tool_arg_filters):
                    continue
                if args.extract_field:
                    if not isinstance(item.arguments, dict) or args.extract_field not in item.arguments:
                        continue
                if args.offset <= total_matches < args.offset + args.limit:
                    page.append(item)
                    if pairer is not None:
                        pairer.want(item)
                total_matches += 1
    except (OSError, json.JSONDecodeError, ValueError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.around is not None and not page:
        print(f"note: no {'/'.join(sorted(wanted))} events at or after {args.around}", file=sys.stderr)
    if args.around is None and args.format != "json" and args.offset + len(page) < total_matches:
        print(f"note: showing {len(page)} of {total_matches} matches; "
              f"continue with --offset {args.offset + len(page)}", file=sys.stderr)
    if args.extract_field:
        for item in page:
            if not isinstance(item.arguments, dict):
                raise ValueError("matched extraction event has no argument object")
            value = item.arguments[args.extract_field]
            for line in _extract_field_lines(value, args.preview_chars):
                print(line)
        return 3 if total_matches == 0 else 0

    rows: list[dict[str, object]] = []
    for item in page:
        row: dict[str, object] = {name: getattr(item, name) for name in OUTPUT_FIELDS}
        row["preview"] = _event_preview(item, args.extract, text_filter, args.preview_chars)
        if args.around is not None:
            row["anchor"] = item.index in anchors
        if pairer is not None:
            row.update(pairer.fields(item))
        rows.append(row)

    if args.format == "json":
        summary: dict[str, object] = {"harness": harness}
        if args.around is not None:
            summary.update({"around": args.around, "before": args.before, "after": args.after,
                            "anchor_indexes": sorted(anchors), "returned": len(rows)})
        else:
            end = args.offset + len(rows)
            truncated = end < total_matches
            summary.update({"total_matches": total_matches, "offset": args.offset, "limit": args.limit,
                            "returned": len(rows), "truncated": truncated})
            if truncated:
                summary["next_offset"] = end
                summary["hint"] = (f"{total_matches - end} more matches; continue with --offset {end}, "
                                   "or narrow with --type/--tool/--query/--regex")
        json.dump({**summary, "events": rows}, sys.stdout, indent=2)
        print()
    elif args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    else:
        fields = list(OUTPUT_FIELDS)
        if args.around is not None:
            fields.append("anchor")
        if pairer is not None:
            fields.extend(PAIR_TSV_FIELDS)
            for row in rows:
                row.update(pair_tsv_fields(row))
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, delimiter="\t", lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return 3 if total_matches == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
