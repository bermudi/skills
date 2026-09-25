---
name: plannotator
description: >
  Drive the Plannotator CLI: open browser review sessions for local code changes,
  GitHub PRs, or GitLab MRs; annotate files, URLs, folders, or the last agent
  message; gate a document for explicit approval; manage live sessions and browse
  archived decisions. Invoke when asked to use Plannotator or to put a plan,
  diff, document, or page in front of the user for annotated review or approval.
---

# Plannotator CLI

Plannotator opens plans, diffs, documents, and pages in a local browser annotation UI. The human marks them up, approves, or closes; the decision comes back to the terminal on stdout.

## Session model

- Every `review`/`annotate` command starts a temporary local server, opens the browser, and **blocks until the human decides** — minutes, not seconds. Run it with a long or no command timeout (the shipped host hooks use 4 days).
- Never kill the process to "finish" a review. A session that ends without a decision reads as dismissed/no feedback. Read stdout when the process exits.
- `plannotator <command> --help` is authoritative for the installed binary. The docs site can lag or lead it (e.g. newer builds accept `--base`, `--diff-type`, `guide` subcommands that the reference no longer documents). Verify before relying on undocumented flags.
- **Never run bare `plannotator` or `plannotator improve-context`.** They are hook entry points that expect hook JSON on stdin. Plan-mode review is handled automatically by the installed host hooks/extension — don't launch it yourself.

## Browser choice

Plannotator does not control the browser: it serves the session on `http://localhost:<random port>`, launches one browser at that URL, and waits for the decision over HTTP. Resolution order: `--browser` flag → `PLANNOTATOR_BROWSER` (app name/path on macOS, executable on Linux) → `BROWSER` (fallback command) → the OS web-browser default. Values `none`, `false`, `0`, `:` launch nothing and print the URL instead.

On Linux the OS default is the *web browser* (URL scheme handler), which can differ from the `text/html` file association — that's why a session may open in a different browser than `xdg-open file.html` does.

To show sessions in terminal-browser (a pane beside the conversation, reusing a running browser when there is one), point `PLANNOTATOR_BROWSER` at the bundled wrapper:

```bash
PLANNOTATOR_BROWSER="$HOME/.agents/skills/plannotator/scripts/open-in-terminal-browser" \
  plannotator annotate plan.md --gate --json
```

## Choose the command

| The user wants | Run |
| --- | --- |
| Review current code changes | `plannotator review` |
| Review a GitHub PR / GitLab MR | `plannotator review <url>` |
| Annotate a file, URL, or folder | `plannotator annotate <target>` |
| Review AND approve a saved plan/spec/doc | `plannotator annotate <file> --gate --json` |
| Annotate your last assistant message | `plannotator last` |
| List / reopen live sessions | `plannotator sessions [--open [N]]` |
| Browse past plan decisions | `plannotator archive` |

## review

```bash
plannotator review [--git | --gitbutler] [--local | --no-local] [PR_URL]
```

- No URL: reviews the current repository's changes. VCS auto-detected (Git, GitButler, Jujutsu, Perforce); `--git`/`--gitbutler` override detection. GitButler needs `but` 0.21+.
- PR/MR URL: needs an authenticated `gh` or `glab` CLI. Prepares a local checkout of the PR head by default so complete files are reviewable; `--no-local` reviews the platform diff only.

## annotate

```bash
plannotator annotate <file.md | file.txt | file.html | https://... | folder/> \
  [--markdown] [--no-jina] [--gate] [--json] [--hook]
```

Targets and formats:

- Documents: `.md`, `.mdx`, `.txt`. HTML (`.html`, `.htm`): rendered as the page by default, `--markdown` converts to Markdown.
- Plain-text config/data rendered as text: `.yaml`, `.yml`, `.json`, `.jsonc`, `.json5`, `.toml`, `.ini`, `.cfg`, `.conf`, `.properties`, `.csv`, `.tsv`, `.log`, `.xml`, `.env.example`. A bare `.env` is refused (secrets). Source-code files belong to `review`, not `annotate`.
- URLs: converted to Markdown via Jina Reader by default; `--no-jina` uses a direct fetch + local conversion. Localhost/private-network URLs automatically use direct fetch. `.md`/`.mdx` URLs are read as text when the response is Markdown. The session annotates an imported copy, not the live page.
- Folders: opens a file browser over the folder's supported files. Generated/dependency dirs (`node_modules`, `dist`, `build`) are skipped.
- Local files are capped at 2 MiB. Quote the path as one shell argument.

