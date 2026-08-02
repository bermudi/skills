---
name: content-retrieval
description: >
  Use this skill when acquiring, extracting, searching, or understanding
  external content: documents (PDF, DOCX, PPTX, XLSX), audio, video, known
  URLs, websites, web search, online research, library documentation, or
  remote GitHub repositories: browsing trees, reading exact files, finding
  code examples, and understanding architecture. For an image or screenshot, do
  not trigger merely because it is attached: use direct model vision first.
  Trigger only after vision fails or the image is omitted/unsupported, or when
  the task specifically requires OCR or image comparison.
license: MIT
metadata:
  version: "1.0"
  topic: content-retrieval
---

# Content Retrieval

Acquire and understand external content through one routing interface. Choose
by **input and intent**, not by provider. Start local and deterministic; pay for
remote/model-based processing only when the cheaper route cannot answer the
question.

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
│   ├── Direct read says unsupported/omitted, or vision otherwise fails
│   │   ├── Need verbatim text/code/error output → local OCR
│   │   └── Need meaning, chart/diagram/UI understanding → image analysis
│   ├── User specifically requests exact OCR/transcription → local OCR
│   └── User specifically requests image comparison → image comparison
│
├── Audio or video
│   ├── Video understanding → video analysis
│   ├── Verify who said a YouTube quote → speaker verification
│   └── Need exact words from a YouTube segment → segment transcription
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

- **Documents:** read
  [LiteParse](references/documents/liteparse.md) before local extraction. Read
  [Mistral Document AI](references/documents/mistral.md) when LiteParse is
  insufficient, the document is multilingual/layout-heavy, or typed structured
  extraction is required.
- **Images:** do not read the media guide for an ordinary attached-image task
  when the current model can inspect it directly. Read
  [Media](references/media.md) only after direct vision fails or reports the
  image omitted/unsupported, or for explicit OCR or image comparison.
- **Audio and video:** read [Media](references/media.md) before using Gemini
  media tools.
- **Known URLs, search, crawling, research, code search, GitHub repositories,
  or online docs:** read [Web](references/web/overview.md), then load only the
  tool-specific reference it points to. For surgical remote GitHub inspection,
  read [GitHub repository reads](references/web/github-repo-read.md).

For a document URL, classify by the content itself rather than leaving it in
the web lane. Downloading a PDF does not turn it into an HTML-extraction task.
For an image of a document, choose based on the requested result: local OCR for
verbatim text, Mistral for document structure, Gemini for visual meaning.

## Vision capability is observed, not assumed

Do not guess whether the current model has vision. For an ordinary request such
as “read this screenshot” or “what is in this photo,” let the model inspect the
attachment directly first. If it succeeds, stop: no skill or external tool is
needed.

If the attachment is absent from model context, direct inspection commonly
returns signals such as `model does not support images`, `image will be
omitted`, `screenshot was omitted`, or an explicit inability to view the file.
Treat that observed failure as the trigger to load the media guide and retry
through OCR or Gemini. Models often assume they have vision before trying, so
capability must be established by the actual read result rather than confidence
or model name.

Explicit requests for **verbatim OCR** or **image comparison** may use this
skill immediately because those are specialized operations, not ordinary
vision.

## Cost and escalation rules

1. **Use direct/local methods first:** native model vision, existing text layer,
   `curl`, LiteParse,
   local OCR, and shell search.
2. **Parse or fetch once, then save and search locally.** Repeated extraction
   wastes latency, money, and context.
3. **Escalate on a concrete failure signal:** absent text, broken reading
   order, illegible OCR, JS-only HTML, blocked fetch, or a request that needs
   semantic/visual reasoning.
4. **Keep outputs bounded.** Save large results to a file; return targeted
   windows, selected pages, or a concise synthesis rather than dumping an
   entire source into context.
5. **Preserve evidence.** Include URLs, page numbers, timestamps, or extracted
   line locations when the answer may need verification.

## MCP calls and timeouts

Several remote routes use `mcporter`, but ordinary content routing belongs in
this skill. Load the separate `mcporter` skill only to configure or troubleshoot
mcporter, inspect changing tool surfaces, or operate Colab MCP.

For non-trivial calls, set both timeouts. `mcporter --timeout` is milliseconds;
the outer shell timeout is seconds and must be strictly greater. Let mcporter
time out first so it can return a useful error instead of being killed silently.
The relevant reference gives concrete values.

## Common mistakes

- Do not load this skill merely because an image is attached.
- Do not trust the model's assumption that it has vision; try direct inspection
  and react to the observed result.
- Do not use Gemini image understanding when native vision already answered the
  ordinary image question or local OCR can transcribe the text.
- Do not send a born-digital PDF to cloud OCR before trying its text layer.
- Do not repeatedly parse a document for each search term.
- Do not use natural-language prose with grep.app; search literal code patterns.
- Do not clone a GitHub repository merely to browse a tree or read one file;
  conversely, do not spend dozens of API calls avoiding a clone.
- Do not crawl a site when one known page or a map is enough.
- Do not assume a URL ending without `.pdf` is HTML; inspect its content type.
