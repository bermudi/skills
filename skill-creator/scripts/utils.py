"""Shared utilities for skill-creator scripts."""

from __future__ import annotations

import json
from pathlib import Path


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    content = (skill_path / "SKILL.md").read_text()
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:"):].strip()
            # Handle YAML multiline indicators (>, |, >-, |-)
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (
                    frontmatter_lines[i].startswith("  ")
                    or frontmatter_lines[i].startswith("\t")
                ):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation_lines)
                continue
            else:
                if value.startswith('"') and value.endswith('"'):
                    try:
                        description = json.loads(value)
                    except json.JSONDecodeError:
                        description = value[1:-1]
                else:
                    description = value.strip("'")
        i += 1

    return name, description, content


def replace_skill_description(content: str, new_description: str) -> str:
    """Return SKILL.md content with its frontmatter description replaced."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    frontmatter = lines[1:end_idx]
    updated: list[str] = []
    replaced = False
    i = 0
    while i < len(frontmatter):
        line = frontmatter[i]
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
            updated.append(f"description: {json.dumps(new_description)}")
            replaced = True
            if value in (">", "|", ">-", "|-"):
                i += 1
                while i < len(frontmatter) and (
                    frontmatter[i].startswith("  ") or frontmatter[i].startswith("\t")
                ):
                    i += 1
                continue
        else:
            updated.append(line)
        i += 1

    if not replaced:
        updated.append(f"description: {json.dumps(new_description)}")

    return "\n".join(["---", *updated, *lines[end_idx:]])
