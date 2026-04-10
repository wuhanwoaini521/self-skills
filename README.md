# self-skills

这是一个纯文档记录仓库，用来整理“如何创建 Skill”的学习过程、可直接复用的 skill、以及模板。

目录入口：

- `docs/`：学习笔记、概念说明、示例讲解
- `skills/`：可直接复制出去使用的完整 skill
- `skills-index.md`：快速查看有哪些 skill、复制哪个目录、怎么运行
- `templates/`：新建 skill 时可直接复制的起步模板
- `tools/`：辅助脚本，例如校验与本地生成
- `archive/`：历史产物与生成结果

常用命令：

```powershell
python -m pytest
python tools\validate_skills.py
python skills\github-trending-report\scripts\generate_report.py --date 2026-04-10
```

建议先从 [docs/index.md](docs/index.md) 开始；如果你是来直接找可用 skill，先看 [skills-index.md](skills-index.md)。
