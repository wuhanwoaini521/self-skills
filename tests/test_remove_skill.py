import pytest
import yaml

from tools.new_skill import create_skill
from tools.registry import STARTER_TEMPLATE, parse_registry
from tools.remove_skill import (
    RemoveError,
    entry_block,
    main,
    plan_remove,
    remove_registry_entry,
    set_entry_fields,
)
from tools.validate_skills import validate_registry

EMPTY_REGISTRY = "version: 1\n\nskills:\n"


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path
    registry_path = root / "registry" / "skills.yaml"
    registry_path.parent.mkdir()
    registry_path.write_text(EMPTY_REGISTRY, encoding="utf-8")
    skills_root = root / "skills"
    skills_root.mkdir()
    archive_root = root / "archive"
    archive_root.mkdir()
    return {
        "root": root,
        "registry": registry_path,
        "skills": skills_root,
        "archive": archive_root,
        "index": root / "skills-index.md",
    }


def make(workspace, name="demo-skill", **kwargs):
    return create_skill(
        name,
        skills_root=workspace["skills"],
        registry_path=workspace["registry"],
        template_dir=STARTER_TEMPLATE,
        repo_root=workspace["root"],
        **kwargs,
    )


def remove(workspace, name="demo-skill", **kwargs):
    return plan_remove(
        name,
        registry_path=workspace["registry"],
        repo_root=workspace["root"],
        index_path=workspace["index"],
        archive_root=workspace["archive"],
        **kwargs,
    )


def registry_data(workspace):
    return yaml.safe_load(workspace["registry"].read_text(encoding="utf-8"))


def index_text(workspace):
    return workspace["index"].read_text(encoding="utf-8") if workspace["index"].exists() else ""


# --------------------------------------------------------------------------- #
# archive (default)
# --------------------------------------------------------------------------- #


def test_archive_moves_the_directory_and_marks_the_entry(workspace):
    make(workspace)

    remove(workspace)

    assert not (workspace["skills"] / "demo-skill").exists()
    assert (workspace["archive"] / "demo-skill" / "SKILL.md").is_file()
    entry = registry_data(workspace)["skills"][0]
    assert entry["status"] == "archived"
    assert entry["path"] == "archive/demo-skill"


def test_archive_keeps_the_skill_content_intact(workspace):
    make(workspace)
    notes = workspace["skills"] / "demo-skill" / "references" / "notes.md"
    notes.write_text("keep me\n", encoding="utf-8")

    remove(workspace)

    archived = workspace["archive"] / "demo-skill" / "references" / "notes.md"
    assert archived.read_text(encoding="utf-8") == "keep me\n"


def test_archived_entry_still_validates_against_the_registry(workspace, monkeypatch):
    # validate_registry resolves entry paths against its own REPO_ROOT, so point
    # it at the temp workspace the way the real repo root would be used.
    monkeypatch.setattr("tools.validate_skills.REPO_ROOT", workspace["root"])
    make(workspace)

    remove(workspace)

    entries = parse_registry(registry_data(workspace))
    assert validate_registry(entries, workspace["skills"]) == []


def test_archived_skill_leaves_the_active_list(workspace):
    make(workspace)
    workspace["index"].write_text("stale\n", encoding="utf-8")

    remove(workspace)

    text = index_text(workspace)
    assert "archived" in text
    assert "| `demo-skill` | 0.1.0 | stable |" not in text


def test_archive_leaves_other_skills_alone(workspace):
    make(workspace, name="alpha")
    make(workspace, name="beta")

    remove(workspace, name="alpha")

    assert (workspace["skills"] / "beta" / "SKILL.md").is_file()
    assert {e["name"] for e in registry_data(workspace)["skills"]} == {"alpha", "beta"}


# --------------------------------------------------------------------------- #
# permanent delete
# --------------------------------------------------------------------------- #


def test_delete_removes_the_directory_and_the_entry(workspace):
    make(workspace)

    remove(workspace, delete=True)

    assert not (workspace["skills"] / "demo-skill").exists()
    assert not registry_data(workspace)["skills"]


def test_delete_refreshes_the_generated_index(workspace):
    make(workspace)
    workspace["index"].write_text("# Skills Index\n\n## Active Skills\n\n| `demo-skill` | 0.1.0 | stable |\n", encoding="utf-8")

    remove(workspace, delete=True)

    assert "demo-skill" not in index_text(workspace)


def test_delete_does_not_touch_the_archive(workspace):
    make(workspace)
    old = workspace["archive"] / "old-skill"
    old.mkdir()
    (old / "SKILL.md").write_text("archived\n", encoding="utf-8")

    remove(workspace, delete=True)

    assert (old / "SKILL.md").read_text(encoding="utf-8") == "archived\n"


# --------------------------------------------------------------------------- #
# dry run
# --------------------------------------------------------------------------- #


def test_dry_run_archive_writes_nothing(workspace):
    make(workspace)
    before = workspace["registry"].read_text(encoding="utf-8")
    workspace["index"].write_text("stale\n", encoding="utf-8")

    plan = remove(workspace, dry_run=True)

    assert (workspace["skills"] / "demo-skill").exists()
    assert not (workspace["archive"] / "demo-skill").exists()
    assert workspace["registry"].read_text(encoding="utf-8") == before
    assert index_text(workspace) == "stale\n"
    assert any(line.startswith("ARCHIVE") for line in plan)


