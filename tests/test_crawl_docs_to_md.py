import unittest
from pathlib import Path
from bs4 import BeautifulSoup

from tools.crawl_docs_to_md import (
    article_to_markdown,
    canonicalize_url,
    extract_headings,
    extract_nav_sections,
    infer_docs_root,
    infer_project_name,
    mermaid_node_id,
    make_page_relative_path,
    normalize_heading_text,
    render_summary,
    resolve_output_dir,
    render_nav_mermaid,
    trim_duplicate_title_heading,
    visible_outline,
)


class CrawlDocsToMdTests(unittest.TestCase):
    def test_infer_docs_root(self) -> None:
        self.assertEqual(
            infer_docs_root("https://alibaba.github.io/page-agent/docs/introduction/overview/"),
            "https://alibaba.github.io/page-agent/docs/",
        )

    def test_extract_nav_sections(self) -> None:
        html = """
        <aside>
          <nav>
            <section>
              <h3>介绍</h3>
              <ul>
                <li><a href="/page-agent/docs/introduction/overview">概览</a></li>
                <li><a href="/page-agent/docs/introduction/quick-start">快速开始</a></li>
              </ul>
            </section>
          </nav>
        </aside>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = extract_nav_sections(
            soup,
            "https://alibaba.github.io/page-agent/docs/introduction/overview/",
            "https://alibaba.github.io/page-agent/docs/",
        )
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].title, "介绍")
        self.assertEqual([item.title for item in sections[0].items], ["概览", "快速开始"])
        self.assertEqual(
            [item.url for item in sections[0].items],
            [
                "https://alibaba.github.io/page-agent/docs/introduction/overview",
                "https://alibaba.github.io/page-agent/docs/introduction/quick-start",
            ],
        )

    def test_extract_headings_and_markdown(self) -> None:
        html = """
        <article>
          <h1>Overview</h1>
          <p>hello <strong>world</strong> and <a href="/docs/x">link</a></p>
          <h2># 什么是 page-agent？</h2>
          <ul><li>能力 A</li><li>能力 B</li></ul>
          <pre><code class="language-bash">npm install page-agent</code></pre>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        headings = extract_headings(article)
        markdown = article_to_markdown(article, "https://example.com/base/")
        self.assertEqual([heading.text for heading in headings], ["Overview", "什么是 page-agent？"])
        self.assertIn("## 什么是 page-agent？", markdown)
        self.assertIn("hello **world** and [link](https://example.com/docs/x)", markdown)
        self.assertIn("- 能力 A", markdown)
        self.assertIn("```bash", markdown)

    def test_custom_div_code_block_renders_fenced_block(self) -> None:
        html = """
        <main>
          <div class="group relative">
            <div class="text-sm font-mono leading-6">
              <code><span>&lt;script src="DEMO_CDN_URL"&gt;&lt;/script&gt;</span></code>
            </div>
            <button title="复制代码">复制</button>
          </div>
          <div class="group relative">
            <div class="text-sm font-mono leading-6">
              <code><span>const agent = new PageAgent({\n  model: 'qwen3.5-plus'\n})</span></code>
            </div>
          </div>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        markdown = article_to_markdown(soup.main, "https://example.com/base/")
        self.assertIn("```html", markdown)
        self.assertIn('<script src="DEMO_CDN_URL"></script>', markdown)
        self.assertIn("```javascript", markdown)
        self.assertIn("const agent = new PageAgent({", markdown)

    def test_mermaid_output(self) -> None:
        html = """
        <aside>
          <nav>
            <section>
              <h3>高级</h3>
              <ul><li><a href="/docs/advanced/page-agent">PageAgent</a></li></ul>
            </section>
          </nav>
        </aside>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = extract_nav_sections(
            soup,
            "https://example.com/docs/introduction/overview",
            "https://example.com/docs/",
        )
        mermaid = render_nav_mermaid(sections)
        self.assertIn('docs["Docs"]', mermaid)
        self.assertIn('["高级"]', mermaid)
        self.assertIn('["PageAgent"]', mermaid)

    def test_summary_and_paths(self) -> None:
        html = """
        <aside>
          <nav>
            <section>
              <h3>介绍</h3>
              <ul><li><a href="/page-agent/docs/introduction/overview">概览</a></li></ul>
            </section>
          </nav>
        </aside>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = extract_nav_sections(
            soup,
            "https://alibaba.github.io/page-agent/docs/introduction/overview/",
            "https://alibaba.github.io/page-agent/docs/",
        )
        summary = render_summary(sections, "https://alibaba.github.io/page-agent/docs/")
        self.assertIn("[概览](introduction/overview.md)", summary)
        self.assertEqual(
            make_page_relative_path("https://alibaba.github.io/page-agent/docs/introduction/overview", "https://alibaba.github.io/page-agent/docs/").as_posix(),
            "introduction/overview.md",
        )

    def test_helpers(self) -> None:
        self.assertEqual(normalize_heading_text("# 标题"), "标题")
        self.assertEqual(canonicalize_url("https://example.com/docs/x/"), "https://example.com/docs/x")
        self.assertNotEqual(mermaid_node_id("介绍"), mermaid_node_id("高级"))
        self.assertEqual(trim_duplicate_title_heading("# 标题\n\n正文\n", "标题"), "正文\n")
        headings = extract_headings(BeautifulSoup("<article><h1>标题</h1><h2>小节</h2></article>", "html.parser").article)
        self.assertEqual([item.text for item in visible_outline(headings, "标题")], ["小节"])
        self.assertEqual(infer_project_name("https://alibaba.github.io/page-agent/docs/introduction/overview/"), "page-agent")
        self.assertEqual(
            resolve_output_dir(Path("output"), "page-agent").as_posix(),
            "output/page-agent",
        )


if __name__ == "__main__":
    unittest.main()
