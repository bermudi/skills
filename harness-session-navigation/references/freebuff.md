# Freebuff conversations

Freebuff calls saved harness sessions **chats** or **conversations**. Do not
confuse these with its timed usage session; `/end-session` changes the free
model/usage slot, not chat history.

## Find and resume

```bash
freebuff --continue                 # activate the most recent chat
freebuff --continue <conversation-id> # activate this chat
freebuff --cwd /path/to/project --continue # activate that project's latest chat
```

These are resume operations, not read-only discovery. For discovery, use
`/history` from an already launched Freebuff session.

Inside Freebuff:

- `/history` (alias `/chats`) opens a searchable chat picker.
- Type to filter by the first user prompt; use arrows and Enter to select.
- `/new` (aliases `/clear`, `/reset`) starts another chat.
- The picker has a delete action. Do not use it without explicit approval.

The history picker is the best discovery interface: it shows relative time,
message count, and first-prompt preview. Freebuff has no Pi/Command Code-style
session tree, fork, or checkpoint navigation interface. Start a new chat when a
separate branch is needed, and preserve any needed context explicitly.

## Project scope and IDs

History is project-scoped. `--cwd` selects the project before applying
`--continue`; without it Freebuff uses the current directory. A bare
`--continue` picks the most recently modified chat directory. A provided ID
selects that chat directly.

Current chat IDs are timestamp-like strings such as:

```text
2026-08-07T21-28-51.123Z
```

Treat IDs as opaque; copy the complete value shown on disk or by the picker.

## Storage and fallback inspection

Current production builds keep chats under the shared Codebuff/Freebuff config
root, not in a project-local `.freebuff` directory:

```text
~/.config/manicode/projects/<project-basename>/chats/<chat-id>/
```

Important files include:

- `chat-meta.json` — bounded first-prompt/message-count summary
- `chat-messages.json` — full conversation

The project key currently uses only the project's basename, so two repositories
with the same final directory name may share a history bucket. `--cwd` cannot
disambiguate that collision. Inspect first-prompt metadata, dates, and bounded
message excerpts before selecting an ID; if still ambiguous, ask the user.

Prefer metadata-only discovery:

```bash
find "$HOME/.config/manicode/projects" -path '*/chats/*/chat-meta.json' \
  -type f -print0 |
  xargs -0 jq -r '[input_filename, .firstPrompt, .messageCount] | @tsv' |
  rg -i 'known phrase'
```

Do not dump `chat-messages.json` unless metadata and the picker are insufficient.
If a chat is marked unreadable, report corruption and preserve the directory;
do not hand-edit the JSON to make it disappear.

Project-local `.freebuff/session-*` files may be user-created terminal logs or
older artifacts. Their names alone do not prove they are resumable Freebuff
chat storage.
