# Media

Image, video, and audio understanding via the `gemini-media` MCP, called through
mcporter: `mcporter call gemini-media.<tool> key=value`.

All media tools are Gemini calls. Image tools accept a local file path or
remote URL. **No clipboard support** — save the image to disk first
(e.g. `grim > /tmp/x.png`).

Audio tools accept a YouTube URL directly — no download needed.

**Cheaper route for YouTube audio:** pull the video's own captions via
[youtube-captions.md](youtube-captions.md) — free, instant, no model — before
reaching for the Gemini `transcribe_segment` below. Gemini is the escalation
when captions are absent.

## Decision Guide

```
What does the user have?
│
├── An image, and they want the TEXT out of it
│   (code, terminal output, a document, log lines, an error message)
│   → analyze_image with a verbatim-transcription prompt
│     ("Transcribe the text exactly, preserving line breaks"),
│     MINIMAL/LOW thinking unless meaning matters
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

**Rule of thumb:** for transcription, use `analyze_image` with an explicit
verbatim-transcription prompt and low thinking — cheapest call that gets text
out of an image. Reserve higher thinking for when meaning, not just text, is
the goal.

For audio/video, the same principle applies: existing YouTube captions
([youtube-captions.md](youtube-captions.md)) and local pipelines beat a Gemini
call when they can answer the question.

## Timeouts

Each command example below shows the correct mcporter `--timeout`. For the
outer pi bash `timeout` (seconds), use `150` for image tools and `330` for
video and audio. **Pi's bash timeout must be
strictly greater than mcporter's timeout in seconds** — mcporter handles its
timeout cleanly; pi's SIGKILL does not.

```bash
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

| Tool | What it does | Key params |
|------|--------------|------------|
| `analyze_image` | Single-image understanding/description/transcription | `image_source`, `prompt`, `thinking?` |
| `compare_images` | Two-image diff (expected vs actual) | `expected_image_source`, `actual_image_source`, `prompt`, `thinking?` |
| `analyze_video` | Video scenes, moments, entities | `video_source`, `prompt`, `thinking?` |
| `verify_speaker` | Who said a quote? → structured verdict | `youtube_url`, `quote_to_locate`, `claimed_speaker`, `known_speakers`, `thinking?` |
| `transcribe_segment` | Verbatim segment + speaker ID | `youtube_url`, `start_time?`, `end_time?`, `quote_to_locate?`, `known_speakers?`, `thinking?` |

Model is fixed server-side (**`gemini-3.5-flash-lite`**) — there is no `model=`
override.

Default thinking: **`MEDIUM`**. Every tool reasons before responding and
accepts an optional `thinking=` override — `MINIMAL`/`LOW` for simple perception
and verbatim transcription (fast, cheap), `MEDIUM` default for general analysis,
`HIGH` for diagnosis, codegen from a mockup, or complex multi-step reasoning
from a diagram. Lower thinking = lower latency + cost.

```bash
# Simple perception — minimal thinking, fastest/cheapest
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/img.png" prompt="What color is the button?" thinking="MINIMAL"

# Hard reasoning — high thinking
mcporter call gemini-media.analyze_image --timeout 120000 \
  image_source="path/to/error.png" prompt="Diagnose this error and propose a fix" thinking="HIGH"
```

## Tool Details

### analyze_image — understanding, description, transcription

Single image → Gemini. Describe contents, answer questions, extract meaning,
identify objects/diagrams/charts, or transcribe text verbatim with a prompt
like "Transcribe the text exactly, preserving line breaks" (use `thinking="LOW"`
for plain transcription; higher only if the text is stylized or the layout
matters).

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
- **The model is fixed to gemini-3.5-flash-lite** — you cannot swap models per
  call. Tune difficulty with `thinking=` instead.
- **Default mcporter timeout (60s) is too short** for Gemini calls. Always
  pass `--timeout` explicitly — see the command examples above.
- **File paths must exist on disk** or be accessible remote URLs.
- **Audio tools only accept YouTube URLs.** Not local audio files or other
  platforms. Supported formats: `youtube.com/watch?v=`, `youtu.be/`,
  `m.youtube.com`, `/embed/`, `/shorts/`, `/live/`, `music.youtube.com`.
- **YouTube URL input is a Gemini preview feature.** Pricing/rate limits may
  change. Audio tools use structured JSON output, which requires a model that
  supports `responseSchema` (Flash/Pro family) — satisfied by the fixed default
  model.
