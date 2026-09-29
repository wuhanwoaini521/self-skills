#!/usr/bin/env python3
"""从 templates/skill-starter/ 创建一个新 skill，并注册到 registry/skills.yaml。

    uv run python tools/new_skill.py project-delivery
    uv run python tools/new_skill.py project-delivery --dry-run

规则：
  * 名称必须是小写 kebab-case
  * 不允许覆盖已存在的目录或已注册的同名 skill
  * 默认 version=0.1.0、status=experimental
  * 默认写入 registry（--no-registry 可跳过）
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

import sys

# 支持 `python tools/<name>.py` 直接运行（把仓库根加入 sys.path）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.console import configure_output, fail, ok, warn  # noqa: E402
from tools.registry import (
    MAX_NAME_LENGTH,
    NAME_PATTERN,
    REGISTRY_FILE,
    REPO_ROOT,
    SKILLS_ROOT,
    STARTER_TEMPLATE,
    VALID_STATUSES,
    RegistryError,
    SkillEntry,
    load_registry,
    read_text,
)
from tools.sync_targets import target_names  # noqa: E402

DEFAULT_VERSION = "0.1.0"
DEFAULT_STATUS = "experimental"
DEFAULT_TARGETS = ("codex",)
PLACEHOLDER_FILES = (".gitkeep",)


class CreateError(Exception):
    """用户可以直接看懂的失败原因。"""


def title_of(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split("-"))


def render_template(template_dir: Path, name: str, description: str) -> list[tuple[Path, str]]:
    replacements = {
        "name": name,
        "title": title_of(name),
        "description": description,
        "short_description": description,
    }
    files: list[tuple[Path, str]] = []
    for source in sorted(template_dir.rglob("*")):
        if not source.is_file() or source.name in PLACEHOLDER_FILES:
            continue
        relative = source.relative_to(template_dir)
        content = read_text(source)
        for key, value in replacements.items():
            content = content.replace("{{" + key + "}}", value)
        if "{{" in content:
            leftover = sorted(set(part.split("}}")[0] for part in content.split("{{")[1:]))
            raise CreateError(f"template {source} has unresolved placeholders: {', '.join(leftover)}")
        files.append((relative, content))
    return files


def check_name(name: str, entries: list[SkillEntry], skills_root: Path = SKILLS_ROOT) -> None:
    if not NAME_PATTERN.fullmatch(name):
        raise CreateError(
            f"invalid skill name: {name!r}\n"
            "expected lowercase kebab-case, e.g. project-delivery"
        )
    if len(name) > MAX_NAME_LENGTH:
        raise CreateError(f"invalid skill name: too long: {len(name)} > {MAX_NAME_LENGTH}")
    if (skills_root / name).exists():
        raise CreateError(f"skill directory already exists: {skills_root / name}")
    if any(entry.name == name for entry in entries):
        raise CreateError(f"skill already registered in registry: {name}")


def registry_block(entry: SkillEntry) -> str:
    data = {
        "name": entry.name,
        "path": entry.path,
        "version": entry.version,
        "status": entry.status,
        "targets": list(entry.targets),
        "description": entry.description,
    }
    dumped = yaml.safe_dump([data], sort_keys=False, allow_unicode=True, default_flow_style=False)
    return "".join("  " + line if line.strip() else line for line in dumped.splitlines(keepends=True))


def append_registry_entry(entry: SkillEntry, registry_path: Path = REGISTRY_FILE) -> str:
    """把 entry 追加到 registry 文本末尾，保留已有内容与注释。

    追加后先在内存里重新解析确认合法，再落盘。
    """

    original = read_text(registry_path) if registry_path.exists() else "version: 1\n\nskills:\n"
    if not original.endswith("\n"):
        original += "\n"
    if "skills:" not in original:
        original += "\nskills:\n"
    updated = original + registry_block(entry)
    try:
        parsed = yaml.safe_load(updated)
    except yaml.YAMLError as exc:  # pragma: no cover - 防御性
        raise CreateError(f"refusing to write a broken registry: {exc}") from exc
    if not isinstance(parsed, dict) or not any(
        isinstance(item, dict) and item.get("name") == entry.name for item in parsed.get("skills", [])
    ):
        raise CreateError(f"refusing to write a broken registry: entry {entry.name} did not round-trip")
    return updated


def _registry_path_for(skills_root: Path, name: str, repo_root: Path) -> str:
    """registry 里记录相对仓库根的路径；仓库外的 skills_root 退化为绝对路径。"""

    resolved = skills_root.resolve()
    try:
        return f"{resolved.relative_to(repo_root.resolve()).as_posix()}/{name}"
    except ValueError:
        return f"{resolved.as_posix()}/{name}"


def create_skill(
    name: str,
    description: str | None = None,
    version: str = DEFAULT_VERSION,
    status: str = DEFAULT_STATUS,
    targets: list[str] | None = None,
    write_registry: bool = True,
    dry_run: bool = False,
    registry_path: Path | None = None,
    skills_root: Path | None = None,
    template_dir: Path | None = None,
    repo_root: Path | None = None,
) -> SkillEntry:
    """创建 skill 骨架。dry_run 时不写任何文件。"""

    registry_path = registry_path or REGISTRY_FILE
    skills_root = skills_root or SKILLS_ROOT
    template_dir = template_dir or STARTER_TEMPLATE
    repo_root = repo_root or REPO_ROOT

    if status not in VALID_STATUSES:
        raise CreateError(
            f"invalid status: {status!r}\nallowed:\n" + "".join(f"{value}\n" for value in VALID_STATUSES)
        )
    chosen_targets = tuple(targets or DEFAULT_TARGETS)
    unknown = [t for t in chosen_targets if t not in target_names()]
    if unknown:
        raise CreateError(
            f"unknown target(s): {', '.join(unknown)}\navailable targets:\n"
            + "".join(f"- {value}\n" for value in target_names())
        )
    if not template_dir.is_dir():
        raise CreateError(f"template not found: {template_dir}")

    skill_dir = skills_root / name
    if skill_dir.exists():
        raise CreateError(
            f"skill directory already exists: {skill_dir}\n"
            "choose another name, or remove the directory before retrying"
        )
    entry = SkillEntry(
        name=name,
        path=_registry_path_for(skills_root, name, repo_root),
        version=version,
        status=status,
        targets=chosen_targets,
        description=description or f"TODO: describe what {name} does and when to use it.",
    )

    try:
        entries = load_registry(registry_path)
    except RegistryError as exc:
        raise CreateError(str(exc)) from exc
    check_name(name, entries, skills_root)

    rendered = render_template(template_dir, name, entry.description)
    directories = sorted({path.parent for path, _ in rendered} | {skill_dir / "references", skill_dir / "scripts"})

    if dry_run:
        return entry

    skill_dir.mkdir(parents=True)
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    for relative, content in rendered:
        target = skill_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    for keep in (skill_dir / "references" / ".gitkeep", skill_dir / "scripts" / ".gitkeep"):
        if not any(path.name == keep.name for path in keep.parent.iterdir()):
            keep.write_text("", encoding="utf-8")

    if write_registry:
        updated = append_registry_entry(entry, registry_path)
        registry_path.write_text(updated, encoding="utf-8", newline="\n")
    return entry


def main(argv: list[str] | None = None) -> int:
    configure_output()
    parser = argparse.ArgumentParser(description="Create a new skill from templates/skill-starter.")
    parser.add_argument("name", help="skill name, lowercase kebab-case")
    parser.add_argument("--description", help="one-line description used in SKILL.md frontmatter")
    parser.add_argument("--version", default=DEFAULT_VERSION, help=f"default: {DEFAULT_VERSION}")
    parser.add_argument(
        "--status",
        default=DEFAULT_STATUS,
        choices=VALID_STATUSES,
        help=f"default: {DEFAULT_STATUS}",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=list(DEFAULT_TARGETS),
        metavar="NAME",
        help="agents to sync to (default: codex)",
    )
    parser.add_argument("--no-registry", action="store_true", help="do not add a registry entry")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing files")
    args = parser.parse_args(argv)

    try:
        entry = create_skill(
            name=args.name,
            description=args.description,
            version=args.version,
            status=args.status,
            targets=list(args.targets),
            write_registry=not args.no_registry,
            dry_run=args.dry_run,
        )
    except CreateError as exc:
        print(fail(str(exc)))
        return 1

    prefix = "would create" if args.dry_run else "created"
    print(f"{ok(prefix)} {entry.path}")
    print(f"  version: {entry.version}")
    print(f"  status:  {entry.status}")
    print(f"  targets: {', '.join(entry.targets)}")
    if args.dry_run:
        print(warn("dry run: nothing was written"))
    elif not args.no_registry:
        print(ok(f"registered in {REGISTRY_FILE.relative_to(REPO_ROOT).as_posix()}"))
    print(f"\nnext: uv run python tools/validate_skills.py {entry.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
