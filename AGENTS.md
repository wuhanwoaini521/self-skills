# Repository Guidelines

## Project Structure & Module Organization

This repository is a documentation-first workspace for learning how to create skills while keeping reusable skills ready to copy out. Keep the root clean and group content by purpose.

- `docs/`: learning notes, walkthroughs, examples, and diagrams
- `skills/`: complete, reusable skills; each folder can be copied into another tool's skills directory
- `templates/`: starter scaffold for new skills
- `tools/`: helper scripts such as validation or local generators
- `tests/`: unit tests for `tools/`
- `archive/`: generated artifacts and historical outputs; do not treat as source

When adding new material, prefer writing docs first, then attach a runnable skill under `skills/<skill-name>/`.

## Build, Test, and Development Commands

Use PowerShell from the repository root.

- `python -m pytest`
  Runs the full test suite.
- `python -m pytest tests\test_github_trending_report.py`
  Runs a focused test file during iteration.
- `python tools\validate_skills.py`
  Validates all skill folders under `skills/`.
- `python skills\github-trending-report\scripts\generate_report.py --date 2026-04-10`
  Generates a sample trending report.
- `python skills\github-trending-report\scripts\package_skill.py --inline-json`
  Builds a zip and inline JSON payload for that skill.

## Coding Style & Naming Conventions

Use Python with 4-space indentation, type hints, and small, composable functions. Prefer `Path` over hard-coded paths and keep file writes UTF-8. Use snake_case for Python files and identifiers; use lowercase hyphen-case for skill or template directories such as `github-trending-report`.

## Testing Guidelines

Tests use `pytest` with `unittest`-style test cases. Place new tests in `tests/` and name them `test_<feature>.py`. Add or update tests for behavior changes, especially parsing, output structure, and skill validation. Prefer targeted parser/render tests over large network-dependent tests.

## Commit & Pull Request Guidelines

Git history is currently minimal and only shows `init`, so use short, imperative commit subjects such as `restructure docs layout` or `add skill starter template`. Keep each commit scoped to one logical change.

For pull requests, include:

- a short summary of what changed
- affected paths, for example `skills/github-trending-report/`
- validation steps and commands run
- sample output screenshots only when UI or rendered Markdown changed

## Security & Generated Files

Do not commit secrets, tokens, or private URLs. Avoid inventing paths or config. Generated artifacts belong under `archive/` or an example skill’s `dist/` directory, not mixed into docs or source folders.
