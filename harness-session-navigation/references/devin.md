# Devin CLI sessions

Devin's session catalog is scoped to the current directory. Run discovery from
the original workspace whenever possible.

## Find and resume

```bash
devin -c                    # continue latest session in this directory
devin -r                    # interactive recent-session picker
devin -r <session-id>       # resume a known ID
devin list                  # interactive session list for this directory
devin list --format json    # scriptable metadata
devin list --format csv     # compact tabular metadata
```

Inside Devin:

- `/resume` or `/resume <id>` finds/resumes sessions.
- `/ls` (`/list-sessions`) lists this directory; `/ls --all` widens the view.
- `/continue` resumes the latest session.
- `/new` starts fresh.
- `/rm-session <id>` is irreversible; never run it without explicit approval.

For automated discovery, prefer `devin list --format json` and select only the
fields needed. Current output includes ID, working directory, last activity,
and title. Example:

```bash
(cd /path/to/project && devin list --format json) |
  jq -r '.[] | [.id, .title, .last_activity_ago, .working_directory] | @tsv'
```

Do not hide Devin failures: if the command is unauthenticated or the database
cannot be read, report the exact error instead of silently falling back.

## Directory mismatch on resume

A session records its original directory. If Devin asks whether to use the
session's original directory or the current one, preserve the original unless
the user explicitly wants to relocate the work. Verify the workspace after
resume before sending a modifying prompt.

## Storage and fallback inspection

The Linux CLI stores its catalog in SQLite under its local data directory.
Common locations include:

```text
~/.local/share/devin/cli/sessions.db
~/.local/share/devin/cli-next/sessions.db
```

Some versions use `cli_sessions.db`. These are implementation details, not the
primary interface. If `devin list` is unavailable, locate candidates and use
the most recently modified database associated with the active install:

```bash
find "$HOME/.local/share/devin" -maxdepth 3 -type f \
  \( -name 'sessions.db' -o -name 'cli_sessions.db' \) \
  -printf '%T@ %p\n' | sort -nr
```

Before querying, inspect `.tables` and `.schema sessions`; only issue a
read-only `SELECT` if those names and columns exist:

```bash
sqlite3 -readonly /chosen/path/sessions.db '.tables'
sqlite3 -readonly /chosen/path/sessions.db '.schema sessions'
```

Never modify the database or lock files. The CLI also keeps summaries and logs;
logs are for troubleshooting, not the default route for finding conversations.
