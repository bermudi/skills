---
name: liteparse
description: >
  Parse, OCR, and screenshot documents (PDF, DOCX, XLSX, PPTX, images) using
  liteparse (CLI: lit). Use when the user asks to extract text from a document,
  parse a PDF or Office file, OCR a scanned document or image, convert a file
  to text or JSON, screenshot PDF pages, or batch-process a directory of
  documents.
---

# liteparse

Parse documents from the command line. Supports PDF, DOCX, XLSX, PPTX, and
images. Uses Tesseract for OCR by default; can also use an HTTP OCR server.

The CLI is `lit` (or `liteparse`), installed globally via pnpm.

## Commands

| Command | Purpose |
|---------|---------|
| `lit parse <file>` | Parse a single document to text or JSON |
| `lit batch-parse <dir> <out>` | Parse all documents in a directory |
| `lit screenshot <file>` | Render PDF pages as images |

## `lit parse` — Single Document

```bash
lit parse document.pdf
```

Output goes to stdout as plain text. Common options:

| Flag | Effect |
|------|--------|
| `-o <file>` | Write to file instead of stdout |
| `--format json` | Output structured JSON (default: text) |
| `--no-ocr` | Skip OCR. Use for text-native PDFs — much faster. |
| `--dpi <n>` | Rendering DPI (default 150). Higher = better OCR quality, slower. |
| `--target-pages <pages>` | Parse specific pages only (e.g. `"1-5,10,15-20"`) |
| `--max-pages <n>` | Cap pages parsed (default 10000) |
| `--ocr-language <lang>` | Tesseract language code (default `en`) |
| `--password <pw>` | Decrypt password-protected documents |
| `--num-workers <n>` | Parallel OCR workers (default: CPU cores − 1) |
| `--preserve-small-text` | Keep very small text that would otherwise be filtered |
| `--no-precise-bbox` | Skip precise bounding boxes (faster, less layout info) |
| `--ocr-server-url <url>` | Use external OCR server instead of local Tesseract |
| `-q` | Suppress progress output |

### Examples

```bash
# Quick text extraction
lit parse report.pdf

# JSON output to file, first 3 pages only
lit parse report.pdf --format json -o report.json --max-pages 3

# OCR a scanned document in Spanish, high DPI
lit parse scan.pdf --ocr-language spa --dpi 300

# Text-only PDF (no images) — skip OCR
lit parse manual.pdf --no-ocr

# Specific page range
lit parse book.pdf --target-pages "42-45,67"

# Password-protected file
lit parse confidential.docx --password "s3cret"
```

## `lit batch-parse` — Directory of Documents

```bash
lit batch-parse ./input-dir ./output-dir
```

Parses every supported file in `input-dir`, writing results to `output-dir`.
Output filenames are derived from input filenames (e.g. `report.pdf` →
`report.txt` or `report.json`).

Options match `parse`, plus:

| Flag | Effect |
|------|--------|
| `--recursive` | Recurse into subdirectories |
| `--extension <.ext>` | Only process files with this extension (e.g. `.pdf`) |

### Example

```bash
# Parse all PDFs in a folder to JSON
lit batch-parse ./documents ./output --format json --extension .pdf --recursive
```

## `lit screenshot` — PDF Pages as Images

```bash
lit screenshot document.pdf
```

Renders PDF pages to PNG (default) or JPG in `./screenshots/`.

| Flag | Effect |
|------|--------|
| `-o <dir>` | Output directory (default `./screenshots`) |
| `--target-pages <pages>` | Which pages to render (e.g. `"1,3,5"` or `"1-10"`) |
| `--dpi <n>` | Rendering DPI (default 150) |
| `--format png\|jpg` | Image format (default `png`) |
| `--password <pw>` | Decrypt password-protected PDF |

### Example

```bash
# First 3 pages as high-res PNGs
lit screenshot presentation.pdf --target-pages "1-3" --dpi 300 -o ./slides
```

## Gotchas

- **OCR is on by default.** For text-native PDFs and Office files, OCR is
  unnecessary and slow. Use `--no-ocr` when you know the document has embedded
  text.
- **Stdout for large files.** `lit parse` writes to stdout. For large documents,
  use `-o <file>` or pipe through a pager.
- **`batch-parse` requires an output directory.** It won't create one
  automatically — ensure the output directory exists first.
- **`screenshot` only works with PDFs.** Office files and images must be
  converted to PDF first if you need screenshots.
- **OCR uses tesseract.js (in-process WASM).** No system binary needed, but
  first run downloads language-traineddata from CDN (~12MB for English). On
  air-gapped machines, pre-download traineddata and set `TESSDATA_PREFIX`.
- **Language codes are normalized.** You can pass `--ocr-language en` or
  `--ocr-language eng` — liteparse maps common 2-letter codes to Tesseract
  3-letter codes automatically.
