# Keybindings

Pi keybindings are defined in `~/.pi/agent/keybindings.json`. View current bindings with `/hotkeys` in interactive mode.

## Commonly used defaults

| Key | Action |
|-----|--------|
| Ctrl+C | Clear editor |
| Ctrl+D | Quit (when editor empty) |
| Escape | Cancel/abort |
| Escape twice | Open `/tree` (configurable via `doubleEscapeAction`) |
| Ctrl+L | Open model selector |
| Ctrl+P / Shift+Ctrl+P | Cycle scoped models forward/backward |
| Shift+Tab | Cycle thinking level |
| Ctrl+O | Collapse/expand tool output |
| Ctrl+T | Collapse/expand thinking blocks |

## Editor shortcuts

| Feature | How |
|---------|-----|
| File reference | Type `@` to fuzzy-search project files |
| Path completion | Tab to complete paths |
| Multi-line | Shift+Enter (or Ctrl+Enter on Windows Terminal) |
| Images | Ctrl+V to paste (Alt+V on Windows), or drag onto terminal |
| Bash commands | `!command` runs and sends output to LLM, `!!command` runs without sending |

## Message queuing

| Key | Action |
|-----|--------|
| Enter | Queue a steering message (delivered after current tool call finishes) |
| Alt+Enter | Queue a follow-up message (delivered after agent finishes all work) |
| Escape | Abort and restore queued messages to editor |
| Alt+Up | Retrieve queued messages back to editor |

On Windows Terminal, `Alt+Enter` is fullscreen by default. Remap it. See `docs/terminal-setup.md`.

## Customization

Edit `~/.pi/agent/keybindings.json` to remap or add bindings. See `docs/keybindings.md` for the full reference, action names, and examples.

## Double-escape action

Configure what double-Escape does:
```json
{ "doubleEscapeAction": "tree" }
```
Values: `"tree"`, `"fork"`, `"none"`.

## Full docs

https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/keybindings.md
