# Pi sessions

Use Pi's picker from the target project directory because normal discovery is
project-scoped.

## Find and resume

```bash
pi -c                       # continue most recent session in this project
pi -r                       # searchable resume picker
pi --session <path-or-id>   # exact file or unique partial session ID
pi --fork <path-or-id>      # resume as a new session file
```

Inside Pi:

- `/resume` opens the same picker.
- `/session` shows the active file, ID, message count, tokens, and cost.
- `/name <name>` makes future discovery easier.
- `/new` starts a new session.

Picker controls include typing to search, `Ctrl+P` for path display, `Ctrl+S`
for sort mode, `Ctrl+N` for named-only filtering, and `Ctrl+R` to rename.
`Ctrl+D` deletes after confirmation; do not use it without explicit user
approval.

## Navigate and branch

- `/tree` navigates any entry in the current session file. Selecting an old
  point and continuing creates another branch in the same tree.
- `/fork` creates a new session from an earlier user message.
- `/clone` copies the active branch into a new session.
- Prefer `/tree` for related alternatives in one history; fork or clone when
  the user wants a separate durable conversation.

## Storage and fallback inspection

Default storage:

```text
~/.pi/agent/sessions/<encoded-working-directory>/<timestamp>_<uuid>.jsonl
```

`PI_CODING_AGENT_SESSION_DIR` or `--session-dir` can override the root, so
check the current command/environment before assuming the default. Session
files are JSONL trees, not flat chat logs.

If the project path is uncertain, list project directories and file mtimes
without dumping content:

```bash
find "${PI_CODING_AGENT_SESSION_DIR:-$HOME/.pi/agent/sessions}" \
  -type f -name '*.jsonl' -printf '%TY-%Tm-%Td %TH:%TM  %p\n' | sort -r | head
```

Once a candidate is found, resume with `pi --session <path>` and verify with
`/session`. Use `pi --export <session.jsonl> [output.html]` when the user wants
a readable export rather than a resumed conversation.
