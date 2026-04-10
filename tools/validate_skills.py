#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml


MAX_SKILL_NAME_LENGTH = 64
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}


def skills_root() -> Path:
    return Path(__file__).resolve().parent.parent / "skills"


def find_skill_dirs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name != "scripts" and (path / "SKILL.md").exists()
    )


def read_text_with_fallbacks(path: Path) -> str:
    encodings = ("utf-8", "utf-8-sig", "cp936")
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding, errors="strict")
        except UnicodeDecodeError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def validate_frontmatter(skill_md: Path) -> list[str]:
    errors: list[str] = []
    content = read_text_with_fallbacks(skill_md)
    if not content.startswith("---"):
        return ["missing YAML frontmatter"]

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return ["invalid frontmatter block"]

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return [f"invalid YAML: {exc}"]

    if not isinstance(frontmatter, dict):
        return ["frontmatter must be a mapping"]

    unexpected = sorted(set(frontmatter.keys()) - ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        errors.append(f"unexpected frontmatter keys: {', '.join(unexpected)}")

    name = str(frontmatter.get("name", "")).strip()
    description = str(frontmatter.get("description", "")).strip()

    if not name:
        errors.append("missing name")
    elif not re.fullmatch(r"[a-z0-9-]+", name):
        errors.append("name must be lowercase hyphen-case")
    elif len(name) > MAX_SKILL_NAME_LENGTH:
        errors.append(f"name too long: {len(name)} > {MAX_SKILL_NAME_LENGTH}")

    if not description:
        errors.append("missing description")

    return errors


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    openai_yaml = skill_dir / "agents" / "openai.yaml"

    if not skill_md.exists():
        errors.append("missing SKILL.md")
        return errors

    errors.extend(validate_frontmatter(skill_md))

    if not openai_yaml.exists():
        errors.append("missing agents/openai.yaml")

    return errors


def validate_all(root: Path) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for skill_dir in find_skill_dirs(root):
        errors = validate_skill_dir(skill_dir)
        if errors:
            results[skill_dir.name] = errors
    return results


def main() -> int:
    root = skills_root()
    results = validate_all(root)
    discovered = [path.name for path in find_skill_dirs(root)]
    print(
        json.dumps(
            {
                "skills_root": str(root),
                "discovered_skills": discovered,
                "invalid_skills": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
