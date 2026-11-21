# Specification

> The complete format specification for Agent Skills.

## Directory structure

A skill is a directory containing, at minimum, a `SKILL.md` file:

```text
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/           # Optional: templates, resources
└── ...               # Any additional files or directories
```

## `SKILL.md` format

The `SKILL.md` file must contain YAML frontmatter followed by Markdown content.

### Frontmatter

| Field | Required | Constraints |
| --- | --- | --- |
| `name` | Yes | Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen. |
| `description` | Yes | Max 1024 characters. Non-empty. Describes what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled license file. |
| `compatibility` | No | Max 500 characters. Indicates environment requirements (intended product, system packages, network access, etc.). |
| `metadata` | No | Arbitrary key-value mapping for additional metadata. |
| `allowed-tools` | No | Space-separated string of pre-approved tools the skill may use. (Experimental) |
| `disable-model-invocation` | No | Set to `true` to prevent the model from automatically loading this skill. Use for manual-only workflows. Default: `false`. |

**Minimal example:**

```markdown
---
name: skill-name
description: A description of what this skill does and when to use it.
---
```

**Example with optional fields:**

```markdown
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
license: Apache-2.0
metadata:
  author: example-org
  version: "1.0"
---
```

#### `name` field

The required `name` field:

* Must be 1-64 characters
* May only contain unicode lowercase alphanumeric characters (`a-z`, `0-9`) and hyphens (`-`)
* Must not start or end with a hyphen (`-`)
* Must not contain consecutive hyphens (`--`)
* Must match the parent directory name

```yaml
# Valid
name: pdf-processing
name: data-analysis
name: code-review

# Invalid
name: PDF-Processing  # uppercase not allowed
name: -pdf            # cannot start with hyphen
name: pdf--processing # consecutive hyphens not allowed
```

#### `description` field

The required `description` field:

* Must be 1-1024 characters
* Should describe both what the skill does and when to use it
* Should include specific keywords that help agents identify relevant tasks

```yaml
# Good
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.

# Poor
description: Helps with PDFs.
```

#### `license` field

The optional `license` field specifies the license applied to the skill (SPDX identifier or reference to a bundled license file):

```yaml
license: Proprietary. LICENSE.txt has complete terms
```

#### `compatibility` field

The optional `compatibility` field (1-500 characters) should only be included when a skill has specific environment requirements (intended product, system packages, network access, runtimes). Most skills do not need it.

```yaml
compatibility: Requires git, docker, jq, and access to the internet
compatibility: Requires Python 3.13+ and uv
```

#### `metadata` field

An optional map from string keys to string values for additional properties not defined by the spec:

```yaml
metadata:
  author: example-org
  version: "1.0"
```

#### `allowed-tools` field

An optional space-separated string of pre-approved tools (experimental; support varies by harness):

```yaml
allowed-tools: Bash(git:*) Bash(jq:*) Read
```

### Body content

The Markdown body after the frontmatter contains the skill instructions. There are no format restrictions. Note that the agent loads this entire file once it activates a skill — split longer `SKILL.md` content into referenced files.

## Optional directories

### `scripts/`

Executable code agents can run. Scripts should be self-contained (or clearly declare dependencies), print helpful error messages, and handle edge cases gracefully.

### `references/`

Additional documentation loaded on demand (`REFERENCE.md`, domain-specific files, etc.). Keep individual reference files focused so each load stays small.

### `assets/`

Static resources: templates, images, lookup tables, schemas.

## Progressive disclosure

Skills manage context in three tiers:

1. **Metadata** (~100 tokens): `name` and `description` load at startup for all model-invoked skills.
2. **Instructions** (< 5000 tokens recommended, < 500 lines): the full `SKILL.md` body loads on activation.
3. **Resources** (as needed): files in `scripts/`, `references/`, or `assets/` load only when required.

## File references

Reference sibling files using relative paths from the skill root (and keep references one level deep from `SKILL.md` where possible):

```markdown
See [the reference guide](references/REFERENCE.md) for details.
```

## Validation

Use [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) to validate skills after any frontmatter edit:

```bash
# Install once
uv tool install git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref

# Validate a skill
skills-ref validate ./my-skill
```

> **Warning:** Always validate after editing frontmatter. The `skills` CLI catches YAML parse errors silently and skips invalid skills — your skill just disappears without an error. (`skills-ref` 0.1.0 flags `disable-model-invocation` as an unexpected field pending agentskills#105; ignore only that line locally.)