def test_dry_run_delete_writes_nothing(workspace):
    make(workspace)
    before = workspace["registry"].read_text(encoding="utf-8")

    plan = remove(workspace, delete=True, dry_run=True)

    assert (workspace["skills"] / "demo-skill").exists()
    assert workspace["registry"].read_text(encoding="utf-8") == before
    assert any(line.startswith("DELETE") for line in plan)
    assert any(line.startswith("REMOVE") for line in plan)


def test_dry_run_plan_names_the_registry_and_the_index(workspace):
    make(workspace)

    plan = remove(workspace, dry_run=True)

    assert any("skills.yaml" in line for line in plan)
    assert any("skills-index.md" in line for line in plan)


# --------------------------------------------------------------------------- #
# safety
# --------------------------------------------------------------------------- #


def test_unknown_skill_is_rejected(workspace):
    with pytest.raises(RemoveError) as excinfo:
        remove(workspace, name="ghost")

    assert "not registered" in str(excinfo.value)


def test_missing_directory_is_reported_not_guessed(workspace):
    make(workspace)
    (workspace["skills"] / "demo-skill").rename(workspace["archive"] / "demo-skill")

    with pytest.raises(RemoveError) as excinfo:
        remove(workspace)

    message = str(excinfo.value)
    assert "directory is missing" in message
    assert "No changes were made" in message


def test_registry_path_outside_skills_is_rejected(workspace):
    make(workspace)
    text = workspace["registry"].read_text(encoding="utf-8")
    workspace["registry"].write_text(
        text.replace("path: skills/demo-skill", "path: elsewhere/demo-skill"), encoding="utf-8"
    )
    stray = workspace["root"] / "elsewhere" / "demo-skill"
    stray.mkdir(parents=True)
    (stray / "SKILL.md").write_text("x\n", encoding="utf-8")

    with pytest.raises(RemoveError) as excinfo:
        remove(workspace)

    assert "does not match its location" in str(excinfo.value)


def test_invalid_name_is_rejected(workspace):
    with pytest.raises(RemoveError) as excinfo:
        remove(workspace, name="Bad_Name")

    assert "invalid skill name" in str(excinfo.value)


def test_archive_collision_never_overwrites(workspace):
    make(workspace)
    existing = workspace["archive"] / "demo-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text("precious\n", encoding="utf-8")

    with pytest.raises(RemoveError) as excinfo:
        remove(workspace)

    assert "Archive destination already exists" in str(excinfo.value)
    assert (existing / "SKILL.md").read_text(encoding="utf-8") == "precious\n"
    assert (workspace["skills"] / "demo-skill").exists()


def test_archive_collision_blocks_the_dry_run_too(workspace):
    make(workspace)
    (workspace["archive"] / "demo-skill").mkdir()

    with pytest.raises(RemoveError):
        remove(workspace, dry_run=True)


# --------------------------------------------------------------------------- #
# registry text editing
# --------------------------------------------------------------------------- #


def test_entry_block_spans_only_its_own_entry():
    text = (
        "# header comment\n\n"
        "version: 1\n\n"
        "skills:\n"
        "  - name: alpha\n"
        "    path: skills/alpha\n"
        "    version: 1.0.0\n"
        "\n"
        "  - name: beta\n"
        "    path: skills/beta\n"
        "    version: 2.0.0\n"
    )

    start, end = entry_block(text.splitlines(), "alpha")

    assert text.splitlines()[start:end] == [
        "  - name: alpha",
        "    path: skills/alpha",
        "    version: 1.0.0",
    ]


def test_remove_registry_entry_keeps_comments_and_neighbours():
    text = (
        "# top comment\n\n"
        "version: 1\n\n"
        "skills:\n"
        "  - name: alpha\n"
        "    path: skills/alpha\n"
        "    version: 1.0.0\n"
        "\n"
        "  - name: beta\n"
        "    path: skills/beta\n"
        "    version: 2.0.0\n"
    )

    updated = remove_registry_entry(text, "alpha")

    assert "# top comment" in updated
    assert "alpha" not in updated
    assert "beta" in updated
    assert updated.endswith("\n")
    assert "\n\n\n" not in updated


def test_set_entry_fields_replaces_existing_keys():
    text = "skills:\n  - name: alpha\n    path: skills/alpha\n    status: stable\n"

    updated = set_entry_fields(text, "alpha", status="archived", path="archive/alpha")

    assert "status: archived" in updated
    assert "path: archive/alpha" in updated
    assert "status: stable" not in updated


def test_set_entry_fields_appends_a_missing_key():
    text = "skills:\n  - name: alpha\n    path: skills/alpha\n"

    updated = set_entry_fields(text, "alpha", status="archived")

    assert "status: archived" in updated


def test_editing_an_unknown_entry_raises():
    with pytest.raises(RemoveError):
        remove_registry_entry("skills:\n  - name: alpha\n", "ghost")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def test_cli_reports_failure_without_a_traceback(workspace, monkeypatch, capsys):
    monkeypatch.setattr("tools.remove_skill.REGISTRY_FILE", workspace["registry"])

    assert main(["Bad_Name"]) == 1
    assert "invalid skill name" in capsys.readouterr().out


def test_cli_dry_run_prints_a_plan(workspace, monkeypatch, capsys):
    make(workspace)
    monkeypatch.setattr("tools.remove_skill.REGISTRY_FILE", workspace["registry"])
    monkeypatch.setattr("tools.remove_skill.REPO_ROOT", workspace["root"])

    assert main(["demo-skill", "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "ARCHIVE" in output
    assert "dry run" in output
    assert (workspace["skills"] / "demo-skill").exists()
