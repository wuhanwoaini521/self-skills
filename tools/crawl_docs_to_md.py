#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import textwrap
from collections import deque
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


DEFAULT_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

BLOCK_TAGS = {
    "article",
    "blockquote",
    "div",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "thead",
    "tr",
    "ul",
}


@dataclass
class NavItem:
    title: str
    url: str


@dataclass
class NavSection:
    title: str
    items: list[NavItem] = field(default_factory=list)


@dataclass
class Heading:
    level: int
    text: str
    anchor: str


@dataclass
class PageData:
    url: str
    title: str
    nav_section: str | None
    nav_title: str | None
    headings: list[Heading]
    content_markdown: str
    internal_links: list[str]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text or "")).strip()


def normalize_heading_text(text: str) -> str:
    cleaned = normalize_space(text)
    return re.sub(r"^#+\s*", "", cleaned)


def slugify(text: str) -> str:
    cleaned = normalize_heading_text(text).lower()
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return cleaned.strip("-") or "section"


def safe_stem(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "page"


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def infer_docs_root(url: str) -> str:
    parsed = urlparse(url)
    match = re.search(r"(.*/docs/)", parsed.path)
    root_path = match.group(1) if match else parsed.path.rsplit("/", 1)[0] + "/"
    return urlunparse((parsed.scheme, parsed.netloc, root_path, "", "", ""))


def infer_project_name(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if "docs" in parts:
        docs_index = parts.index("docs")
        if docs_index > 0:
            return parts[docs_index - 1]
    if parts:
        return parts[-1]
    return parsed.netloc.replace(".", "-")


def is_doc_url(url: str, docs_root: str) -> bool:
    return canonicalize_url(url).startswith(canonicalize_url(docs_root))


def find_browser(preferred: str | None = None) -> str | None:
    if preferred:
        path = Path(preferred)
        return str(path) if path.exists() else None
    for candidate in DEFAULT_BROWSERS:
        if Path(candidate).exists():
            return candidate
    return None


def render_with_browser(url: str, browser_path: str, timeout: int) -> str:
    command = [
        browser_path,
        "--headless",
        "--disable-gpu",
        "--dump-dom",
        "--virtual-time-budget=8000",
        url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=True,
    )
    return completed.stdout


def fetch_html(url: str, session: requests.Session, browser_path: str | None, timeout: int) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    html = response.text
    if browser_path:
        soup = BeautifulSoup(html, "html.parser")
        if soup.find("article") or soup.find("main"):
            return html
        return render_with_browser(url, browser_path, timeout)
    return html


def extract_nav_sections(soup: BeautifulSoup, base_url: str, docs_root: str) -> list[NavSection]:
    nav_sections: list[NavSection] = []
    aside = soup.find("aside")
    if not aside:
        return nav_sections
    for section in aside.find_all("section", recursive=True):
        title_tag = section.find(["h2", "h3", "h4"])
        title = normalize_space(title_tag.get_text(" ", strip=True)) if title_tag else "未命名分组"
        items: list[NavItem] = []
        for link in section.find_all("a", href=True):
            absolute = canonicalize_url(urljoin(base_url, link["href"]))
            if not is_doc_url(absolute, docs_root):
                continue
            items.append(NavItem(title=normalize_space(link.get_text(" ", strip=True)), url=absolute))
        if items:
            nav_sections.append(NavSection(title=title, items=items))
    return nav_sections


def find_primary_article(soup: BeautifulSoup) -> Tag | None:
    article = soup.find("article")
    if article:
        return article
    main = soup.find("main")
    return main


def extract_headings(article: Tag | None) -> list[Heading]:
    headings: list[Heading] = []
    if not article:
        return headings
    seen: set[str] = set()
    for heading in article.find_all(re.compile(r"^h[1-6]$")):
        text = normalize_heading_text(heading.get_text(" ", strip=True))
        if not text:
            continue
        anchor = heading.get("id") or slugify(text)
        original = anchor
        suffix = 2
        while anchor in seen:
            anchor = f"{original}-{suffix}"
            suffix += 1
        seen.add(anchor)
        headings.append(Heading(level=int(heading.name[1]), text=text, anchor=anchor))
    return headings


def extract_internal_links(container: Tag | None, base_url: str, docs_root: str) -> list[str]:
    if not container:
        return []
    links: list[str] = []
    seen: set[str] = set()
    for link in container.find_all("a", href=True):
        absolute = canonicalize_url(urljoin(base_url, link["href"]))
        if not is_doc_url(absolute, docs_root):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def flatten_inline_children(node: Tag, base_url: str) -> str:
    parts: list[str] = []
    for child in node.children:
        parts.append(convert_inline(child, base_url))
    text = "".join(parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def convert_inline(node: NavigableString | Tag, base_url: str) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()
    if name == "br":
        return "  \n"
    if name == "code":
        return f"`{normalize_space(node.get_text())}`"
    if name in {"strong", "b"}:
        return f"**{flatten_inline_children(node, base_url)}**"
    if name in {"em", "i"}:
        return f"*{flatten_inline_children(node, base_url)}*"
    if name == "a":
        label = flatten_inline_children(node, base_url) or normalize_space(node.get_text(" ", strip=True))
        href = urljoin(base_url, node.get("href", "").strip())
        return f"[{label}]({href})" if href else label
    if name == "img":
        alt = normalize_space(node.get("alt", "image"))
        src = urljoin(base_url, node.get("src", "").strip())
        return f"![{alt}]({src})" if src else alt
    if name in BLOCK_TAGS:
        return ""
    return flatten_inline_children(node, base_url)


def table_to_markdown(table: Tag, base_url: str) -> str:
    rows: list[list[str]] = []
    for tr in table.find_all("tr", recursive=True):
        cells = tr.find_all(["th", "td"], recursive=False) or tr.find_all(["th", "td"])
        if not cells:
            continue
        rows.append([flatten_inline_children(cell, base_url) for cell in cells])
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def looks_like_block_code_container(node: Tag) -> bool:
    if node.name != "div":
        return False
    classes = set(node.get("class", []))
    if "font-mono" not in classes:
        return False
    code = node.find("code", recursive=False)
    if not code:
        return False
    text = code.get_text("", strip=False)
    if "\n" in text:
        return True
    if len(text.strip()) >= 20:
        return True
    return False


def infer_code_language(code: str) -> str:
    stripped = code.strip()
    lowered = stripped.lower()
    if not stripped:
        return ""
    if stripped.startswith("<") and ("</" in stripped or "<script" in lowered):
        return "html"
    if any(token in stripped for token in ("const ", "let ", "import ", "export ", "await ", "=>", "new PageAgent(")):
        return "javascript"
    if stripped.startswith("{") and stripped.endswith("}"):
        return "json"
    if stripped.startswith("pip ") or stripped.startswith("python ") or "def " in stripped or "import " in stripped:
        return "python"
    if stripped.startswith("npm ") or stripped.startswith("pnpm ") or stripped.startswith("yarn "):
        return "bash"
    return ""


def code_block_to_markdown(code: str, language: str = "") -> str:
    normalized = code.strip("\n")
    return f"```{language}\n{normalized}\n```"


def extract_block_code_markdown(node: Tag) -> str:
    code = node.find("code", recursive=False)
    if not code:
        return ""
    text = code.get_text("", strip=False).strip("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return code_block_to_markdown(text, infer_code_language(text))


def element_to_markdown(node: NavigableString | Tag, base_url: str, list_depth: int = 0) -> str:
    if isinstance(node, NavigableString):
        return normalize_space(str(node))
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()

    if looks_like_block_code_container(node):
        return extract_block_code_markdown(node)
    if name in {"section", "div", "main", "article"}:
        chunks = [element_to_markdown(child, base_url, list_depth) for child in node.children]
        return "\n\n".join(chunk for chunk in chunks if chunk.strip())
    if re.fullmatch(r"h[1-6]", name):
        text = normalize_heading_text(node.get_text(" ", strip=True))
        if not text:
            return ""
        return f"{'#' * int(name[1])} {text}"
    if name == "p":
        return flatten_inline_children(node, base_url)
    if name == "blockquote":
        text = "\n".join(
            f"> {line}" if line else ">"
            for line in flatten_inline_children(node, base_url).splitlines()
        )
        return text
    if name == "pre":
        code = node.get_text("\n", strip=False).strip("\n")
        code_tag = node.find("code")
        language = ""
        if code_tag:
            classes = " ".join(code_tag.get("class", []))
            match = re.search(r"language-([\w-]+)", classes)
            if match:
                language = match.group(1)
        if not language:
            language = infer_code_language(code)
        return code_block_to_markdown(code, language)
    if name in {"ul", "ol"}:
        lines: list[str] = []
        for index, li in enumerate(node.find_all("li", recursive=False), start=1):
            item = flatten_inline_children(li, base_url)
            nested_chunks = [
                element_to_markdown(child, base_url, list_depth + 1)
                for child in li.children
                if isinstance(child, Tag) and child.name in {"ul", "ol"}
            ]
            prefix = f"{index}. " if name == "ol" else "- "
            indent = "  " * list_depth
            if item:
                lines.append(f"{indent}{prefix}{item}")
            for nested in nested_chunks:
                if nested.strip():
                    lines.append(nested)
        return "\n".join(lines)
    if name == "table":
        return table_to_markdown(node, base_url)
    if name == "hr":
        return "---"
    if name in {"img"}:
        return convert_inline(node, base_url)

    return flatten_inline_children(node, base_url)


def article_to_markdown(article: Tag | None, base_url: str) -> str:
    if not article:
        return ""
    chunks = [element_to_markdown(child, base_url) for child in article.children]
    markdown = "\n\n".join(chunk for chunk in chunks if chunk.strip())
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return markdown + "\n" if markdown else ""


def trim_duplicate_title_heading(markdown: str, title: str) -> str:
    escaped = re.escape(title.strip())
    pattern = rf"^\#\s+{escaped}\s*\n+"
    return re.sub(pattern, "", markdown, count=1, flags=re.IGNORECASE).lstrip()


def visible_outline(headings: list[Heading], page_title: str) -> list[Heading]:
    if headings and headings[0].level == 1 and headings[0].text == page_title:
        return headings[1:]
    return headings


def build_page_data(
    html: str,
    url: str,
    docs_root: str,
    nav_lookup: dict[str, tuple[str, str]],
) -> tuple[PageData, list[NavSection]]:
    soup = BeautifulSoup(html, "html.parser")
    article = find_primary_article(soup)
    headings = extract_headings(article)
    content_markdown = article_to_markdown(article, url)
    internal_links = extract_internal_links(article, url, docs_root)
    nav_sections = extract_nav_sections(soup, url, docs_root)
    page_title = headings[0].text if headings else normalize_space(soup.title.get_text(strip=True) if soup.title else url)
    content_markdown = trim_duplicate_title_heading(content_markdown, page_title)
    nav_section, nav_title = nav_lookup.get(canonicalize_url(url), (None, None))
    return (
        PageData(
            url=canonicalize_url(url),
            title=page_title,
            nav_section=nav_section,
            nav_title=nav_title,
            headings=headings,
            content_markdown=content_markdown,
            internal_links=internal_links,
        ),
        nav_sections,
    )


def build_nav_lookup(nav_sections: Iterable[NavSection]) -> dict[str, tuple[str, str]]:
    lookup: dict[str, tuple[str, str]] = {}
    for section in nav_sections:
        for item in section.items:
            lookup[item.url] = (section.title, item.title)
    return lookup


def make_page_relative_path(page_url: str, docs_root: str) -> Path:
    relative = canonicalize_url(page_url).removeprefix(canonicalize_url(docs_root)).strip("/")
    parts = [safe_stem(part) for part in relative.split("/") if part]
    return Path(*parts).with_suffix(".md")


def mermaid_node_id(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"n_{digest}"


def render_nav_mermaid(nav_sections: list[NavSection]) -> str:
    lines = ["graph TD"]
    lines.append('  docs["Docs"]')
    for section in nav_sections:
        section_id = mermaid_node_id(f"section:{section.title}")
        lines.append(f'  docs --> {section_id}["{section.title}"]')
        for item in section.items:
            item_id = mermaid_node_id(f"page:{item.url}")
            label = item.title.replace('"', "'")
            lines.append(f'  {section_id} --> {item_id}["{label}"]')
    return "\n".join(lines)


def render_outline_mermaid(page: PageData) -> str:
    lines = ["graph TD"]
    root_id = mermaid_node_id(page.url)
    lines.append(f'  {root_id}["{page.title.replace(chr(34), chr(39))}"]')
    stack: list[tuple[int, str]] = [(0, root_id)]
    for heading in visible_outline(page.headings, page.title):
        node_id = mermaid_node_id(f"{page.url}#{heading.anchor}")
        label = heading.text.replace('"', "'")
        while stack and stack[-1][0] >= heading.level:
            stack.pop()
        parent_id = stack[-1][1] if stack else root_id
        lines.append(f'  {parent_id} --> {node_id}["{label}"]')
        stack.append((heading.level, node_id))
    return "\n".join(lines)


def render_nav_tree(nav_sections: list[NavSection]) -> str:
    lines: list[str] = []
    for section in nav_sections:
        lines.append(f"- {section.title}")
        for item in section.items:
            lines.append(f"  - [{item.title}]({item.url})")
    return "\n".join(lines)


def render_summary(nav_sections: list[NavSection], docs_root: str) -> str:
    lines = ["# Summary", ""]
    for section in nav_sections:
        lines.append(f"- {section.title}")
        for item in section.items:
            relative = make_page_relative_path(item.url, docs_root).as_posix()
            lines.append(f"  - [{item.title}]({relative})")
    return "\n".join(lines).strip() + "\n"


def render_outline_list(headings: list[Heading]) -> str:
    if not headings:
        return ""
    base_level = min(heading.level for heading in headings)
    lines: list[str] = []
    for heading in headings:
        indent = "  " * max(heading.level - base_level, 0)
        lines.append(f"{indent}- {heading.text}")
    return "\n".join(lines)


def write_site_index(
    output_dir: Path,
    project_name: str,
    start_url: str,
    docs_root: str,
    nav_sections: list[NavSection],
    pages: list[PageData],
) -> None:
    lines = [
        f"# {project_name}",
        "",
        f"- Start URL: [{start_url}]({start_url})",
        f"- Docs Root: [{docs_root}]({docs_root})",
        f"- Total Pages: {len(pages)}",
        f"- Summary: [summary.md](summary.md)",
        "",
        "## Navigation Mermaid",
        "",
        "```mermaid",
        render_nav_mermaid(nav_sections),
        "```",
        "",
        "## Navigation Tree",
        "",
        render_nav_tree(nav_sections),
        "",
        "## Pages",
        "",
    ]
    for page in pages:
        relative_path = make_page_relative_path(page.url, docs_root).as_posix()
        lines.append(f"- [{page.title}]({relative_path})")
    output_dir.joinpath("index.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    output_dir.joinpath("summary.md").write_text(render_summary(nav_sections, docs_root), encoding="utf-8")


def write_page_markdown(output_dir: Path, docs_root: str, page: PageData) -> None:
    relative_path = make_page_relative_path(page.url, docs_root)
    full_path = output_dir / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {page.title}",
        "",
        f"- Source: [{page.url}]({page.url})",
    ]
    if page.nav_section:
        lines.append(f"- Section: {page.nav_section}")
    if page.nav_title and page.nav_title != page.title:
        lines.append(f"- Nav Title: {page.nav_title}")
    lines.extend(
        [
            "",
            "## Outline Mermaid",
            "",
            "```mermaid",
            render_outline_mermaid(page),
            "```",
            "",
            "## Outline",
            "",
            render_outline_list(visible_outline(page.headings, page.title)) or "- 无可提取标题",
            "",
            "## Content",
            "",
            page.content_markdown.strip() or "_未提取到正文_",
            "",
        ]
    )
    if page.internal_links:
        lines.extend(
            [
                "## Internal Links",
                "",
                *[f"- [{link}]({link})" for link in page.internal_links],
                "",
            ]
        )
    full_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def resolve_output_dir(base_output_dir: Path, project_name: str) -> Path:
    if base_output_dir.name.lower() == safe_stem(project_name).lower():
        return base_output_dir
    return base_output_dir / safe_stem(project_name)


def crawl_site(start_url: str, output_dir: Path, browser_path: str | None, timeout: int, max_pages: int) -> dict[str, object]:
    project_name = infer_project_name(start_url)
    output_dir = resolve_output_dir(output_dir, project_name)
    docs_root = infer_docs_root(start_url)
    output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0 Safari/537.36",
        }
    )

    first_html = fetch_html(start_url, session, browser_path, timeout)
    first_soup = BeautifulSoup(first_html, "html.parser")
    nav_sections = extract_nav_sections(first_soup, start_url, docs_root)
    discovered = [item.url for section in nav_sections for item in section.items] or [canonicalize_url(start_url)]
    nav_lookup = build_nav_lookup(nav_sections)

    pages: dict[str, PageData] = {}
    queue: deque[str] = deque(dict.fromkeys([canonicalize_url(start_url), *discovered]))

    while queue and len(pages) < max_pages:
        current_url = canonicalize_url(queue.popleft())
        if current_url in pages:
            continue
        html = first_html if current_url == canonicalize_url(start_url) else fetch_html(current_url, session, browser_path, timeout)
        page, current_nav_sections = build_page_data(html, current_url, docs_root, nav_lookup)
        pages[current_url] = page
        if current_nav_sections and not nav_sections:
            nav_sections = current_nav_sections
            nav_lookup = build_nav_lookup(nav_sections)
        for link in current_nav_sections:
            for item in link.items:
                if item.url not in pages:
                    queue.append(item.url)
        for link in page.internal_links:
            if link not in pages and is_doc_url(link, docs_root):
                queue.append(link)

    ordered_pages = sorted(pages.values(), key=lambda item: (item.nav_section or "zzzz", item.nav_title or item.title, item.url))
    write_site_index(output_dir, project_name, canonicalize_url(start_url), docs_root, nav_sections, ordered_pages)
    for page in ordered_pages:
        write_page_markdown(output_dir, docs_root, page)

    manifest = {
        "project_name": project_name,
        "start_url": canonicalize_url(start_url),
        "docs_root": docs_root,
        "browser_path": browser_path,
        "output_dir": str(output_dir.resolve()),
        "total_pages": len(ordered_pages),
        "pages": [
            {
                "title": page.title,
                "url": page.url,
                "nav_section": page.nav_section,
                "nav_title": page.nav_title,
                "headings": [heading.__dict__ for heading in page.headings],
                "internal_links": page.internal_links,
                "file": make_page_relative_path(page.url, docs_root).as_posix(),
            }
            for page in ordered_pages
        ],
    }
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl a documentation site and export navigation, outlines, and page content as Markdown + Mermaid.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Example:
              python tools/crawl_docs_to_md.py ^
                https://alibaba.github.io/page-agent/docs/introduction/overview/ ^
                --output-dir archive/generated/page-agent
            """
        ),
    )
    parser.add_argument("start_url", help="Documentation page URL used as the crawl entry point.")
    parser.add_argument("--output-dir", default="archive/generated/docs-export", help="Output directory for markdown files.")
    parser.add_argument("--browser", help="Optional browser path used for JS-rendered sites.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP and browser timeout in seconds.")
    parser.add_argument("--max-pages", type=int, default=200, help="Maximum number of pages to crawl.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    browser_path = find_browser(args.browser)
    try:
        manifest = crawl_site(
            start_url=args.start_url,
            output_dir=Path(args.output_dir),
            browser_path=browser_path,
            timeout=args.timeout,
            max_pages=args.max_pages,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output_dir": manifest["output_dir"],
                "total_pages": manifest["total_pages"],
                "browser_path": manifest["browser_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
