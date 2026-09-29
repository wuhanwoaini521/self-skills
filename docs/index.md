# 文档索引

这个仓库现在是 **Personal Skills Registry**——你个人 Skill 的唯一事实源。所有 skill 的正文都放在 `skills/` 下面，GitHub 上的 `self-skills` 仓库是唯一需要编辑的地方；各 Agent 的全局 skills 目录只是同步工具生成的部署目标。仓库同时提供校验、同步和体检工具，让同一份 skill 定义可以被 Codex CLI、Claude Code、OpenCode 和 Pi 共用。

## 文档

| 文档 | 回答什么问题 |
| --- | --- |
| [`docs/architecture.md`](architecture.md) | 唯一事实源规则是什么，各层（仓库、注册表、同步工具、Agent 全局目录）如何分工。 |
| [`docs/lifecycle.md`](lifecycle.md) | skill 有哪五个生命周期状态，一个 skill 如何在状态之间流转。 |
| [`docs/skill-authoring.md`](skill-authoring.md) | 个人 skill 开发规范：命名、目录布局、`SKILL.md`、`references/`、`scripts/`、`assets/`、`agents` 元数据、version、status、测试。**这是编写 skill 的权威文档。** |
| [`docs/sync-guide.md`](sync-guide.md) | skill 怎么同步到 Codex / Claude Code / OpenCode / Pi，以及同步过程中如何保证安全。 |
| [`docs/compatibility.md`](compatibility.md) | Agent 支持矩阵，以及哪些路径是真验证过的、哪些只是猜测。 |

## 实战示例

这两个文档是 `skills/` 下两个真实 skill 的完整走查，想直接看成品长什么样就从这里开始。

| 文档 | 对应的 skill | 回答什么问题 |
| --- | --- | --- |
| [`docs/examples/crawl-docs-to-markdown.md`](examples/crawl-docs-to-markdown.md) | `skills/crawl-docs-to-markdown` | 怎么把一个文档站点抓取成 Markdown：SKILL.md 怎么写、逻辑何时放进 `scripts/`、输出目录和结果文件怎么定。 |
| [`docs/examples/github-trending-report.md`](examples/github-trending-report.md) | `skills/github-trending-report` | 怎么抓取 GitHub Trending 并生成带中英说明和 Mermaid 图的报告：如何封装抓取逻辑、如何设计输出产物、如何在文档里加入结构化示意。 |

## 旧学习笔记（历史归档）

以下两篇写于注册表重构之前，保留仅为参考。涉及 skill 结构与写法时，以 [`docs/skill-authoring.md`](skill-authoring.md) 为准。

| 文档 | 说明 |
| --- | --- |
| [`docs/concepts/repository-skill-layout.md`](concepts/repository-skill-layout.md) | 旧版学习笔记：当时的仓库目录布局。 |
| [`docs/getting-started/create-first-skill.md`](getting-started/create-first-skill.md) | 旧版学习笔记：当时的第一个 skill 教程。 |

## 仓库内其他入口

- [`skills-index.md`](../skills-index.md)（仓库根目录）：自动生成的可读 skill 清单，想快速浏览有哪些 skill 看这里。
- [`README.md`](../README.md)：命令速查表，日常用到的校验、同步、体检命令都在这里。

## 常用命令

```bash
# 校验 skills/ 下所有 skill 的结构
uv run python tools/validate_skills.py

# 同步前先干跑
uv run python tools/sync_skills.py --target codex --dry-run

# 执行同步
uv run python tools/sync_skills.py --target codex

# 检查注册表与各目标状态
uv run python tools/doctor.py
```

细节见 [`docs/sync-guide.md`](sync-guide.md)。
