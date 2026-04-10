import unittest

from tools.github_trending_report import (
    RepoSummary,
    build_mermaid,
    extract_readme_headings,
    extract_readme_intro,
    find_workflow_hints,
    parse_trending_page,
    render_report,
)
from bs4 import BeautifulSoup


class GitHubTrendingReportTests(unittest.TestCase):
    def test_parse_trending_page(self) -> None:
        html = """
        <article class="Box-row">
          <h2><a href="/owner-one/repo-one">owner-one / repo-one</a></h2>
          <p>Project description.</p>
          <span itemprop="programmingLanguage">Python</span>
          <a class="Link--muted">1,234</a>
          <a class="Link--muted">56</a>
          <span>789 stars today</span>
        </article>
        """
        repos = parse_trending_page(html, since="daily", max_items=10)
        self.assertEqual(len(repos), 1)
        repo = repos[0]
        self.assertEqual(repo.owner, "owner-one")
        self.assertEqual(repo.name, "repo-one")
        self.assertEqual(repo.description, "Project description.")
        self.assertEqual(repo.language, "Python")
        self.assertEqual(repo.stars, "1,234")
        self.assertEqual(repo.forks, "56")
        self.assertEqual(repo.trending_stars, "789")

    def test_extract_readme_bits(self) -> None:
        soup = BeautifulSoup(
            """
            <article class="markdown-body">
              <h1>Repo Title</h1>
              <h2>Quick Start</h2>
              <p>This project helps teams move from idea to release with a guided setup workflow.</p>
              <h2>Architecture</h2>
              <p>It includes an API layer, a worker layer, and a UI layer for orchestration.</p>
            </article>
            """,
            "html.parser",
        )
        readme = soup.select_one("article")
        self.assertEqual(extract_readme_headings(readme), ["Repo Title", "Quick Start", "Architecture"])
        self.assertEqual(
            extract_readme_intro(readme),
            [
                "This project helps teams move from idea to release with a guided setup workflow.",
                "It includes an API layer, a worker layer, and a UI layer for orchestration.",
            ],
        )

    def test_workflow_hints_and_mermaid(self) -> None:
        repo = RepoSummary(
            since="weekly",
            rank=1,
            owner="owner",
            name="repo",
            url="https://github.com/owner/repo",
            description="An automation agent for developers.",
            readme_headings=["Quick Start", "Core Features", "Architecture"],
            readme_intro=["This project defines a workflow for local automation."],
            topics=["automation", "agent"],
        )
        hints = find_workflow_hints(repo.readme_headings, repo.readme_intro)
        self.assertEqual(hints, ["Quick Start", "Core Features", "Architecture", "This project defines a workflow for local automation."])
        mermaid = build_mermaid(repo)
        self.assertIn('"theme": "base"', mermaid)
        self.assertIn('\\"Press Start 2P\\", \\"Courier New\\", monospace', mermaid)
        self.assertIn("flowchart LR", mermaid)
        self.assertIn('repo["owner/repo"]', mermaid)
        self.assertIn("classDef punch", mermaid)

    def test_render_report(self) -> None:
        repo = RepoSummary(
            since="monthly",
            rank=1,
            owner="owner",
            name="repo",
            url="https://github.com/owner/repo",
            description="A sample project.",
            language="TypeScript",
            stars="100",
            forks="20",
            trending_stars="50",
            topics=["demo"],
            readme_headings=["Quick Start"],
            readme_intro=["A sample README summary paragraph that is long enough to keep."],
            zh_explanation="中文说明。",
            en_explanation="English explanation.",
            generated_mermaid='flowchart LR\nrepo["owner/repo"] --> quick["Quick Start"]',
        )
        report = render_report("2026-04-10", {"daily": [], "weekly": [], "monthly": [repo]}, detail_limit=1)
        self.assertIn("# GitHub Trending Report (2026-04-10)", report)
        self.assertIn("## 每月 Trending", report)
        self.assertIn("中文说明。", report)
        self.assertIn("```mermaid", report)


if __name__ == "__main__":
    unittest.main()
