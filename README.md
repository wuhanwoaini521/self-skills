# self-skills

**Personal Skills Registry** —— 我个人 Skill 的唯一事实源（source of truth）。

这里存放 Skill 的源码、注册表、校验/测试/同步工具。所有个人 Skill 的完整流程是：

```text
Create → Register → Validate → Test → Commit → Push → Sync → Use globally
```

目录约定：

- `skills/<name>/`：Skill 源码，**唯一的 canonical 副本**
- `registry/skills.yaml`：机器可读的注册表（机器事实源）
- `templates/skill-starter/`：新 Skill 的起步模板
- `tools/`：创建、校验、列出、同步、自检脚本
- `docs/`：架构、编写规范、同步指南、兼容性、生命周期
- `tests/`：工具与 Skill 的测试
- `skills-index.md`：由注册表生成的**人类可读视图**（不要手改）
- `archive/`：历史产物，不参与校验与同步

## Quick Start

```bash
uv sync
```

## 常用命令

```bash
# 看看注册了哪些 skill
uv run python tools/list_skills.py

# 校验全部 skill（新增/修改后必跑）
uv run python tools/validate_skills.py

# 创建一个新 skill（自动注册，默认 status=experimental, version=0.1.0）
uv run python tools/new_skill.py my-skill

# 同步到 Codex
uv run python tools/sync_skills.py --target codex

# 同步到所有能识别的 Agent
uv run python tools/sync_skills.py --all

# 全流程自检
uv run python tools/doctor.py
```

改文件前先看状态，改完跑一次校验：

```bash
uv run python tools/sync_skills.py --target codex --dry-run
```

## 工作流

1. **创建** —— `uv run python tools/new_skill.py <name>`
2. **编写** —— 填写 `SKILL.md` 的 description 与正文，脚本放 `scripts/`，参考文档放 `references/`
3. **校验** —— `uv run python tools/validate_skills.py`
4. **测试** —— `uv run pytest`
5. **提交推送** —— 状态在 `registry/skills.yaml` 里，成熟度见 [docs/lifecycle.md](docs/lifecycle.md)
6. **同步** —— `uv run python tools/sync_skills.py --target codex`
7. **自检** —— `uv run python tools/doctor.py`

## Source of Truth

```text
GitHub self-skills
        ↓
   Local clone
        ↓
    skills/*          ← canonical source
        ↓
    sync tool
        ↓
Agent global skills   ← 只是部署目标
```

Codex / Claude Code / OpenCode / Pi 的全局 skills 目录只是副本。**永远不要在全局目录里改 skill**，改仓库再重新同步。

## 现有 Skills

| Name | Version | Status | Targets |
| --- | --- | --- | --- |
| `crawl-docs-to-markdown` | 1.0.0 | stable | codex |
| `github-trending-report` | 1.0.0 | stable | codex |

完整列表见 [skills-index.md](skills-index.md)。

## 文档

- [docs/architecture.md](docs/architecture.md) —— source of truth 原则与分层
- [docs/skill-authoring.md](docs/skill-authoring.md) —— Skill 编写规范
- [docs/lifecycle.md](docs/lifecycle.md) —— experimental → archived 生命周期
- [docs/sync-guide.md](docs/sync-guide.md) —— 同步模式与安全边界
- [docs/compatibility.md](docs/compatibility.md) —— Agent 支持矩阵与已验证路径
- [docs/index.md](docs/index.md) —— 文档入口

## 依赖

Python 标准库 + `PyYAML` + `pytest`，没有引入 CLI 框架。依赖用 [uv](https://docs.astral.sh/uv/) 管理。
