#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Find bounded session candidates for Pi, Devin, Command Code, and Freebuff.

Read-only: uses metadata and at most the first user-message preview. It never
prints complete transcripts or resumes a session.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

HARNESSES = ("pi", "devin", "commandcode", "freebuff")


@dataclass(frozen=True)
class Candidate:
    harness: str
    id: str
    title: str
    preview: str
    project: str
    updated_at: str
    resume_command: str
    source: str


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def clean_text(value: object, limit: int = 160) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def text_from_content(content: object) -> str:
    if isinstance(content, str):
        return clean_text(content)
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return clean_text(" ".join(parts))


def iso_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def iso_mtime(path: Path) -> str:
    return iso_timestamp(path.stat().st_mtime)


def shell_command(*arguments: str) -> str:
    """Render argv as a command safe to paste into a POSIX shell."""
    return " ".join(shlex.quote(argument) for argument in arguments)


class DiscoveryError(RuntimeError):
    """A harness could not be queried, so an empty result would be misleading."""


def read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        warn(f"cannot parse {path}: {error}")
        return None
    if not isinstance(value, dict):
        warn(f"expected a JSON object in {path}")
        return None
    return value


def iter_jsonl(path: Path, max_lines: int = 200) -> Iterable[dict[str, object]]:
    try:
        with path.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= max_lines:
                    return
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    yield value
    except OSError as error:
        warn(f"cannot read {path}: {error}")


def find_pi(home: Path) -> list[Candidate]:
    root = Path(os.environ.get("PI_CODING_AGENT_SESSION_DIR", home / ".pi/agent/sessions"))
    results: list[Candidate] = []
    if not root.is_dir():
        return results
    for path in root.rglob("*.jsonl"):
        session_id = path.stem.rsplit("_", 1)[-1]
        project = ""
        title = ""
        preview = ""
        for record in iter_jsonl(path):
            kind = record.get("type")
            if kind == "session":
                project = clean_text(record.get("cwd"), 500)
                session_id = clean_text(record.get("id"), 100) or session_id
            elif kind == "session_info":
                title = clean_text(record.get("name")) or title
            elif kind == "message" and not preview:
                message = record.get("message")
                if isinstance(message, dict) and message.get("role") == "user":
                    preview = text_from_content(message.get("content"))
        results.append(Candidate("pi", session_id, title, preview, project, iso_mtime(path),
                                 shell_command("pi", "--session", str(path)), str(path)))
    return results


def find_commandcode(home: Path) -> list[Candidate]:
    root = home / ".commandcode/projects"
    results: list[Candidate] = []
    if not root.is_dir():
        return results
    for path in root.glob("*/*.jsonl"):
        if any(path.name.endswith(suffix) for suffix in (".checkpoints.jsonl", ".prompts.jsonl")):
            continue
        session_id = path.stem
        meta_path = path.with_name(f"{session_id}.meta.json")
        meta = read_json(meta_path) if meta_path.is_file() else {}
        title = clean_text((meta or {}).get("title"))
        preview = ""
        for record in iter_jsonl(path, 80):
            if record.get("role") == "user":
                preview = text_from_content(record.get("content"))
                if preview:
                    break
        project = path.parent.name
        results.append(Candidate("commandcode", session_id, title, preview, project,
                                 iso_mtime(path), shell_command("cmd", "--session", str(path)), str(path)))
    return results


def find_freebuff(home: Path) -> list[Candidate]:
    root = home / ".config/manicode/projects"
    results: list[Candidate] = []
    if not root.is_dir():
        return results
    for meta_path in root.glob("*/chats/*/chat-meta.json"):
        meta = read_json(meta_path)
        if meta is None:
            continue
        chat_dir = meta_path.parent
        chat_id = chat_dir.name
        project = meta_path.parents[2].name
        preview = clean_text(meta.get("firstPrompt"))
        messages_path = chat_dir / "chat-messages.json"
        messages_mtime_ms = meta.get("messagesMtimeMs")
        if isinstance(messages_mtime_ms, (int, float)) and messages_mtime_ms >= 0:
            updated_at = iso_timestamp(messages_mtime_ms / 1000)
        elif messages_path.is_file():
            updated_at = iso_mtime(messages_path)
        else:
            updated_at = iso_mtime(meta_path)
        # The on-disk project key is only a basename, not a verified cwd. A bare
        # command could resume a same-named project, so deliberately omit it.
        results.append(Candidate("freebuff", chat_id, "", preview, project,
                                 updated_at, "", str(chat_dir)))
    return results


def find_devin(project: Path) -> list[Candidate]:
    try:
        process = subprocess.run(
            ["devin", "list", "--format", "json"], cwd=project,
            text=True, capture_output=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DiscoveryError(f"Devin listing failed: {error}") from error
    if process.returncode != 0:
        detail = clean_text(process.stderr, 300) or f"exit {process.returncode}"
        raise DiscoveryError(f"Devin listing failed: {detail}")
    try:
        rows = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise DiscoveryError(f"Devin returned invalid JSON: {error}") from error
    if not isinstance(rows, list):
        raise DiscoveryError("Devin returned JSON that is not a list")
    results: list[Candidate] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        session_id = clean_text(row.get("id"), 100)
        if not session_id:
            continue
        timestamp = row.get("last_activity_at")
        updated = ""
        if isinstance(timestamp, (int, float)):
            updated = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        resume = f"(cd -- {shlex.quote(str(project))} && {shell_command('devin', '-r', session_id)})"
        results.append(Candidate(
            "devin", session_id, clean_text(row.get("title")), "",
            clean_text(row.get("working_directory"), 500), updated,
            resume, shell_command("devin", "list", "--format", "json"),
        ))
    return results


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find session candidates without printing full transcripts or resuming them.",
        epilog=("Examples:\n  uv run scripts/find_sessions.py --harness pi --query webhook\n"
                "  uv run scripts/find_sessions.py --harness devin --project . --format tsv"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--harness", choices=("all", *HARNESSES), default="all")
    parser.add_argument("--query", default="", help="Case-insensitive title, preview, ID, or project filter")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project used for Devin listing")
    parser.add_argument("--limit", type=int, default=20, help="Maximum results (1-500; default: 20)")
    parser.add_argument("--format", choices=("json", "jsonl", "tsv"), default="json")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if not args.project.is_dir():
        parser.error(f"--project is not a directory: {args.project}")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    home = Path.home()
    selected = HARNESSES if args.harness == "all" else (args.harness,)
    candidates: list[Candidate] = []
    try:
        for harness in selected:
            if harness == "pi":
                candidates.extend(find_pi(home))
            elif harness == "devin":
                candidates.extend(find_devin(args.project.resolve()))
            elif harness == "commandcode":
                candidates.extend(find_commandcode(home))
            elif harness == "freebuff":
                candidates.extend(find_freebuff(home))
    except DiscoveryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    query = args.query.casefold().strip()
    if query:
        candidates = [candidate for candidate in candidates if query in " ".join((
            candidate.title, candidate.preview, candidate.id, candidate.project,
        )).casefold()]
    candidates.sort(key=lambda candidate: candidate.updated_at, reverse=True)
    candidates = candidates[: args.limit]

    rows = [asdict(candidate) for candidate in candidates]
    if args.format == "json":
        json.dump(rows, sys.stdout, indent=2)
        print()
    elif args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    else:
        fields = list(Candidate.__dataclass_fields__)
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 0 if candidates else 3


if __name__ == "__main__":
    raise SystemExit(main())
