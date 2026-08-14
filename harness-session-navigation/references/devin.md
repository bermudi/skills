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

When `devin list` is unavailable (unauthenticated, binary missing, or no
sessions in the current directory), fall back to scanning the transcript
directory (see below) or use `find_sessions.py --devin-source disk`. Do not
hide CLI failures: report the exact error on stderr, then fall back rather
than returning an empty result silently.

## Directory mismatch on resume

A session records its original directory. If Devin asks whether to use the
session's original directory or the current one, preserve the original unless
the user explicitly wants to relocate the work. Verify the workspace after
resume before sending a modifying prompt.

## Storage and transcript inspection

Devin keeps two separate on-disk sources: a **transcript directory** (one JSON
file per session, the primary source for message bodies and tool calls) and a
**SQLite catalog** (metadata only — IDs, titles, working directories, activity
timestamps).

### Transcripts (primary source for content)

```text
~/.local/share/devin/cli/transcripts/<session-id>.json
```

Each transcript is a single JSON object (not JSONL) with this shape:

```text
{
  "session_id": "...",
  "schema_version": "ATIF-v1.7",
  "agent": { "name": "devin", "version": "...", "model_name": "..." },
  "steps": [
    {
      "step_id": 1,
      "source": "system" | "user" | "agent",
      "message": "<string, may be long>",
      "timestamp": "2026-08-14T02:42:23.983707132+00:00",
      "tool_calls": [ { "function_name": "...", "arguments": {...}, "tool_call_id": "..." } ],
      "observation": { "results": [ { "content": "...", "source_call_id": "..." } ] }
    },
    ...
  ],
  "final_metrics": { "total_steps": ..., "total_prompt_tokens": ..., ... }
}
```

Key fields:

- **`source`** — `system` (instructions, tool definitions), `user` (prompts),
  `agent` (assistant responses, tool calls, and their results).
- **`message`** — a string. For `user` steps it is the prompt; for `agent`
  steps it is the assistant's text output.
- **`tool_calls`** — present on `agent` steps that invoke tools. Each entry has
  `function_name`, `arguments` (a JSON object), and `tool_call_id`.
- **`observation.results`** — present on the same step as its `tool_calls`.
  Each result has `content` (the tool output string) and `source_call_id`
  (matching the `tool_call_id`).

To find a transcript by session ID:

```bash
ls "$HOME/.local/share/devin/cli/transcripts/<session-id>.json"
```

To list recent transcripts without dumping content:

```bash
find "$HOME/.local/share/devin/cli/transcripts" -name '*.json' \
  -printf '%TY-%Tm-%Td %TH:%TM  %f\n' | sort -r | head
```

To extract user prompts from a transcript:

```bash
jq -r '.steps[] | select(.source == "user") | .message' transcript.json
```

To list tool calls (e.g., recovering files written by a past session):

```bash
jq -r '.steps[] | select(.tool_calls) | .tool_calls[] | "\(.function_name)\t\(.arguments.file_path // .arguments.command // "")"' transcript.json
```

Prefer the helper scripts (`inspect_session.py`, `search_session.py`) over
ad-hoc `jq` for structured inspection — they normalize across harnesses and
bound output.

### Recovering files from a past session

A common use case is recovering files written by a session whose working tree
was lost. The helper scripts handle this directly:

```bash
# See what files a session wrote or edited:
uv run scripts/inspect_session.py ~/.local/share/devin/cli/transcripts/<id>.json

# Extract just the file paths from write calls:
uv run scripts/search_session.py ~/.local/share/devin/cli/transcripts/<id>.json \
  --tool write --extract --extract-field file_path

# Extract full file contents from write calls (raise the preview cap):
uv run scripts/search_session.py ~/.local/share/devin/cli/transcripts/<id>.json \
  --tool write --extract --preview-chars 100000 --format jsonl

# Filter tool calls by argument content:
uv run scripts/search_session.py ~/.local/share/devin/cli/transcripts/<id>.json \
  --type tool_call --tool-arg file_path=skills
```

The `inspect_session.py` output for Devin includes `files_touched` (unique
paths from write/edit calls), `tool_call_summary` (counts by tool name),
`duration`, `step_counts`, and `final_metrics` — enough to decide whether a
transcript is worth recovering from before reading its full content.

### SQLite catalog (metadata only)

The catalog stores IDs, titles, working directories, and activity timestamps.
It does **not** store message bodies or tool calls — those live in transcripts.

```text
~/.local/share/devin/cli/sessions.db
~/.local/share/devin/cli-next/sessions.db
```

Some versions use `cli_sessions.db`. This is an implementation detail; prefer
`devin list` and the transcript directory over direct SQLite access. If
`devin list` is unavailable, locate the most recently modified database:

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

Never modify the database, lock files, or transcript files. The CLI also keeps
summaries and logs; logs are for troubleshooting, not the default route for
finding conversations.
