# 仓库中的 Skill 布局

这个仓库把可直接复用的 skill 放在 `skills/`，而不是根目录。

约定：

- `skills/` 下每个子目录都是一个完整可复用 skill
- 目录名使用小写连字符，例如 `crawl-docs-to-markdown`
- 每个示例至少包含：
  - `SKILL.md`
  - `agents/openai.yaml`
- 常见可选目录：
  - `scripts/`
  - `references/`
  - `assets/`
  - `dist/`

配套目录：

- `templates/skill-starter/`：最小起步模板
- `tools/validate_skills.py`：校验 `skills/` 下结构
- `archive/`：历史生成产物

校验命令：

```powershell
python tools\validate_skills.py
```
