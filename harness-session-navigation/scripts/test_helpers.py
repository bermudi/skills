#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic tests for the session-navigation helper scripts."""
from __future__ import annotations

import contextlib
import importlib.util
import io
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

    def test_devin_extracts_tool_summary_files_duration_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session-id.json"
            steps = [
                {"step_id": 1, "source": "system", "message": "instructions",
                 "timestamp": "2026-08-14T02:42:30.000000000+00:00"},
                {"step_id": 2, "source": "user", "message": "build a thing",
                 "timestamp": "2026-08-14T02:42:30.000000000+00:00"},
                {"step_id": 3, "source": "agent", "message": "ok",
                 "timestamp": "2026-08-14T02:43:30.000000000+00:00",
                 "tool_calls": [
                     {"function_name": "write", "arguments": {"file_path": "/tmp/a.txt", "content": "A"}, "tool_call_id": "tc1"},
                     {"function_name": "exec", "arguments": {"command": "ls"}, "tool_call_id": "tc2"},
                 ]},
                {"step_id": 4, "source": "agent", "message": "done",
                 "timestamp": "2026-08-14T02:45:30.000000000+00:00",
                 "tool_calls": [
                     {"function_name": "edit", "arguments": {"file_path": "/tmp/a.txt", "content": "B"}, "tool_call_id": "tc3"},
                     {"function_name": "write", "arguments": {"file_path": "/tmp/b.txt", "content": "C"}, "tool_call_id": "tc4"},
                 ]},
            ]
            path.write_text(json.dumps({
                "session_id": "session-id",
                "schema_version": "ATIF-v1.7",
                "agent": {"name": "devin", "version": "3000.4.16", "model_name": "GLM-5.2 High"},
                "steps": steps,
                "final_metrics": {"total_steps": 4, "total_prompt_tokens": 100, "total_completion_tokens": 50, "total_cached_tokens": 10},
            }))
            result = inspect_session.inspect_devin(path, 1, 20)
            self.assertEqual(result["harness"], "devin")
            self.assertEqual(result["schema_version"], "ATIF-v1.7")
            self.assertEqual(result["step_counts"], {"system": 1, "user": 1, "agent": 2})
            self.assertEqual(result["duration"], "3m 0s")
            self.assertEqual(result["tool_call_summary"], {"exec": 1, "write": 2, "edit": 1})
            self.assertEqual(result["files_touched"], ["/tmp/a.txt", "/tmp/b.txt"])
            self.assertEqual(result["total_steps"], 4)
            self.assertEqual(result["total_prompt_tokens"], 100)
            self.assertEqual(result["total_completion_tokens"], 50)
            self.assertEqual(result["user_prompt_previews"], ["build a thing"])

    def test_devin_caps_files_touched_with_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session-id.json"
            tool_calls = [
                {"function_name": "write", "arguments": {"file_path": f"/tmp/file-{i:02d}.txt", "content": ""}, "tool_call_id": f"tc{i}"}
                for i in range(55)
            ]
            # Split tool calls across two agent steps so the test still exercises aggregation.
            steps = [
                {"step_id": 1, "source": "agent", "message": "", "timestamp": f"2026-08-14T02:42:{i:02d}.000000000+00:00", "tool_calls": tool_calls[:30]}
                for i in range(1)
            ] + [
                {"step_id": 2, "source": "agent", "message": "", "timestamp": "2026-08-14T02:43:00.000000000+00:00", "tool_calls": tool_calls[30:]}
            ]
            path.write_text(json.dumps({
                "session_id": "session-id",
                "schema_version": "ATIF-v1.7",
                "agent": {"model_name": "test"},
                "steps": steps,
            }))
            result = inspect_session.inspect_devin(path, 0, 20)
            self.assertEqual(len(result["files_touched"]), 50)
            self.assertTrue(result["files_touched"][-1].startswith("... and"))
            self.assertIn("6 more", result["files_touched"][-1])

    def test_devin_disk_extracts_first_user_prompt_and_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            transcript_dir = home / ".local/share/devin/cli/transcripts"
            transcript_dir.mkdir(parents=True)
            (transcript_dir / "from-file.json").write_text(json.dumps({
                "schema_version": "ATIF-v1.7",
                "steps": [
                    {"step_id": 1, "source": "system", "message": "instructions"},
                    {"step_id": 2, "source": "user", "message": "  first\nprompt  "},
                    {"step_id": 3, "source": "user", "message": "second"},
                ],
            }))
            (transcript_dir / "from-field.json").write_text(json.dumps({
                "session_id": "from-field",
                "steps": [
                    {"step_id": 1, "source": "user", "message": "x" * 200},
                ],
            }))
            candidates = find_sessions.find_devin_disk(home)
            self.assertEqual(len(candidates), 2)
            by_id = {candidate.id: candidate for candidate in candidates}
            self.assertEqual(by_id["from-file"].preview, "first prompt")
            self.assertEqual(by_id["from-field"].preview, "x" * 160)
            self.assertTrue(by_id["from-file"].source.endswith("from-file.json"))
            self.assertEqual(by_id["from-field"].source, str(transcript_dir / "from-field.json"))

    def test_devin_cli_uses_transcript_path_and_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = home / "project"
            project.mkdir()
            transcript_dir = home / ".local/share/devin/cli/transcripts"
            transcript_dir.mkdir(parents=True)
            (transcript_dir / "cli-session.json").write_text(json.dumps({
                "session_id": "cli-session",
                "steps": [
                    {"step_id": 1, "source": "system", "message": "instructions"},
                    {"step_id": 2, "source": "user", "message": "  user prompt  "},
                ],
            }))
            process = subprocess.CompletedProcess([], 0, json.dumps([
                {"id": "cli-session", "title": "CLI Session", "working_directory": str(project), "last_activity_at": 1},
            ]), "")
            original_run = find_sessions.subprocess.run
            find_sessions.subprocess.run = lambda *args, **kwargs: process
            try:
                candidate = find_sessions.find_devin(project, "cli", home)[0]
            finally:
                find_sessions.subprocess.run = original_run
            self.assertEqual(candidate.id, "cli-session")
            self.assertEqual(candidate.title, "CLI Session")
            self.assertEqual(candidate.preview, "user prompt")
            self.assertEqual(candidate.project, str(project))
            self.assertEqual(candidate.source, str(transcript_dir / "cli-session.json"))
            self.assertIn("cd --", candidate.resume_command)

    def test_devin_auto_falls_back_to_disk_when_cli_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = home / "project"
            project.mkdir()
            transcript_dir = home / ".local/share/devin/cli/transcripts"
            transcript_dir.mkdir(parents=True)
            (transcript_dir / "fallback.json").write_text(json.dumps({
                "session_id": "fallback",
                "steps": [
                    {"step_id": 1, "source": "user", "message": "fallback prompt"},
                ],
            }))

            def fake_run(*args, **kwargs):
                raise FileNotFoundError("devin")

            original_run = find_sessions.subprocess.run
            find_sessions.subprocess.run = fake_run
            try:
                candidate = find_sessions.find_devin(project, "auto", home)[0]
            finally:
                find_sessions.subprocess.run = original_run
            self.assertEqual(candidate.id, "fallback")
            self.assertEqual(candidate.preview, "fallback prompt")
            self.assertEqual(candidate.source, str(transcript_dir / "fallback.json"))

    def test_summarize_tool_call_uses_smart_previews(self) -> None:
        self.assertEqual(
            search_session.summarize_tool_call("write", {"file_path": "/tmp/foo", "content": "x" * 1000}),
            "/tmp/foo",
        )
        self.assertEqual(
            search_session.summarize_tool_call("exec", {"command": "ls", "workdir": "/tmp"}),
            "ls (workdir: /tmp)",
        )
        self.assertEqual(
            search_session.summarize_tool_call("skill", {"command": "invoke", "skill": "content-retrieval"}),
            "command: invoke skill: content-retrieval",
        )
        self.assertEqual(
            search_session.summarize_tool_call("todo_write", {"todos": [{"content": "a"}, {"content": "b"}]}),
            "2 todo(s)",
        )
        self.assertTrue(
            search_session.summarize_tool_call("unknown", {"content": "x" * 1000}).endswith("…"),
        )

    def test_tool_arg_filter_uses_partial_case_insensitive_match(self) -> None:
        self.assertTrue(search_session._tool_arg_matches(
            {"file_path": "/home/daniel/build/skills/html-communication/SKILL.md"},
            [("file_path", "html-communication")],
        ))
        self.assertTrue(search_session._tool_arg_matches(
            {"login": True}, [("login", "true")],
        ))
        self.assertFalse(search_session._tool_arg_matches(
            {"file_path": "/other/path.md"}, [("file_path", "html-communication")],
        ))

    def test_extract_and_extract_field_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session-id.json"
            path.write_text(json.dumps({
                "session_id": "session-id",
                "schema_version": "ATIF-v1.7",
                "steps": [
                    {"step_id": 1, "source": "agent", "message": "ok",
                     "timestamp": "2026-08-14T02:43:30.000000000+00:00",
                     "tool_calls": [
                         {"function_name": "write", "arguments": {"file_path": "/tmp/a.md", "content": "A"}, "tool_call_id": "tc1"},
                     ]},
                ],
            }))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_session.main([str(path), "--tool", "write", "--extract", "--extract-field", "file_path"])
            self.assertEqual(rc, 0)
            self.assertEqual(out.getvalue().strip(), "/tmp/a.md")


if __name__ == "__main__":
    unittest.main()
