"""Agent 同步目标（部署目标）定义。

这里只描述 *部署目标*：self-skills 仓库是 source of truth，
Codex / Claude Code / OpenCode / Pi 的全局 skills 目录只是副本落点。

增加新 Agent 时，只需要在这里追加一个 `SyncTarget`，
sync / doctor 两个工具会自动识别，不需要改动其它逻辑。
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "self-skills" / "sync.json"


@dataclass(frozen=True)
class SyncTarget:
    """一个 Agent 的全局 skills 目录。"""

    name: str
    label: str
    candidates: tuple[str, ...]
    verified: bool
    notes: str

    def expected_paths(self) -> list[Path]:
        return [Path.home() / candidate for candidate in self.candidates]

    def describe(self) -> str:
        expected = ", ".join(str(path) for path in self.expected_paths())
        state = "verified" if self.verified else "NOT VERIFIED"
        return f"{self.label} ({self.name}) [{state}]\n  expected: {expected}\n  notes: {self.notes}"


# `verified=True` 表示目录约定已在本机实测确认；`verified=False` 的目标
# 必须显式配置（配置文件或 --target-path）才会写入，sync 不会擅自创建。
TARGETS: dict[str, SyncTarget] = {
    "codex": SyncTarget(
        name="codex",
        label="Codex CLI",
        candidates=(".codex/skills",),
        verified=True,
        notes="Codex 全局 skills 目录，实测存在。",
    ),
    "claude": SyncTarget(
        name="claude",
        label="Claude Code",
        candidates=(".claude/skills",),
        verified=True,
        notes="Claude Code 全局 skills 目录，实测存在。",
    ),
    "opencode": SyncTarget(
        name="opencode",
        label="OpenCode",
        candidates=(".config/opencode/skills", ".config/opencode/skill"),
        verified=False,
        notes="目录约定未在本机确认；请用 --target-path 或配置文件指定。",
    ),
    "pi": SyncTarget(
        name="pi",
        label="Pi",
        candidates=(".pi/skills",),
        verified=False,
        notes="目录约定未在本机确认；请用 --target-path 或配置文件指定。",
    ),
}


def target_names() -> list[str]:
    return list(TARGETS)


def get_target(name: str) -> SyncTarget:
    try:
        return TARGETS[name]
    except KeyError:
        raise KeyError(name) from None


def load_config(path: Path | None = None) -> dict[str, str]:
    """读取用户级路径覆盖配置 `~/.config/self-skills/sync.json`。

    格式::

        {"codex": "D:/tools/codex-skills"}
    """

    config_path = path or CONFIG_PATH
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid sync config {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid sync config {config_path}: expected a JSON object")

    resolved: dict[str, str] = {}
    for name, value in data.items():
        if name not in TARGETS:
            raise ValueError(
                f"invalid sync config {config_path}: unknown target {name!r}\n"
                f"available targets: {', '.join(target_names())}"
            )
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"invalid sync config {config_path}: target {name!r} needs a non-empty path")
        resolved[name] = value
    return resolved


@dataclass(frozen=True)
class TargetResolution:
    """某个 target 的解析结果。"""

    name: str
    path: Path | None
    state: str  # ready | explicit | missing | unverified
    detail: str

    @property
    def ok(self) -> bool:
        return self.path is not None


def resolve_target(
    name: str,
    override: str | Path | None = None,
    config: dict[str, str] | None = None,
) -> TargetResolution:
    """解析某个 target 的 skills 目录，绝不静默创建目录。"""

    if name not in TARGETS:
        raise KeyError(name)
    target = TARGETS[name]

    if override is not None:
        path = Path(override).expanduser()
        return TargetResolution(
            name=name,
            path=path,
            state="explicit",
            detail=f"using --target-path {path}",
        )

    configured = (config or {}).get(name)
    if configured:
        path = Path(configured).expanduser()
        state = "explicit" if path.is_dir() else "missing"
        detail = f"using configured path {path}"
        if not path.is_dir():
            detail += " (not created yet)"
        return TargetResolution(name=name, path=path, state=state, detail=detail)

    for candidate in target.expected_paths():
        if candidate.is_dir():
            return TargetResolution(
                name=name,
                path=candidate,
                state="ready",
                detail=f"detected {candidate}",
            )

    expected = ", ".join(str(path) for path in target.expected_paths())
    if target.verified:
        return TargetResolution(
            name=name,
            path=None,
            state="missing",
            detail=(
                f"{target.label} global skills directory not found.\n"
                f"detected platform: {platform.system()}\n"
                f"expected: {expected}\n"
                "use --target-path to override, or create the directory yourself."
            ),
        )
    return TargetResolution(
        name=name,
        path=None,
        state="unverified",
        detail=(
            f"{target.label} skills directory is not verified for this registry.\n"
            f"guessed: {expected}\n"
            "use --target-path (or ~/.config/self-skills/sync.json) to set the real path."
        ),
    )
