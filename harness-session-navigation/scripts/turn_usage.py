#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Per-user-turn cost summary for one Claude Code or Pi session.

A turn starts at a typed (or injected) user prompt and runs until the next
one. For each turn: API calls, tool calls and tool errors, output tokens,
peak context (input + cache read + cache write of the largest request),
compactions, models, and wall-clock duration. Read-only; prompts are
reported as bounded previews only.

Claude writes one record per content block, all repeating the request's
usage, so API calls are counted by ``message.id``. Pi transcripts hold every
branch of the session tree in file order; turns are reported in that order.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import claude_sessions  # noqa: E402  (same directory)
import search_session as ss  # noqa: E402  (same directory)

COLUMNS = ("turn", "start", "duration_s", "source_ref", "api_calls", "tool_calls", "tool_errors",
           "api_errors", "output_tokens", "peak_context", "compactions", "models", "prompt")


@dataclass
class Turn:
    number: int
    start: str
    source_ref: str
    prompt: str
    end: str = ""
    api_calls: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    api_errors: int = 0
    output_tokens: int = 0
    peak_context: int = 0
    compactions: int = 0
    models: set[str] = field(default_factory=set)
    _requests: dict[str, tuple[int, int]] = field(default_factory=dict)  # Claude: id -> (output, context)

    def touch(self, timestamp: object) -> None:
        if isinstance(timestamp, str) and timestamp:
            self.end = timestamp
        elif isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
            self.end = str(int(timestamp))

    def request(self, request_id: str, output: int, context: int) -> None:
        """One API request; Claude repeats a request's usage on every block record."""
        if request_id:
            previous = self._requests.get(request_id)
            if previous is None:
                self.api_calls += 1
                self._requests[request_id] = (output, context)
                self.output_tokens += output
            elif output > previous[0]:
                self.output_tokens += output - previous[0]
                self._requests[request_id] = (output, max(context, previous[1]))
        else:
            self.api_calls += 1
            self.output_tokens += output
        self.peak_context = max(self.peak_context, context)

    def duration_s(self) -> float | None:
        start, end = ss.parse_time_ms(self.start), ss.parse_time_ms(self.end)
        if start is None or end is None or end < start:
            return None
        return round((end - start) / 1000, 1)

    def as_dict(self) -> dict[str, object]:
        return {
            "turn": self.number, "start": self.start, "end": self.end, "duration_s": self.duration_s(),
            "source_ref": self.source_ref, "api_calls": self.api_calls, "tool_calls": self.tool_calls,
            "tool_errors": self.tool_errors, "api_errors": self.api_errors,
            "output_tokens": self.output_tokens, "peak_context": self.peak_context,
            "compactions": self.compactions, "models": sorted(self.models), "prompt": self.prompt,
        }


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def claude_turns(path: Path, preview_chars: int) -> Iterator[Turn]:
    turn: Turn | None = None
    number = 0
    for line_number, record in ss.jsonl(path):
        if record.get("isSidechain"):
            continue
        kind = record.get("type")
        timestamp = record.get("timestamp")
        message = _dict(record.get("message"))
        content = message.get("content")
        if kind == "user":
            has_result = isinstance(content, list) and any(
                isinstance(block, dict) and block.get("type") == "tool_result" for block in content)
            prompt = "" if has_result else claude_sessions.user_prompt(record)
            if prompt.strip():
                if turn is not None:
                    yield turn
                number += 1
                turn = Turn(number, str(timestamp or ""), f"line {line_number}",
                            ss.excerpt(ss.clean(prompt), None, preview_chars))
            elif turn is not None and isinstance(content, list):
                turn.tool_errors += sum(1 for block in content if isinstance(block, dict)
                                        and block.get("type") == "tool_result" and block.get("is_error") is True)
        if turn is None:
            continue
        turn.touch(timestamp)
        if kind == "system" and record.get("subtype") == "compact_boundary":
            turn.compactions += 1
        if kind != "assistant":
            continue
        if record.get("isApiErrorMessage"):
            turn.api_errors += 1
        usage = _dict(message.get("usage"))
        context = (_int(usage.get("input_tokens")) + _int(usage.get("cache_read_input_tokens"))
                   + _int(usage.get("cache_creation_input_tokens")))
        if usage:
            request_id = message.get("id") or record.get("requestId")
            turn.request(request_id if isinstance(request_id, str) else "",
                         _int(usage.get("output_tokens")), context)
        model = message.get("model")
        if isinstance(model, str) and model and not model.startswith("<"):
            turn.models.add(model)
        if isinstance(content, list):
            turn.tool_calls += sum(1 for block in content
                                   if isinstance(block, dict) and block.get("type") == "tool_use")
    if turn is not None:
        yield turn


