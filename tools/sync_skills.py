#!/usr/bin/env python3
"""把仓库里的 skill 同步到各 Agent 的全局 skills 目录。

仓库是 source of truth，全局目录只是部署目标。

    uv run python tools/sync_skills.py --target codex
    uv run python tools/sync_skills.py --target codex --dry-run
    uv run python tools/sync_skills.py --target codex --skill project-delivery
    uv run python tools/sync_skills.py --all

安全约束：
  * 只管理 registry 里登记且声明了该 target 的 skill
  * 绝不删除 target 目录中不属于本仓库的 skill
  * 默认 copy 模式，不默认 symlink
  * 重复执行是幂等的：内容一致则 SKIP
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 支持 `python tools/<name>.py` 直接运行（把仓库根加入 sys.path）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.console import ARROW, configure_output, fail, ok, skip  # noqa: E402
from tools.registry import REPO_ROOT, RegistryError, SkillEntry, load_registry  # noqa: E402
from tools.sync_targets import TARGETS, TargetResolution, load_config, resolve_target, target_names  # noqa: E402

STATE_FILE = REPO_ROOT / ".sync-state.json"
STATE_VERSION = 1
MODES = ("copy", "symlink")
#: 这些内容永远不进入部署副本。
EXCLUDED_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

ADD = "ADD"
UPDATE = "UPDATE"
SKIP = "SKIP"
PRUNE = "PRUNE"


class SyncError(Exception):
    """给用户看的同步失败原因。"""


@dataclass
class SyncPlanItem:
    action: str
    name: str
    reason: str = ""


@dataclass
class TargetResult:
    name: str
    label: str
    state: str
    detail: str
    path: Path | None = None
    items: list[SyncPlanItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def synced(self) -> bool:
        return self.state in {"ready", "explicit"}

    @property
    def changed(self) -> int:
        return sum(1 for item in self.items if item.action in {ADD, UPDATE, PRUNE})


# --------------------------------------------------------------------------- #
# 指纹与状态
# --------------------------------------------------------------------------- #


def _is_excluded(path: Path) -> bool:
    return path.suffix in EXCLUDED_SUFFIXES or any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def fingerprint(skill_dir: Path) -> str:
    """skill 目录内容指纹，用于判断 ADD / UPDATE / SKIP。"""

    digest = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        if _is_excluded(path.relative_to(skill_dir)):
            continue
        digest.update(path.relative_to(skill_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def load_state(path: Path = STATE_FILE) -> dict:
    if not path.exists():
        return {"version": STATE_VERSION, "targets": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": STATE_VERSION, "targets": {}}
    if not isinstance(data, dict) or not isinstance(data.get("targets"), dict):
        return {"version": STATE_VERSION, "targets": {}}
    return data


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# 计划
# --------------------------------------------------------------------------- #


def select_entries(
    entries: list[SkillEntry],
    target: str,
    names: list[str] | None = None,
    include_archived: bool = False,
) -> list[SkillEntry]:
    selected = [
        entry
        for entry in entries
        if entry.serves(target) and (include_archived or entry.syncable)
    ]
    if names:
        wanted = set(names)
        selected = [entry for entry in selected if entry.name in wanted]
    return sorted(selected, key=lambda entry: entry.name)


def build_plan(
    entries: list[SkillEntry],
    resolution: TargetResolution,
    state: dict,
    mode: str,
    prune: bool = False,
    repo_root: Path | None = None,
) -> list[SyncPlanItem]:
    root = repo_root or REPO_ROOT
    target_state = state.get("targets", {}).get(resolution.name, {})
    recorded = target_state.get("skills", {}) if isinstance(target_state, dict) else {}
    destination_root = resolution.path
    if destination_root is None:  # pragma: no cover - 调用方保证已过滤
        return []

    items: list[SyncPlanItem] = []
    for entry in entries:
        source = (root / entry.path).resolve()
        if not source.is_dir():
            items.append(SyncPlanItem(SKIP, entry.name, f"source missing: {entry.path}"))
            continue
        destination = destination_root / entry.name
        if mode == "symlink":
            current = destination.is_symlink() and destination.resolve() == source.resolve()
            action = SKIP if current else UPDATE
        else:
            if not destination.exists():
                action = ADD
            else:
                action = SKIP if fingerprint(source) == fingerprint(destination) else UPDATE
        items.append(SyncPlanItem(action, entry.name))

    if prune:
        planned = {item.name for item in items}
        for name in sorted(recorded):
            if name not in planned and (destination_root / name).exists():
                items.append(SyncPlanItem(PRUNE, name, "no longer in registry for this target"))
    return items


# --------------------------------------------------------------------------- #
# 执行
# --------------------------------------------------------------------------- #


def deploy(source: Path, destination: Path, mode: str) -> None:
    if mode == "symlink":
        if destination.is_symlink() or destination.exists():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        try:
            destination.symlink_to(source.resolve(), target_is_directory=True)
        except OSError as exc:
            raise SyncError(
                f"cannot create symlink for {destination.name}: {exc}\n"
                "symlinks may require elevated rights on Windows; use --mode copy instead."
            ) from exc
        return

    staging = destination.with_name(destination.name + ".selfskills-staging")
    trash = destination.with_name(destination.name + ".selfskills-trash")
    for path in (staging, trash):
        if path.is_symlink() or path.exists():
            _remove(path)

    ignore = shutil.ignore_patterns(*EXCLUDED_DIR_NAMES, *[s.lstrip(".") for s in EXCLUDED_SUFFIXES])
    shutil.copytree(source, staging, ignore=ignore, symlinks=False)

    had_previous = destination.is_symlink() or destination.exists()
    if had_previous:
        os.replace(destination, trash)
    try:
        os.replace(staging, destination)
    except OSError:
        if had_previous:
            os.replace(trash, destination)
        raise
    if had_previous:
        _remove(trash)


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def sync_target(
    name: str,
    entries: list[SkillEntry],
    override: str | Path | None = None,
    config: dict[str, str] | None = None,
    skill_names: list[str] | None = None,
    mode: str = "copy",
    dry_run: bool = False,
    prune: bool = False,
    include_archived: bool = False,
    state_path: Path | None = None,
    repo_root: Path | None = None,
) -> TargetResult:
    """同步单个 target，返回结果（不打印）。"""

    root = repo_root or REPO_ROOT
    state_path = state_path or STATE_FILE

    target = TARGETS[name]
    resolution = resolve_target(name, override=override, config=config)
    result = TargetResult(
        name=name,
        label=target.label,
        state=resolution.state,
        detail=resolution.detail,
        path=resolution.path,
    )
    if resolution.path is None:
        return result

    selected = select_entries(entries, name, skill_names, include_archived)
    if skill_names:
        known = {entry.name for entry in entries}
        unknown = [value for value in skill_names if value not in known]
        if unknown:
            raise SyncError(
                f"unknown skill(s): {', '.join(unknown)}\navailable: {', '.join(sorted(known))}"
            )

    state = load_state(state_path)
    items = build_plan(selected, resolution, state, mode, prune=prune, repo_root=root)
    result.items = items

    if dry_run:
        return result

    if not resolution.path.is_dir():
        resolution.path.mkdir(parents=True, exist_ok=True)

    target_state = state.setdefault("targets", {}).setdefault(name, {})
    recorded = target_state.setdefault("skills", {})

    for item in items:
        entry = next((e for e in selected if e.name == item.name), None)
        if item.action in {ADD, UPDATE}:
            if entry is None:  # pragma: no cover - 计划已保证
                continue
            source = (root / entry.path).resolve()
            try:
                deploy(source, resolution.path / item.name, mode)
            except SyncError as exc:
                result.errors.append(str(exc))
            except OSError as exc:
                result.errors.append(f"failed to deploy {item.name}: {exc}")
            else:
                recorded[item.name] = {
                    "version": entry.version,
                    "fingerprint": fingerprint(source) if mode == "copy" else "symlink",
                }
        elif item.action == PRUNE:
            _remove(resolution.path / item.name)
            recorded.pop(item.name, None)

    target_state["path"] = str(resolution.path)
    target_state["mode"] = mode
    state["version"] = STATE_VERSION
    save_state(state, state_path)
    return result


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def print_result(result: TargetResult, dry_run: bool) -> None:
    headline = f"{result.label} ({result.name})"
    if result.synced:
        print(f"{ok(headline)} {ARROW} {result.path or result.detail}")
    else:
        print(f"{skip(headline)} {ARROW} not configured")
        for line in result.detail.splitlines():
            print(f"    {line}")
        return

    if not result.items:
        print(f"  {skip('no skills registered for this target')}")
    for item in result.items:
        suffix = f" ({item.reason})" if item.reason else ""
        label = f"{item.action:<7}"
        if dry_run:
            print(f"  {label} {item.name}{suffix}")
        elif item.action in {ADD, UPDATE, PRUNE}:
            print(f"  {ok(label)} {item.name}{suffix}")
        else:
            print(f"  {skip(label)} {item.name}{suffix}")
    for error in result.errors:
        print(f"  {fail('ERROR')} {error}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync skills from this repository to agent global skills directories.",
        epilog="available targets: " + ", ".join(target_names()),
    )
    parser.add_argument("--target", action="append", choices=target_names(), help="sync one target (repeatable)")
    parser.add_argument("--all", action="store_true", help="sync every detectable target")
    parser.add_argument("--skill", action="append", metavar="NAME", help="sync only these skills (repeatable)")
    parser.add_argument("--target-path", help="explicit skills directory; only valid with a single --target")
    parser.add_argument("--mode", choices=MODES, default="copy", help="default: copy")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing anything")
    parser.add_argument("--prune", action="store_true", help="remove previously synced skills that left the registry")
    parser.add_argument("--include-archived", action="store_true", help="also sync archived skills")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_output()
    args = _parse_args(argv)

    if args.target and args.all:
        print(fail("--target and --all are mutually exclusive"))
        return 2
    if not args.target and not args.all:
        print(fail("nothing to do: pass --target <name> or --all"))
        print(f"available targets: {', '.join(target_names())}")
        return 2
    if args.target_path and (args.all or len(args.target) != 1):
        print(fail("--target-path requires exactly one --target"))
        return 2

    try:
        entries = load_registry()
    except RegistryError as exc:
        print(fail(str(exc)))
        return 1

    try:
        config = load_config()
    except ValueError as exc:
        print(fail(str(exc)))
        return 1

    names = args.target or list(TARGETS)
    results: list[TargetResult] = []
    for name in names:
        try:
            results.append(
                sync_target(
                    name,
                    entries,
                    override=args.target_path,
                    config=config,
                    skill_names=args.skill,
                    mode=args.mode,
                    dry_run=args.dry_run,
                    prune=args.prune,
                    include_archived=args.include_archived,
                )
            )
        except SyncError as exc:
            print(fail(str(exc)))
            return 1

    for result in results:
        print_result(result, args.dry_run)

    changed = sum(result.changed for result in results)
    failed = [result for result in results if result.errors]
    print()
    if args.dry_run:
        print(f"dry run: {changed} skill(s) would change, nothing written")
    else:
        print(f"{changed} skill(s) synced")
    if failed:
        print(fail("FAIL"))
        return 1
    print(ok("PASS") if any(r.synced for r in results) else skip("no configured target"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
