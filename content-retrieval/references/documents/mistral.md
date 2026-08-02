# Mistral Document AI

OCR, structured extraction, and document QnA via Mistral's
`mistral-ocr-latest` + chat models. Cloud-based, multilingual out of the box
(no language flag), preserves layout as Markdown. Complements `liteparse`
(local Tesseract): prefer this for scanned/complex docs, multilingual content,
tables, structured field extraction, or document Q&A. Use `liteparse` for
quick offline text extraction.

## Authenticate without exposing the key

The API key lives in Proton Pass. Give it only to the child process with
`pass-cli run`; do not materialize it in command output or source it into the
agent's shell:

```bash
export MISTRAL_API_KEY='pass://Keys/Mistral/Api Key'
PROTON_PASS_AGENT_REASON="OCR the document requested by the user" \
  pass-cli run -- uv run scripts/mistral_ocr.py report.pdf
```

The remaining examples show the underlying `uv run` command for readability.
When `MISTRAL_API_KEY` is a `pass://` reference rather than an already-resolved
process environment variable, wrap each command with `pass-cli run --` as
above.

## Extract text — the common case

`scripts/mistral_ocr.py` handles local files and URLs. It base64-encodes local
files, picks `document_url` vs `image_url` correctly, and prints extracted Markdown:

```bash
uv run scripts/mistral_ocr.py report.pdf                 # -> Markdown to stdout
uv run scripts/mistral_ocr.py scan.png -o scan.md        # -> write to file
uv run scripts/mistral_ocr.py https://example.com/doc.pdf
uv run scripts/mistral_ocr.py book.pdf --pages 0-4       # 0-indexed page subset
```

### Layout, blocks, tables, confidence, headers/footers

```bash
uv run scripts/mistral_ocr.py report.pdf --blocks                  # paragraph-level bboxes (OCR 4+)
uv run scripts/mistral_ocr.py report.pdf --table-format html       # tables as HTML separately (OCR 2512+)
uv run scripts/mistral_ocr.py report.pdf --confidence word         # per-word confidence scores
uv run scripts/mistral_ocr.py report.pdf --header --footer         # split out running headers/footers (OCR 2512+)
uv run scripts/mistral_ocr.py report.pdf --images                  # embed figures as base64
```

## Understand / analyze — structured extraction

Two annotation modes from the OCR API:

**Document annotation** — typed fields from the whole document
(receipts, invoices, forms). Pass a JSON Schema + prompt:

```bash
# invoice.schema.json defines { invoice_number, total, line_items, ... }
uv run scripts/mistral_ocr.py invoice.pdf \
  --prompt "Extract invoice number, total, and line items." \
  --schema invoice.schema.json
# -> { "invoice_number": "...", "total": "...", "line_items": [...] }
```

**BBox annotation** — typed fields per extracted image (charts, figures).
Implies `--images` so the API has figures to annotate. Annotations land in
`pages[].images[].image_annotation`:

```bash
# chart.schema.json defines { image_type, short_description, summary }
uv run scripts/mistral_ocr.py paper.pdf --bbox chart.schema.json
# -> [ { "image_type": "scatter plot", ... }, ... ]
```

Schemas must be strict: every property listed in `required`, plus
`"additionalProperties": false`. The script marks the request `strict: true`,
but the API will reject schemas that don't follow this shape — structure the
schema correctly yourself.

## Document QnA — natural-language questions

`scripts/mistral_qna.py` sends the document as a chat content item and answers
a question. Defaults to `mistral-small-latest` (cheap, fast); reach for
`mistral-large-latest` on hard reasoning:

```bash
uv run scripts/mistral_qna.py report.pdf "What is the last sentence in the document?"
uv run scripts/mistral_qna.py contract.pdf "List the termination clauses." \
  --model mistral-large-latest
uv run scripts/mistral_qna.py https://arxiv.org/pdf/1805.04770 "Summarize the abstract."
```

Use OCR (`ocr.py`) when you need **exact text** (transcription, tables,
layout). Use QnA (`qna.py`) when you need **meaning** (summary, Q&A,
classification). For a single image where you only want meaning, `qna.py`
with an image path skips OCR entirely.

## What the response contains

Use `--json` to inspect the raw OCR response. The primary output is the
per-page `markdown` field (text + layout); `images`, `tables`, `hyperlinks`,
`blocks`, and `confidence_scores` arrive alongside it when the corresponding
flags are set.

Read `references/documents/mistral-response-structure.md` when parsing the raw JSON response —
the full per-page field table, the top-level fields (`model`,
`document_annotation`, `usage_info`), the image/table placeholder mapping, and
the `--blocks` block-type vocabulary.

## Large files

Inline `data:` URIs (what `scripts/mistral_ocr.py` uses) suit typical documents. For
large PDFs, upload via the files API first and feed the signed URL back to the
OCR endpoint.

Read `references/documents/mistral-large-files.md` when OCRing a PDF too large for inline
base64. It covers the upload → signed-URL → OCR three-step pattern, signed-URL
expiry, and the Batch Inference service for large-scale workloads.

## Gotchas

- **No `base64` document type.** Files go in as `data:application/pdf;base64,…`
  (or `data:image/png;base64,…`) inside `document_url` / `image_url`. The
  script does this; when hand-rolling curl, follow the same shape.
- **`image_url` vs `document_url`.** Images (PNG/JPG/AVIF/…) must use
  `image_url`; PDFs, DOCX, PPTX, and other docs use `document_url`. The script
  picks based on the file.
- **Language is auto-detected.** There is no language parameter — don't go
  looking for one. This is the main advantage over Tesseract-based `liteparse`,
  which needs a `--ocr-language` code.
- **Pages are 0-indexed.** `--pages 0-4` covers pages 1 through 5. The API
  accepts a string of comma-separated numbers and ranges (`"0,1,2"`,
  `"0-5"`, `"0,2-4"`) or a list of ints.
- **Output is Markdown, not plain text.** Tables and layout are preserved;
  strip it if you need raw text.
- **Office files need their real MIME type** in the data URL, not
  `application/pdf`. DOCX →
  `data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,…`.
  The script sniffs via `mimetypes`; when hand-rolling curl, use
  `file -b --mime-type "$f"`.
- **`include_image_base64` bloats the response.** Only enable `--images` when
  you need the figures — it can 10× the output size.
- **Version-gated features.** `table_format` and `extract_header`/`extract_footer`
  require OCR 2512+; `include_blocks` requires OCR 4 (`mistral-ocr-4-0`)+.
  `mistral-ocr-latest` tracks the current best — use it unless you need to pin
  a version for reproducibility.
- **For large-scale OCR**, use Mistral's Batch Inference service rather than
  looping the OCR API — see `references/documents/mistral-large-files.md`.
- **`qna.py` has no `--pages` flag.** The whole document is sent to the chat
  model as one content item; the chat API has no page-slice parameter. For
  large docs where you only need a section, OCR the relevant pages with
  `ocr.py --pages` first, then point `qna.py` at the resulting markdown.
