---
name: gh-repo-read
description: >
  Explore GitHub repositories without cloning using `gh repo read-file` and
  `gh repo read-dir`. Use when the user asks to inspect, browse, or read files
  from a remote repo (e.g. "what's in repo X", "read file Y from Z", "show me
  the structure of ..."), fetch a single file from GitHub, or compare a file
  across branches/tags/commits. Prefers these commands over cloning when only
  inspection — not modification — is needed.
metadata:
  version: "1.0"
  topic: repo-exploration
---

# gh-repo-read

Browse GitHub repositories and read files **without a clone**, using two
preview commands added in `gh` 2.95.0:

- `gh repo read-dir` — list directory entries
- `gh repo read-file` — read a single file

Both hit the GitHub API directly. No checkout, no `.git`, no disk footprint
unless you ask for one. Great for answering "what does this repo look like?"
before deciding whether to clone, or for grabbing one config file from a
dependency.

## Prerequisites

- **`gh` ≥ 2.95.0.** Check with `gh --version`.
- **Auth for private repos.** Public repos work anonymously; private repos
  require `gh auth login`. The `[HOST/]OWNER/REPO` form of `--repo` supports
  GitHub Enterprise Server too.
- **Preview status.** These commands may change or disappear between releases.
  Don't pin production logic to their output shape.

## Shared flags

| Flag | Effect |
|------|--------|
| `-R, --repo [HOST/]OWNER/REPO` | Target repo (required unless CWD is a repo) |
| `--ref <branch\|tag\|commit>` | Read from a non-default ref |
| `--json <fields>` | Output JSON (default: human-readable TTY format) |
| `-q, --jq <expr>` | Filter JSON via jq expression |
| `-t, --template <tpl>` | Format via Go template |

`--repo` defaults to the current directory's repo if omitted. For pure remote
inspection, always pass `--repo OWNER/REPO` explicitly.

---

## `gh repo read-dir` — list a directory

```bash
# Root of the default branch (omit <path>)
gh repo read-dir --repo cli/cli

# A subdirectory
gh repo read-dir script --repo cli/cli

# At a specific tag
gh repo read-dir docs --repo cli/cli --ref v2.94.0
```

### Output formats

**Default (same in a TTY or piped)** — four tab-separated columns:
`type  name  mode  size`:

```
dir   .github      040000   0
file  .gitignore   100644   582
file  go.mod       100644   9154
```

`type` is `dir` or `file`. `mode` is the git tree mode in octal (`040000` =
dir, `100644` = file, `100755` = executable). `size` is bytes (always `0`
for directories). Unlike many `gh` commands, `read-dir` does **not**
reformat between TTY and piped output — both produce the same columns.

**JSON** (`--json`) — entries are wrapped under `.entries[]`:

```bash
gh repo read-dir --repo cli/cli --json name,type,path
# => {"entries":[{"name":".github","path":".github","type":"dir"}, ...],
#      "gitSHA":"d38b678...", "id":"..."}
```

Available JSON fields: `gitSHA`, `gitType`, `mode`, `modeOctal`, `name`,
`nameRaw`, `path`, `pathRaw`, `size`, `submodule`, `type`.

> **`mode` vs `modeOctal` are different types.** `mode` is a decimal
> integer (`33188`); `modeOctal` is a string (`"100644"`). Compare with a
> string literal: `select(.modeOctal=="100755")`, not `==100755`.

> **The `.entries[]` wrapper matters.** A bare `--jq '.[]'` returns nothing.
> Always drill into `.entries[]` first.

### Useful jq patterns

```bash
# Just the subdirectory names
gh repo read-dir --repo cli/cli --json name,type \
  --jq '.entries[] | select(.type=="dir") | .name'

# Files with sizes, sorted descending
gh repo read-dir docs --repo cli/cli --json name,type,size \
  --jq '.entries[] | select(.type=="file") | "\(.size)\t\(.name)"'

# Anything executable (modeOctal is a string — quote it)
gh repo read-dir script --repo cli/cli --json name,modeOctal \
  --jq '.entries[] | select(.modeOctal=="100755") | .name'
```

---

## `gh repo read-file` — read a single file

```bash
# To stdout (raw content when piped/redirected; paged in a TTY)
gh repo read-file README.md --repo cli/cli

# From a pinned ref
gh repo read-file go.mod --ref v2.94.0 --repo cli/cli

# Save to disk (use --clobber to overwrite an existing file)
gh repo read-file README.md --output ./README.md --repo cli/cli
```

### Flags

| Flag | Effect |
|------|--------|
| `-o, --output <path>` | Write to disk instead of stdout (raw bytes, always) |
| `--clobber` | Overwrite an existing `--output` target |
| `--allow-escape-sequences` | Bypass the terminal-escape-sequence safety check |

### JSON metadata (without the content)

Useful for checking size, SHA, or download URL before pulling bytes:

```bash
gh repo read-file go.mod --repo cli/cli --json name,path,size,gitSHA
# => {"gitSHA":"d2dd343...","name":"go.mod","path":"go.mod","size":9154}
```

Available fields: `content`, `downloadUrl`, `encoding`, `gitSHA`, `gitUrl`,
`htmlUrl`, `name`, `path`, `size`, `type`, `url`.

### Escape-sequence safety (read this)

By default `read-file` **refuses to print files containing terminal escape
sequences** to a terminal or pipe — a guard against malicious content that
could manipulate your terminal. It will error rather than emit them.

- Want the file anyway? Use `--allow-escape-sequences`, **or**
- Write to disk with `--output` — disk writes always contain the raw bytes
  (equivalent to `--allow-escape-sequences`), where the bytes can't hijack a
  terminal.

The guard keys on **literal ESC (`0x1b`) bytes** — actual ANSI/CSI
sequences. Files that merely *look* escapey (zsh `%{$fg[green]%}` prompt
syntax, `$\033`-as-text in source) are not blocked, and arbitrary binaries
are only blocked if they happen to contain an `0x1b` byte. When in doubt
about a file's contents, `--output` to a temp path and read it back, rather
than streaming to stdout.

---

## When to use this vs. cloning

| Situation | Use |
|-----------|-----|
| "What's in this repo?" / browse structure | `read-dir` |
| Grab one or two files | `read-file` |
| Check a file at a specific tag/commit | `read-file --ref` |
| Compare a file across refs | `read-file --ref v1` + `read-file --ref v2` |
| Need to grep the whole tree, run builds, edit, or traverse >~20 files | **clone instead** |

Each command is one API call, but each file is a separate call. For broad
exploration (reading many files, searching code), `gh repo clone` + local tools
is cheaper and faster. These commands shine for **surgical, read-only** peeks.

## Gotchas

- **One file = one API call.** Reading 50 files = 50 round-trips. At that
  scale, clone.
- **`read-dir` does not recurse.** It lists one level. Walk the tree by
  descending into `dir` entries.
- **Directories have `size: 0`** — don't use it to measure directory weight.
- **No search.** To search code across a repo, use `gh search code` or the
  GitHub code-search API instead — `read-*` only reads known paths.
- **Binary files** are fetched as-is; stdout will be raw bytes. Prefer
  `--output` for anything non-text.
- **`--repo` shorthand.** `OWNER/REPO` is enough for github.com; prefix
  `HOST/` for GHES.
- **Preview commands.** Output shapes and flags may change across `gh`
  releases. Re-check `gh repo read-file --help` if behavior seems off.
