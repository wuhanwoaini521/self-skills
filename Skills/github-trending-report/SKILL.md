---
name: github-trending-report
description: Scrape GitHub Trending for daily, weekly, and monthly repos, then generate a bilingual Markdown report with repository summaries, README-based explanations, and stylized Mermaid workflow diagrams. Use when Codex needs to collect GitHub hot projects, summarize trending repositories, produce Chinese and English explanations, or export a reusable Markdown trend brief. 用户要抓取 GitHub 热榜、生成中英对照解读、补充 Mermaid / workflow 示意，并导出为本地报告时使用。
---

# GitHub Trending Report

## Overview

Use `scripts/generate_report.py` to scrape:

- `https://github.com/trending?since=daily`
- `https://github.com/trending?since=weekly`
- `https://github.com/trending?since=monthly`

The script extracts trending cards, visits each repository page, reads topics and README headings, then writes:

- a Markdown report
- a JSON data dump

The Markdown report includes:

- 日 / 周 / 月榜单表格
- 重点项目详细说明
- 中文讲解
- English explanation
- Mermaid / workflow 示意图

## Workflow

1. Run the bundled script.
2. Open the generated Markdown report first.
3. Spot-check at least one repo detail section.
4. If Mermaid styling matters, confirm the renderer supports Mermaid `init` blocks.

Example:

```powershell
python scripts/generate_report.py --date 2026-04-10
```

## Output Contract

The script writes files into the output directory:

```text
<output-dir>/
  report_<date>.md
  trending_<date>.json
```

Defaults:

- output directory: current skill directory
- date: today
- max items per period: 10
- detailed notes per period: 5

## What To Extract

For each period:

- Trending rank
- Repository owner/name
- Description
- Language
- Stars / forks
- Trending star increment
- Topics
- README headings
- README summary paragraphs
- Workflow hints

## Mermaid Style

The bundled Mermaid output uses a retro pixel-style approximation:

- monospace / pixel-like font fallback
- straight line flowchart edges
- thick dark borders
- retro game palette

If the user asks for a different visual direction, adjust the Mermaid `init` theme variables inside `scripts/generate_report.py`.

## Validation

After running the script:

- Open the generated `report_<date>.md`.
- Confirm all three periods exist: daily / weekly / monthly.
- Confirm at least one repo detail section contains bilingual explanation.
- Confirm Mermaid blocks render in the target Markdown environment.

## scripts

- `scripts/generate_report.py`: Main scraper and report generator.
- `scripts/package_skill.py`: Package the skill as zip and optional inline JSON.

