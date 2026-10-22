---
name: telegram-bridge
description: >
  Use when bermudi asks to send something to his Telegram — "send X to
  telegram", "telegram me this", "voice-note me this", "notify me on
  telegram". Sends text messages, files, or TTS voice notes he checks on
  his phone, using the local telegram-bridge scripts.
---

Senders live in `/home/daniel/build/telegram-bridge/` — invoke by absolute
path, they work from any cwd. Dispatch on what X is:

- **A file path** (pdf, image, log, existing audio):
  `…/tg.py file /path [--caption "..."]`
- **Prose / a message to deliver** (the usual case): send it as a voice
  note — `printf '%s' "the text" | tgsay` (edge-tts → OGG/Opus, arrives
  playable on his phone). Options: `--voice NAME`, `--rate "+10%"`,
  `--dry-run` (synthesize only, print the path, don't send).
  Exception: long or structured text (logs, code, tables) is better as a
  text message — `…/tg.py msg "text"` — nobody listens to a stack trace.
- **Quick ping**: `…/tg.py msg "text"`. Text over 4096 chars (UTF-16)
  auto-escalates: one rich markdown bubble up to 32768 chars (falls back
  to plain chunks if the rich parser rejects it), plain chunks beyond —
  a long message never needs manual splitting.
- **Scheduling / reminders** ("remind me to X at 17:00", "in 2h nudge me"):
  `uv run --project /home/daniel/build/telegram-bridge remind add --at "2026-10-13 17:00" "text"`
  or `… --project … remind add --in 2h "text"` — stored on an always-on
  server, fires even with this workstation off. Subcommands: `list`,
  `show`, `cancel`, `retry`, `health` (details: `REMINDERS.md` in the repo).
  ⚠️ DEPLOYED AND LIVE since 2026-10-12 (lithium). If `remind health`
  reports the worker NOT ALIVE or clock UNHEALTHY, say so instead of
  promising the reminder; details in the repo's AGENTS.md.

Rules:

- Never read, cat, or print `config.json` next to the scripts: it holds a
  live bot token. Credentials are handled inside the scripts (env
  `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`, or that config file).
- `tgsay` needs `ffmpeg`/`ffprobe` on PATH; its Python deps come from its
  uv script header, so execute it directly.
- `tgsay`/`tg.py` print progress lines (endpoint failover notice, "sending
  N KB…", "upload stalled … retrying"): informational. A stalled upload
  retries once on a fresh connection and fails loudly on a second stall
  (audio kept at the printed path — report that, don't discard it).
- This is his real phone. One send per request; report the outcome in your
  reply instead of sending extra Telegram messages.
