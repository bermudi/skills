---
name: media
description: >
  Transcribe or analyze images, video, and audio. Use when read returned "model
  does not support images" or "image will be omitted", when you need OCR on a
  screenshot, or when you need to verify who said a quote in a YouTube video.
  Local tesseract for fast free image transcription; Gemini for understanding,
  comparison, video analysis, and audio speaker verification.
---

# Media

Image, video, and audio understanding via the `gemini-media` MCP, called through
mcporter: `mcporter call gemini-media.<tool> key=value`.

**If `read` returned "model does not support images" or "image will be omitted"**
— you're in the right place. Use the appropriate tool below for the image instead.

All vision tools accept a local file path or remote URL. **No clipboard support**
— save the image to disk first (e.g. `grim > /tmp/x.png`).

Audio tools accept a YouTube URL directly — no download needed.

## Decision Guide

```
What does the user have?
│
├── An image, and they want the TEXT out of it
│   (code, terminal output, a document, log lines, an error message)
│   → ocr  (local tesseract: instant, free, no rate limits)
│       └─ only reach for analyze_image if OCR fails (handwriting,
│          low-contrast/stylized text, mixed text+graphics where
│          meaning matters more than verbatim text)
│
├── An image, and they want UNDERSTANDING or DESCRIPTION
│   (what's in this photo, read this diagram, describe this UI,
│    what does this chart show)
│   → analyze_image
│
├── Two images to COMPARE (expected vs actual, before/after,
│   design vs implementation)
│   → compare_images
│
├── A video file → analyze_video
│
├── A YouTube video, and they need to verify WHO SAID a quote
│   (transcript attribution is uncertain, deferred note needs audio
│    confirmation, speaker boundaries are ambiguous)
│   → verify_speaker
│
└── A YouTube video, and they need the VERBATIM TEXT of a segment
    (exact quote for citation, fact-check transcript accuracy, get
     surrounding context for a quote)
    → transcribe_segment
```

**Rule of thumb:** reach for `ocr` first when the goal is *transcription*. It's
local (~0.1s), free, and never rate-limited. Use `analyze_image` only when you
need meaning, description, or OCR-quality is insufficient.

## Timeouts

| Tool | mcporter `--timeout` | pi bash `timeout` |
|------|---------------------|-------------------|
| `ocr` (local) | `15000` (15s) | `30` |
| Gemini image tools | `120000` (2 min) | `150` (2.5 min) |
| `analyze_video` | `300000` (5 min) | `330` (5.5 min) |
| Audio tools (YouTube) | `300000` (5 min) | `330` (5.5 min) |

The rule: pi's bash timeout (seconds) must be > mcporter's timeout (seconds).
mcporter handles the timeout cleanly; pi's SIGKILL does not.

```bash
# Local OCR — fast
mcporter call gemini-media.ocr --timeout 15000 \
  image_source="path/to/terminal.png"

# Gemini image analysis
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/img.png" prompt="Describe this diagram's data flow"

# Compare two UIs
mcporter call gemini-media.compare_images --timeout 120000 \
  expected_image_source="path/to/design.png" \
  actual_image_source="path/to/implementation.png" \
  prompt="Check spacing, color, and layout differences"

# Video
mcporter call gemini-media.analyze_video --timeout 300000 \
  video_source="path/to/clip.mp4" prompt="What happens in this video?"

# Verify who said a quote (audio)
mcporter call gemini-media.verify_speaker --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=..." \
  quote_to_locate="It's just turtles all the way down" \
  claimed_speaker="Sarah Isgur" \
  known_speakers='["Sarah Isgur","David French"]'

# Transcribe a segment by timestamp
mcporter call gemini-media.transcribe_segment --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=..." \
  start_time="33:35" end_time="33:50" \
  known_speakers='["Sarah Isgur","David French"]'
```

## Quick Reference

| Tool | Engine | What it does | Key params |
|------|--------|--------------|------------|
| `ocr` | local tesseract | Verbatim text transcription (fast, free) | `image_source` |
| `analyze_image` | Gemini | Single-image understanding/description | `image_source`, `prompt`, `model?`, `thinking?` |
| `compare_images` | Gemini | Two-image diff (expected vs actual) | `expected_image_source`, `actual_image_source`, `prompt`, `model?`, `thinking?` |
| `analyze_video` | Gemini (File API) | Video scenes, moments, entities | `video_source`, `prompt`, `model?`, `thinking?` |
| `verify_speaker` | Gemini (YouTube URL) | Who said a quote? → structured verdict | `youtube_url`, `quote_to_locate`, `claimed_speaker`, `known_speakers`, `model?`, `thinking?` |
| `transcribe_segment` | Gemini (YouTube URL) | Verbatim segment + speaker ID | `youtube_url`, `start_time?`, `end_time?`, `quote_to_locate?`, `known_speakers?`, `model?`, `thinking?` |

Default model: **`gemini-3.1-flash-lite`**. Override per call with `model=`
(e.g. `model="gemini-3.5-flash"` for harder reasoning, `model="gemini-3.5-pro"`
for the strongest model).

