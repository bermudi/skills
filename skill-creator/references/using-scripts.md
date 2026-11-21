# Using scripts in skills

> How to run commands and bundle executable scripts in your skills.

Skills can instruct agents to run shell commands and bundle reusable scripts in a `scripts/` directory. This guide covers one-off commands, self-contained scripts with inline dependencies, and designing script interfaces for agentic use.

## One-off commands

When an existing package already does what you need, invoke it directly without adding a `scripts/` wrapper:

- **Python (`uvx`):** runs packages in isolated, aggressively cached environments.
  ```bash
  uvx ruff@0.8.0 check .
  ```
- **JS/TS (`bunx` / `npx`):** downloads and caches packages on demand (`bunx` in Bun environments, `npx` where Node is the baseline).
  ```bash
  bunx eslint@9 --fix .
  ```
- **Go (`go run`):** compiles and runs Go packages directly.
  ```bash
  go run golang.org/x/tools/cmd/goimports@v0.28.0 .
  ```

**Tips for one-off commands:**

* **Pin versions** (and prefer versions published at least 7 days ago) so behavior stays reproducible.
* **State prerequisites** in `SKILL.md` or the [`compatibility` frontmatter field](specification.md#compatibility-field).
* **Move complex commands into scripts.** When flags and quoting get fragile, bundle a tested script in `scripts/`.

### Injecting script output into skill content (Claude Code)

Claude Code supports a `` !`cmd` `` syntax that runs a command when the skill loads and interpolates its output into the body — useful for deterministic starting context like `git log --oneline -10` in Claude-only skills. Don't rely on it in cross-harness skills (other harnesses show it literally).

## Referencing scripts from `SKILL.md`

List bundled scripts in `SKILL.md` using relative paths from the skill directory root so the agent knows they exist:

```markdown
## Available scripts

- **`scripts/validate.sh`** — Validates configuration files
- **`scripts/process.py`** — Processes input data
```

> **Path resolution note:** Agents execute shell commands from the **user's working directory**, not from the skill directory. Tell the agent to resolve `scripts/...` against the skill's directory path (or pass `PYTHONPATH=<skill-dir>` for `python -m scripts.<mod>`).

## Self-contained scripts

Bundle reusable logic in `scripts/` with inline dependency declarations so a single command runs it without a separate manifest or install step.

### Python (PEP 723 + `uv run`)

Declare dependencies in a TOML block inside `# /// script` markers:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "beautifulsoup4>=4.12,<5",
# ]
# ///

from bs4 import BeautifulSoup

html = '<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>'
print(BeautifulSoup(html, "html.parser").select_one("p.info").get_text())
```

Run with `uv run <skill-dir>/scripts/extract.py` (creates a cached isolated env automatically; `uv lock --script` pins a lockfile if needed).

### TypeScript (`bun run`)

Bun auto-installs missing packages when no `node_modules` exists up the directory tree. Pin versions directly in the import path:

```typescript
#!/usr/bin/env bun

import * as cheerio from "cheerio@1.0.0";

const html = `<html><body><h1>Welcome</h1><p class="info">This is a test.</p></body></html>`;
const $ = cheerio.load(html);
console.log($("p.info").text());
```

Run with `bun run <skill-dir>/scripts/extract.ts`. Note: if a `node_modules` directory exists anywhere above the script, Bun disables auto-install and uses standard Node resolution.

## Designing scripts for agentic use

When an agent runs your script, it reads stdout and stderr to decide what to do next.

### Avoid interactive prompts

Agents operate in non-interactive shells — TTY prompts, password dialogs, and confirmation menus hang indefinitely. Accept all input via flags, env vars, or stdin, and fail fast with usage guidance when required flags are missing:

```text
Error: --env is required. Options: development, staging, production.
Usage: uv run scripts/deploy.py --env staging --tag v1.2.3
```

### Document usage with `--help`

`--help` output is the primary way an agent learns a script's interface. Keep it concise (brief description, flags, defaults, 2–3 examples) because it enters context.

### Write helpful error messages

Say what went wrong, what was expected, and what to try:

```text
Error: --format must be one of: json, csv, table.
       Received: "xml"
```

### Use structured output

Prefer JSON, CSV, or TSV over whitespace-aligned tables so outputs compose cleanly with `jq` and standard tools. Send structured data to **stdout** and progress/warnings/diagnostics to **stderr**.

### Further considerations

* **Idempotency.** Agents retry commands; "create if not exists" beats failing on duplicate.
* **Input constraints.** Reject ambiguous input with a clear error rather than guessing.
* **Dry-run support.** Provide `--dry-run` for destructive or stateful operations.
* **Meaningful exit codes.** Document non-zero exit codes in `--help`.
* **Safe defaults.** Gate destructive operations behind explicit confirmation flags (`--confirm`, `--force`).
* **Predictable output size.** Harnesses truncate long tool outputs (often 10–30K chars). Default to summaries or bounded limits, support `--offset`/`--limit`, or write large output to `--output <file>` (with `-` opting in to stdout).
