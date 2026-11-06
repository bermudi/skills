---
name: mq
description: >
  `mq` is jq for Markdown: query, filter and transform headings, code blocks,
  links, sections and frontmatter via the AST, not regex.
compatibility: Requires the mq CLI (https://mqlang.org/install.sh)
metadata:
  topic: markdown-processing
  version: "1.2"
---

# mq

Use for Markdown *structure*; plain-text munging doesn't need it. `mq --help` and `mq --doc` (300+ functions) are the runtime truth; the language is in flux.

If `mq` is missing, don't install it just because this skill loaded. On explicit request: download the official installer to a temp file, inspect it, run it, verify `mq --version`.

## Workflow

1. Probe read-only first; inspect output before writing anything.
2. Input format: `.md`/`.mdx` files parse as Markdown. Stdin has no extension, so pass `-I` explicitly (`markdown`, `raw`, `json`, `yaml`, `csv`, `html`, ...).
3. Output: default is rendered Markdown. `-F json` emits AST node objects (not strings); also `grep` (with `--context N`), `html`, `text`, `raw`.
4. Write only after the probe is right. `-U` emits the updated document to stdout or `-o`; it is **not** an in-place edit. Write to a new path, diff, then replace. Check repo files with `git diff --check`.
5. Single-quote the query, double quotes inside.

## Selectors

`.h`/`.h1`–`.h6`, `.text`, `.p`, `.code`, `.code_inline`, `.strong`, `.emphasis`, `.delete`, `.link`, `.image`, `.list`, `.blockquote`, `.[row][col]` (table cells), `.html`, `.yaml`, `.toml`, `.footnote`, `.footnote_ref`, `.link_ref`, `.image_ref`, `.definition`, `.math`, MDX nodes, `nodes` (flat array of all). `..ident` descends recursively.

Filtered calls: `.h(2, 3)`, `.h(1..3)`, `.code("rust")`.

Attributes (not covered by `mq --doc`):

| Node | Attributes |
| --- | --- |
| `.h` | `level`/`depth`, `value` |
| `.code` | `lang`/`language`, `value`, `meta`, `fence` |
| `.link` | `url`, `title`, `value` |
| `.image` | `url`, `title`, `alt` |
| `.list` | `index`, `level`, `ordered`, `checked`, `value` |
| `.[r][c]` | `row`, `column`, `last_cell_in_row`, `value` |
| `.link_ref`/`.image_ref` | `ident`, `label` (+ `alt`) |
| `.footnote`/`.footnote_ref` | `ident`, `text`/`label` |
| `.definition` | `ident`, `url`, `title`, `label` |

## Gotchas

- **Edits:** return `update(...)` for content and `set_attr(...)` for structure; `|=` works for simple attributes (`.code.lang |= "rust"`, `.link.url |= "..."`). jq-style `.h.value |= "x"` does not rewrite the Markdown.
  ```bash
  mq -U '.h | select(.h.level == 2) | update(.h.value + " (updated)")' README.md -o /tmp/out.md
  mq -U '.h | select(.h.level == 2) | set_attr("level", 3)' README.md -o /tmp/out.md
  ```
- **Per-file by default.** Section and cross-file queries need `-A`: `mq -A 'section::section("Installation")' README.md`, `mq -A 'section::sections() | section::by_level(1)' docs/*.md`. `-S` adds a per-file separator; `__FILE__`, `__FILE_NAME__`, `__FILE_STEM__` name the current input.
- **HTML input** (`-I html`) converts to Markdown first: use Markdown selectors (`.text`, `.link.url`, `.h`), not tags (`.p` is wrong).
- Gates: `-c` counts matches; `-e` exits 1 on an empty result (CI gate); `-f query.mq` loads a query file.
- **Capability flags** only when the query needs them (a normal file argument needs none): `--allow-read` (`read_file`, `collection`, `file_exists`), `--allow-write` (`write_file`), `--allow-net` (`http`, HTTPS only, private/loopback blocked). Treat `mq-*` executables on PATH as plugins: inspect before running.
- On failure, keep the error and shrink to the smallest working selector. Usual causes: shell quoting, `-F json` when Markdown was wanted, missing `-A`, a jq construct mq lacks, missing `-I`.

Docs: <https://mqlang.org/book/>.
