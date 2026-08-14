# Command Code sessions

`cmd` and `commandcode` are the same harness. Its picker and `--continue` are
project-scoped, so launch from the target working directory.

## Find and resume

```bash
cmd -c                         # latest visible session in this project
cmd -r                         # searchable picker
cmd -r "session name"          # name or ID
cmd --session <path-or-id>     # transcript path or unique ID prefix
cmd -c --fork-session          # continue latest as a new session
```

Inside Command Code:

- `/resume` and `/sessions` open the picker.
- `/session-file` prints the active session ID and absolute transcript path.
- `/rename <name>` (`/name`) improves later discovery.
- `/clear` or `/new` starts a new session while preserving the old one.

The picker searches and can rename/delete/filter sessions. Deletion requires
explicit user approval. Headless `cmd -p` sessions are normally hidden from the
picker and `--continue`, but an exact session ID can still resume them.

## Navigate, restore, and branch

- `/tree` browses all branches and jumps to a point without copying the file.
- `/fork [name]` copies the whole session tree plus checkpoints and switches to
  the copy.
- `/clone` copies only the active conversation branch; checkpoints are not
  copied.
- `/rewind` or double `Esc` opens checkpoint restoration. It can restore
  conversation, code, or both. This may overwrite, recreate, or delete working
  files, so it is a mutating recovery operation—not session browsing.

Use `cmd -c --fork-session` or `/fork` before risky alternatives when the
original must stay pristine.

## Storage and fallback inspection

Default transcripts:

```text
~/.commandcode/projects/<project-slug>/<session-id>.jsonl
```

Common sidecars:

- `<id>.meta.json` — title, model, lineage, trace/compaction metadata
- `<id>.checkpoints.jsonl` — rewind checkpoints
- `<id>.prompts.jsonl` — prompt history
- `<id>.share.json` — sharing state

Search metadata before transcripts:

```bash
find "$HOME/.commandcode/projects" -name '*.meta.json' -type f -print0 |
  xargs -0 jq -r '[input_filename, (.title // ""), (.model // "")] | @tsv' |
  rg -i 'known phrase'
```

Metadata formats can change; if `jq` reports a shape mismatch, inspect one
candidate's keys rather than guessing. Never edit transcript or sidecar files.
A transcript path outside the current project can be passed to `--session`;
Command Code may continue appending to that file, so fork first if preservation
matters.
