---
name: content-retrieval
description: >
  Use this skill when acquiring, extracting, searching, or understanding
  external content: documents, audio, video, images, URLs, websites, web
  search, online research, library documentation, or even remote GitHub
  repos.
license: MIT
metadata:
  version: "1.3"
  topic: content-retrieval
---

# Content Retrieval

Route by **input and intent**, not provider. Start local and deterministic; pay for remote or model-based processing only when the cheaper route can't answer.

## Route the task

```text
What does the user have?
│
├── Local document (PDF, DOCX, PPTX, XLSX, or document image)
│   ├── Need exact text, tables, or a few values
│   │   ├── Born-digital/simple → LiteParse, parse once and search the file
│   │   └── Scanned, complex, multilingual, or layout-sensitive → Mistral OCR
│   └── Need summary, classification, or answers → extract first; use Mistral
│       Q&A directly when whole-document model analysis is justified
│
├── Image or screenshot
│   ├── Ordinary description/question and model can see it → answer directly;
│   │   do not load or use this skill
│   ├── User specifically requests exact transcription → image analysis
│   │   with a verbatim-transcription prompt
│   └── User specifically requests image comparison → image comparison
│
├── Audio or video
│   ├── Video understanding (scenes, moments, what happens) → video analysis
│   ├── YouTube video and you need its words
│   │   ├── Captions exist → pull them directly via InnerTube (free, deterministic)
│   │   └── No captions, or need speaker ID on a segment → transcribe_segment
│   └── Verify who said a specific quote → speaker verification
│
├── Known URL
│   ├── Direct document/media URL → use the matching route above
│   ├── Raw file → curl
│   └── HTML → markdown negotiation → Jina Reader → Tavily Extract
│
├── Remote GitHub repository, path, or ref
│   ├── Browse a tree or read/compare exact files → gh repo read-dir/read-file
│   ├── Understand architecture or design → DeepWiki
│   ├── Find literal code patterns across repositories → grep.app
│   └── Search/traverse many files, build, or edit → clone and use local tools
│
├── Topic or question, no URL
│   ├── Quick/current fact → Tavily Search
│   ├── Synthesized research → Poe Research
│   └── Library documentation → Tavily Skill or Context7
│
└── Whole site → Tavily Map for discovery; Tavily Crawl for content
```

## Load only the relevant guide

- **Documents:** [LiteParse](references/documents/liteparse.md) before any local extraction; [Mistral Document AI](references/documents/mistral.md) when LiteParse falls short, the document is multilingual or layout-heavy, or typed structured extraction is needed.
- **Images:** an ordinary attached image needs no guide (your own vision answers it). Explicit transcription or comparison: [Media overview](references/media/overview.md).
- **Audio/video:** [Media overview](references/media/overview.md) before any Gemini media tool; for a YouTube video's existing captions (free, no model) read [YouTube captions](references/media/youtube-captions.md) first.
- **URLs, search, crawling, research, code search, GitHub, online docs:** [Web](references/web/overview.md), then only the tool reference it points to; [GitHub repository reads](references/web/github-repo-read.md) for surgical remote inspection.

A document URL is classified by its content, not left in the web lane: downloading a PDF doesn't make it HTML extraction, and a URL without `.pdf` may still be one (check the content type). For an image of a document: image analysis for verbatim text or visual meaning, Mistral for document structure.

## Rules

1. Direct/local first: your own vision, an existing text layer, `curl`, LiteParse, shell search. A born-digital PDF never goes to cloud OCR before its text layer is tried.
2. Parse or fetch once, save to a file, search locally. Return targeted windows or a synthesis, not whole sources.
3. Escalate only on a concrete failure: no text, broken reading order, illegible OCR, JS-only HTML, blocked fetch, or a need for semantic/visual reasoning.
4. Keep evidence (URLs, pages, timestamps, line locations) when the answer may need verification.
5. grep.app takes literal code patterns, not prose. Don't clone a repo just to browse a tree or read one file, and don't burn dozens of API calls to avoid a clone. Don't crawl when one page or a map is enough.

## MCP timeouts

Several remote routes go through `mcporter`; load the `mcporter` skill only to configure or troubleshoot it or to operate Colab MCP. Set both timeouts on non-trivial calls: `--timeout` in ms, the outer shell timeout (seconds) strictly greater, so mcporter errors out instead of being killed silently. The relevant reference gives values.
