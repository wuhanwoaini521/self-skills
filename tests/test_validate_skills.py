import pytest
import yaml

from tools.validate_skills import (
    find_skill_dirs,
    read_text_with_fallbacks,
    validate_all,
    validate_references,
    validate_skill_dir,
)


def openai_yaml_for(name):
    return (
        "interface:\n"
        f'  display_name: "Demo {name}"\n'
        '  short_description: "demo skill"\n'
        f'  default_prompt: "Use ${name}."\n'
        "policy:\n"
        "  allow_implicit_invocation: true\n"
    )


def write_skill(
    root,
    name,
    *,
    description="desc",
    openai_yaml=None,
    write_openai_yaml=True,
    body="# Skill\n",
    name_override=None,
):
    skill_dir = root / name
    (skill_dir / "agents").mkdir(parents=True, exist_ok=True)
    declared = name_override if name_override is not None else name
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {declared}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
    )
    if write_openai_yaml:
        content = openai_yaml if openai_yaml is not None else openai_yaml_for(declared)
        (skill_dir / "agents" / "openai.yaml").write_text(content, encoding="utf-8")
    return skill_dir


def test_valid_skill_has_no_errors(tmp_path):
    skill_dir = write_skill(tmp_path, "good-skill")

    assert validate_skill_dir(skill_dir) == []


def test_frontmatter_requires_name_and_description(tmp_path):
    skill_dir = write_skill(tmp_path, "bad-skill", description="")
    (skill_dir / "SKILL.md").write_text("---\nname: bad-skill\n---\n", encoding="utf-8")

    errors = validate_skill_dir(skill_dir)

    assert "missing description" in errors


def test_name_must_be_kebab_case(tmp_path):
    skill_dir = write_skill(tmp_path, "BadSkill", name_override="BadSkill")

    errors = validate_skill_dir(skill_dir)

    assert "name must be lowercase hyphen-case" in errors
    assert "directory name must be lowercase kebab-case" in errors


def test_directory_name_must_match_skill_name(tmp_path):
    skill_dir = write_skill(tmp_path, "crawl-docs", name_override="crawl-docs-to-markdown")

    errors = validate_skill_dir(skill_dir)

    assert "directory name 'crawl-docs' does not match skill name 'crawl-docs-to-markdown'" in errors


def test_missing_referenced_file_is_reported(tmp_path):
    skill_dir = write_skill(
        tmp_path,
        "doc-skill",
        body="See `references/testing.md` and `scripts/run.py`.\n",
    )

    errors = validate_skill_dir(skill_dir)

    assert "missing referenced file: references/testing.md" in errors
    assert "missing referenced file: scripts/run.py" in errors


def test_existing_referenced_file_passes(tmp_path):
    skill_dir = write_skill(tmp_path, "doc-skill", body="Read `references/testing.md`.\n")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "testing.md").write_text("# testing\n", encoding="utf-8")

    assert validate_references(skill_dir, (skill_dir / "SKILL.md").read_text(encoding="utf-8")) == []


def test_urls_and_output_paths_are_not_treated_as_references(tmp_path):
    content = "See https://example.com/scripts/run.py and `archive/generated/docs-export/report.md`.\n"

    assert validate_references(tmp_path, content) == []


def test_missing_agent_metadata_is_reported(tmp_path):
    skill_dir = write_skill(tmp_path, "no-agents", write_openai_yaml=False)

    assert "missing agents/openai.yaml" in validate_skill_dir(skill_dir)


def test_agent_metadata_must_mention_the_skill(tmp_path):
    skill_dir = write_skill(
        tmp_path,
        "demo-skill",
        openai_yaml=(
            "interface:\n"
            '  display_name: "Demo"\n'
            '  short_description: "demo"\n'
            '  default_prompt: "Use $other-skill."\n'
        ),
    )

    assert "agents/openai.yaml: interface.default_prompt should mention $demo-skill" in validate_skill_dir(skill_dir)


def test_agent_metadata_must_be_a_mapping(tmp_path):
    skill_dir = write_skill(tmp_path, "broken-skill", openai_yaml="- just\n- a list\n")

    assert "agents/openai.yaml must be a mapping" in validate_skill_dir(skill_dir)


def test_invalid_yaml_reports_an_error(tmp_path):
    skill_dir = write_skill(tmp_path, "broken-skill", openai_yaml="interface:\n  display_name: [unclosed\n")

    assert any("invalid agents/openai.yaml" in error for error in validate_skill_dir(skill_dir))


def test_validate_all_only_reports_failures(tmp_path):
    write_skill(tmp_path, "good-skill")
    write_skill(tmp_path, "bad-skill", write_openai_yaml=False)

    results = validate_all(tmp_path)

    assert set(results) == {"bad-skill"}



def test_read_text_with_fallbacks_supports_cp936(tmp_path):
    path = tmp_path / "skill.md"
    content = "---\nname: test-skill\ndescription: 中文说明\n---\n"
    path.write_bytes(content.encode("cp936"))

    assert read_text_with_fallbacks(path) == content


def test_repository_skills_and_registry_agree():
    from tools.registry import load_registry
    from tools.validate_skills import validate_registry

    entries = load_registry()

    assert validate_registry(entries) == []


def test_committed_index_matches_registry():
    from tools.list_skills import INDEX_FILE, render_index
    from tools.registry import load_registry

    assert INDEX_FILE.read_text(encoding="utf-8") == render_index(load_registry())


def test_registry_is_valid_yaml():
    from tools.registry import REGISTRY_FILE, read_text

    data = yaml.safe_load(read_text(REGISTRY_FILE))

    assert data["version"] == 1
    assert isinstance(data["skills"], list)