### Output contracts (annotate and annotate-last)

Default (plaintext): submitted annotations are printed as feedback; approval prints exactly `The user approved.`; closing prints nothing. Completed decisions exit `0`.

`--json`: one record on stdout. `--json` alone does **not** add an Approve button — add `--gate` when approval is part of the deal.

| User action | stdout |
| --- | --- |
| Submit annotations | `{"decision":"annotated","feedback":"<feedback>"}` |
| Approve | `{"decision":"approved"}` or `{"decision":"approved","feedback":"<notes>"}` |
| Close | `{"decision":"dismissed"}` |

`--hook`: for real host PostToolUse/Stop hook contexts only. Implies `--gate`. Annotations emit `{"decision":"block","reason":"<feedback>"}`; **both** Approve and Close emit nothing (the hook passes). If `--hook` and `--json` are both present, the hook contract wins.

Strict approval — when success requires explicit approval (not just feedback):

```bash
plannotator annotate spec.md --gate --json --require-approval --result-file <path>
```

Direct `annotate --gate --json` calls only; rejects `annotate-last` and `--hook`. Exit `0` only on approval; annotations/dismissal exit `1`; invalid flags, startup, or result-publication failure exit `2`. `--result-file` publishes the same JSON to a path that must not already exist, in a parent that must.

## annotate-last / last

`plannotator annotate-last` (alias `last`) reads the last assistant message from a supported agent session and opens it for annotation. Same output contracts as `annotate`. Pipe text directly with `--stdin`:

```bash
printf '%s' "$message" | plannotator annotate-last --stdin
```

## sessions and archive

- `plannotator sessions` lists live local servers; `--open [N]` reopens session N (default 1); `--clean` removes stale records.
- `plannotator archive` opens the read-only archive of saved plan decisions (`~/.plannotator/plans/` by default).

## setup-goal

`plannotator setup-goal <interview|facts> <bundle.json | -` `> [--json]` belongs to the installed `/goal` workflow: `interview` opens goal questions, `facts` opens facts acceptance. `-` reads the bundle JSON from stdin. Don't invoke it outside that workflow.

## Install, update, uninstall

- Full installer — binary plus host hooks, core skills, command files, optional `sem` sidecar and agent-terminal runtime (needs Git): `curl -fsSL https://plannotator.ai/install.sh | bash` (Windows: `irm https://plannotator.ai/install.ps1 | iex`). Rerun the same installer to update; data under `~/.plannotator/` survives.
- Binary only — `bash -s -- --minimal` (`--binary-only` alias, or `PLANNOTATOR_MINIMAL=1`): no hooks/skills/runtimes, Git not required. Pin with `--version vX.Y.Z`; add `--verify-attestation` for SLSA provenance via `gh`.
- Pi hosts integrate through the `@plannotator/pi-extension` package instead of the installer.
- This machine runs binary-only: single ELF at `~/.local/bin/plannotator`, no installer-managed files in any host.
- To remove: `plannotator uninstall --dry-run` first; `--purge` also deletes local data under `~/.plannotator/`.

## Gotchas

- Classify outcomes only by the `decision` field, never by message text. **Approval with notes is guidance, not a change request** — an `approved` decision with `feedback` means proceed, treating the notes as preferences.
- Plain `annotate` shows only **Close** — no Approve button. When the user asks to review/approve/accept/gate a generated plan or doc, add `--gate --json`. Never tell the user they can approve a non-gate session.
- Never use `--hook` for interactive runs: a close reads as hook-pass (empty output), i.e. silent success.
