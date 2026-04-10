# Skills Index

这个文件用于快速查看当前仓库里有哪些可直接复制使用的 skill。

使用方式：

1. 找到目标 skill
2. 直接复制 `skills/<skill-name>/` 整个目录
3. 放到目标工具的 skills 目录下
4. 如目标工具需要，保留目录名不变

## 1. crawl-docs-to-markdown

- 目录：`skills/crawl-docs-to-markdown/`
- 用途：抓取文档站点，导出本地 Markdown、导航结构和 Mermaid 图
- 适合场景：镜像文档、沉淀离线资料、整理站点结构

主要文件：

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/crawl_docs_to_md.py`
- `scripts/package_skill.py`

常用命令：

```powershell
python skills\crawl-docs-to-markdown\scripts\crawl_docs_to_md.py https://alibaba.github.io/page-agent/docs/introduction/overview/ --output-dir archive\generated\page-agent
python skills\crawl-docs-to-markdown\scripts\package_skill.py --inline-json
```

## 2. github-trending-report

- 目录：`skills/github-trending-report/`
- 用途：抓取 GitHub Trending 日榜、周榜、月榜，并生成中英双语 Markdown 报告
- 适合场景：热榜观察、项目学习记录、技术趋势整理

主要文件：

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/generate_report.py`
- `scripts/package_skill.py`

常用命令：

```powershell
python skills\github-trending-report\scripts\generate_report.py --date 2026-04-10
python skills\github-trending-report\scripts\package_skill.py --inline-json
```

## 复制提醒

- 复制时建议带上整个目录，不要只拿 `SKILL.md`
- `agents/`、`scripts/`、`references/`、`assets/` 都属于 skill 的一部分
- `dist/` 通常是打包产物，可按需要决定是否复制
- 想先检查结构是否完整，可以运行：

```powershell
python tools\validate_skills.py
```
