# Skills Layout

本仓库内的自定义技能统一放在 `Skills/` 目录下。

约定：

- `Skills/` 下每个子目录都是一个独立 skill
- skill 目录名使用小写连字符命名，例如 `crawl-docs-to-markdown`
- 每个 skill 至少包含：
  - `SKILL.md`
  - `agents/openai.yaml`
- 可选目录：
  - `scripts/`
  - `references/`
  - `assets/`
  - `dist/`

约束：

- 不在 `Skills/` 根目录混放单个 skill 文件
- `dist/` 只放发布产物，例如 zip 和 inline JSON
- 调试产物不要留在 skill 根目录

校验：

```powershell
python Skills\scripts\validate_skills.py
```
