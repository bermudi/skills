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
import time
import unittest
from unittest import mock
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Order matters: shared modules first so later plain imports inside script
# bodies resolve to the very instances registered here (no A/B duplicates).
session_cache = load("session_cache")
search_session = load("search_session")
zcode_store = load("zcode_store")
find_sessions = load("find_sessions")
inspect_session = load("inspect_session")
search_sessions = load("search_sessions")


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
        for text in ("x" * 200 + "needle", "ß" * 200 + "needle" + "z" * 100):
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

    def test_full_event_is_searchable_but_display_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pi.jsonl"
            text = "x" * 1_100_000 + " deep_message_needle"
            path.write_text(json.dumps({
                "type": "message", "message": {"role": "bashExecution", "output": text},
            }) + "\n")
            event = next(search_session.pi_events(path))
            self.assertEqual(event.preview, text)
            self.assertTrue(search_session.event_matches(
                event, {"tool_result"}, set(), "deep_message_needle", [],
            ))
            preview = search_session._event_preview(event, False, "deep_message_needle", 100)
            self.assertLessEqual(len(preview), 100)
            self.assertIn("deep_message_needle", preview)

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

    def test_query_matches_full_text_beyond_old_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pi.jsonl"
            filler = "x" * 20_000
            path.write_text(json.dumps({
                "type": "message", "id": "u1",
                "message": {"role": "user", "timestamp": 1,
                            "content": f"{filler} the needle is here {filler}"},
            }) + "\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_session.main([str(path), "--harness", "pi", "--type", "user", "--query", "needle is here"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["total_matches"], 1)
            self.assertIn("needle is here", payload["events"][0]["preview"])

    def test_query_matches_tool_call_arguments_not_just_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pi.jsonl"
            path.write_text(json.dumps({
                "type": "message", "id": "a1",
                "message": {"role": "assistant", "timestamp": 2, "provider": "p", "model": "m1",
                            "content": [
                                {"type": "toolCall", "id": "tc1", "name": "edit",
                                 "arguments": {"path": "/tmp/AGENTS.md",
                                                "edits": [{"oldText": "a", "newText": "the needle patch"}]}},
                            ]},
            }) + "\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_session.main([str(path), "--harness", "pi", "--type", "tool_call", "--query", "needle patch"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["total_matches"], 1)
            event = payload["events"][0]
            # Display falls back to the arguments so the hit is visible evidence.
            self.assertIn("needle patch", event["preview"])
            self.assertEqual(event["model"], "m1")
            self.assertEqual(event["provider"], "p")
            self.assertTrue(event["source_ref"].startswith("line "))

    def test_cache_round_trip_and_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.txt"
            source.write_text("v1")
            path = Path(tmp) / "nested" / "sessions.json"
            cache = session_cache.Cache.load(path)
            stat = source.stat()
            cache.put("key", {str(source): (stat.st_mtime, stat.st_size)}, {"preview": "v1"})
            cache.save()
            self.assertTrue(path.exists())
            reloaded = session_cache.Cache.load(path)
            self.assertEqual(reloaded.get("key"), {"preview": "v1"})
            # Same mtime+size -> hit; changed mtime -> miss.
            self.assertEqual(reloaded.entries["key"]["deps"][0][0], str(source))
            time.sleep(0.01)
            source.write_text("v2")
            reloaded = session_cache.Cache.load(path)
            self.assertIsNone(reloaded.get("key"))
            # Missing source -> pruned on save.
            source.unlink()
            reloaded.save()
            self.assertNotIn("key", reloaded.entries)

    def test_find_sessions_cache_reuses_and_refreshes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session_dir = home / ".pi/agent/sessions/--work-repo--"
            session_dir.mkdir(parents=True)
            path = session_dir / "2026-01-01T00-00-00Z_deadbeef.jsonl"

            def write_session(prompt: str) -> None:
                rows = [
                    {"type": "session", "id": "deadbeef", "cwd": "/work/repo"},
                    {"type": "message", "message": {"role": "user", "content": prompt}},
                ]
                path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

            write_session("first prompt")
            cache = session_cache.Cache.load(find_sessions.cache_path(home))
            first = find_sessions.find_pi(home, cache)
            self.assertEqual(first[0].preview, "first prompt")
            # Second run: served from cache even when extraction would fail.
            with mock.patch.object(find_sessions, "read_pi_candidate",
                                   side_effect=AssertionError("must not extract")):
                second = find_sessions.find_pi(home, cache)
            self.assertEqual(second[0].preview, "first prompt")
            # Changed file -> cache miss -> re-extraction picks up new content.
            time.sleep(0.01)
            write_session("updated prompt")
            third = find_sessions.find_pi(home, cache)
            self.assertEqual(third[0].preview, "updated prompt")

    def _write_cross_harness_fixtures(self, home: Path) -> None:
        pi_dir = home / ".pi/agent/sessions/--work-alpha--"
        pi_dir.mkdir(parents=True)
        pi_hit = pi_dir / "2026-10-01T00-00-00Z_ffff0001.jsonl"
        pi_hit.write_text(json.dumps({
            "type": "session", "id": "ffff0001", "cwd": "/work/alpha",
        }) + "\n" + json.dumps({
            "type": "message", "id": "u1", "message": {"role": "user", "timestamp": 1790000000000,
                                                          "content": "please fix the needle bug"},
        }) + "\n" + json.dumps({
            "type": "message", "id": "a1", "message": {"role": "assistant", "timestamp": 1790000001000,
                                                          "provider": "prov", "model": "model-x", "content": [
                {"type": "toolCall", "id": "tc1", "name": "edit",
                 "arguments": {"path": "/work/alpha/AGENTS.md", "edits": [{"oldText": "a", "newText": "b"}]}},
            ]},
        }) + "\n")
        pi_miss = pi_dir / "2026-10-01T00-00-00Z_ffff0002.jsonl"
        pi_miss.write_text(json.dumps({
            "type": "session", "id": "ffff0002", "cwd": "/work/alpha",
        }) + "\n" + json.dumps({
            "type": "message", "message": {"role": "user", "content": "nothing relevant"},
        }) + "\n")
        devin_dir = home / ".local/share/devin/cli/transcripts"
        devin_dir.mkdir(parents=True)
        (devin_dir / "devin-needle.json").write_text(json.dumps({
            "session_id": "devin-needle", "steps": [
                {"step_id": 1, "source": "user", "message": "plan around the needle",
                 "timestamp": "2026-10-01T00:00:00+00:00"},
            ],
        }))
        cmd_dir = home / ".commandcode/projects/work-beta"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "cmd-1.jsonl").write_text(json.dumps({
            "sessionId": "cmd-1", "role": "user", "id": "u1", "timestamp": "2026-10-01T00:00:00Z",
            "content": "totally different topic",
        }) + "\n")
        fb_dir = home / ".config/manicode/projects/work-gamma/chats/chat-1"
        fb_dir.mkdir(parents=True)
        (fb_dir / "chat-messages.json").write_text(json.dumps([
            {"id": "m1", "variant": "user", "timestamp": "2026-10-01T00:00:00Z",
             "content": "the needle appears here too"},
        ]))
        # Make fixtures old enough that --since 30d excludes them deterministically,
        # but keep relative order: pi_hit newest.
        import os as os_module
        old = time.time() - 90 * 86_400
        for path in (pi_hit, pi_miss, cmd_dir / "cmd-1.jsonl", fb_dir / "chat-messages.json"):
            os_module.utime(path, (old, old))
        newer = old + 86_400
        os_module.utime(pi_hit, (newer, newer))
        os_module.utime(devin_dir / "devin-needle.json", (old, old))

    def test_search_sessions_finds_matches_across_harnesses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._write_cross_harness_fixtures(home)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_sessions.run(search_sessions.parse_args(["--query", "needle", "--format", "json"]), home)
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            by_harness = {session["harness"]: session for session in payload["sessions"]}
            self.assertIn("pi", by_harness)
            self.assertIn("devin", by_harness)
            self.assertIn("freebuff", by_harness)
            self.assertNotIn("commandcode", by_harness)
            pi_session = by_harness["pi"]
            self.assertEqual(pi_session["session_id"], "ffff0001")
            self.assertEqual(pi_session["project"], "/work/alpha")
            self.assertTrue(pi_session["resume_command"].startswith("pi --session"))
            kinds = {hit["kind"] for hit in pi_session["hits"]}
            self.assertIn("user", kinds)
            devin_session = by_harness["devin"]
            self.assertTrue(devin_session["resume_command"].startswith("devin -r devin-needle"))
            freebuff_session = by_harness["freebuff"]
            self.assertEqual(freebuff_session["resume_command"], "")

    def test_search_sessions_action_search_attributes_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._write_cross_harness_fixtures(home)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_sessions.run(search_sessions.parse_args([
                    "--harness", "pi", "--tool", "edit", "--tool-arg", "path=AGENTS.md",
                    "--format", "json",
                ]), home)
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(len(payload["sessions"]), 1)
            session = payload["sessions"][0]
            hit = session["hits"][0]
            self.assertEqual(hit["tool"], "edit")
            self.assertEqual(hit["model"], "model-x")
            self.assertEqual(hit["provider"], "prov")
            self.assertIn("line ", hit["source_ref"])

    def test_search_sessions_since_and_project_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._write_cross_harness_fixtures(home)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_sessions.run(search_sessions.parse_args(["--query", "needle", "--since", "30d", "--format", "json"]), home)
            self.assertEqual(rc, 3)
            self.assertEqual(json.loads(out.getvalue())["sessions"], [])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = search_sessions.run(search_sessions.parse_args(["--query", "needle", "--project", "work-gamma", "--format", "json"]), home)
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(len(payload["sessions"]), 1)
            self.assertEqual(payload["sessions"][0]["harness"], "freebuff")

    def _write_user_transcript(self, home: Path, harness: str, text: str) -> Path:
        if harness == "zcode":
            import sqlite3

            db = home / ".zcode/cli/db/db.sqlite"
            db.parent.mkdir(parents=True)
            conn = sqlite3.connect(db)
            conn.executescript(
                "CREATE TABLE session (id text primary key, project_id text not null,"
                " workspace_id text, parent_id text, slug text not null, directory text not null,"
                " path text, title text not null, version text not null, share_url text,"
                " summary_additions integer, summary_deletions integer, summary_files integer,"
                " summary_diffs text, revert text, permission text, time_created integer not null,"
                " time_updated integer not null, time_compacting integer, time_archived integer,"
                " task_type text not null default 'interactive',"
                " title_source text not null default 'first_input', title_message_id text,"
                " time_title_updated integer, trace_id text, time_deleted integer, last_outcome text);"
                "CREATE TABLE message (id text primary key, session_id text not null,"
                " time_created integer not null, time_updated integer not null,"
                " data text not null, sequence integer);"
                "CREATE TABLE part (id text primary key, message_id text not null,"
                " session_id text not null, time_created integer not null,"
                " time_updated integer not null, data text not null, sequence integer);")
            now_ms = int(time.time() * 1000)
            conn.execute(
                "INSERT INTO session (id, project_id, slug, directory, title, version,"
                " time_created, time_updated) VALUES ('sess_z1','p','sess_z1','/work/zeta','t','0.17.0',?,?)",
                (now_ms, now_ms))
            conn.execute(
                "INSERT INTO message (id, session_id, time_created, time_updated, data, sequence)"
                " VALUES ('mz1','sess_z1',0,0,?,0)",
                (json.dumps({"role": "user", "time": {"created": now_ms}}, ensure_ascii=False),))
            conn.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data, sequence)"
                " VALUES ('pz1','mz1','sess_z1',0,0,?,0)",
                (json.dumps({"type": "text", "text": text}, ensure_ascii=False),))
            conn.commit()
            conn.close()
            return db
        if harness == "pi":
            path = home / ".pi/agent/sessions/repo/date_session.jsonl"
            data: object = {"type": "message", "id": "u1", "message": {"role": "user", "content": text}}
        elif harness == "commandcode":
            path = home / ".commandcode/projects/repo/session.jsonl"
            data = {"sessionId": "session", "role": "user", "content": text}
        elif harness == "devin":
            path = home / ".local/share/devin/cli/transcripts/session.json"
            data = {"session_id": "session", "steps": [{"step_id": 1, "source": "user", "message": text}]}
        else:
            path = home / ".config/manicode/projects/repo/chats/session/chat-messages.json"
            data = [{"variant": "user", "content": text}]
        path.parent.mkdir(parents=True)
        # A real literal non-ASCII record exercises casefolding before/after
        # byte filtering. The escaped-ASCII variant is made explicitly below.
        path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def test_cross_search_prefilter_preserves_decoded_matches(self) -> None:
        cases = [
            ("webhook\nretries", "webhook retries"),
            ("webhook\t  retries", "webhook retries"),
            ("needle", " needle "),
            ("needle", "needle"),
            ("ſearch", "search"),
            ("needle::", "::"),
            ("café", "café"),
        ]
        for harness in search_sessions.HARNESSES:
            for text, query in cases:
                with self.subTest(harness=harness, text=text, query=query), tempfile.TemporaryDirectory() as tmp:
                    home = Path(tmp)
                    path = self._write_user_transcript(home, harness, text)
                    # The escaped-ASCII variant rewrites a raw transcript file;
                    # zcode stores JSON inside SQLite, so its escape case is
                    # covered by test_zcode_sql_prefilter_tolerates_escapes.
                    if text == query == "needle" and harness != "zcode":
                        path.write_text(path.read_text().replace("needle", r"\u006eeedle"))
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                        rc = search_sessions.run(search_sessions.parse_args([
                            "--harness", harness, "--query", query,
                        ]), home)
                    self.assertEqual(rc, 0)
                    sessions = json.loads(out.getvalue())["sessions"]
                    self.assertEqual(len(sessions), 1)
                    self.assertIn(query.strip().casefold(), sessions[0]["hits"][0]["excerpt"].casefold())

    def test_cross_search_type_only_parses_without_text_needles(self) -> None:
        for harness in search_sessions.HARNESSES:
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                self._write_user_transcript(home, harness, "hello")
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    rc = search_sessions.run(search_sessions.parse_args([
                        "--harness", harness, "--type", "user",
                    ]), home)
                self.assertEqual(rc, 0)
                self.assertEqual(json.loads(out.getvalue())["sessions"][0]["hits"][0]["kind"], "user")

    def test_cross_search_preserves_synthetic_tool_summary_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".pi/agent/sessions/repo/date_id.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "type": "message", "message": {"role": "assistant", "content": [
                    {"type": "toolCall", "name": "exec", "arguments": {"command": "ls", "cwd": "/work"}},
                ]},
            }) + "\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = search_sessions.run(search_sessions.parse_args([
                    "--harness", "pi", "--query", "workdir",
                ]), home)
            self.assertEqual(rc, 0)
            self.assertIn("workdir", json.loads(out.getvalue())["sessions"][0]["hits"][0]["excerpt"])

    def test_deep_tool_arguments_match_and_render_in_both_searches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".pi/agent/sessions/repo/date_id.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "type": "message", "message": {"role": "assistant", "content": [
                    {"type": "toolCall", "id": "tc1", "name": "edit", "arguments": {
                        "path": "/work/file", "newText": "x" * 210_000 + " deep_argument_needle",
                    }},
                ]},
            }) + "\n")
            for extract in (False, True):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = search_session.main([
                        str(path), "--harness", "pi", "--query", "deep_argument_needle",
                        "--preview-chars", "100", *(["--extract"] if extract else []),
                    ])
                self.assertEqual(rc, 0)
                preview = json.loads(out.getvalue())["events"][0]["preview"]
                self.assertIn("deep_argument_needle", preview)
                self.assertLessEqual(len(preview), 100)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = search_sessions.run(search_sessions.parse_args([
                    "--harness", "pi", "--query", "deep_argument_needle", "--preview-chars", "100",
                ]), home)
            self.assertEqual(rc, 0)
            preview = json.loads(out.getvalue())["sessions"][0]["hits"][0]["excerpt"]
            self.assertIn("deep_argument_needle", preview)
            self.assertLessEqual(len(preview), 100)

    def test_cache_invalidates_when_optional_sidecar_appears_changes_or_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".commandcode/projects/repo/session.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"role": "user", "content": "hello"}) + "\n")
            cache_path = home / "cache.json"
            cache = session_cache.Cache(cache_path)
            self.assertEqual(find_sessions.find_commandcode(home, cache)[0].title, "")
            cache.save()
            cache = session_cache.Cache.load(cache_path)
            self.assertIsNotNone(cache.get(f"commandcode:{path}"))
            sidecar = path.with_name("session.meta.json")
            for title in ("new title", "a changed title"):
                sidecar.write_text(json.dumps({"title": title}))
                self.assertEqual(find_sessions.find_commandcode(home, cache)[0].title, title)
            sidecar.unlink()
            self.assertEqual(find_sessions.find_commandcode(home, cache)[0].title, "")
            cache.save()
            self.assertIsNotNone(session_cache.Cache.load(cache_path).get(f"commandcode:{path}"))

    def test_cache_upgrade_discards_entries_without_absence_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text(json.dumps({"version": 1, "entries": {"old": {"value": "stale"}}}))
            self.assertEqual(session_cache.Cache.load(path).entries, {})

    def test_freebuff_cache_depends_on_optional_messages_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            chat = home / ".config/manicode/projects/repo/chats/chat-1"
            chat.mkdir(parents=True)
            (chat / "chat-meta.json").write_text(json.dumps({"firstPrompt": "hello"}))
            messages = chat / "chat-messages.json"
            cache = session_cache.Cache(home / "cache.json")
            find_sessions.find_freebuff(home, cache)
            messages.write_text("[]")
            import os
            os.utime(messages, (1_000, 1_000))
            self.assertEqual(find_sessions.find_freebuff(home, cache)[0].updated_at, find_sessions.iso_mtime(messages))
            os.utime(messages, (2_000, 2_000))
            self.assertEqual(find_sessions.find_freebuff(home, cache)[0].updated_at, find_sessions.iso_mtime(messages))

    def test_search_sessions_no_match_exits_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._write_cross_harness_fixtures(home)
            err = io.StringIO()
            out = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = search_sessions.run(search_sessions.parse_args(["--query", "definitely-not-there-xyz", "--format", "json"]), home)
            self.assertEqual(rc, 3)


    # --- ZCode (SQLite session store) --------------------------------------

    ZCODE_MAIN = "sess_11111111-1111-1111-1111-111111111111"
    ZCODE_SUB = "sess_subagent_agent_22222222-2222-2222-2222-222222222222"
    ZCODE_DELETED = "sess_33333333-3333-3333-3333-333333333333"
    ZCODE_FORK = "sess_44444444-4444-4444-4444-444444444444-fork-ab12"
    ZCODE_OTHER_PROJECT = "sess_55555555-5555-5555-5555-555555555555"

    def _write_zcode_fixture(self, home: Path) -> Path:
        """Build a zcode store with the real schema and representative rows."""
        import sqlite3

        db = home / ".zcode/cli/db/db.sqlite"
        db.parent.mkdir(parents=True)
        now_ms = int(time.time() * 1000)
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE session (
              id text primary key, project_id text not null, workspace_id text,
              parent_id text, slug text not null, directory text not null,
              path text, title text not null, version text not null, share_url text,
              summary_additions integer, summary_deletions integer,
              summary_files integer, summary_diffs text, revert text, permission text,
              time_created integer not null, time_updated integer not null,
              time_compacting integer, time_archived integer,
              task_type text not null default 'interactive',
              title_source text not null default 'first_input',
              title_message_id text, time_title_updated integer, trace_id text,
              time_deleted integer, last_outcome text);
            CREATE TABLE message (
              id text primary key, session_id text not null,
              time_created integer not null, time_updated integer not null,
              data text not null, sequence integer);
            CREATE TABLE part (
              id text primary key, message_id text not null,
              session_id text not null, time_created integer not null,
              time_updated integer not null, data text not null, sequence integer);
            """
        )
        sessions = [
            # (id, parent, slug, directory, title, updated_ms, deleted_ms)
            (self.ZCODE_MAIN, None, self.ZCODE_MAIN, "/tmp/proj-wiki",
             "Wiki rethink", now_ms - 3_600_000, None),
            (self.ZCODE_SUB, self.ZCODE_MAIN, self.ZCODE_SUB, "/tmp/proj-wiki",
             "You are a FIXER", now_ms - 3_000_000, None),
            (self.ZCODE_DELETED, None, self.ZCODE_DELETED, "/tmp/proj-wiki",
             "gone", now_ms - 2_000_000, now_ms - 1_000_000),
            (self.ZCODE_FORK, self.ZCODE_MAIN, self.ZCODE_FORK, "/tmp/proj-wiki",
             "fork of main", 1_577_836_800_000, None),  # 2020: excluded by --since
            (self.ZCODE_OTHER_PROJECT, None, self.ZCODE_OTHER_PROJECT, "/tmp/other",
             "other project", now_ms - 5_400_000, None),
        ]
        for sid, parent, slug, directory, title, updated, deleted in sessions:
            conn.execute(
                "INSERT INTO session (id, project_id, slug, directory, title, version,"
                " time_created, time_updated, time_deleted, parent_id)"
                " VALUES (?, 'p', ?, ?, ?, '0.17.0', ?, ?, ?, ?)",
                (sid, slug, directory, title, updated, updated, deleted, parent))

        model = {"providerID": "account:zai-individual-coding-plan", "modelID": "GLM-5.3"}
        rows: list[tuple[str, str, int, object]] = [
            ("m1", self.ZCODE_MAIN, 0,
             {"role": "user", "time": {"created": now_ms - 3_600_000},
              "model": {"providerID": "account:zai-individual-coding-plan", "modelID": "GLM-5.3"}}),
            ("m2", self.ZCODE_MAIN, 1,
             {"role": "assistant", "time": {"created": now_ms - 3_500_000}, "model": model}),
            ("m3", self.ZCODE_OTHER_PROJECT, 0,
             {"role": "user", "time": {"created": now_ms - 5_400_000}}),
        ]
        for mid, sid, seq, payload in rows:
            conn.execute(
                "INSERT INTO message (id, session_id, time_created, time_updated, data, sequence)"
                " VALUES (?, ?, ?, ?, ?, ?)", (mid, sid, 0, 0, json.dumps(payload), seq))

        parts: list[tuple[str, str, str, int, object]] = [
            # Boilerplate first: previews must skip it, search must still see it.
            ("p0", "m1", self.ZCODE_MAIN, 0,
             {"type": "text", "text": "The TodoWrite tool hasn't been used recently."}),
            ("p1", "m1", self.ZCODE_MAIN, 1,
             {"type": "text", "text": "rethink the wiki with a zettelkasten obelisk"}),
            ("p2", "m2", self.ZCODE_MAIN, 0,
             {"type": "reasoning", "text": "user wants breadth of options"}),
            ("p3", "m2", self.ZCODE_MAIN, 1,
             {"type": "text", "text": "here are five architectures"}),
            ("p4", "m2", self.ZCODE_MAIN, 2,
             {"type": "tool", "callID": "call_1", "tool": "Edit",
              "state": {"status": "completed",
                        "input": {"file_path": "/tmp/proj-wiki/index.md", "new_str": "obelisk"},
                        "output": "the file has been updated with the obelisk section"}}),
            ("p5", "m3", self.ZCODE_OTHER_PROJECT, 0,
             {"type": "text", "text": "unrelated work in another project"}),
        ]
        for pid, mid, sid, seq, payload in parts:
            conn.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data, sequence)"
                " VALUES (?, ?, ?, 0, 0, ?, ?)", (pid, mid, sid, json.dumps(payload), seq))
        conn.commit()
        conn.close()
        return db

    def test_zcode_sql_prefilter_tolerates_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            db = self._write_zcode_fixture(home)
            import sqlite3

            conn = sqlite3.connect(db)
            # Store the needle as a JSON unicode escape: the SQL prefilter
            # must not reject the row before Python matching can decode it.
            conn.execute(
                "UPDATE part SET data = ? WHERE id = 'p5'",
                (json.dumps({"type": "text", "text": "needle"}).replace("needle", r"\u006eeedle"),))
            conn.commit()
            conn.close()
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = search_sessions.run(search_sessions.parse_args([
                    "--harness", "zcode", "--query", "needle",
                ]), home)
            self.assertEqual(rc, 0)
            sessions = json.loads(out.getvalue())["sessions"]
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["session_id"], self.ZCODE_OTHER_PROJECT)
            self.assertIn("needle", sessions[0]["hits"][0]["excerpt"])

    def test_zcode_finder_filters_and_previews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._write_zcode_fixture(home)
            candidates = find_sessions.find_zcode(home)
            ids = {candidate.id for candidate in candidates}
            self.assertIn(self.ZCODE_MAIN, ids)
            self.assertIn(self.ZCODE_FORK, ids)  # forks are user-facing
            self.assertNotIn(self.ZCODE_SUB, ids)  # subagents are listing noise
            self.assertNotIn(self.ZCODE_DELETED, ids)  # deleted stays hidden
            main = next(c for c in candidates if c.id == self.ZCODE_MAIN)
            self.assertEqual(main.harness, "zcode")
            self.assertEqual(main.project, "/tmp/proj-wiki")
            self.assertTrue(main.preview.startswith("rethink the wiki"))  # boilerplate skipped
            self.assertEqual(main.resume_command, f"zcode --resume {self.ZCODE_MAIN}")
            self.assertTrue(main.updated_at.endswith("+00:00"))

    def test_zcode_cross_search_kinds_provenance_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._write_zcode_fixture(home)
            args = search_sessions.parse_args(
                ["--harness", "zcode", "--query", "obelisk", "--project", "proj-wiki",
                 "--since", "30d", "--format", "json"])
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = search_sessions.run(args, home)
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(len(payload["sessions"]), 1)
            match = payload["sessions"][0]
            self.assertEqual(match["session_id"], self.ZCODE_MAIN)
            self.assertEqual(match["project"], "/tmp/proj-wiki")
            kinds = {hit["kind"] for hit in match["hits"]}
            self.assertIn("user", kinds)
            self.assertIn("tool_call", kinds)
            self.assertIn("tool_result", kinds)
            tool_hits = [hit for hit in match["hits"] if hit["kind"] == "tool_call"]
            self.assertTrue(tool_hits and tool_hits[0]["tool"] == "Edit")
            self.assertIn("msg 1 part 2", {hit["source_ref"] for hit in match["hits"]})
            user_hit = next(hit for hit in match["hits"] if hit["kind"] == "user")
            self.assertEqual(user_hit["model"], "GLM-5.3")
            self.assertEqual(user_hit["provider"], "account:zai-individual-coding-plan")
            self.assertIn("zettelkasten", user_hit["excerpt"])

    def test_zcode_single_session_and_prefix_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            db = self._write_zcode_fixture(home)
            out = io.StringIO()
            err = io.StringIO()
            env = {"ZCODE_DB": str(db)}
            with mock.patch.dict("os.environ", env), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = search_session.main([self.ZCODE_MAIN[:13], "--type", "user",
                                          "--query", "zettelkasten", "--format", "jsonl"])
            self.assertEqual(rc, 0)
            events = [json.loads(line) for line in out.getvalue().splitlines()]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["kind"], "user")
            self.assertTrue(events[0]["message_id"])  # table id threaded through
            self.assertIn("zettelkasten", events[0]["preview"])
            self.assertEqual(events[0]["source_ref"], "msg 0 part 1")

    def test_zcode_inspect_reports_activity_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            db = self._write_zcode_fixture(home)
            out = io.StringIO()
            err = io.StringIO()
            env = {"ZCODE_DB": str(db)}
            with mock.patch.dict("os.environ", env), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = inspect_session.main([self.ZCODE_MAIN[:13], "--max-prompts", "2"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["harness"], "zcode")
            self.assertEqual(result["project"], "/tmp/proj-wiki")
            self.assertEqual(result["tool_call_summary"], {"Edit": 1})
            self.assertEqual(result["files_touched"], ["/tmp/proj-wiki/index.md"])
            self.assertEqual(result["user_prompt_previews"],
                             ["rethink the wiki with a zettelkasten obelisk"])
            self.assertEqual(result["resume_command"], f"zcode --resume {self.ZCODE_MAIN}")


if __name__ == "__main__":
    unittest.main()
