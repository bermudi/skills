# OCR Response Structure

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

## Block types (when `--blocks` is set)

`text`, `title`, `list`, `table`, `image`, `equation`, `caption`, `code`,
`references`, `aside_text`, `header`, `footer`, `signature`. Blocks are
returned in reading order with `top_left_x/y`, `bottom_right_x/y`, `content`,
and `type`.
