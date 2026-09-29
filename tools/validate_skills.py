#!/usr/bin/env python3
"""校验 skills/ 下的 skill 结构，以及 registry/skills.yaml 的一致性。

    uv run python tools/validate_skills.py            # 校验全部
    uv run python tools/validate_skills.py foo bar     # 只校验指定 skill
    uv run python tools/validate_skills.py --json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

import sys

# 支持 `python tools/<name>.py` 直接运行（把仓库根加入 sys.path）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.console import configure_output, fail, ok, skip  # noqa: E402
from tools.registry import (
    MAX_NAME_LENGTH,
    NAME_PATTERN,
    REGISTRY_FILE,
    REPO_ROOT,
    SKILLS_ROOT,
    RegistryError,
    SkillEntry,
    discover_skill_dirs,
    entry_map,
    load_registry,
    read_text,
)
from tools.sync_targets import target_names  # noqa: E402

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
SKILL_SUBDIRS = ("agents", "assets", "references", "scripts")
#: SKILL.md 中形如 `references/foo.md` 的引用必须真实存在。
REFERENCE_PATTERN = re.compile(
    r"(?<![\w./-])((?:" + "|".join(SKILL_SUBDIRS) + r")/[\w./-]+\.[A-Za-z0-9]+)"
)

# 兼容旧调用方：仓库历史上已有 cp936 编码的 skill 文件。
read_text_with_fallbacks = read_text


def skills_root() -> Path:
    return SKILLS_ROOT


def find_skill_dirs(root: Path | None = None) -> list[Path]:
    return discover_skill_dirs(root or SKILLS_ROOT)


def validate_frontmatter(skill_md: Path) -> list[str]:
    errors: list[str] = []
    content = read_text_with_fallbacks(skill_md)
    if not content.startswith("---"):
        return ["missing YAML frontmatter"]

    match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
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
    elif not NAME_PATTERN.fullmatch(name):
        errors.append("name must be lowercase hyphen-case")
    elif len(name) > MAX_NAME_LENGTH:
        errors.append(f"name too long: {len(name)} > {MAX_NAME_LENGTH}")

    if not description:
        errors.append("missing description")

    return errors


def frontmatter_name(skill_md: Path) -> str:
    content = read_text_with_fallbacks(skill_md)
    match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if not match:
        return ""
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("name", "")).strip()


def validate_references(skill_dir: Path, content: str) -> list[str]:
    errors: list[str] = []
    for ref in sorted(set(REFERENCE_PATTERN.findall(content))):
        if not (skill_dir / ref).exists():
            errors.append(f"missing referenced file: {ref}")
    return errors


def validate_agent_metadata(skill_dir: Path, skill_name: str) -> list[str]:
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        return ["missing agents/openai.yaml"]

    try:
        data = yaml.safe_load(read_text_with_fallbacks(openai_yaml))
    except yaml.YAMLError as exc:
        return [f"invalid agents/openai.yaml: {exc}"]

    if not isinstance(data, dict):
        return ["agents/openai.yaml must be a mapping"]

    errors: list[str] = []
    interface = data.get("interface")
    if not isinstance(interface, dict):
        errors.append("agents/openai.yaml: missing 'interface' mapping")
        return errors

    for field in ("display_name", "short_description", "default_prompt"):
        if not str(interface.get(field, "")).strip():
            errors.append(f"agents/openai.yaml: interface.{field} is empty")

    prompt = str(interface.get("default_prompt", ""))
    if prompt and skill_name and f"${skill_name}" not in prompt:
        errors.append(f"agents/openai.yaml: interface.default_prompt should mention ${skill_name}")
    return errors


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return ["missing SKILL.md"]

    if not NAME_PATTERN.fullmatch(skill_dir.name):
        errors.append("directory name must be lowercase kebab-case")

    errors.extend(validate_frontmatter(skill_md))

    declared = frontmatter_name(skill_md)
    if declared and declared != skill_dir.name:
        errors.append(f"directory name '{skill_dir.name}' does not match skill name '{declared}'")

    content = read_text_with_fallbacks(skill_md)
    errors.extend(validate_references(skill_dir, content))
    errors.extend(validate_agent_metadata(skill_dir, declared or skill_dir.name))
    return errors


def validate_all(root: Path | None = None) -> dict[str, list[str]]:
    """返回 {skill_name: [错误...]}，只包含有问题的 skill。"""

    results: dict[str, list[str]] = {}
    for skill_dir in find_skill_dirs(root):
        errors = validate_skill_dir(skill_dir)
        if errors:
            results[skill_dir.name] = errors
    return results


def validate_registry(entries: list[SkillEntry], skills_root: Path | None = None) -> list[str]:
    """registry 自身合法性与仓库目录的一致性检查。"""

    errors: list[str] = []
    root = skills_root or SKILLS_ROOT
    known = entry_map(entries)

    for entry in entries:
        location = (REPO_ROOT / entry.path).resolve()
        if not location.is_dir():
            errors.append(f"registry: {entry.name} path does not exist: {entry.path}")
            continue
        if not (location / "SKILL.md").exists():
            errors.append(f"registry: {entry.name} has no SKILL.md in {entry.path}")

    discovered = {path.name for path in discover_skill_dirs(root)}
    for name in sorted(discovered - set(known)):
        errors.append(f"registry: skill '{name}' is not registered in {REGISTRY_FILE.name}")

    known_targets = set(target_names())
    for entry in entries:
        location = (REPO_ROOT / entry.path).resolve()
        if entry.archived:
            continue
        if location.is_dir() and location.parent.resolve() != root.resolve():
            errors.append(f"registry: active skill '{entry.name}' must live in {root.name}/: {entry.path}")
        if location.is_dir():
            declared = frontmatter_name(location / "SKILL.md")
            if declared and declared != entry.name:
                errors.append(f"registry: entry '{entry.name}' does not match SKILL.md name '{declared}'")
        unknown = [t for t in entry.targets if t not in known_targets]
        if unknown:
            errors.append(f"registry: {entry.name} has unknown targets: {', '.join(unknown)}")
        if entry.syncable and not entry.targets:
            errors.append(f"registry: {entry.name} has no targets")
    return errors


def _report(names: list[str], results: dict[str, list[str]], registry_errors: list[str]) -> None:
    for name in names:
        errors = results.get(name)
        if errors:
            print(fail(name))
            for error in errors:
                print(f"  - {error}")
        else:
            print(ok(name))

    if registry_errors:
        print(fail("registry"))
        for error in registry_errors:
            print(f"  - {error}")

    total = len(names)
    print()
    print(f"{total} skills validated")
    if results or registry_errors:
        print(fail("FAIL"))
    else:
        print(ok("PASS"))


def main(argv: list[str] | None = None) -> int:
    configure_output()
    parser = argparse.ArgumentParser(description="Validate skills and the skill registry.")
    parser.add_argument("names", nargs="*", help="只校验指定 skill（默认全部）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    try:
        entries = load_registry()
    except RegistryError as exc:
        if args.json:
            print(json.dumps({"registry_error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(fail(str(exc)))
            print(fail("FAIL"))
        return 1

    discovered = {path.name for path in find_skill_dirs()}
    if args.names:
        unknown = [name for name in args.names if name not in discovered]
        if unknown:
            print(fail(f"unknown skill(s): {', '.join(unknown)}"))
            print(f"available: {', '.join(sorted(discovered)) or '(none)'}")
            return 1
        selected = [name for name in args.names if name in discovered]
    else:
        selected = sorted(discovered)

    results = {name: validate_skill_dir(SKILLS_ROOT / name) for name in selected}
    results = {name: errors for name, errors in results.items() if errors}
    registry_errors = validate_registry(entries) if not args.names else []

    if args.json:
        print(
            json.dumps(
                {
                    "skills_root": str(SKILLS_ROOT),
                    "registry": str(REGISTRY_FILE),
                    "validated": selected,
                    "invalid_skills": results,
                    "registry_errors": registry_errors,
                    "status": "PASS" if not results and not registry_errors else "FAIL",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if results or registry_errors else 0

    if not selected:
        print(skip("no skills found under skills/"))
    _report(selected, results, registry_errors)
    return 1 if results or registry_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
