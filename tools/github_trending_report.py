#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import textwrap
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://github.com"
DEFAULT_SINCE_VALUES = ("daily", "weekly", "monthly")
SINCE_LABELS_ZH = {
    "daily": "每日",
    "weekly": "每周",
    "monthly": "每月",
}
WORKFLOW_KEYWORDS = (
    "workflow",
    "how it works",
    "architecture",
    "pipeline",
    "flow",
    "getting started",
    "quick start",
    "quick install",
    "usage",
    "core features",
    "technology highlights",
)
GENERIC_HEADINGS = {
    "license",
    "contributing",
    "community",
    "feedback",
    "development",
    "documentation",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
PIXEL_MERMAID_INIT = """%%{init: {
  "theme": "base",
  "themeVariables": {
    "fontFamily": "\\"Press Start 2P\\", \\"Courier New\\", monospace",
    "primaryColor": "#F7D354",
    "primaryTextColor": "#1A1A1A",
    "primaryBorderColor": "#1A1A1A",
    "secondaryColor": "#63D1F4",
    "secondaryTextColor": "#1A1A1A",
    "secondaryBorderColor": "#1A1A1A",
    "tertiaryColor": "#FF7A90",
    "tertiaryTextColor": "#1A1A1A",
    "tertiaryBorderColor": "#1A1A1A",
    "lineColor": "#1A1A1A",
    "mainBkg": "#F4EBD0",
    "clusterBkg": "#F4EBD0",
    "clusterBorder": "#1A1A1A",
    "edgeLabelBackground": "#F4EBD0",
    "nodeBorder": "#1A1A1A"
  },
  "flowchart": {
    "curve": "linear",
    "htmlLabels": false
  }
}}%%"""


@dataclass
class RepoSummary:
    since: str
    rank: int
    owner: str
    name: str
    url: str
    description: str = ""
    language: str = ""
    stars: str = ""
    forks: str = ""
    trending_stars: str = ""
    topics: list[str] = field(default_factory=list)
    readme_headings: list[str] = field(default_factory=list)
    readme_intro: list[str] = field(default_factory=list)
    readme_mermaid_count: int = 0
    workflow_hints: list[str] = field(default_factory=list)
    zh_explanation: str = ""
    en_explanation: str = ""
    generated_mermaid: str | None = None
    fetch_note: str = ""

    @property
    def repo_slug(self) -> str:
        return f"{self.owner}/{self.name}"


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def trim_text(text: str, limit: int = 220) -> str:
    cleaned = normalize_space(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_space(item)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def label_from_since(since: str) -> str:
    return SINCE_LABELS_ZH.get(since, since)


def parse_trending_stars(article: Tag) -> str:
    text = normalize_space(article.get_text(" ", strip=True))
    match = re.search(r"([\d.,]+[kKmM]?) stars (today|this week|this month)", text)
    return match.group(1) if match else ""


def parse_trending_page(html: str, since: str, max_items: int | None = None) -> list[RepoSummary]:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.Box-row")
    items: list[RepoSummary] = []
    for index, article in enumerate(articles, start=1):
        anchor = article.select_one("h2 a[href]")
        if not anchor:
            continue
        href = anchor.get("href", "").strip()
        parts = [part for part in href.strip("/").split("/") if part]
        if len(parts) != 2:
            continue
        muted_links = article.select("a.Link--muted")
        description = article.select_one("p")
        language = article.select_one("[itemprop='programmingLanguage']")
        items.append(
            RepoSummary(
                since=since,
                rank=index,
                owner=parts[0],
                name=parts[1],
                url=f"{BASE_URL}/{parts[0]}/{parts[1]}",
                description=normalize_space(description.get_text(" ", strip=True)) if description else "",
                language=normalize_space(language.get_text(" ", strip=True)) if language else "",
                stars=normalize_space(muted_links[0].get_text(" ", strip=True)) if len(muted_links) > 0 else "",
                forks=normalize_space(muted_links[1].get_text(" ", strip=True)) if len(muted_links) > 1 else "",
                trending_stars=parse_trending_stars(article),
            )
        )
        if max_items and len(items) >= max_items:
            break
    return items


def fetch_html(session: requests.Session, url: str, timeout: int = 30) -> str:
    response = session.get(url, timeout=timeout, headers=HEADERS)
    response.raise_for_status()
    return response.text


def extract_readme_headings(readme: Tag | None, limit: int = 6) -> list[str]:
    if not readme:
        return []
    headings = []
    for heading in readme.select("h1, h2, h3"):
        text = normalize_space(heading.get_text(" ", strip=True))
        if not text:
            continue
        headings.append(text)
        if len(headings) >= limit:
            break
    return dedupe_keep_order(headings)


def extract_readme_intro(readme: Tag | None, limit: int = 3) -> list[str]:
    if not readme:
        return []
    blocks: list[str] = []
    for node in readme.select("p, li"):
        text = trim_text(node.get_text(" ", strip=True), 260)
        lowered = text.casefold()
        if not text or len(text) < 40:
            continue
        if lowered.startswith("table of contents"):
            continue
        if text in blocks:
            continue
        blocks.append(text)
        if len(blocks) >= limit:
            break
    return blocks


def extract_topics(soup: BeautifulSoup, limit: int = 8) -> list[str]:
    topics = [normalize_space(node.get_text(" ", strip=True)) for node in soup.select("a.topic-tag")]
    return dedupe_keep_order(topics)[:limit]


def find_workflow_hints(headings: Iterable[str], intro_blocks: Iterable[str]) -> list[str]:
    hints: list[str] = []
    patterns = tuple(keyword.casefold() for keyword in WORKFLOW_KEYWORDS)
    for candidate in list(headings) + list(intro_blocks):
        lowered = candidate.casefold()
        if any(pattern in lowered for pattern in patterns):
            hints.append(candidate)
    return dedupe_keep_order(hints)[:4]


def infer_project_type(repo: RepoSummary) -> tuple[str, str]:
    bag = " ".join(
        [repo.description, " ".join(repo.topics), " ".join(repo.readme_headings), " ".join(repo.readme_intro)]
    ).casefold()
    if any(keyword in bag for keyword in ("agent", "codex", "claude", "llm", "chatgpt", "openai")):
        return "AI 智能体/开发者工具", "AI agent and developer tool"
    if any(keyword in bag for keyword in ("gallery", "showcase", "preview", "use cases")):
        return "示例展示/体验项目", "showcase and hands-on demo project"
    if any(keyword in bag for keyword in ("screen studio", "demo", "video", "presentation")):
        return "演示内容创作工具", "demo and content creation tool"
    if any(keyword in bag for keyword in ("sdk", "runtime", "library", "framework")):
        return "底层库/运行时项目", "core library or runtime project"
    return "开源项目", "open-source project"


def infer_focus_areas(repo: RepoSummary) -> tuple[list[str], list[str]]:
    bag = " ".join([repo.description, " ".join(repo.topics), " ".join(repo.readme_headings)]).casefold()
    zh: list[str] = []
    en: list[str] = []
    mapping = [
        (("install", "getting started", "quick start", "quick install"), ("快速上手", "quick onboarding")),
        (("feature", "highlight", "use case", "capability"), ("核心能力", "core capabilities")),
        (("workflow", "architecture", "pipeline", "flow"), ("工作流/架构", "workflow and architecture")),
        (("cli", "terminal", "command"), ("命令行体验", "CLI experience")),
        (("mobile", "app", "android", "ios", "on-device"), ("端侧应用", "on-device or app usage")),
        (("agent", "automation", "schedule"), ("自动化与智能体", "automation and agent behaviors")),
        (("model", "inference", "runtime"), ("模型与推理", "models and inference")),
        (("development", "contributing", "sdk"), ("开发扩展", "developer extension")),
    ]
    for keywords, labels in mapping:
        if any(keyword in bag for keyword in keywords):
            zh.append(labels[0])
            en.append(labels[1])
    return dedupe_keep_order(zh)[:3], dedupe_keep_order(en)[:3]


def infer_audience(repo: RepoSummary) -> tuple[str, str]:
    bag = " ".join([repo.description, " ".join(repo.topics), " ".join(repo.readme_headings)]).casefold()
    if any(keyword in bag for keyword in ("agent", "codex", "claude", "cli", "sdk")):
        return "需要自动化编码或多端协同的开发者", "developers who need coding automation or multi-channel workflows"
    if any(keyword in bag for keyword in ("gallery", "showcase", "use cases", "preview")):
        return "想快速试用能力和参考样例的开发者/产品团队", "developers or product teams who want quick hands-on examples"
    if any(keyword in bag for keyword in ("demo", "video", "presentation")):
        return "要制作演示视频或产品展示内容的创作者", "creators making product demos or presentation content"
    if any(keyword in bag for keyword in ("runtime", "inference", "model")):
        return "需要把模型能力集成到产品中的工程团队", "engineering teams integrating model capabilities into products"
    return "关注该方向的开源使用者", "open-source users exploring this space"


def build_explanations(repo: RepoSummary) -> tuple[str, str]:
    project_type_zh, project_type_en = infer_project_type(repo)
    focus_zh, focus_en = infer_focus_areas(repo)
    audience_zh, audience_en = infer_audience(repo)
    focus_zh_text = "、".join(focus_zh) if focus_zh else "README 中强调的核心能力"
    focus_en_text = ", ".join(focus_en) if focus_en else "the key capabilities highlighted in the README"
    intro_signal = repo.readme_intro[0] if repo.readme_intro else repo.description
    intro_signal = trim_text(intro_signal, 140)
    zh = (
        f"这是一个偏向 {project_type_zh} 的仓库。结合 Trending 简介和 README 开头内容看，"
        f"它主要围绕 {focus_zh_text} 展开，目标用户是 {audience_zh}。"
        f"如果你想快速判断是否值得跟进，可以先看仓库开头强调的这条信号：{intro_signal}"
    )
    en = (
        f"This repository is best understood as an {project_type_en}. Based on the trending card and README opening, "
        f"it mainly focuses on {focus_en_text}, and it is aimed at {audience_en}. "
        f"A good early signal to judge fit is this opening emphasis: {intro_signal}"
    )
    return zh, en


def sanitize_mermaid_label(text: str) -> str:
    cleaned = re.sub(r"[\"`]", "", normalize_space(text))
    if len(cleaned) > 28:
        cleaned = cleaned[:25].rstrip() + "..."
    return cleaned or "Signal"


def mermaid_node_id(text: str) -> str:
    letters = re.sub(r"[^a-z0-9]+", "", text.casefold())
    return letters[:12] or "node"


def select_mermaid_steps(repo: RepoSummary) -> list[str]:
    steps: list[str] = []
    for heading in repo.readme_headings:
        lowered = heading.casefold()
        if lowered in GENERIC_HEADINGS:
            continue
        if any(keyword in lowered for keyword in ("quick", "getting started", "install", "preview", "feature", "usage", "cli")):
            steps.append(heading)
    if not steps and repo.workflow_hints:
        steps.extend(repo.workflow_hints[:3])
    if not steps and repo.topics:
        steps.extend(repo.topics[:3])
    return dedupe_keep_order(steps)[:3]


def build_mermaid(repo: RepoSummary) -> str | None:
    steps = select_mermaid_steps(repo)
    if not steps:
        return None
    lines = [
        PIXEL_MERMAID_INIT,
        "flowchart LR",
        'user["Trending Reader"] --> repo["' + sanitize_mermaid_label(repo.repo_slug) + '"]',
        "classDef punch fill:#F7D354,stroke:#1A1A1A,stroke-width:4px,color:#1A1A1A,font-family:'Courier New',monospace;",
        "classDef pop fill:#63D1F4,stroke:#1A1A1A,stroke-width:4px,color:#1A1A1A,font-family:'Courier New',monospace;",
        "classDef spark fill:#FF7A90,stroke:#1A1A1A,stroke-width:4px,color:#1A1A1A,font-family:'Courier New',monospace;",
        "classDef soft fill:#8EEB7A,stroke:#1A1A1A,stroke-width:4px,color:#1A1A1A,font-family:'Courier New',monospace;",
    ]
    previous = "repo"
    step_classes = ("pop", "spark", "soft")
    for step in steps:
        node_id = mermaid_node_id(step)
        lines.append(f'{previous} --> {node_id}["{sanitize_mermaid_label(step)}"]')
        lines.append(f"class {node_id} {step_classes[(len(lines) - 1) % len(step_classes)]};")
        previous = node_id
    lines.append("class user,repo punch;")
    return "\n".join(lines)


def enrich_repo(repo: RepoSummary, session: requests.Session) -> RepoSummary:
    updated = replace(repo)
    try:
        html = fetch_html(session, repo.url)
    except requests.RequestException as exc:
        updated.fetch_note = f"fetch failed: {exc}"
        updated.zh_explanation, updated.en_explanation = build_explanations(updated)
        return updated

    soup = BeautifulSoup(html, "html.parser")
    repo_desc = soup.select_one("p.f4")
    if repo_desc and not updated.description:
        updated.description = normalize_space(repo_desc.get_text(" ", strip=True))
    updated.topics = extract_topics(soup)
    readme = soup.select_one("#readme article.markdown-body") or soup.select_one("article.markdown-body")
    updated.readme_headings = extract_readme_headings(readme)
    updated.readme_intro = extract_readme_intro(readme)
    updated.readme_mermaid_count = len(readme.select(".highlight-source-mermaid, pre code.language-mermaid")) if readme else 0
    updated.workflow_hints = find_workflow_hints(updated.readme_headings, updated.readme_intro)
    updated.zh_explanation, updated.en_explanation = build_explanations(updated)
    updated.generated_mermaid = build_mermaid(updated)
    return updated


def scrape_trending(session: requests.Session, since: str, max_items: int) -> list[RepoSummary]:
    html = fetch_html(session, f"{BASE_URL}/trending?since={since}")
    return parse_trending_page(html, since=since, max_items=max_items)


def enrich_repositories(repos: list[RepoSummary], workers: int = 6) -> list[RepoSummary]:
    unique_by_url: dict[str, RepoSummary] = {}
    for repo in repos:
        unique_by_url.setdefault(repo.url, repo)

    def job(item: RepoSummary) -> RepoSummary:
        with requests.Session() as session:
            return enrich_repo(item, session)

    enriched_by_url: dict[str, RepoSummary] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(job, repo): repo.url for repo in unique_by_url.values()}
        for future in concurrent.futures.as_completed(futures):
            enriched = future.result()
            enriched_by_url[enriched.url] = enriched

    return [replace(enriched_by_url.get(repo.url, repo), since=repo.since, rank=repo.rank) for repo in repos]


def group_by_since(repos: Iterable[RepoSummary]) -> dict[str, list[RepoSummary]]:
    grouped: dict[str, list[RepoSummary]] = {since: [] for since in DEFAULT_SINCE_VALUES}
    for repo in repos:
        grouped.setdefault(repo.since, []).append(repo)
    for since in grouped:
        grouped[since].sort(key=lambda item: item.rank)
    return grouped


def format_repo_table(rows: Iterable[RepoSummary]) -> str:
    lines = [
        "| Rank | Repo | Lang | Stars | Forks | Trend | Description |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for repo in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(repo.rank),
                    f"[{repo.repo_slug}]({repo.url})",
                    repo.language or "-",
                    repo.stars or "-",
                    repo.forks or "-",
                    repo.trending_stars or "-",
                    repo.description or "-",
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def render_repo_detail(repo: RepoSummary) -> str:
    lines = [
        f"### {repo.rank}. {repo.repo_slug}",
        "",
        f"- Repository: [{repo.repo_slug}]({repo.url})",
        f"- Period: {label_from_since(repo.since)}",
        f"- Language: {repo.language or '-'}",
        f"- Stars / Forks: {repo.stars or '-'} / {repo.forks or '-'}",
        f"- Trending Increment: {repo.trending_stars or '-'}",
        f"- Topics: {', '.join(repo.topics) if repo.topics else '未抓到 topic'}",
        f"- README Headings: {', '.join(repo.readme_headings) if repo.readme_headings else '未抓到 README 标题'}",
        f"- Mermaid In README: {repo.readme_mermaid_count}",
        (
            f"- Workflow Hints: {', '.join(repo.workflow_hints)}"
            if repo.workflow_hints
            else "- Workflow Hints: 未发现明显的 workflow / architecture 标题"
        ),
        "",
        "#### README Summary",
        "",
    ]
    if repo.readme_intro:
        lines.extend([f"- {item}" for item in repo.readme_intro])
    else:
        lines.append("- 未抓到足够长的 README 摘要段落。")
    lines.extend(
        [
            "",
            "#### 中文讲解",
            "",
            repo.zh_explanation,
            "",
            "#### English Explanation",
            "",
            repo.en_explanation,
        ]
    )
    if repo.generated_mermaid:
        lines.extend(
            [
                "",
                "#### Mermaid / Workflow",
                "",
                "> 下面是基于 README 标题整理的示意图，不是仓库原图。",
                "",
                "```mermaid",
                repo.generated_mermaid,
                "```",
            ]
        )
    return "\n".join(lines)


def render_report(report_date: str, grouped: dict[str, list[RepoSummary]], detail_limit: int) -> str:
    sections = [
        f"# GitHub Trending Report ({report_date})",
        "",
        "- Source: `https://github.com/trending?since=daily|weekly|monthly`",
        "- Method: 抓 Trending 卡片 + 仓库主页 + README 标题/前几段，生成中英对照解读。",
        f"- Scope: 每个周期抓取前 {max(len(items) for items in grouped.values() if items)} 个可见项目，详细讲解保留前 {detail_limit} 个。",
        "",
        "## Overview",
        "",
    ]
    for since in DEFAULT_SINCE_VALUES:
        items = grouped.get(since, [])
        if not items:
            continue
        sections.append(f"- {label_from_since(since)}: {len(items)} repos, top repo is `{items[0].repo_slug}`")
    for since in DEFAULT_SINCE_VALUES:
        items = grouped.get(since, [])
        if not items:
            continue
        sections.extend(
            [
                "",
                f"## {label_from_since(since)} Trending",
                "",
                format_repo_table(items),
                "",
                f"### Detailed Notes ({min(detail_limit, len(items))} repos)",
                "",
            ]
        )
        for repo in items[:detail_limit]:
            sections.extend([render_repo_detail(repo), ""])
    return "\n".join(sections).strip() + "\n"


def write_outputs(output_dir: Path, report_date: str, repos: list[RepoSummary], detail_limit: int) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped = group_by_since(repos)
    json_path = output_dir / f"trending_{report_date}.json"
    report_path = output_dir / f"report_{report_date}.md"
    json_path.write_text(
        json.dumps([asdict(repo) for repo in repos], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path.write_text(render_report(report_date, grouped, detail_limit), encoding="utf-8")
    return json_path, report_path


def run(report_date: str, output_dir: Path, max_items: int, detail_limit: int) -> tuple[Path, Path]:
    repos: list[RepoSummary] = []
    with requests.Session() as session:
        for since in DEFAULT_SINCE_VALUES:
            repos.extend(scrape_trending(session, since=since, max_items=max_items))
    enriched = enrich_repositories(repos)
    return write_outputs(output_dir, report_date, enriched, detail_limit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape GitHub Trending and render a bilingual markdown report.")
    parser.add_argument("--date", default=str(date.today()), help="Report date in YYYY-MM-DD format.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "archive" / "generated" / "github-trending-report",
    )
    parser.add_argument("--max-items", type=int, default=10, help="Visible repos to keep per period.")
    parser.add_argument("--detail-limit", type=int, default=5, help="Detailed repo notes per period.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    json_path, report_path = run(
        report_date=args.date,
        output_dir=args.output_dir,
        max_items=args.max_items,
        detail_limit=args.detail_limit,
    )
    print(f"JSON: {json_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
