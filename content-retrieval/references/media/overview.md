# Media

Image, video, and audio understanding via the `gemini-media` MCP, called through
mcporter: `mcporter call gemini-media.<tool> key=value`. Run `mcporter list gemini-media`
for live schemas.

All media tools are Gemini calls. Image tools accept a local file path or
remote URL. **No clipboard support** — save the image to disk first
(e.g. `grim > /tmp/x.png`).

YouTube tools accept a YouTube URL directly — no download needed.

**Cheaper route for YouTube words:** pull the video's own captions via
[youtube-captions.md](youtube-captions.md) — free, instant, no model — before
reaching for Gemini `transcribe_segment`. Escalate to Gemini when captions are
absent, when you need speaker attribution, or when you need visual understanding.

## Decision Guide

```text
What does the user have?
│
├── An image, and they want the TEXT out of it (code, terminal, logs, error)
│   → analyze_image with a verbatim-transcription prompt, thinking="LOW" (or "MINIMAL")
│
├── An image, and they want UNDERSTANDING or DESCRIPTION (diagram, chart, UI)
│   → analyze_image (default MEDIUM; HIGH for diagnosis/complex reasoning)
│
├── Two images to COMPARE (expected vs actual, before/after, design vs impl)
│   → compare_images
│
├── An image, and they need BOUNDING BOXES or POLYGON MASKS
│   ├── Boxes + labels → detect_objects
│   └── Boxes + labels + polygon masks → segment_objects (thinking="MINIMAL")
│
├── A local or remote VIDEO file (≤8 MB, MP4/MOV/M4V) → analyze_video
│
├── A YouTube video, and they want VISUAL + AUDIO understanding → analyze_youtube_video
│
├── A YouTube video, and they need to verify WHO SAID a quote → verify_speaker
│
└── A YouTube video, and they need VERBATIM TEXT + speaker ID of a segment → transcribe_segment
```

## Timeouts

Set `--timeout` (ms) explicitly — mcporter's 60s default is too short for Gemini.
Outer shell timeout must strictly exceed `--timeout` (seconds in Pi, ms in Claude/Devin;
see the `mcporter` skill):

| Tool group | `--timeout` (ms) | Outer shell timeout |
|---|---|---|
| Image tools (`analyze_image`, `compare_images`, `detect_objects`, `segment_objects`) | `120000` (2 min) | >120s (e.g. 150s / 150000ms) |
| Video & YouTube tools (`analyze_video`, `analyze_youtube_video`, `verify_speaker`, `transcribe_segment`) | `300000` (5 min) | >300s (e.g. 330s / 330000ms) |
| `verify_keys` | default | default |

## Quick Reference

| Tool | What it does | Key params |
|------|--------------|------------|
| `analyze_image` | Single-image understanding, description, or verbatim transcription | `image_source`, `prompt`, `thinking?` |
| `compare_images` | Two-image diff (expected vs actual) | `expected_image_source`, `actual_image_source`, `prompt`, `thinking?` |
| `detect_objects` | Object detection → bounding boxes + labels | `image_source`, `prompt`, `thinking?` |
| `segment_objects` | Object segmentation → boxes + labels + polygon masks | `image_source`, `prompt`, `thinking?` |
| `analyze_video` | Local/URL video scenes & moments (≤8 MB, MP4/MOV/M4V) | `video_source`, `prompt`, `thinking?` |
| `analyze_youtube_video` | Public YouTube video visual + audio understanding | `youtube_url`, `prompt`, `thinking?` |
| `verify_speaker` | Who said a quote? → `confirmed` / `misattributed` / `ambiguous` / `not_found` | `youtube_url`, `quote_to_locate`, `claimed_speaker`, `known_speakers?`, `thinking?` |
| `transcribe_segment` | Verbatim YouTube segment + speaker ID | `youtube_url`, `start_time?`, `end_time?`, `quote_to_locate?`, `known_speakers?`, `thinking?` |
| `verify_keys` | Live-check configured Gemini keys (no tokens spent, no key material returned) | *(none)* |

## Examples

```bash
# Verbatim transcription (low thinking = faster & cheaper)
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/error.png" \
  prompt="Transcribe the text exactly, preserving line breaks" thinking="LOW"

# Compare two UIs
mcporter call gemini-media.compare_images --timeout 120000 \
  expected_image_source="path/to/design.png" \
  actual_image_source="path/to/implementation.png" \
  prompt="Check spacing, color, and layout differences"

# Segment objects (Gemini docs recommend MINIMAL thinking)
mcporter call gemini-media.segment_objects --timeout 120000 \
  image_source="path/to/scene.png" \
  prompt="segment the wooden and glass items" thinking="MINIMAL"

# Local video (<=8 MB)
mcporter call gemini-media.analyze_video --timeout 300000 \
  video_source="path/to/clip.mp4" prompt="What happens in this video?"

# Public YouTube video (visual + audio)
mcporter call gemini-media.analyze_youtube_video --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=..." \
  prompt="Summarize what is shown on screen at each major section"

# Verify who said a quote
mcporter call gemini-media.verify_speaker --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=..." \
  quote_to_locate="It's just turtles all the way down" \
  claimed_speaker="Sarah Isgur" \
  known_speakers='["Sarah Isgur","David French"]'

# Transcribe a segment (MM:SS or HH:MM:SS; omitting end_time transcribes ~30s)
mcporter call gemini-media.transcribe_segment --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=..." \
  start_time="33:35" end_time="33:50" \
  known_speakers='["Sarah Isgur","David French"]'
```

## Gotchas

- **Model is fixed server-side (`gemini-3.5-flash-lite`)** — no `model=` override. Tune difficulty with `thinking=`: `MINIMAL`/`LOW` for simple perception, verbatim transcription, and `segment_objects`; `MEDIUM` default for general analysis; `HIGH` for diagnosis, codegen from a mockup, or complex diagram reasoning.
- **No clipboard input.** Save to disk first (`grim`, `spectacle`, `curl`). KDE's clipboard manager makes clipboard reads unreliable.
- **`analyze_video` cap:** max 8 MB, MP4/MOV/M4V. For public YouTube videos, use `analyze_youtube_video` instead of downloading.
- **YouTube audio/video tools only accept public YouTube URLs** (`youtube.com/watch?v=`, `youtu.be/`, `m.youtube.com`, `/embed/`, `/shorts/`, `/live/`, `music.youtube.com`) — not local audio files or private videos.
- **`known_speakers`** is a JSON array string (e.g. `'["Alice","Bob"]'`). Omitting it returns generic labels (`Speaker 1`, `Speaker 2`).
- **Auth/key issues:** run `mcporter call gemini-media.verify_keys` to verify both configured keys without spending tokens.
