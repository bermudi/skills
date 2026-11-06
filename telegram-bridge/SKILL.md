---
name: telegram-bridge
description: >
  Use when bermudi asks to send something to Telegram: "telegram me this",
  "voice-note me this", "notify me on telegram". Sends text, files or TTS
  voice notes.
---

Scripts live in `/home/daniel/build/telegram-bridge/`; call them by absolute path. Dispatch on what X is:

- **File** (pdf, image, log, audio): `…/tg.py file /path [--caption "..."]`
- **Prose to deliver** (default): voice note, `printf '%s' "the text" | tgsay` (`--voice NAME`, `--rate "+10%"`, `--dry-run` synthesizes without sending). Long or structured text (logs, code, tables) goes as text instead: nobody listens to a stack trace.
- **Quick ping / text**: `…/tg.py msg "text"`. Over 4096 chars it escalates itself (one rich bubble to 32768, plain chunks beyond); never split manually.
- **Reminders** ("remind me at 17:00", "in 2h"): `uv run --project /home/daniel/build/telegram-bridge remind add --at "2026-10-13 17:00" "text"` or `--in 2h`. Stored on an always-on server (lithium, live since 2026-10-12) so it fires with this workstation off. Also `list`, `show`, `cancel`, `retry`, `health`; details in the repo's `REMINDERS.md`. If `remind health` says the worker is NOT ALIVE or the clock UNHEALTHY, say so instead of promising the reminder.

Rules:

- Never read or print the `config.json` next to the scripts: live bot token.
- A stalled upload retries once, then fails loudly with the audio kept at the printed path; report that path, don't discard it.
- It's his real phone: one send per request, and report the outcome in your reply instead of sending extra messages.
