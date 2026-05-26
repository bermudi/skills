---
name: vision
description: >
  Analyze images, screenshots, videos, diagrams, charts, and UI mockups. Use 
  when read returns "model does not support images" or "image will be omitted" — 
  fall back to mcporter call zai-vision instead.
---

# Vision

Visual understanding via Z.AI GLM-4.6V, called through mcporter:
`mcporter call zai-vision.<tool> key=value`.

**If `read` returned "model does not support images" or "image will be omitted"** —
you're in the right place. Use the appropriate tool below for the image instead.

All tools accept `image_source` (local file path or remote URL). Video tools
accept `video_source` (local path or URL, ≤8 MB, MP4/MOV/M4V).

## Decision Guide

```
What does the user have?
│
├── A screenshot or image
│   ├── UI design / mockup → ui_to_artifact
│   │   ├── Want code? → output_type=code
│   │   ├── Want a prompt for another AI? → output_type=prompt
│   │   ├── Want design specs? → output_type=spec
│   │   └── Just describe it → output_type=description
│   │
│   ├── Text to extract (code, terminal, docs) → extract_text_from_screenshot
│   ├── Error message / stack trace → diagnose_error_screenshot
│   ├── Technical diagram (architecture, UML, flowchart) → understand_technical_diagram
│   ├── Chart / graph / dashboard → analyze_data_visualization
│   └── None of the above → analyze_image (general fallback)
│
├── Two UI screenshots to compare → ui_diff_check
│
└── A video file → analyze_video
```

## Quick Reference

| Tool | What it does | Key params |
|------|-------------|------------|
| `ui_to_artifact` | UI → code, prompt, spec, or description | `image_source`, `output_type`, `prompt` |
| `extract_text_from_screenshot` | OCR for code, terminals, docs | `image_source`, `prompt`, `programming_language?` |
| `diagnose_error_screenshot` | Error analysis + actionable fixes | `image_source`, `prompt`, `context?` |
| `understand_technical_diagram` | Architecture, UML, flowcharts, ER | `image_source`, `prompt`, `diagram_type?` |
| `analyze_data_visualization` | Charts, dashboards, graphs | `image_source`, `prompt`, `analysis_focus?` |
| `ui_diff_check` | Compare expected vs actual UI | `expected_image_source`, `actual_image_source`, `prompt` |
| `analyze_image` | General-purpose image understanding | `image_source`, `prompt` |
| `analyze_video` | Video scenes, moments, entities | `video_source`, `prompt` |

## Tool Details

### ui_to_artifact — UI screenshots to artifacts

Turn a UI screenshot into code, an AI prompt, design specs, or a description.
Pick `output_type` based on what the user wants:

```bash
# Generate frontend code
mcporter call zai-vision.ui_to_artifact \
  image_source="path/to/mockup.png" \
  output_type=code \
  prompt="Generate a React component with Tailwind CSS"

# Generate an AI prompt for another model to recreate this UI
mcporter call zai-vision.ui_to_artifact \
  image_source="path/to/mockup.png" \
  output_type=prompt \
  prompt="Describe this UI for an AI image generator"

# Extract design specifications
mcporter call zai-vision.ui_to_artifact \
  image_source="path/to/mockup.png" \
  output_type=spec \
  prompt="Extract colors, spacing, typography"

# Natural language description
mcporter call zai-vision.ui_to_artifact \
  image_source="path/to/mockup.png" \
  output_type=description \
  prompt="Describe the layout and components"
```

### extract_text_from_screenshot — OCR

Extract text from screenshots of code, terminal output, documentation, or
anything with text. Optionally specify the programming language for code
screenshots.

```bash
mcporter call zai-vision.extract_text_from_screenshot \
  image_source="path/to/terminal.png" \
  prompt="Extract the error message and stack trace"

mcporter call zai-vision.extract_text_from_screenshot \
  image_source="path/to/code.png" \
  prompt="Extract the function signatures" \
  programming_language="typescript"
```

### diagnose_error_screenshot — Error diagnosis

Analyze error screenshots and propose actionable fixes. Provide context about
when the error occurred for better diagnosis.

```bash
mcporter call zai-vision.diagnose_error_screenshot \
  image_source="path/to/error.png" \
  prompt="What caused this error and how do I fix it?" \
  context="during npm install"
```

### understand_technical_diagram — Diagram interpretation

Interpret architecture diagrams, flowcharts, UML, ER diagrams, sequence
diagrams. Optionally specify the diagram type for better results.

```bash
mcporter call zai-vision.understand_technical_diagram \
  image_source="path/to/architecture.png" \
  prompt="Explain the data flow between services" \
  diagram_type="architecture"
```

### analyze_data_visualization — Charts and dashboards

Extract insights from charts, graphs, and dashboards. Optionally focus on
trends, anomalies, comparisons, or performance metrics.

```bash
mcporter call zai-vision.analyze_data_visualization \
  image_source="path/to/dashboard.png" \
  prompt="What are the key metrics and trends?" \
  analysis_focus="trends"
```

### ui_diff_check — Compare two UIs

Compare a reference/expected UI screenshot against an actual implementation.
Catches visual drift and implementation discrepancies.

```bash
mcporter call zai-vision.ui_diff_check \
  expected_image_source="path/to/design.png" \
  actual_image_source="path/to/implementation.png" \
  prompt="Check for spacing, color, and layout differences"
```

### analyze_image — General-purpose fallback

Use when none of the specialized tools fit. Works for any image.

```bash
mcporter call zai-vision.analyze_image \
  image_source="path/to/photo.jpg" \
  prompt="Describe what's in this image in detail"
```

### analyze_video — Video understanding

Analyze video content: scenes, actions, objects, people. Supports local files
and remote URLs. Max 8 MB, MP4/MOV/M4V.

```bash
mcporter call zai-vision.analyze_video \
  video_source="path/to/demo.mp4" \
  prompt="What happens in this video? Describe key moments."
```

## Gotchas

- **File paths must exist on disk** or be accessible remote URLs. The tool
  can't see images pasted into chat — save them first.
- **Video limit is 8 MB.** For larger files, trim or compress first.
- **Pick the right tool.** Using `analyze_image` for a UI mockup will give a
  description, not code — use `ui_to_artifact` instead. Using
  `extract_text_from_screenshot` for an error will transcribe it, not diagnose
  it — use `diagnose_error_screenshot`.
- **The `output_type` on `ui_to_artifact` must be exactly one of:** `code`,
  `prompt`, `spec`, `description`.
- **diagram_type is optional** but helps accuracy. Valid values include
  `architecture`, `flowchart`, `uml`, `er-diagram`, `sequence`.
