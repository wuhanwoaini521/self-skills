---
name: crawl-docs-to-markdown
description: Crawl documentation websites and export a project-named Markdown bundle with index.md, summary.md, per-page Markdown files, internal link preservation, and Mermaid diagrams for navigation and page outlines. Use when Codex needs to mirror docs sites, scrape developer documentation, convert online docs to Markdown, preserve sidebar or table-of-contents hierarchy, or package a docs site for local reading and reuse. 当用户要求爬取文档网站、抓取开发者文档、导出 Markdown、保留侧边栏目录层级、保留页面大纲、生成 Mermaid 导航图，或把在线文档站打包为本地可读文档时使用。
---

# Crawl Docs To Markdown

## Overview

Use `scripts/crawl_docs_to_md.py` instead of reimplementing a crawler from scratch. The script handles both plain HTML docs pages and JS-rendered docs sites by falling back to local Edge or Chrome headless DOM rendering when needed.

If the user also wants the skill itself packaged for OpenAI-hosted Skills or inline skill source usage, run `scripts/package_skill.py`. Read `references/openai-skills-publishing.md` when the task involves zip upload, inline base64 source, or OpenAI Skills publishing constraints.

## Workflow

1. Start from a concrete docs page URL, not just a site homepage.
2. Run the bundled script.
3. Inspect `index.md` and `summary.md` first.
4. Spot-check at least one generated page that contains headings, links, tables, and code blocks.

Example:

```powershell
python scripts/crawl_docs_to_md.py https://alibaba.github.io/page-agent/docs/introduction/overview/ --output-dir output
```

## Output Contract

The script must produce this structure:

```text
<output-dir>/<project-name>/
  index.md
  summary.md
  introduction/...
  features/...
  advanced/...
```

Rules:

- Name the root folder after the project name inferred from the docs URL.
- Use `index.md` as the overall index.
- Use `summary.md` as the navigation hierarchy file.
- Write page files directly under their docs hierarchy; do not create an extra `pages/` layer.
- Do not leave temporary debug artifacts such as rendered HTML dumps in the workspace unless the user explicitly asks for them.

## What To Extract

For each crawl:

- Extract sidebar navigation groups and page links.
- Extract each page outline from headings.
- Convert page content to Markdown.
- Preserve internal documentation links.
- Emit Mermaid for site navigation and per-page outlines.

## JS-Rendered Sites

If the first HTTP response does not contain the real docs body, rely on the script's browser fallback. The script looks for local Edge or Chrome and uses headless `--dump-dom` rendering to recover the actual navigation and content.

## Validation

After running the script:

- Open `index.md` and confirm the project name, page count, and Mermaid site graph look reasonable.
- Open `summary.md` and confirm section nesting and relative links are correct.
- Open a generated page with code samples and confirm fenced code blocks use the expected format such as ` ```python ` or ` ```javascript `.
- If the site is multilingual, verify the exported files are UTF-8 and display correctly in a UTF-8 aware editor.

## scripts

- `scripts/crawl_docs_to_md.py`: Main crawler and exporter.
- `scripts/package_skill.py`: Build a zip bundle for OpenAI Skills upload and optionally emit inline skill JSON.

## references

- `references/openai-skills-publishing.md`: Official packaging constraints, zip structure, inline source notes, and safety reminders.
