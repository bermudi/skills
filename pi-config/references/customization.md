# Customization: Extensions, Skills, Themes, Packages

Pi has four customization mechanisms, all composable and all sharable via pi packages.

## Extensions

TypeScript modules that add tools, commands, keyboard shortcuts, event handlers, and UI components. The most powerful customization mechanism — can do anything from custom bash tools to sub-agents to a Doom game while waiting.

**Locations:** `~/.pi/agent/extensions/`, `.pi/extensions/`

**Minimal example:**

```typescript
export default function (pi: ExtensionAPI) {
  pi.registerTool({ name: "deploy", /* ... */ });
  pi.registerCommand("stats", { /* ... */ });
}
```

**Key capabilities:**
- Register custom tools (or replace built-in tools entirely)
- Register slash commands
- Hook into events (`tool_call`, `before_tool_call`, `after_tool_call`, `message`, `compaction`)
- Custom TUI components (editors, headers, footers, overlays)
- Custom providers and auth flows
- Permission gates and path protection
- MCP server integration

**CLI flags:** `-e <path>`, `--no-extensions`

**Full docs:** https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md
(TUI components: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/tui.md)

## Skills

On-demand capability packages following the [Agent Skills standard](https://agentskills.io). Invoke via `/skill:name` or let the agent load them automatically when the description matches the task.

**Locations:** `~/.pi/agent/skills/`, `~/.agents/skills/`, `.pi/skills/`, `.agents/skills/` (walked up from cwd)

**Structure:**
```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + instructions
├── scripts/          # Optional: executable tooling
├── references/       # Optional: deep-dive docs (progressive disclosure)
└── assets/           # Optional: templates, resources
```

**CLI flags:** `--skill <path>`, `--no-skills`

**Full docs:** https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md

## Prompt Templates

Reusable prompts as Markdown files. Type `/name` to expand.

**Locations:** `~/.pi/agent/prompts/`, `.pi/prompts/`

**Example** (`~/.pi/agent/prompts/review.md`):
```markdown
Review this code for bugs, security issues, and performance problems.
Focus on: {{focus}}
```

**CLI flags:** `--prompt-template <path>`, `--no-prompt-templates`

**Full docs:** https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/prompt-templates.md

## Themes

Terminal color themes. Hot-reload: edit the active theme file and pi applies changes immediately. Built-in: `dark`, `light`.

**Locations:** `~/.pi/agent/themes/`, `.pi/themes/`

**CLI flags:** `--theme <path>`, `--no-themes`

**Full docs:** https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/themes.md

## Pi Packages

Bundle and share extensions, skills, prompts, and themes via npm or git.

```bash
pi install npm:@foo/pi-tools
pi install git:github.com/user/repo
pi remove npm:@foo/pi-tools
pi list
pi update
pi config  # enable/disable package resources
```

**Create a package** by adding a `pi` key to `package.json`:
```json
{
  "name": "my-pi-package",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions"],
    "skills": ["./skills"],
    "prompts": ["./prompts"],
    "themes": ["./themes"]
  }
}
```

Without a `pi` manifest, pi auto-discovers from conventional directories (`extensions/`, `skills/`, `prompts/`, `themes/`).

**Security:** Pi packages run with full system access. Extensions execute arbitrary code. Review source code before installing.

**Full docs:** https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/packages.md

## Resource management in settings

Customize which resources load via `settings.json`:

```json
{
  "packages": ["pi-skills", { "source": "@org/my-ext", "skills": ["brave-search"], "extensions": [] }],
  "extensions": ["./my-ext.ts"],
  "skills": [".pi/skills/custom/"],
  "prompts": ["~/.pi/agent/prompts/"],
  "themes": [],
  "enableSkillCommands": true
}
```

Arrays support glob patterns and exclusions (`!pattern` to exclude, `+path` to force-include, `-path` to force-exclude).
