#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""A tiny on-disk memo for session discovery metadata.

Caches extraction results (candidate fields, preview strings) keyed by the
files they were read from. An entry is valid only while every dependency file
still has the recorded mtime and size, and optional sidecars recorded as
absent are still absent. Changed dependencies are re-extracted on the next
run. Entries whose required source files vanish are pruned on
save. The cache is a performance memo, never a source of truth: every run
still enumerates the real filesystem.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import os
import tempfile
from pathlib import Path

VERSION = 2


class Cache:
    def __init__(self, path: Path, entries: dict[str, dict[str, object]] | None = None) -> None:
        self.path = path
        self.entries: dict[str, dict[str, object]] = entries or {}
        self.dirty = False

    @classmethod
    def load(cls, path: Path) -> "Cache":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(path)
        if not isinstance(data, dict) or data.get("version") != VERSION:
            return cls(path)
        entries = data.get("entries")
        if not isinstance(entries, dict):
            return cls(path)
        return cls(path, entries)

    def get(self, key: str) -> object | None:
        """Return the cached value if every dependency is unchanged, else None."""
        entry = self.entries.get(key)
        if not isinstance(entry, dict):
            return None
        deps = entry.get("deps")
        if not isinstance(deps, list) or not deps:
            return None
        for dep in deps:
            if not (isinstance(dep, list) and len(dep) == 3):
                return None
            file_path, mtime, size = dep
            if not isinstance(file_path, str):
                return None
            try:
                stat = os.stat(file_path)
            except FileNotFoundError:
                if mtime is None and size is None:
                    continue  # An explicitly absent dependency is still absent.
                return None
            except OSError:
                return None
            if mtime is None or size is None:
                return None  # A previously absent sidecar was created.
            if stat.st_mtime != mtime or stat.st_size != size:
                return None
        value = entry.get("value")
        return value

    def put(self, key: str, deps: Mapping[str, tuple[float, int] | None], value: object) -> None:
        self.entries[key] = {
            "deps": [[path, *(state if state is not None else (None, None))]
                     for path, state in deps.items()],
            "value": value,
        }
        self.dirty = True

    def prune(self) -> int:
        """Drop entries whose dependency files no longer exist. Returns count."""
        kept: dict[str, dict[str, object]] = {}
        removed = 0
        for key, entry in self.entries.items():
            deps = entry.get("deps") if isinstance(entry, dict) else None
            alive = isinstance(deps, list) and bool(deps) and all(
                isinstance(dep, list) and len(dep) == 3 and isinstance(dep[0], str)
                and ((dep[1] is None and dep[2] is None) or Path(dep[0]).exists())
                for dep in deps
            )
            if alive:
                kept[key] = entry
            else:
                removed += 1
        self.entries = kept
        self.dirty = self.dirty or removed > 0
        return removed

    def save(self) -> None:
        """Atomically write the cache, pruning dead entries first."""
        self.prune()
        if not self.dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"version": VERSION, "entries": self.entries})
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, prefix=".sessions-", suffix=".tmp", delete=False,
        )
        try:
            handle.write(payload)
            handle.close()
            os.replace(handle.name, self.path)
        except OSError:
            try:
                os.unlink(handle.name)
            except OSError:
                pass
            raise
        self.dirty = False
