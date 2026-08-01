---
name: mq
description: >
  `mq` is `jq` for Markdown. It parses a document into an AST and lets you
  query, filter, and transform it with a jq-like syntax instead of fragile
  regex or line-oriented parsing.
compatibility: Requires the mq CLI (https://mqlang.org/install.sh)
metadata:
  topic: markdown-processing
  version: "1.1"
---

# mq — Markdown Query Language

Use `mq` as the AST-aware tool for Markdown work. Prefer it over regex, `sed`,
or line-oriented shell parsing whenever the task involves Markdown *structure*
(headings, code blocks, links, sections, frontmatter). If the task is plain-text
munging with no structural awareness needed, a simpler tool is fine.

## Start safely

Check the binary before doing anything else:

```bash
command -v mq && mq --version
```

If `mq` is missing, **do not install it merely because this skill loaded.**
If the user explicitly requests installation: download the official installer
to a temp file, inspect it, execute it, then verify `mq --version`. The
installer places `mq` in `~/.local/bin/` (or `$MQ_HOME`, or
`${XDG_DATA_HOME}/bin`). The installed version and `mq --help` are the runtime
source of truth; the language is under active development.

## The query workflow

1. **Identify the input.** Named `.md`/`.mdx` files parse as Markdown by
   default. Use `-I markdown` to force it, `-I raw` for literal text, or the
   matching `-I` for JSON, YAML, CSV, HTML, etc. Stdin has no extension —
   pass `-I` explicitly when it is not Markdown.
2. **Probe read-only first.** Run a small query and inspect output before
   writing anything. Use `mq --doc` for the built-in function reference when
   a selector or function is uncertain.
3. **Choose the output contract.** Default output is rendered Markdown.
   `-F json` emits AST node objects (not a simple array of strings).
   `-F grep` gives matching nodes with context. `-F html`/`text`/`raw`
   for those representations.
4. **Transform only after the probe is correct.** Use `-U` and write to a
   *new* path with `-o`; inspect the diff before replacing the source.
   `-U` writes to stdout (or `-o`) — it is not a safe same-file in-place edit.
5. **Verify.** Confirm the output is valid Markdown and the source changed
   only where intended. For repo files: `git diff --check -- <output>` and
   review `git diff` before committing.

Basic invocation:

```bash
mq 'QUERY' file.md
printf '# Title\n' | mq '.h'
mq -f query.mq file.md
```

Quote shell queries with **single quotes**; use double quotes inside the query.
This avoids shell expansion of `$`, `*`, and query punctuation.

## Selectors

| Selector | Matches |
| --- | --- |
| `.h`, `.h1`–`.h6` | All headings, or a specific level |
| `.text`, `.p` | Text nodes / paragraphs |
| `.code`, `.code_inline` | Fenced code blocks / inline code |
| `.strong`, `.emphasis`, `.delete` | Bold / italic / strikethrough |
| `.link`, `.image` | Links / images |
| `.list` | List items |
| `.blockquote` | Block quotes |
| `.[row][col]` | Table cells |
| `.html` / `.<>` | Raw HTML nodes |
| `.yaml`, `.toml` | Frontmatter |
| `.footnote`, `.footnote_ref` | Footnotes / footnote references |
| `.link_ref`, `.image_ref`, `.definition` | Reference-style links/images/definitions |
| `.math` | Math blocks |
| `.mdx_jsx_flow_element`, `.mdx_flow_expression` | MDX nodes |
| `nodes` | All nodes as a flat array |

### Filtered selector calls

```mq
.h(1)          # Only h1
.h(2, 3)       # h2 and h3
.h(1..3)       # h1 through h3 (range)
.code("rust")  # Only Rust code blocks
```

### Key attributes

| Node | Attributes |
| --- | --- |
| `.h` | `level`/`depth` (1–6), `value` |
| `.code` | `lang`/`language`, `value`, `meta`, `fence` (bool) |
| `.link` | `url`, `title`, `value` |
| `.image` | `url`, `title`, `alt` |
| `.list` | `index`, `level`, `ordered` (bool), `checked` (bool), `value` |
| `.[r][c]` | `row`, `column`, `last_cell_in_row` (bool), `value` |
| `.link_ref` / `.image_ref` | `ident`, `label` (+ `alt` for image_ref) |
| `.footnote` / `.footnote_ref` | `ident`, `text` / `label` |
| `.definition` | `ident`, `url`, `title`, `label` |

These are Markdown-selector-specific and are **not** covered by `mq --doc`.

### Recursive descent

```mq
..ident    # Recursively select matching nodes in nested structures
```

## Common patterns

```bash
# Extract
mq '.h' file.md
mq '.h(2)' file.md
mq '.code("rust")' file.md
mq '.link.url' file.md
mq '.yaml | to_text' post.md

# Filter
mq 'select(.code)' file.md
mq 'select(!.code)' file.md
mq '.h | select(.h.level <= 2)' file.md
mq 'select(contains("TODO"))' file.md

# Count / gate
mq -c '.h' file.md                        # count matches
mq -e 'select(contains("DRAFT"))' file.md # exit 1 if no match (CI gate)

# Output formats
mq -F json '.h' file.md                   # AST objects
mq -F grep --context 2 '.h(2)' file.md   # grep-style with context
mq -F html 'identity' file.md            # Markdown → HTML
```

## Transformations

For content changes, select the node and return `update(...)`. For structural
attributes (heading depth, code language), use `set_attr(...)`. With `-U`, mq
maps the returned node back to its original position in the document.

For simple attribute swaps, `|=` works:

```mq
.code.lang |= "rust"
.link.url  |= "https://new.example"
```

**Do not** assume jq-style `.h.value |= "new text"` will rewrite the original
Markdown structure. For content replacement, `update(...)` and `set_attr(...)`
make the replacement node explicit and work correctly with `-U`.

```bash
# Rename h2 headings (preview → write → diff)
mq -U '.h | select(.h.level == 2) | update(.h.value + " (updated)")' \
  README.md -o /tmp/README.updated.md
diff -u README.md /tmp/README.updated.md

# Promote h2 → h3
mq -U '.h | select(.h.level == 2) | set_attr("level", 3)' \
  README.md -o /tmp/README.promoted.md

# Swap a link URL
mq -U 'if (and(.link, .link.url == "https://old.example")): \
  update("https://new.example")' input.md -o output.md
```

## Multiple files and sections

A query is evaluated per input file by default. Use `-A` when a query needs
one aggregate input (cross-file or section operations). Use `-S` to insert a
separator between each file's result.

```bash
# Section-aware operations require -A
mq -A 'section::section("Installation")' README.md
mq -A 'section::sections() | section::by_level(1)' docs/*.md

# Batch output attributable to source
mq -S 's"--- ${__FILE__} ---"' '.h' docs/*.md

# mq accepts multiple file args directly (shell glob expansion)
mq '.h | to_text' *.md docs/*.md
```

`__FILE__`, `__FILE_NAME__`, and `__FILE_STEM__` expose the current input file
inside a query. The shell expands globs before mq sees them; use a deliberate
file list when order matters.

## HTML input: always use Markdown selectors

With `-I html`, mq converts HTML → Markdown *first*. Use Markdown selectors,
not HTML tags.

```bash
# WRONG
curl -s https://example.com | mq -I html '.p | to_text'

# CORRECT
curl -s https://example.com | mq -I html '.text | to_text'
curl -s https://example.com | mq -I html '.link.url'
curl -s https://example.com | mq -I html '.h | to_text'
```

## CLI flags (quick reference)

| Flag | Purpose |
| --- | --- |
| `-A, --aggregate` | Combine inputs into one array |
| `-F, --output-format` | Set output format (json, html, text, raw, grep) |
| `-I, --input-format` | Set input format |
| `-U, --update` | Emit updated document (use with `-o`) |
| `-o FILE` | Write output to a file |
| `-S QUERY` | Insert separator between files |
| `-c` | Count non-None matches |
| `-e` | Exit 1 on false/null/empty result |
| `-f FILE` | Load query from a file |
| `-P N` | Parallel-processing threshold for many files |
| `--args NAME VAL` / `--argv ...` | Pass data as `ARGS` |

For the full flag list: `mq --help`. For 300+ built-in functions: `mq --doc`.

## Capability gates

The CLI exposes explicit capabilities to queries. **Do not add these flags
unless the query requires the capability.** Reading a file passed as a normal
CLI input does not require `--allow-read`.

| Flag | Enables |
| --- | --- |
| `--allow-read` | `read_file`, `read_file_bytes`, `collection`, `file_exists` |
| `--allow-write` | `write_file` |
| `--allow-net` | `http` (HTTPS only; private/loopback blocked) |

Treat external `mq-*` subcommands on `PATH` as executable plugins: inspect
before invoking.

## When NOT to use mq

- Binary file processing.
- Simple `cat`/`echo` with no structural transformation.
- Pure JSON → use `jq`. Pure YAML → use `yq`.
- Tasks where the Markdown structure is irrelevant and plain-text tools suffice.

## Reference and troubleshooting

- Runtime reference: `mq --help`, `mq --doc`.
- Official docs: <https://mqlang.org/book/>.
- Source: <https://github.com/harehare/mq/tree/main/docs>.

When a query fails: preserve the error, reduce to the smallest working
selector, check the installed version's help. Common causes:

- Shell quoting (use single quotes outside, double inside).
- Using `-F json` when rendered Markdown was intended.
- Forgetting `-A` for section or cross-file queries.
- Using a jq construct that mq does not support (check `mq --doc`).
- Omitting `-I` for stdin or non-`.md` extensions.
