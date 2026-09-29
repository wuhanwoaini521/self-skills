import pytest
import yaml

from tools.new_skill import CreateError, append_registry_entry, create_skill, main
from tools.registry import STARTER_TEMPLATE
from tools.validate_skills import validate_skill_dir

EMPTY_REGISTRY = "version: 1\n\nskills:\n"


@pytest.fixture
def workspace(tmp_path):
    registry_path = tmp_path / "registry" / "skills.yaml"
    registry_path.parent.mkdir()
    registry_path.write_text(EMPTY_REGISTRY, encoding="utf-8")
    root = tmp_path
    skills_root = root / "skills"
    skills_root.mkdir()
    return {"root": root, "registry": registry_path, "skills": skills_root}


def make(workspace, name="project-delivery", **kwargs):
    return create_skill(
        name,
        skills_root=workspace["skills"],
        registry_path=workspace["registry"],
        template_dir=STARTER_TEMPLATE,
        repo_root=workspace["root"],
        **kwargs,
    )


def test_creates_a_valid_skill_skeleton(workspace):
    entry = make(workspace, description="Ship projects on time.")

    skill_dir = workspace["skills"] / "project-delivery"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "agents" / "openai.yaml").is_file()
    assert (skill_dir / "references").is_dir()
    assert (skill_dir / "scripts").is_dir()
    assert entry.version == "0.1.0"
    assert entry.status == "experimental"
    assert entry.targets == ("codex",)
    assert entry.path == "skills/project-delivery"


def test_rendered_frontmatter_matches_the_registry_entry(workspace):
    entry = make(workspace, description="Ship projects on time.")

    content = (workspace["skills"] / "project-delivery" / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(content.split("---")[1])

    assert frontmatter["name"] == entry.name
    assert frontmatter["description"] == "Ship projects on time."


def test_created_skill_passes_validation(workspace):
    make(workspace, description="Ship projects on time.")

    assert validate_skill_dir(workspace["skills"] / "project-delivery") == []


def test_registers_the_skill_by_default(workspace):
    make(workspace)

    data = yaml.safe_load(workspace["registry"].read_text(encoding="utf-8"))

    assert [entry["name"] for entry in data["skills"]] == ["project-delivery"]
    assert data["skills"][0]["status"] == "experimental"
    assert data["skills"][0]["version"] == "0.1.0"


def test_no_registry_leaves_the_registry_untouched(workspace):
    make(workspace, write_registry=False)

    assert workspace["registry"].read_text(encoding="utf-8") == EMPTY_REGISTRY


def test_dry_run_writes_nothing(workspace):
    before = workspace["registry"].read_text(encoding="utf-8")

    entry = make(workspace, dry_run=True)

    assert entry.name == "project-delivery"
    assert not (workspace["skills"] / "project-delivery").exists()
    assert workspace["registry"].read_text(encoding="utf-8") == before


def test_refuses_to_overwrite_an_existing_directory(workspace):
    (workspace["skills"] / "project-delivery").mkdir()

    with pytest.raises(CreateError) as excinfo:
        make(workspace)

    assert "already exists" in str(excinfo.value)


def test_refuses_a_name_already_in_the_registry(workspace):
    workspace["registry"].write_text(
        EMPTY_REGISTRY
        + "  - name: project-delivery\n"
        "    path: archive/project-delivery\n"
        "    version: 0.0.1\n"
        "    status: archived\n"
        "    targets: []\n"
        "    description: old\n",
        encoding="utf-8",
    )

    with pytest.raises(CreateError) as excinfo:
        make(workspace)

    assert "already registered" in str(excinfo.value)


@pytest.mark.parametrize("name", ["Project_Delivery", "project delivery", "project_delivery", "-bad"])
def test_rejects_names_that_are_not_kebab_case(workspace, name):
    with pytest.raises(CreateError) as excinfo:
        make(workspace, name=name)

    assert "invalid skill name" in str(excinfo.value)


def test_rejects_an_unknown_target(workspace):
    with pytest.raises(CreateError) as excinfo:
        make(workspace, targets=["emacs"])

    assert "unknown target(s): emacs" in str(excinfo.value)


def test_rejects_an_unsupported_status(workspace):
    with pytest.raises(CreateError) as excinfo:
        make(workspace, status="prod")

    assert "invalid status" in str(excinfo.value)


def test_append_registry_entry_keeps_existing_comments(tmp_path):
    from tools.registry import SkillEntry

    path = tmp_path / "skills.yaml"
    path.write_text("# a comment\nversion: 1\n\nskills:\n", encoding="utf-8")
    entry = SkillEntry(
        name="demo",
        path="skills/demo",
        version="0.1.0",
        status="experimental",
        targets=("codex",),
        description="Demo.",
    )

    updated = append_registry_entry(entry, path)

    assert "# a comment" in updated
    assert yaml.safe_load(updated)["skills"][0]["name"] == "demo"


def test_cli_reports_failure_without_a_traceback(workspace, monkeypatch, capsys):
    monkeypatch.setattr("tools.new_skill.REGISTRY_FILE", workspace["registry"])
    monkeypatch.setattr("tools.new_skill.SKILLS_ROOT", workspace["skills"])

    assert main(["Bad_Name"]) == 1
    assert "invalid skill name" in capsys.readouterr().out


def test_cli_dry_run_prints_a_plan(monkeypatch, capsys, workspace):
    monkeypatch.setattr("tools.new_skill.REGISTRY_FILE", workspace["registry"])
    monkeypatch.setattr("tools.new_skill.SKILLS_ROOT", workspace["skills"])

    assert main(["project-delivery", "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "would create" in output
    assert not (workspace["skills"] / "project-delivery").exists()
