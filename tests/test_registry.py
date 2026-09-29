import pytest

from tools.registry import (
    NAME_PATTERN,
    RegistryError,
    SkillEntry,
    discover_skill_dirs,
    entry_map,
    load_registry,
    parse_registry,
)

BASE_ENTRY = {
    "name": "demo-skill",
    "path": "skills/demo-skill",
    "version": "1.0.0",
    "status": "stable",
    "targets": ["codex"],
    "description": "Demo skill.",
}


def registry(*entries):
    return {"version": 1, "skills": list(entries)}


def test_parses_a_valid_registry():
    entries = parse_registry(registry(BASE_ENTRY))

    assert entries == [SkillEntry(**{**BASE_ENTRY, "targets": ("codex",)})]
    assert entries[0].syncable is True
    assert entries[0].archived is False
    assert entries[0].serves("codex") is True
    assert entries[0].serves("claude") is False


def test_archived_skills_are_not_syncable_by_default():
    entries = parse_registry(registry({**BASE_ENTRY, "status": "archived"}))

    assert entries[0].archived is True
    assert entries[0].syncable is False


def test_deprecated_skills_are_still_syncable():
    entries = parse_registry(registry({**BASE_ENTRY, "status": "deprecated"}))

    assert entries[0].syncable is True


@pytest.mark.parametrize("field", ["name", "path", "version", "status", "targets", "description"])
def test_missing_required_field_is_reported(field):
    payload = {key: value for key, value in BASE_ENTRY.items() if key != field}

    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry(payload))

    assert f"skills[0].{field}" in str(excinfo.value)


def test_invalid_status_lists_the_allowed_values():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry({**BASE_ENTRY, "status": "prod"}))

    message = str(excinfo.value)
    assert "'prod' is not supported" in message
    for status in ("experimental", "beta", "stable", "deprecated", "archived"):
        assert status in message


def test_invalid_version_is_reported():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry({**BASE_ENTRY, "version": "1.0"}))

    assert "is not MAJOR.MINOR.PATCH" in str(excinfo.value)


def test_unknown_target_is_reported():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry({**BASE_ENTRY, "targets": ["emacs"]}))

    assert "unknown target 'emacs'" in str(excinfo.value)


def test_duplicate_names_are_reported():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry(BASE_ENTRY, {**BASE_ENTRY, "path": "skills/other"}))

    assert "duplicate name 'demo-skill'" in str(excinfo.value)


def test_duplicate_paths_are_reported():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry(BASE_ENTRY, {**BASE_ENTRY, "name": "other-skill"}))

    assert "duplicate path 'skills/demo-skill'" in str(excinfo.value)


def test_unknown_field_is_reported():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(registry({**BASE_ENTRY, "colour": "blue"}))

    assert "unknown fields: colour" in str(excinfo.value)


def test_wrong_version_number_is_reported():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry({"version": 2, "skills": []})

    assert "expected 1" in str(excinfo.value)


def test_root_must_be_a_mapping():
    with pytest.raises(RegistryError) as excinfo:
        parse_registry(["demo-skill"])

    assert "root must be a mapping" in str(excinfo.value)


def test_missing_registry_file_reports_the_path(tmp_path):
    with pytest.raises(RegistryError) as excinfo:
        load_registry(tmp_path / "nope.yaml")

    assert "registry not found" in str(excinfo.value)


def test_broken_yaml_reports_the_path(tmp_path):
    path = tmp_path / "skills.yaml"
    path.write_text("version: 1\nskills: [\n", encoding="utf-8")

    with pytest.raises(RegistryError) as excinfo:
        load_registry(path)

    assert "invalid registry" in str(excinfo.value)


@pytest.mark.parametrize("name", ["crawl_docs", "crawl--docs", "-leading", "trailing-", "Crawl", "docs skill", ""])
def test_name_pattern_rejects_non_kebab_case(name):
    assert not NAME_PATTERN.fullmatch(name)


def test_entry_map_indexes_by_name():
    entries = parse_registry(registry(BASE_ENTRY, {**BASE_ENTRY, "name": "other", "path": "skills/other"}))

    assert set(entry_map(entries)) == {"demo-skill", "other"}


def test_discover_skill_dirs_ignores_directories_without_skill_md(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "SKILL.md").write_text("---\nname: real\n---\n", encoding="utf-8")
    (tmp_path / "empty").mkdir()

    assert [path.name for path in discover_skill_dirs(tmp_path)] == ["real"]


def test_committed_registry_loads():
    entries = load_registry()

    assert {entry.name for entry in entries} == {
        "crawl-docs-to-markdown",
        "github-trending-report",
        "project-delivery",
    }
