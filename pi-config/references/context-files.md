# Context Files

Pi loads context files at startup to customize the system prompt and project instructions.

## AGENTS.md (or CLAUDE.md)

Project instructions, conventions, and common commands. Pi loads all matching files from:

1. `~/.pi/agent/AGENTS.md` (global)
2. Parent directories (walking up from cwd)
3. Current directory

All found files are concatenated into the system prompt.

**Disable:** `--no-context-files` (or `-nc`)

## System prompt customization

| File | What it does |
|------|-------------|
| `.pi/SYSTEM.md` | Replaces the default system prompt entirely |
| `~/.pi/agent/SYSTEM.md` | Same, but global |
| `APPEND_SYSTEM.md` | Appends to the default prompt without replacing |

**CLI flags:**
```bash
pi --system-prompt "You are a Rust expert"          # replace
pi --append-system-prompt "Always use cargo fmt"    # append
```

## Startup loading order

1. Default system prompt
2. `SYSTEM.md` (replaces default if present) or `APPEND_SYSTEM.md` (appends)
3. `AGENTS.md` / `CLAUDE.md` files (concatenated)
4. Skills (metadata only — name + description)
5. Prompt templates
6. Extensions

The final system prompt includes all of the above, plus any `--system-prompt` / `--append-system-prompt` CLI overrides.

## Full docs

https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/usage.md (see "Context Files" section)

## Tips

- Put project-wide conventions in `.pi/AGENTS.md` at the repo root
- Put personal defaults in `~/.pi/agent/AGENTS.md`
- Use `APPEND_SYSTEM.md` when you want to add instructions without replacing the default prompt
- Use `SYSTEM.md` when you need full control over the prompt
