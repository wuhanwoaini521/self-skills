#!/usr/bin/env python3
"""环境自检：仓库结构、registry、skill 校验、同步目标可用性。

    uv run python tools/doctor.py
"""


import platform
import sys

from pathlib import Path

# 支持 `python tools/<name>.py` 直接运行（把仓库根加入 sys.path）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.console import bold, configure_output, fail, ok, warn  # noqa: E402
from tools.list_skills import render_index, INDEX_FILE  # noqa: E402
from tools.registry import (
    REGISTRY_FILE,
    REPO_ROOT,
    SKILLS_ROOT,
    STARTER_TEMPLATE,
    TEMPLATES_ROOT,
    RegistryError,
    discover_skill_dirs,
    load_registry,
)
from tools.sync_targets import TARGETS, load_config, resolve_target  # noqa: E402

TOOL_FILES = (
    "new_skill.py",
    "validate_skills.py",
    "sync_skills.py",
    "list_skills.py",
    "doctor.py",
    "remove_skill.py",
)


class Report:
    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def check(self, condition: bool, message: str, warn_only: bool = False) -> bool:
        if condition:
            print(f"  {ok(message)}")
        elif warn_only:
            self.warnings += 1
            print(f"  {warn(message)}")
        else:
            self.failures += 1
            print(f"  {fail(message)}")
        return condition


def run() -> Report:
    configure_output()
    report = Report()
    print(bold("Self Skills Doctor"))
    print(f"  repo: {REPO_ROOT}")
    print(f"  platform: {platform.system()} {platform.machine()} / python {sys.version.split()[0]}")

    print(bold("\nRepository"))
    report.check(REGISTRY_FILE.is_file(), f"registry: {REGISTRY_FILE.relative_to(REPO_ROOT).as_posix()}")
    report.check(SKILLS_ROOT.is_dir(), "skills directory")
    report.check(TEMPLATES_ROOT.is_dir(), "templates directory")
    report.check(
        (STARTER_TEMPLATE / "SKILL.md").is_file() and (STARTER_TEMPLATE / "agents" / "openai.yaml").is_file(),
        "skill-starter template",
    )
    missing_tools = [name for name in TOOL_FILES if not (REPO_ROOT / "tools" / name).is_file()]
    report.check(not missing_tools, "tools" + (f" (missing: {', '.join(missing_tools)})" if missing_tools else ""))

    print(bold("\nRegistry"))
    entries = []
    try:
        entries = load_registry()
        report.check(True, f"{len(entries)} skill(s) registered")
    except RegistryError as exc:
        report.check(False, str(exc).splitlines()[0])

    from tools.validate_skills import validate_registry, validate_skill_dir

    registry_errors = validate_registry(entries) if entries else ["registry could not be loaded"]
    report.check(not registry_errors, "registry matches skills/ layout")
    for error in registry_errors:
        print(f"      - {error}")

    print(bold("\nSkills"))
    discovered = discover_skill_dirs()
    for skill_dir in discovered:
        errors = validate_skill_dir(skill_dir)
        report.check(not errors, skill_dir.name)
        for error in errors:
            print(f"      - {error}")
    if not discovered:
        report.check(False, "no skills found under skills/")

    print(bold("\nTargets"))
    try:
        config = load_config()
    except ValueError as exc:
        config = {}
        report.check(False, str(exc).splitlines()[0])

    for name, target in TARGETS.items():
        resolution = resolve_target(name, config=config)
        if resolution.state in {"ready", "explicit"}:
            writable = resolution.path.is_dir()
            report.check(writable, f"{target.label}: {resolution.path}")
        else:
            report.check(False, f"{target.label}: {resolution.detail.splitlines()[0]}", warn_only=True)

    print(bold("\nIndex"))
    if entries:
        current = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""
        up_to_date = current == render_index(entries)
        report.check(
            up_to_date,
            "skills-index.md is up to date"
            if up_to_date
            else "skills-index.md is out of date (run: uv run python tools/list_skills.py --write-index)",
            warn_only=True,
        )

    print()
    if report.failures:
        print(fail(f"Result: FAIL ({report.failures} problem(s), {report.warnings} warning(s))"))
    else:
        print(ok(f"Result: PASS ({report.warnings} warning(s))"))
    return report


def main() -> int:
    return 1 if run().failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
