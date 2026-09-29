#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import zipfile
from pathlib import Path


def skill_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md is missing valid YAML frontmatter")
    frontmatter: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter


def should_skip(path: Path, root: Path, out_dir: Path) -> bool:
    relative = path.relative_to(root)
    parts = set(relative.parts)
    if "__pycache__" in parts:
        return True
    if path.suffix in {".pyc", ".pyo", ".zip"}:
        return True
    if relative.parts and relative.parts[0] == out_dir.name:
        return True
    return False


def build_zip(skill_dir: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_dir():
                continue
            if should_skip(path, skill_dir, out_dir):
                continue
            arcname = Path(skill_dir.name) / path.relative_to(skill_dir)
            zf.write(path, arcname.as_posix())
    return zip_path


def write_inline_json(zip_path: Path, skill_name: str, description: str) -> Path:
    payload = {
        "type": "inline",
        "name": skill_name,
        "description": description,
        "source": {
            "type": "base64",
            "media_type": "application/zip",
            "data": base64.b64encode(zip_path.read_bytes()).decode("ascii"),
        },
    }
    output_path = zip_path.with_suffix(".inline.json")
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package a skill folder for OpenAI Skills zip upload or inline source usage.")
    parser.add_argument("--skill-dir", default=str(skill_root_from_script()), help="Path to the skill root directory.")
    parser.add_argument("--out-dir", help="Directory for generated zip and inline JSON. Defaults to <skill-dir>/dist.")
    parser.add_argument("--inline-json", action="store_true", help="Also write a base64 inline-skill JSON payload next to the zip.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = Path(args.skill_dir).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else skill_dir / "dist"
    frontmatter = parse_frontmatter(skill_dir / "SKILL.md")
    zip_path = build_zip(skill_dir, out_dir)
    result: dict[str, str] = {"zip_path": str(zip_path)}
    if args.inline_json:
        inline_path = write_inline_json(
            zip_path=zip_path,
            skill_name=frontmatter["name"],
            description=frontmatter["description"],
        )
        result["inline_json_path"] = str(inline_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

