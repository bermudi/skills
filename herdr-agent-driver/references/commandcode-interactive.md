# Command Code — Interactive Mode (Driver Distillation)

> **Distilled from** <https://commandcode.ai/docs/interactive-mode> — 2026-05-13. Covers TUI surface, model/mode handling, keybindings.
> Herdr kind is unintegrated (`cmd`/`commandcode`) — drive via `herdr pane run` + `herdr wait output` or hook-reported state; see **references/harness-recipes.md** and **references/interactive-patterns.md**.

## Surface (whole screen, three prefixes + five keys)

| Prefix | Result |
|---|---|
| `/` at start | Slash menu — built-in, custom (`$ARGUMENTS` templating), skill, mod commands. Ranked: names starting with query > names containing > description |
| `!` at start | Bash mode: line runs as shell; command + output joins session (e.g. `!git status`) |
| `@` anywhere | File-path autocomplete; mentioned file becomes context; also pulls any `AGENTS.md` between file's dir and project root (Memory) |

| Key | Action |
|---|---|
| `Shift+Tab` (also `Alt+M` on Windows) | Cycle permission mode |
| `Esc` | Stop what's running |
| `Esc Esc` | Rewind to previous checkpoint (`/rewind`) |
| `Ctrl+O` | Toggle full tool output |
| `Ctrl+G` | Open prompt in `$EDITOR` (`code`/`vim`/`nano`/`emacs`/`subl`…) |

- `/hotkeys` shows every shortcut (incl. overrides); `/help` is short list.
- Slash menu: `↑/↓` move, `Enter` runs, `Tab`/`→` inserts with trailing space for args, `Esc` closes. Full catalog at `https://commandcode.ai/docs/reference/slash-commands` (60+ commands; safe mid-turn vs not, plus custom).

## Bash & file mentions

- `!` runs shell directly — both command and output added to session so agent sees what you saw.
- `@` mention pulls intermediate `AGENTS.md` files along the path to root (subdirectory memory).

## Model picking

`/model` switches model for running session **and becomes default for new sessions** (next `cmd` starts there). Existing sessions untouched.

`--model` / `-m` is **session-scoped** override — doesn't change saved default; cleared by an explicit `/model` pick or a `/resume` switch. Unknown IDs rejected up front; `cmd --list-models` enumerates. Details at `https://commandcode.ai/docs/reference/cli/models`.

Resolution order for requests:

1. `--model` flag (until cleared by `/model` or conversation switch)
2. Model picked via `/model` this session, or adopted from resumed conversation
3. Default (last `/model` pick snapshotted at session start → built-in default) — banner and requests stay in sync.

