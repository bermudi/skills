#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic tests for the session-navigation helper scripts."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).parent


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


find_sessions = load("find_sessions")
inspect_session = load("inspect_session")
search_session = load("search_session")


class HelperTests(unittest.TestCase):
    def test_pi_finder_and_inspector_bound_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".pi/agent/sessions/--work-repo--/date_abc.jsonl"
            path.parent.mkdir(parents=True)
            rows = [
                {"type": "session", "id": "abc", "cwd": "/work/repo"},
                {"type": "session_info", "name": "Auth work"},
                {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "first secret prompt"}]}},
                {"type": "message", "message": {"role": "user", "content": "second prompt"}},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            candidates = find_sessions.find_pi(home)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].preview, "first secret prompt")
            result = inspect_session.inspect_pi(path, 1, 20)
            self.assertEqual(result["user_prompt_previews"], ["first secret prompt"])

    def test_pi_search_normalizes_roles_thinking_and_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pi.jsonl"
            rows = [
                {"type": "session", "id": "abc", "cwd": "/work/repo"},
                {"type": "message", "id": "u1", "message": {"role": "user", "timestamp": 1, "content": "deploy app"}},
                {"type": "message", "id": "a1", "message": {"role": "assistant", "timestamp": 2, "content": [
                    {"type": "thinking", "thinking": "inspect logs"},
                    {"type": "text", "text": "I will inspect it"},
                    {"type": "toolCall", "id": "tc1", "name": "bash", "arguments": {"command": "deploy --dry-run"}},
                ]}},
                {"type": "message", "id": "r1", "message": {"role": "toolResult", "timestamp": 3, "toolCallId": "tc1", "toolName": "bash", "content": [{"type": "text", "text": "dry run ok"}]}},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            events = list(search_session.pi_events(path))
            self.assertEqual([event.kind for event in events], ["user", "thinking", "assistant", "tool_call", "tool_result"])
            self.assertEqual([event.tool for event in events[-2:]], ["bash", "bash"])
            self.assertNotIn("dry run ok", events[-2].preview)

    def test_commandcode_search_normalizes_tool_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cc.jsonl"
            rows = [
                {"role": "assistant", "id": "a1", "timestamp": "now", "sessionId": "s1", "content": [
                    {"type": "reasoning", "text": "need file"},
                    {"type": "tool-call", "toolCallId": "tc1", "toolName": "read_file", "input": {"path": "a.ts"}},
                ]},
                {"role": "tool", "id": "t1", "timestamp": "later", "sessionId": "s1", "content": [
                    {"type": "tool-result", "toolCallId": "tc1", "toolName": "read_file", "output": "contents"},
                ]},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            events = list(search_session.commandcode_events(path))
            self.assertEqual([event.kind for event in events], ["thinking", "tool_call", "tool_result"])
            self.assertEqual(events[-1].preview, "contents")

    def test_excerpt_centers_query_and_stays_bounded(self) -> None:
        text = "a" * 100 + "needle" + "z" * 100
        result = search_session.excerpt(text, "needle", 30)
        self.assertLessEqual(len(result), 30)
        self.assertIn("needle", result)

    def test_commandcode_skips_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = home / ".commandcode/projects/work-repo"
            project.mkdir(parents=True)
            transcript = project / "session-id.jsonl"
            transcript.write_text(json.dumps({"role": "user", "content": [{"type": "text", "text": "database migration"}], "sessionId": "session-id"}) + "\n")
            (project / "session-id.meta.json").write_text(json.dumps({"title": "Migration"}))
            (project / "session-id.checkpoints.jsonl").write_text("{}\n")
            candidates = find_sessions.find_commandcode(home)
            self.assertEqual([item.id for item in candidates], ["session-id"])
            self.assertEqual(candidates[0].title, "Migration")

    def test_freebuff_reads_metadata_not_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            chat = home / ".config/manicode/projects/repo/chats/chat-1"
            chat.mkdir(parents=True)
            (chat / "chat-meta.json").write_text(json.dumps({"firstPrompt": "Houthis article", "messageCount": 9, "messagesSize": 1, "messagesMtimeMs": 1}))
            (chat / "chat-messages.json").write_text("not valid json")
            candidates = find_sessions.find_freebuff(home)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].preview, "Houthis article")

    def test_freebuff_search_normalizes_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chat = Path(tmp) / "chat-1"
            chat.mkdir()
            messages = [
                {"variant": "user", "id": "u1", "timestamp": 1, "content": "fix auth"},
                {"variant": "ai", "id": "a1", "timestamp": 2, "content": "", "blocks": [
                    {"type": "text", "textType": "reasoning", "content": "inspect code"},
                    {"type": "text", "textType": "text", "content": "I found it"},
                    {"type": "tool", "toolCallId": "tc1", "toolName": "read_files", "input": {"paths": ["a.ts"]}, "output": "file body"},
                ]},
            ]
            (chat / "chat-messages.json").write_text(json.dumps(messages))
            events = list(search_session.freebuff_events(chat))
            self.assertEqual([event.kind for event in events], ["user", "thinking", "assistant", "tool_call", "tool_result"])
            self.assertEqual(events[-1].tool, "read_files")

    def test_resume_commands_are_shell_quoted_and_project_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repo $(touch nope) ") as tmp:
            path = Path(tmp) / "session `id`.jsonl"
            path.write_text(json.dumps({"type": "session", "id": "abc", "cwd": tmp}) + "\n")
            result = inspect_session.inspect_pi(path, 0, 20)
            self.assertEqual(result["resume_command"], find_sessions.shell_command("pi", "--session", str(path)))

            process = subprocess.CompletedProcess([], 0, json.dumps([
                {"id": "id $(bad)", "title": "test", "working_directory": tmp, "last_activity_at": 1},
            ]), "")
            original_run = find_sessions.subprocess.run
            find_sessions.subprocess.run = lambda *args, **kwargs: process
            try:
                candidate = find_sessions.find_devin(Path(tmp))[0]
            finally:
                find_sessions.subprocess.run = original_run
            self.assertIn("cd --", candidate.resume_command)
            self.assertIn(find_sessions.shell_command("devin", "-r", "id $(bad)"), candidate.resume_command)

    def test_freebuff_uses_message_timestamp_and_omits_ambiguous_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            chat = home / ".config/manicode/projects/repo/chats/chat-1"
            chat.mkdir(parents=True)
            (chat / "chat-meta.json").write_text(json.dumps({
                "firstPrompt": "prompt", "messagesMtimeMs": 2_000,
            }))
            candidate = find_sessions.find_freebuff(home)[0]
            self.assertEqual(candidate.updated_at, "1970-01-01T00:00:02+00:00")
            self.assertEqual(candidate.resume_command, "")

    def test_event_payload_is_bounded_when_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pi.jsonl"
            path.write_text(json.dumps({
                "type": "message", "message": {"role": "bashExecution", "output": "x" * 20_000},
            }) + "\n")
            event = next(search_session.pi_events(path))
            self.assertEqual(len(event.preview), search_session.MAX_EVENT_CHARS)


if __name__ == "__main__":
    unittest.main()
