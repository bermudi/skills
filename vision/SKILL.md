---
name: vision
description: >
  Transcribe or analyze images and video. Use when read returns "model does
  not support images" or "image will be omitted", or when you need OCR on a
  screenshot. Local tesseract for fast free transcription; Gemini for
  understanding, comparison, and video.
---

# Vision

Image/video understanding via the `gemini-vision` MCP, called through mcporter:
`mcporter call gemini-vision.<tool> key=value`.

**If `read` returned "model does not support images" or "image will be omitted"**
— you're in the right place. Use the appropriate tool below for the image instead.

All tools accept a local file path or remote URL. **No clipboard support** —
save the image to disk first (e.g. `grim > /tmp/x.png`).

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
└── A video file → analyze_video
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

The rule: pi's bash timeout (seconds) must be > mcporter's timeout (seconds).
mcporter handles the timeout cleanly; pi's SIGKILL does not.

```bash
# Local OCR — fast
mcporter call gemini-vision.ocr --timeout 15000 \
  image_source="path/to/terminal.png"

# Gemini image analysis
mcporter call gemini-vision.analyze_image --timeout 120000 \
  image_source="path/to/img.png" prompt="Describe this diagram's data flow"

# Compare two UIs
mcporter call gemini-vision.compare_images --timeout 120000 \
  expected_image_source="path/to/design.png" \
  actual_image_source="path/to/implementation.png" \
  prompt="Check spacing, color, and layout differences"

# Video
mcporter call gemini-vision.analyze_video --timeout 300000 \
  video_source="path/to/clip.mp4" prompt="What happens in this video?"
```

## Quick Reference

| Tool | Engine | What it does | Key params |
|------|--------|--------------|------------|
| `ocr` | local tesseract | Verbatim text transcription (fast, free) | `image_source` |
| `analyze_image` | Gemini | Single-image understanding/description | `image_source`, `prompt`, `model?`, `thinking?` |
| `compare_images` | Gemini | Two-image diff (expected vs actual) | `expected_image_source`, `actual_image_source`, `prompt`, `model?`, `thinking?` |
| `analyze_video` | Gemini (File API) | Video scenes, moments, entities | `video_source`, `prompt`, `model?`, `thinking?` |

Default model: **`gemini-3.1-flash-lite`**. Override per call with `model=`
(e.g. `model="gemini-3.5-flash"` for harder reasoning, `model="gemini-3.5-pro"`
for the strongest vision model).

Default thinking: **`MEDIUM`**. Every Gemini tool reasons before responding and
accepts an optional `thinking=` override — `MINIMAL`/`LOW` for simple perception
(fast, cheap: "what color is this", "is there a button"), `MEDIUM` default for
general analysis, `HIGH` for diagnosis, codegen from a mockup, or complex
multi-step reasoning from a diagram. Lower thinking = lower latency + cost.

```bash
# Simple perception — minimal thinking, fastest/cheapest
mcporter call gemini-vision.analyze_image --timeout 120000 \
  image_source="path/to/img.png" prompt="What color is the button?" thinking="MINIMAL"

# Hard reasoning — high thinking
mcporter call gemini-vision.analyze_image --timeout 120000 \
  image_source="path/to/error.png" prompt="Diagnose this error and propose a fix" thinking="HIGH"
```

## Tool Details

### ocr — fast local transcription

`tesseract` on the image. Use as the **default** for extracting text/code/
terminal output/documents. ~0.1s, free, offline, no rate limits.

```bash
mcporter call gemini-vision.ocr --timeout 15000 \
  image_source="path/to/error.png"
```

Falls short on handwriting, low-contrast/stylized text, and mixed
text+graphics where meaning matters — for those use `analyze_image`.

### analyze_image — understanding & description

Single image → Gemini. Describe contents, answer questions, extract meaning,
identify objects/diagrams/charts. Use when you need *understanding*, not just
transcription.

```bash
mcporter call gemini-vision.analyze_image --timeout 120000 \
  image_source="path/to/architecture.png" \
  prompt="Explain the data flow between these services"
```

### compare_images — two-image diff

First image = expected/reference, second = actual/candidate. Use for UI diff,
before/after, design vs implementation.

```bash
mcporter call gemini-vision.compare_images --timeout 120000 \
  expected_image_source="path/to/design.png" \
  actual_image_source="path/to/implementation.png" \
  prompt="What visual differences are there?"
```

### analyze_video — video understanding

Video file or URL → Gemini File API. Understand scenes, extract moments,
identify activities. Max 8 MB, MP4/MOV/M4V.

```bash
mcporter call gemini-vision.analyze_video --timeout 300000 \
  video_source="path/to/demo.mp4" \
  prompt="What happens in this video? Describe key moments."
```

## Gotchas

- **No clipboard input.** Save the image to disk first (`grim`, `spectacle`,
  `curl`, etc.). KDE's clipboard manager makes "current clipboard" unreliable.
- **Pick ocr vs analyze_image deliberately.** `ocr` transcribes verbatim and is
  free/instant; `analyze_image` understands and costs a Gemini call. For "get
  this text off my screen", `ocr` is almost always right.
- **gemini-3.1-flash-lite is the default** for speed and low rate-limit
  pressure. Bump to `gemini-3.5-flash` or `gemini-3.5-pro` per call when you
  need stronger reasoning.
- **Default mcporter timeout (60s) is too short** for Gemini image calls.
  Always pass `--timeout 120000` for images, `--timeout 300000` for video.
  Local `ocr` only needs `--timeout 15000`.
- **File paths must exist on disk** or be accessible remote URLs.