**Resuming restores model transiently** (doesn't rewrite default):

- **Cold `--resume`/`--continue`** (fresh process): adopts saved conversation's model — unless same command also passes `--model X` (which wins).
- **In-TUI `/resume`**: always adopts jumped-into conversation's model, even over launch `--model` or prior `/model`.

## Permission modes

`Shift+Tab` cycles `default → auto-accept → plan → default`. With `--yolo`, cycle gains `bypass` as 4th rung: `plan → bypass → default`.

Two off-cycle modes:
- `dont-ask` — from settings or `--permission-mode dont-ask`; `Shift+Tab` from it goes to `auto-accept`.
- `bypass` — only via `--yolo`.

Jump directly via `/mode` or shorthands `/mode:default`, `/mode:auto-accept`, `/mode:plan`. Complete permissions (rule syntax, decision ladder, safety) at `https://commandcode.ai/docs/permissions`.

## Pasting

Paste >300 chars collapses to `[Text#N]` placeholder for readability; full text still submits, and `Ctrl+G` edits real prompt. To inline raw, set in `~/.commandcode/config.json`:

```json
{ "collapsePastedText": false }
```

Top-level key (alongside `theme`, `compactMode`). Legacy fallback `input.collapsePastedText` in `settings.json` honored only if top-level absent.

## Keybindings — all via `~/.commandcode/keybindings.json`

File is optional; missing/typoed lines fall back to defaults; one bad entry never breaks the rest. `/reload` applies edits mid-session. Earlier short names (`cursorUp`, `expandTools`) auto-mapped to dotted IDs.

**How a binding is written:** `modifier+key` (`ctrl+a`, `alt+left`, `shift+enter`); multi-mods allowed, order irrelevant. Modifiers: `ctrl`/`control`, `shift`, `alt`/`option`/`opt`/`meta`. Keys: letters/digits/symbols or named `up/down/left/right/home/end/pageup/pagedown/enter/return/escape/esc/tab/space/backspace/delete/insert` (case-insensitive). Value can be single string or list (`["ctrl+a","home"]`); `[]` unbinds.

**Coverage today:** Remapping live for Moving cursor, word/line deletion, whole `/tree` navigator, and `app.permission.cycle`, `app.tools.expand`, `app.model.select`, `app.todos.toggle`. Rest listed for reference; custom bindings for them "on the way". `backspace` stays fixed.

### Moving cursor

| Action | Default | Does |
|---|---|---|
| `tui.editor.cursorLeft` | `left` | Char left |
| `tui.editor.cursorRight` | `right` | Char right |
| `tui.editor.cursorUp` | `up` | Line up |
| `tui.editor.cursorDown` | `down` | Line down |
| `tui.editor.cursorWordLeft` | `alt+left`, `ctrl+left`, `alt+b` | Word back |
| `tui.editor.cursorWordRight` | `alt+right`, `ctrl+right`, `alt+f` | Word forward |
| `tui.editor.cursorLineStart` | `home`, `ctrl+a` | Line start |
| `tui.editor.cursorLineEnd` | `end`, `ctrl+e` | Line end |

### Editing

| Action | Default | Does |
|---|---|---|
| `tui.editor.deleteCharBackward` | `backspace` | Char behind |
| `tui.editor.deleteCharForward` | `delete` | Char ahead |
| `tui.editor.deleteWordBackward` | `ctrl+w`, `alt+backspace` | Word behind |
| `tui.editor.deleteToLineStart` | `ctrl+u` | To line start |
| `tui.editor.deleteToLineEnd` | `ctrl+k` | To line end |

### Composing

| Action | Default | Does |
|---|---|---|
| `tui.input.newLine` | `shift+enter`, `ctrl+j` | Newline not submit |
| `tui.input.submit` | `enter` | Send |

### Session

| Action | Default | Does |
|---|---|---|
| `app.permission.cycle` | `shift+tab`, `alt+m` | Cycle permission |
| `app.tools.expand` | `ctrl+o` | Full tool output |
| `app.model.select` | `alt+p` | Quick model picker (`option+p` macOS) |
| `app.todos.toggle` | `ctrl+x` | Todo manager (`/todos` overlay) |
| `app.editor.external` | `ctrl+g` | `$EDITOR` |
| `app.input.stash` | `ctrl+s` | Stash/restore prompt |
| `app.interrupt` | `escape` | Stop |
| `app.clipboard.pasteImage` | `ctrl+v` | Paste image |

### `/tree` browser (applies inside `https://commandcode.ai/docs/sessions#branching`)

| Action | Default | Does |
|---|---|---|
| `app.tree.foldOrPrevBranch` | `alt+left`, `shift+tab`, `ctrl+left` | Fold / jump prev branch (Mission Control owns `ctrl+←/→` on macOS, so Alt-arrows default) |
| `app.tree.unfoldOrNextBranch` | `alt+right`, `tab`, `ctrl+right` | Unfold / jump next |
| `app.tree.label` | `shift+l` | Edit entry label |
| `app.tree.labelTime` | `shift+t` | Toggle label timestamps |
| `app.tree.filter.default` | `ctrl+d` | Default view |
| `app.tree.filter.noTools` | `ctrl+t` | Hide tool rows |
| `app.tree.filter.userOnly` | `ctrl+u` | User msgs only |
| `app.tree.filter.labeledOnly` | `ctrl+l` | Labeled only |
| `app.tree.filter.all` | `ctrl+a` | Show every entry |
| `app.tree.filter.cycle` | `ctrl+o` | Cycle filter forward |
| `app.tree.filter.cycleBack` | `shift+ctrl+o` | Cycle filter back |

### Fixed (not remappable)

| Key | Where | Does |
|---|---|---|
| `Ctrl+E` (`Ctrl+Y` in VS Code-family terminals) | Permission prompt | Explain pending shell command in plain English (On-demand explanations in `/config` General; on = only on `Ctrl+E`, off = every explanation upfront) |
| `Ctrl+E` / `Ctrl+Y` | Transcript on | Toggle limited/full transcript (permission prompt takes priority) |

Inside VS Code/Cursor/Windsurf terminals, `Ctrl+E` is claimed by IDE, so `cmd` uses `Ctrl+Y`.

## Herdr driver notes

- No official `herdr agent start` kind — use `herdr pane run <pane> "cmd -t --auto-accept"` (or `--yolo` in sandbox) and `herdr wait output` for a completion marker, or report state via `herdr pane report-agent "$HERDR_PANE_ID" --source cmd-hook --agent cmd --state idle --seq N`.
- Don't send multi-line pastes raw — write to file, then prompt with `Read task.md`. Collapsed `[Text#N]` is display-only; model still gets full text, but driver shouldn't rely on it.
- Reset context with `Esc Esc` (`/rewind`) or new session; `/tree` browser is driver-visible via `agent read --source visible`.
