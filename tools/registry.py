"""Skill Registry：`registry/skills.yaml` 是本仓库的机器事实源。

所有工具（validate / new / sync / list / doctor）都从这里读取 skill 清单，
不允许各自去扫目录再猜元数据。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from tools.sync_targets import target_names

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = REPO_ROOT / "registry" / "skills.yaml"
SKILLS_ROOT = REPO_ROOT / "skills"
TEMPLATES_ROOT = REPO_ROOT / "templates"
STARTER_TEMPLATE = TEMPLATES_ROOT / "skill-starter"

VALID_STATUSES = ("experimental", "beta", "stable", "deprecated", "archived")
#: archived 的 skill 默认不同步；deprecated 仍然同步（只是不再推荐新用）。
SYNCABLE_STATUSES = ("experimental", "beta", "stable", "deprecated")
MAX_NAME_LENGTH = 64

NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+\Z")

REQUIRED_FIELDS = ("name", "path", "version", "status", "targets", "description")
OPTIONAL_FIELDS = ("notes",)


class RegistryError(Exception):
    """Registry 结构非法。消息本身已经是给用户看的完整说明。"""


@dataclass(frozen=True)
class SkillEntry:
    """一个 skill 的注册信息。"""

    name: str
    path: str
    version: str
    status: str
    targets: tuple[str, ...]
    description: str
    notes: str = ""

    @property
    def skill_dir(self) -> Path:
        return (REPO_ROOT / self.path).resolve()

    @property
    def archived(self) -> bool:
        return self.status == "archived"

    @property
    def syncable(self) -> bool:
        return self.status in SYNCABLE_STATUSES

    def serves(self, target: str) -> bool:
        return target in self.targets


def read_text(path: Path) -> str:
    """读取文本，兼容仓库里历史上出现过的 GBK 编码文件。"""

    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp936"):
        try:
            return path.read_text(encoding=encoding, errors="strict")
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error if last_error else OSError(f"cannot read {path}")


def load_registry(path: Path | None = None) -> list[SkillEntry]:
    """读取并校验 registry，返回 SkillEntry 列表。"""

    registry_path = path or REGISTRY_FILE
    if not registry_path.exists():
        raise RegistryError(
            f"registry not found: {registry_path}\nrun 'uv run python tools/new_skill.py --help' or restore registry/skills.yaml"
        )
    try:
        data = yaml.safe_load(read_text(registry_path))
    except yaml.YAMLError as exc:
        raise RegistryError(f"invalid registry:\n{registry_path}\n{exc}") from exc
    return parse_registry(data)


def parse_registry(data: object) -> list[SkillEntry]:
    """把已解析的 YAML 结构转成 SkillEntry，结构非法时抛 RegistryError。"""

    problems: list[str] = []

    if not isinstance(data, dict):
        raise RegistryError(
            "invalid registry:\n"
            "root must be a mapping with 'version' and 'skills'\n"
            f"got: {type(data).__name__}"
        )

    if data.get("version") != 1:
        problems.append("version:\n  expected 1\n  got: " + repr(data.get("version")))

    raw_skills = data.get("skills")
    if raw_skills is None and "skills" in data:
        raw_skills = []  # `skills:` 后面还没有条目是合法的新仓库状态
    if not isinstance(raw_skills, list):
        problems.append("skills:\n  expected a list\n  got: " + type(raw_skills).__name__)
        raise RegistryError("invalid registry:\n\n" + "\n".join(problems))

    entries: list[SkillEntry] = []
    for index, item in enumerate(raw_skills):
        problems.extend(f"skills[{index}].{p}" for p in _entry_problems(item, index))
        if isinstance(item, dict):
            entries.append(_build_entry(item))

    _check_duplicates(entries, problems)

    if problems:
        raise RegistryError("invalid registry:\n\n" + "\n".join(problems))
    return entries


def _entry_problems(item: object, index: int) -> list[str]:
    if not isinstance(item, dict):
        return [f"skills[{index}]:\n  expected a mapping\n  got: {type(item).__name__}"]

    problems: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in item:
            problems.append(f"skills[{index}].{field}:\n  missing required field")

    unknown = sorted(set(item) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown:
        problems.append(f"skills[{index}]:\n  unknown fields: {', '.join(unknown)}")

    name = item.get("name")
    if isinstance(name, str) and name:
        if not NAME_PATTERN.fullmatch(name):
            problems.append(f"skills[{index}].name:\n  '{name}' is not lowercase kebab-case")
        elif len(name) > MAX_NAME_LENGTH:
            problems.append(f"skills[{index}].name:\n  too long: {len(name)} > {MAX_NAME_LENGTH}")

    version = item.get("version")
    if version is not None and not (isinstance(version, str) and VERSION_PATTERN.fullmatch(version)):
        problems.append(f"skills[{index}].version:\n  '{version}' is not MAJOR.MINOR.PATCH")

    status = item.get("status")
    if status is not None and status not in VALID_STATUSES:
        problems.append(
            f"skills[{index}].status:\n  '{status}' is not supported.\n\nallowed:\n"
            + "".join(f"{value}\n" for value in VALID_STATUSES)
        )

    targets = item.get("targets")
    if targets is not None:
        if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
            problems.append(f"skills[{index}].targets:\n  expected a list of target names")
        else:
            known = target_names()
            for target in targets:
                if target not in known:
                    problems.append(
                        f"skills[{index}].targets:\n  unknown target '{target}'\n"
                        f"available: {', '.join(known)}"
                    )

    description = item.get("description")
    if description is not None and not (isinstance(description, str) and description.strip()):
        problems.append(f"skills[{index}].description:\n  must be a non-empty string")

    return problems


def _build_entry(item: dict) -> SkillEntry:
    return SkillEntry(
        name=str(item.get("name", "")),
        path=str(item.get("path", "")),
        version=str(item.get("version", "")),
        status=str(item.get("status", "")),
        targets=tuple(item.get("targets") or ()),
        description=str(item.get("description", "")),
        notes=str(item.get("notes", "")),
    )


def _check_duplicates(entries: list[SkillEntry], problems: list[str]) -> None:
    for field, label in (("name", "name"), ("path", "path")):
        seen: dict[str, int] = {}
        for index, entry in enumerate(entries):
            value = getattr(entry, field)
            if not value:
                continue
            if value in seen:
                problems.append(
                    f"skills[{index}].{label}:\n  duplicate {label} '{value}' (already used by skills[{seen[value]}])"
                )
            else:
                seen[value] = index


def entry_map(entries: list[SkillEntry]) -> dict[str, SkillEntry]:
    return {entry.name: entry for entry in entries}


def discover_skill_dirs(root: Path | None = None) -> list[Path]:
    """列出 skills/ 下所有含 SKILL.md 的目录。"""

    skills_root = root or SKILLS_ROOT
    if not skills_root.is_dir():
        return []
    return sorted(
        path
        for path in skills_root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and (path / "SKILL.md").exists()
    )
