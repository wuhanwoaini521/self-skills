# 创建第一个 Skill

最小 skill 只需要这些内容：

- `SKILL.md`
- `agents/openai.yaml`

推荐步骤：

1. 先复制 `templates/skill-starter/`
2. 修改 `SKILL.md` 的 `name` 和 `description`
3. 修改 `agents/openai.yaml` 的展示名称和默认提示词
4. 如果需要脚本，再往 `scripts/` 里加
5. 运行 `python tools\validate_skills.py` 检查结构

Skill 目录参考：

- `skills/crawl-docs-to-markdown/`
- `skills/github-trending-report/`
