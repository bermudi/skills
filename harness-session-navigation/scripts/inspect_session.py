#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Inspect one Pi, Command Code, or Freebuff session without dumping it."""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Iterable, Sequence


def clean(value: object, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def content_text(content: object, limit: int) -> str:
    if isinstance(content, str):
        return clean(content, limit)
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return clean(" ".join(parts), limit)


def records(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                print(f"warning: skipped invalid JSON at {path}:{line_number}: {error}", file=sys.stderr)
                continue
            if isinstance(value, dict):
                yield value


def inspect_pi(path: Path, max_prompts: int, preview_chars: int) -> dict[str, object]:
    session_id = path.stem.rsplit("_", 1)[-1]
    project = ""
    title = ""
    prompts: list[str] = []
    messages = 0
    for record in records(path):
        kind = record.get("type")
        if kind == "session":
            session_id = clean(record.get("id"), 100) or session_id
            project = clean(record.get("cwd"), 500)
        elif kind == "session_info":
            title = clean(record.get("name"), 200) or title
        elif kind == "message":
            messages += 1
            message = record.get("message")
            if isinstance(message, dict) and message.get("role") == "user" and len(prompts) < max_prompts:
                text = content_text(message.get("content"), preview_chars)
                if text:
                    prompts.append(text)
    return {"harness": "pi", "id": session_id, "title": title, "project": project,
            "message_records": messages, "user_prompt_previews": prompts,
            "resume_command": f"pi --session {shlex.quote(str(path))}", "source": str(path)}


def inspect_commandcode(path: Path, max_prompts: int, preview_chars: int) -> dict[str, object]:
    session_id = path.stem
    meta_path = path.with_name(f"{session_id}.meta.json")
    meta: dict[str, object] = {}
    if meta_path.is_file():
        value = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            meta = value
    prompts: list[str] = []
    messages = 0
    for record in records(path):
        if record.get("role") in ("user", "assistant", "tool"):
            messages += 1
        if record.get("role") == "user" and len(prompts) < max_prompts:
            text = content_text(record.get("content"), preview_chars)
            if text:
                prompts.append(text)
    return {"harness": "commandcode", "id": session_id, "title": clean(meta.get("title"), 200),
            "project": path.parent.name, "message_records": messages, "user_prompt_previews": prompts,
            "resume_command": f"cmd --session {shlex.quote(str(path))}", "source": str(path)}


def inspect_freebuff(path: Path, max_prompts: int, preview_chars: int) -> dict[str, object]:
    chat_dir = path if path.is_dir() else path.parent
    meta_path = chat_dir / "chat-meta.json"
    messages_path = chat_dir / "chat-messages.json"
    meta: dict[str, object] = {}
    if meta_path.is_file():
        value = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            meta = value
    prompts: list[str] = []
    if messages_path.is_file() and max_prompts > 1:
        value = json.loads(messages_path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            for message in value:
                if not isinstance(message, dict) or message.get("variant") != "user":
                    continue
                text = content_text(message.get("content"), preview_chars)
                if text:
                    prompts.append(text)
                if len(prompts) >= max_prompts:
                    break
    first = clean(meta.get("firstPrompt"), preview_chars)
    if first and (not prompts or prompts[0] != first):
        prompts.insert(0, first)
    prompts = prompts[:max_prompts]
    chat_id = chat_dir.name
    project = chat_dir.parents[1].name if len(chat_dir.parents) > 1 else ""
    return {"harness": "freebuff", "id": chat_id, "title": "", "project": project,
            "message_records": meta.get("messageCount"), "user_prompt_previews": prompts,
            # Storage records only a project basename, which is not a verified cwd.
            "resume_command": "", "source": str(chat_dir)}


def detect(path: Path) -> str:
    if path.is_dir() and (path / "chat-meta.json").is_file():
        return "freebuff"
    if path.name in ("chat-meta.json", "chat-messages.json"):
        return "freebuff"
    if path.name.endswith((".checkpoints.jsonl", ".prompts.jsonl")):
        raise ValueError("pass the main Command Code <session-id>.jsonl, not a sidecar")
    first = next(records(path), None)
    if first and first.get("type") == "session":
        return "pi"
    if first and ("sessionId" in first or first.get("role") in ("user", "assistant", "tool")):
        return "commandcode"
    raise ValueError("could not identify the session format")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show bounded metadata and user-prompt previews for one local session.",
        epilog="Example: uv run scripts/inspect_session.py /path/to/session.jsonl --max-prompts 3",
    )
    parser.add_argument("source", type=Path, help="Pi/Command Code JSONL or Freebuff chat directory/file")
    parser.add_argument("--harness", choices=("auto", "pi", "commandcode", "freebuff"), default="auto")
    parser.add_argument("--max-prompts", type=int, default=3, help="Prompt previews to return (0-20; default: 3)")
    parser.add_argument("--preview-chars", type=int, default=200, help="Characters per preview (20-1000; default: 200)")
    args = parser.parse_args(argv)
    if not args.source.exists():
        parser.error(f"source does not exist: {args.source}")
    if not 0 <= args.max_prompts <= 20:
        parser.error("--max-prompts must be between 0 and 20")
    if not 20 <= args.preview_chars <= 1000:
        parser.error("--preview-chars must be between 20 and 1000")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        harness = detect(args.source) if args.harness == "auto" else args.harness
        if harness == "pi":
            result = inspect_pi(args.source, args.max_prompts, args.preview_chars)
        elif harness == "commandcode":
            result = inspect_commandcode(args.source, args.max_prompts, args.preview_chars)
        else:
            result = inspect_freebuff(args.source, args.max_prompts, args.preview_chars)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
