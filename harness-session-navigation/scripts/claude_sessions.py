"""Claude Code transcript discovery and metadata (read-only).

Transcripts live at ``<config>/projects/<slug>/<session-id>.jsonl`` where
``<config>`` is ``$CLAUDE_CONFIG_DIR`` or ``~/.claude``. The slug is a lossy
path encoding, so the real working directory is read from the records' ``cwd``.
Only the top-level ``*.jsonl`` per project are sessions; ``<id>/`` sibling
directories hold tool-result spill files, not transcripts.
"""
from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Record types that identify a Claude Code transcript when the path is unknown.
RECORD_TYPES = frozenset({
    "user", "assistant", "system", "attachment", "mode", "permission-mode",
    "ai-title", "custom-title", "last-prompt", "file-history-snapshot",
    "queue-operation", "summary", "tools-used", "api-request",
})
TITLE_TYPES = {"ai-title": "aiTitle", "custom-title": "customTitle"}


@dataclass(frozen=True)
class Meta:
    session_id: str
    cwd: str
    title: str
    preview: str


def projects_root(home: Path) -> Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(override) if override else home / ".claude") / "projects"


def transcripts(home: Path) -> Iterator[Path]:
    root = projects_root(home)
    if root.is_dir():
        yield from root.glob("*/*.jsonl")


def _clean(value: object, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def user_prompt(record: dict[str, object]) -> str:
    """Typed prompt text of a user record; '' for tool results and meta rows."""
    if record.get("type") != "user" or record.get("isMeta"):
        return ""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(block["text"] for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                        and isinstance(block.get("text"), str))
    return ""


def read_meta(path: Path, preview_chars: int = 160) -> Meta:
    """Id, cwd, latest title, first prompt. Streams the file once, parsing only
    lines that can matter (titles are rewritten throughout; the last one wins)."""
    cwd = title = preview = ""
    try:
        with path.open("rb") as handle:
            for raw in handle:
                wants_title = b'-title"' in raw
                if cwd and preview and not wants_title:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if not cwd:
                    cwd = _clean(record.get("cwd"), 500)
                field = TITLE_TYPES.get(str(record.get("type")))
                if field and _clean(record.get(field), 200):
                    title = _clean(record.get(field), 200)
                if not preview:
                    preview = _clean(user_prompt(record), preview_chars)
    except OSError:
        pass
    return Meta(path.stem, cwd, title, preview)


def resume_command(session_id: str, cwd: str) -> str:
    """Resume is cwd-scoped, so the command carries the cd. '' when cwd unknown."""
    if not session_id or not cwd:
        return ""
    return f"cd {shlex.quote(cwd)} && claude --resume {shlex.quote(session_id)}"


def looks_like_claude(path: Path, first: dict[str, object] | None) -> bool:
    if ".claude" in path.parts and "projects" in path.parts:
        return True
    if first is None:
        return False
    return "role" not in first and first.get("type") in RECORD_TYPES
