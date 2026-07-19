---
name: document-ai
description: >
  Extract text from documents and pull structured data out of them using
  Mistral's document AI / OCR API. Use when liteparse is not good enough.
---

# Document AI (Mistral OCR)

OCR, structured extraction, and document QnA via Mistral's
`mistral-ocr-latest` + chat models. Cloud-based, multilingual out of the box
(no language flag), preserves layout as Markdown. Complements `liteparse`
(local Tesseract): prefer this for scanned/complex docs, multilingual content,
tables, structured field extraction, or document Q&A. Use `liteparse` for
quick offline text extraction.

## Authenticate

The API key lives in Proton Pass. Load it into the environment for the session:

```bash
export MISTRAL_API_KEY=$(pass-cli item view 'pass://Keys/Mistral/Api Key')
```

All commands below assume `$MISTRAL_API_KEY` is set.

## Extract text — the common case

`scripts/ocr.py` handles local files and URLs. It base64-encodes local files,
picks `document_url` vs `image_url` correctly, and prints extracted Markdown:

```bash
python3 scripts/ocr.py report.pdf                 # -> Markdown to stdout
python3 scripts/ocr.py scan.png -o scan.md        # -> write to file
python3 scripts/ocr.py https://example.com/doc.pdf
python3 scripts/ocr.py book.pdf --pages 0-4       # 0-indexed page subset
```

### Layout, blocks, tables, confidence, headers/footers

```bash
python3 scripts/ocr.py report.pdf --blocks                  # paragraph-level bboxes (OCR 4+)
python3 scripts/ocr.py report.pdf --table-format html       # tables as HTML separately (OCR 2512+)
python3 scripts/ocr.py report.pdf --confidence word         # per-word confidence scores
python3 scripts/ocr.py report.pdf --header --footer         # split out running headers/footers (OCR 2512+)
python3 scripts/ocr.py report.pdf --images                  # embed figures as base64
```

## Understand / analyze — structured extraction

Two annotation modes from the OCR API:

**Document annotation** — typed fields from the whole document
(receipts, invoices, forms). Pass a JSON Schema + prompt:

```bash
# invoice.schema.json defines { invoice_number, total, line_items, ... }
python3 scripts/ocr.py invoice.pdf \
  --prompt "Extract invoice number, total, and line items." \
  --schema invoice.schema.json
# -> { "invoice_number": "...", "total": "...", "line_items": [...] }
```

**BBox annotation** — typed fields per extracted image (charts, figures).
Implies `--images` so the API has figures to annotate. Annotations land in
`pages[].images[].image_annotation`:

```bash
# chart.schema.json defines { image_type, short_description, summary }
python3 scripts/ocr.py paper.pdf --bbox chart.schema.json
# -> [ { "image_type": "scatter plot", ... }, ... ]
```

Schemas must be strict: every property listed in `required`, plus
`"additionalProperties": false`. The script marks the request `strict: true`,
but the API will reject schemas that don't follow this shape — structure the
schema correctly yourself.

## Document QnA — natural-language questions

`scripts/qna.py` sends the document as a chat content item and answers a
question. Defaults to `mistral-small-latest` (cheap, fast); reach for
`mistral-large-latest` on hard reasoning:

```bash
python3 scripts/qna.py report.pdf "What is the last sentence in the document?"
python3 scripts/qna.py contract.pdf "List the termination clauses." \
  --model mistral-large-latest
python3 scripts/qna.py https://arxiv.org/pdf/1805.04770 "Summarize the abstract."
```

Use OCR (`ocr.py`) when you need **exact text** (transcription, tables,
layout). Use QnA (`qna.py`) when you need **meaning** (summary, Q&A,
classification). For a single image where you only want meaning, `qna.py`
with an image path skips OCR entirely.

## What the response contains

Use `--json` to inspect the raw OCR response. Each page carries:

| Field | Content |
|-------|---------|
| `markdown` | Text + layout (tables, lists) as Markdown — the primary output |
| `images` | Embedded figures (base64 when `--images` is set) |
| `tables` | Tables extracted separately when `--table-format` is set |
| `hyperlinks` | Detected hyperlinks |
| `header` / `footer` | Running headers/footers (when `--header` / `--footer` are set) |
| `dimensions` | Page size in pixels |
| `blocks` | Paragraph-level bounding boxes + block labels (OCR 4+, `--blocks`) |
| `confidence_scores` | Page/word confidence (when `--confidence` is set) |

Top level also has `model`, `document_annotation` (when `--prompt` is used),
and `usage_info` (`pages_processed`, `doc_size_bytes`).

When images/tables are extracted, the `markdown` field replaces them with
placeholders (`![img-0.jpeg](img-0.jpeg)`, `[tbl-3.html](tbl-3.html)`) — map
them back via the `images` and `tables` arrays.

### Block types (when `--blocks` is set)

`text`, `title`, `list`, `table`, `image`, `equation`, `caption`, `code`,
`references`, `aside_text`, `header`, `footer`, `signature`. Blocks are
returned in reading order with `top_left_x/y`, `bottom_right_x/y`, `content`,
and `type`.

## Large files — use the files API

Inline `data:` URIs (what the script uses) suit typical documents. For large
PDFs, upload first and feed the signed URL back to the OCR endpoint:

```bash
# 1. upload (purpose MUST be "ocr")
FILE_ID=$(curl -s https://api.mistral.ai/v1/files \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -F purpose=ocr -F file=@big.pdf \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 2. get a signed URL
URL=$(curl -s "https://api.mistral.ai/v1/files/$FILE_ID/url" \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["url"])')

# 3. OCR the signed URL (the script accepts URLs directly)
python3 scripts/ocr.py "$URL"
```

Signed URLs expire — use them immediately, don't cache them.

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
- **For large-scale OCR**, use Mistral's Batch Inference service — cheaper and
  parallel — rather than looping the OCR API directly.
- **`qna.py` has no `--pages` flag.** The whole document is sent to the chat
  model as one content item; the chat API has no page-slice parameter. For
  large docs where you only need a section, OCR the relevant pages with
  `ocr.py --pages` first, then point `qna.py` at the resulting markdown.
