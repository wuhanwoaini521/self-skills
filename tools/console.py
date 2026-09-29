"""CLI 输出约定。

所有工具共用同一套符号与颜色，保证 plain terminal / CI / Windows Terminal 表现一致。
"""

from __future__ import annotations

import os
import sys

OK = "✓"
FAIL = "✗"
SKIP = "○"
WARN = "!"
ARROW = "→"


def configure_output() -> None:
    """尽量让 stdout 使用 UTF-8，避免 Windows 控制台打印符号时抛 UnicodeEncodeError。"""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):  # pragma: no cover - 平台相关
            pass


def use_color(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


def paint(text: str, code: str, stream=None) -> str:
    if not use_color(stream):
        return text
    return f"\033[{code}m{text}\033[0m"


def ok(text: str) -> str:
    return paint(f"{OK} {text}", "32")


def fail(text: str) -> str:
    return paint(f"{FAIL} {text}", "31")


def skip(text: str) -> str:
    return paint(f"{SKIP} {text}", "90")


def warn(text: str) -> str:
    return paint(f"{WARN} {text}", "33")


def bold(text: str) -> str:
    return paint(text, "1")
