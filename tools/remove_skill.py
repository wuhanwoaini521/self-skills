#!/usr/bin/env python3
"""从 registry 与仓库中移除一个 skill。

默认是**可恢复**的归档：目录移到 archive/<name>/，registry 条目标记为 archived。
只有显式 --delete 才会真正删除目录并删掉 registry 条目。

    uv run python tools/remove_skill.py my-skill
    uv run python tools/remove_skill.py my-skill --dry-run
    uv run python tools/remove_skill.py my-skill --delete
"""

from __future__ import annotations

import argparse
import re
import shutil

from pathlib import Path
import sys

# 支持 `python tools/<name>.py` 直接运行（把仓库根加入 sys.path）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.console import configure_output, fail, ok, warn  # noqa: E402
from tools.list_skills import render_index  # noqa: E402
from tools.registry import (  # noqa: E402
    NAME_PATTERN,
    REGISTRY_FILE,
    REPO_ROOT,
    RegistryError,
    load_registry,
    read_text,
)

ARCHIVED_STATUS = "archived"
#: registry 里一个条目的起始行，例如 "  - name: my-skill"。
ENTRY_START = re.compile(r"^(?P<indent>\s*)-\s+name:\s*(?P<name>.+?)\s*$")


class RemoveError(Exception):
    """用户可以直接看懂的失败原因。"""


def entry_block(lines: list[str], name: str) -> tuple[int, int]:
    """定位 registry 文本里 name 对应条目的行区间 [start, end)。找不到抛 RemoveError。"""

    start = base_indent = -1
    for index, line in enumerate(lines):
        match = ENTRY_START.match(line)
        if match and match.group("name").strip("'\"") == name:
            start, base_indent = index, len(match.group("indent"))
            break
    if start < 0:
        raise RemoveError(f"skill is not registered: {name}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= base_indent:
            end = index
            break
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return start, end


def _finish(lines: list[str], start: int) -> str:
    """删除区间后收拾空行，保持文件与 new_skill.py 生成的形态一致。"""

    if 0 < start < len(lines) and not lines[start - 1].strip() and not lines[start].strip():
        del lines[start]
    return "\n".join(lines).rstrip("\n") + "\n"


def remove_registry_entry(text: str, name: str) -> str:
    """删掉 name 的 registry 条目，保留文件其余内容与注释。"""

    lines = text.splitlines()
    start, end = entry_block(lines, name)
    del lines[start:end]
    return _finish(lines, start)


def set_entry_fields(text: str, name: str, **fields: str) -> str:
    """就地修改 name 条目里的字段；字段不存在时追加到条目末尾。"""

    lines = text.splitlines()
    start, end = entry_block(lines, name)
    for key, value in fields.items():
        pattern = re.compile(rf"^(?P<indent>\s*){re.escape(key)}\s*:\s*")
        for index in range(start, end):
            match = pattern.match(lines[index])
            if match:
                lines[index] = f"{match.group('indent')}{key}: {value}"
                break
        else:
            lines.insert(end, f"    {key}: {value}")
            end += 1
    return "\n".join(lines).rstrip("\n") + "\n"


def check_consistent(name: str, entries, repo_root: Path) -> tuple[Path, Path]:
    """确认 registry 条目与磁盘目录一致，返回 (条目 path, 绝对目录)。不一致就报错。"""

    entry = next((e for e in entries if e.name == name), None)
    if entry is None:
        raise RemoveError(f"skill is not registered: {name}")

    location = (repo_root / entry.path).resolve()
    expected = (repo_root / "skills" / name).resolve()
    if not location.is_dir():
        raise RemoveError(
            f"Skill '{name}' exists in registry but directory is missing.\n"
            f"  registry says: {entry.path}\n"
            f"  expected: {location}\n"
            "No changes were made."
        )
    if location != expected:
        raise RemoveError(
            f"Skill '{name}' registry path does not match its location under skills/.\n"
            f"  registry says: {entry.path}\n"
            f"  expected: {expected.relative_to(repo_root).as_posix()}\n"
            "No changes were made."
        )
    return location, expected


def plan_remove(
    name: str,
    delete: bool = False,
    dry_run: bool = False,
    registry_path: Path | None = None,
    repo_root: Path | None = None,
    index_path: Path | None = None,
    archive_root: Path | None = None,
) -> list[str]:
    """执行移除，返回人类可读的计划行。dry_run 时不写任何文件。"""

    registry_path = registry_path or REGISTRY_FILE
    repo_root = repo_root or REPO_ROOT
    index_path = index_path or (repo_root / "skills-index.md")
    archive_root = archive_root or (repo_root / "archive")

    if not NAME_PATTERN.fullmatch(name):
        raise RemoveError(
            f"invalid skill name: {name!r}\n"
            "expected lowercase kebab-case, e.g. my-skill"
        )

    try:
        entries = load_registry(registry_path)
    except RegistryError as exc:
        raise RemoveError(str(exc)) from exc

    location, _ = check_consistent(name, entries, repo_root)

    plan: list[str] = []
    if delete:
        destination = None
        plan.append(f"DELETE   {location.relative_to(repo_root).as_posix()}")
        plan.append("REMOVE   registry entry")
    else:
        destination = archive_root / name
        if destination.exists():
            raise RemoveError(
                f"Archive destination already exists.\n"
                f"  {destination}\n"
                "Nothing was overwritten. Move or remove it first, or use --delete."
            )
        plan.append(
            f"ARCHIVE  {location.relative_to(repo_root).as_posix()} -> "
            f"{destination.relative_to(repo_root).as_posix()}"
        )
        plan.append("UPDATE   registry entry (status: archived, path: archive/...)")

    plan.append(f"UPDATE   {registry_path.relative_to(repo_root).as_posix()}")
    plan.append(f"UPDATE   {index_path.relative_to(repo_root).as_posix()}")

    if dry_run:
        return plan

    text = read_text(registry_path)
    if delete:
        updated = remove_registry_entry(text, name)
    else:
        updated = set_entry_fields(
            text, name, status=ARCHIVED_STATUS, path=destination.relative_to(repo_root).as_posix()
        )
    registry_path.write_text(updated, encoding="utf-8", newline="\n")

    if delete:
        shutil.rmtree(location)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(location), str(destination))

    entries = load_registry(registry_path)
    index_path.write_text(render_index(entries), encoding="utf-8", newline="\n")
    return plan


def main(argv: list[str] | None = None) -> int:
    configure_output()
    parser = argparse.ArgumentParser(
        description="Remove a skill from the registry. Archives by default.",
        epilog="without --delete the skill is archived and stays recoverable",
    )
    parser.add_argument("name", help="skill name, lowercase kebab-case")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="permanently delete the directory and the registry entry (irreversible)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing anything")
    args = parser.parse_args(argv)

    try:
        plan = plan_remove(args.name, delete=args.delete, dry_run=args.dry_run)
    except RemoveError as exc:
        print(fail(str(exc)))
        return 1

    for line in plan:
        print(f"  {line}")

    if args.dry_run:
        print(warn("dry run: nothing was written"))
    elif args.delete:
        print(ok(f"deleted {args.name}"))
    else:
        print(ok(f"archived {args.name} (restore by moving it back and setting status back)"))
    print("\nnext: uv run python tools/validate_skills.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