def pi_turns(path: Path, preview_chars: int) -> Iterator[Turn]:
    turn: Turn | None = None
    number = 0
    for line_number, record in ss.jsonl(path):
        kind = record.get("type")
        message = _dict(record.get("message"))
        role = message.get("role")
        if kind == "message" and role == "user":
            prompt = ss.content_text(message.get("content"))
            if prompt.strip():
                if turn is not None:
                    yield turn
                number += 1
                turn = Turn(number, str(record.get("timestamp") or ""), f"line {line_number}",
                            ss.excerpt(prompt, None, preview_chars))
        if turn is None:
            continue
        turn.touch(record.get("timestamp"))
        if kind == "compaction":
            turn.compactions += 1
        if kind != "message":
            continue
        if role == "toolResult" and message.get("isError") is True:
            turn.tool_errors += 1
        if role != "assistant":
            continue
        if message.get("stopReason") == "error" or message.get("errorMessage"):
            turn.api_errors += 1
        usage = _dict(message.get("usage"))
        if usage:
            context = _int(usage.get("input")) + _int(usage.get("cacheRead")) + _int(usage.get("cacheWrite"))
            turn.request("", _int(usage.get("output")), context)
        model = message.get("model")
        if isinstance(model, str) and model:
            turn.models.add(model)
        content = message.get("content")
        if isinstance(content, list):
            turn.tool_calls += sum(1 for block in content
                                   if isinstance(block, dict) and block.get("type") == "toolCall")
    if turn is not None:
        yield turn


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Per-user-turn API calls, tool calls/errors, output tokens and peak context "
                    "for one Claude Code or Pi session.",
        epilog=("Examples:\n"
                "  uv run scripts/turn_usage.py <claude-session-id> --format tsv\n"
                "  uv run scripts/turn_usage.py session.jsonl --query 'quota reset' --limit 50\n"
                "  uv run scripts/turn_usage.py session.jsonl --min-calls 1   # skip no-op turns"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="Claude Code or Pi transcript path, or a session id")
    parser.add_argument("--harness", choices=("auto", "claude", "pi"), default="auto")
    parser.add_argument("--query", action="append", default=[],
                        help="Only turns whose prompt contains this (case-insensitive); repeat to AND")
    parser.add_argument("--min-calls", type=int, default=0, help="Only turns with at least this many API calls")
    parser.add_argument("--offset", type=int, default=0, help="Matching turns to skip (default: 0)")
    parser.add_argument("--limit", type=int, default=200, help="Maximum turns (1-2000; default: 200)")
    parser.add_argument("--preview-chars", type=int, default=120, help="Prompt preview length (20-2000)")
    parser.add_argument("--format", choices=("json", "tsv"), default="json")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 2000:
        parser.error("--limit must be between 1 and 2000")
    if not 20 <= args.preview_chars <= 2000:
        parser.error("--preview-chars must be between 20 and 2000")
    if args.offset < 0 or args.min_calls < 0:
        parser.error("--offset and --min-calls must be non-negative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        source, harness, _ = ss.open_events(args.source, args.harness)
        if harness not in ("claude", "pi"):
            raise ValueError(f"turn usage needs a Claude Code or Pi transcript; {source} is {harness}")
        stream = claude_turns if harness == "claude" else pi_turns
        terms = [term.casefold() for term in args.query]
        turns = [turn for turn in stream(source, args.preview_chars)
                 if turn.api_calls >= args.min_calls
                 and all(term in turn.prompt.casefold() for term in terms)]
    except (OSError, json.JSONDecodeError, ValueError, LookupError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if terms:
        print("note: --query matches the bounded prompt preview; raise --preview-chars for long prompts",
              file=sys.stderr)
    page = turns[args.offset: args.offset + args.limit]
    end = args.offset + len(page)
    totals = {
        "turns": len(turns), "api_calls": sum(t.api_calls for t in turns),
        "tool_calls": sum(t.tool_calls for t in turns), "tool_errors": sum(t.tool_errors for t in turns),
        "api_errors": sum(t.api_errors for t in turns), "output_tokens": sum(t.output_tokens for t in turns),
        "peak_context": max((t.peak_context for t in turns), default=0),
        "compactions": sum(t.compactions for t in turns),
    }
    print(f"{len(turns)} turn(s); showing {len(page)}", file=sys.stderr)
    if args.format == "json":
        summary: dict[str, object] = {"harness": harness, "source": str(source), "totals": totals,
                                      "offset": args.offset, "returned": len(page),
                                      "truncated": end < len(turns)}
        if end < len(turns):
            summary["next_offset"] = end
        json.dump({**summary, "turns": [turn.as_dict() for turn in page]}, sys.stdout, indent=2,
                  ensure_ascii=False)
        print()
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        for turn in page:
            row = turn.as_dict()
            row["models"] = ",".join(turn.models)
            writer.writerow(row)
    return 0 if turns else 3


if __name__ == "__main__":
    raise SystemExit(main())
