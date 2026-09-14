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
- **Quick ping**: `…/tg.py msg "text"`

Rules:

- Never read, cat, or print `config.json` next to the scripts: it holds a
  live bot token. Credentials are handled inside the scripts (env
  `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`, or that config file).
- `tgsay` needs `ffmpeg`/`ffprobe` on PATH; its Python deps come from its
  uv script header, so execute it directly.
- This is his real phone. One send per request; report the outcome in your
  reply instead of sending extra Telegram messages.