Default thinking: **`MEDIUM`**. Every Gemini tool reasons before responding and
accepts an optional `thinking=` override — `MINIMAL`/`LOW` for simple perception
(fast, cheap: "what color is this", "is there a button"), `MEDIUM` default for
general analysis, `HIGH` for diagnosis, codegen from a mockup, or complex
multi-step reasoning from a diagram. Lower thinking = lower latency + cost.

```bash
# Simple perception — minimal thinking, fastest/cheapest
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/img.png" prompt="What color is the button?" thinking="MINIMAL"

# Hard reasoning — high thinking
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/error.png" prompt="Diagnose this error and propose a fix" thinking="HIGH"
```

## Tool Details

### ocr — fast local transcription

`tesseract` on the image. Use as the **default** for extracting text/code/
terminal output/documents. ~0.1s, free, offline, no rate limits.

```bash
mcporter call gemini-media.ocr --timeout 15000 \
  image_source="path/to/error.png"
```

Falls short on handwriting, low-contrast/stylized text, and mixed
text+graphics where meaning matters — for those use `analyze_image`.

### analyze_image — understanding & description

Single image → Gemini. Describe contents, answer questions, extract meaning,
identify objects/diagrams/charts. Use when you need *understanding*, not just
transcription.

```bash
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/architecture.png" \
  prompt="Explain the data flow between these services"
```

### compare_images — two-image diff

First image = expected/reference, second = actual/candidate. Use for UI diff,
before/after, design vs implementation.

```bash
mcporter call gemini-media.compare_images --timeout 120000 \
  expected_image_source="path/to/design.png" \
  actual_image_source="path/to/implementation.png" \
  prompt="What visual differences are there?"
```

### analyze_video — video understanding

Video file or URL → Gemini File API. Understand scenes, extract moments,
identify activities. Max 8 MB, MP4/MOV/M4V.

```bash
mcporter call gemini-media.analyze_video --timeout 300000 \
  video_source="path/to/demo.mp4" \
  prompt="What happens in this video? Describe key moments."
```

### verify_speaker — audio attribution verification

YouTube URL + quote → Gemini listens to the actual audio and identifies who
said it. Returns a structured verdict: `confirmed`, `misattributed` (with the
actual speaker), `ambiguous`, or `not_found` — plus a verbatim quote and
timestamps.

Use when transcript attribution is uncertain: speaker boundaries are ambiguous,
a deferred note needs audio confirmation, or two speakers overlap and the
transcript can't tell them apart.

```bash
mcporter call gemini-media.verify_speaker --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=OYs2VF4ivsw" \
  quote_to_locate="It's just turtles all the way down" \
  claimed_speaker="Sarah Isgur" \
  known_speakers='["Sarah Isgur","David French"]'
```

Pass `known_speakers` as a JSON array of all hosts/guests in the audio — this
helps Gemini map voices to names. The `claimed_speaker` is the attribution
under verification; Gemini compares it against the actual voice.

### transcribe_segment — verbatim segment transcription

YouTube URL + time range or quote → verbatim transcription with speaker ID.
Returns the exact words spoken, identified speaker, and timestamps.

Use for fact-checking transcript accuracy, getting exact quotes for citation,
or resolving attribution when `verify_speaker` returned `ambiguous` and you
need the surrounding context.

```bash
# By timestamp range
mcporter call gemini-media.transcribe_segment --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=OYs2VF4ivsw" \
  start_time="33:30" end_time="33:50" \
  known_speakers='["Sarah Isgur","David French"]'

# By quote to locate (Gemini finds the closest match)
mcporter call gemini-media.transcribe_segment --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=OYs2VF4ivsw" \
  quote_to_locate="turtles all the way down" \
  known_speakers='["Sarah Isgur","David French"]'
```

Timestamps must be `MM:SS` or `HH:MM:SS` format. If `end_time` is omitted,
Gemini transcribes ~30 seconds from `start_time`. If `known_speakers` is
omitted, Gemini returns generic labels (Speaker 1, Speaker 2, etc.).

## Gotchas

- **No clipboard input.** Save the image to disk first (`grim`, `spectacle`,
  `curl`, etc.). KDE's clipboard manager makes "current clipboard" unreliable.
- **Pick ocr vs analyze_image deliberately.** `ocr` transcribes verbatim and is
  free/instant; `analyze_image` understands and costs a Gemini call. For "get
  this text off my screen", `ocr` is almost always right.
- **gemini-3.1-flash-lite is the default** for speed and low rate-limit
  pressure. Bump to `gemini-3.5-flash` or `gemini-3.5-pro` per call when you
  need stronger reasoning.
- **Default mcporter timeout (60s) is too short** for Gemini calls.
  Always pass `--timeout 120000` for images, `--timeout 300000` for video and
  audio. Local `ocr` only needs `--timeout 15000`.
- **File paths must exist on disk** or be accessible remote URLs.
- **Audio tools only accept YouTube URLs.** Not local audio files or other
  platforms. Supported formats: `youtube.com/watch?v=`, `youtu.be/`,
  `m.youtube.com`, `/embed/`, `/shorts/`, `/live/`, `music.youtube.com`.
- **YouTube URL input is a Gemini preview feature.** Pricing/rate limits may
  change. Audio tools use structured JSON output, which requires a model that
  supports `responseSchema` (Flash/Pro family). Don't override `model=` to one
  without structured output support.
