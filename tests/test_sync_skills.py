import json

import pytest

from tools.registry import SkillEntry
from tools.sync_skills import (
    SyncError,
    deploy,
    fingerprint,
    load_state,
    main,
    select_entries,
    sync_target,
)


def make_entry(name, tmp_path, *, status="stable", targets=("codex",), body="v1"):
    source = tmp_path / "skills" / name
    (source / "references").mkdir(parents=True, exist_ok=True)
    (source / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {body}\n---\n", encoding="utf-8")
    (source / "references" / "notes.md").write_text(f"{body}\n", encoding="utf-8")
    return SkillEntry(
        name=name,
        path=f"skills/{name}",
        version="1.0.0",
        status=status,
        targets=targets,
        description=body,
    )


@pytest.fixture
def workspace(tmp_path):
    target = tmp_path / "agent" / "skills"
    target.mkdir(parents=True)
    return {"root": tmp_path, "target": target, "state": tmp_path / "state.json"}


def run(workspace, entries, **kwargs):
    kwargs.setdefault("override", workspace["target"])
    kwargs.setdefault("state_path", workspace["state"])
    kwargs.setdefault("repo_root", workspace["root"])
    return sync_target("codex", entries, **kwargs)


def test_deploys_a_new_skill(workspace):
    entry = make_entry("alpha", workspace["root"])

    result = run(workspace, [entry])

    assert [item.action for item in result.items] == ["ADD"]
    assert (workspace["target"] / "alpha" / "SKILL.md").is_file()
    assert (workspace["target"] / "alpha" / "references" / "notes.md").is_file()
    assert result.errors == []


def test_second_run_is_idempotent(workspace):
    entry = make_entry("alpha", workspace["root"])
    run(workspace, [entry])

    result = run(workspace, [entry])

    assert [item.action for item in result.items] == ["SKIP"]


def test_changed_content_is_an_update(workspace):
    entry = make_entry("alpha", workspace["root"])
    run(workspace, [entry])
    make_entry("alpha", workspace["root"], body="v2")

    result = run(workspace, [entry])

    assert [item.action for item in result.items] == ["UPDATE"]
    assert "v2" in (workspace["target"] / "alpha" / "SKILL.md").read_text(encoding="utf-8")


def test_update_removes_files_deleted_in_the_source(workspace):
    entry = make_entry("alpha", workspace["root"])
    run(workspace, [entry])
    (workspace["root"] / "skills" / "alpha" / "references" / "notes.md").unlink()

    run(workspace, [entry])

    assert not (workspace["target"] / "alpha" / "references" / "notes.md").exists()


def test_dry_run_writes_nothing(workspace):
    entry = make_entry("alpha", workspace["root"])

    result = run(workspace, [entry], dry_run=True)

    assert [item.action for item in result.items] == ["ADD"]
    assert not (workspace["target"] / "alpha").exists()
    assert not workspace["state"].exists()


def test_single_skill_sync(workspace):
    alpha = make_entry("alpha", workspace["root"])
    beta = make_entry("beta", workspace["root"])

    run(workspace, [alpha, beta], skill_names=["beta"])

    assert (workspace["target"] / "beta").is_dir()
    assert not (workspace["target"] / "alpha").exists()


def test_unknown_skill_name_is_rejected(workspace):
    entry = make_entry("alpha", workspace["root"])

    with pytest.raises(SyncError) as excinfo:
        run(workspace, [entry], skill_names=["ghost"])

    assert "unknown skill(s): ghost" in str(excinfo.value)


def test_skills_not_registered_for_the_target_are_not_deployed(workspace):
    entry = make_entry("alpha", workspace["root"], targets=("claude",))

    result = run(workspace, [entry])

    assert result.items == []


def test_archived_skills_are_skipped_unless_requested(workspace):
    entry = make_entry("alpha", workspace["root"], status="archived")

    assert run(workspace, [entry]).items == []
    assert [item.action for item in run(workspace, [entry], include_archived=True).items] == ["ADD"]


def test_unknown_skills_in_the_target_are_never_touched(workspace):
    third_party = workspace["target"] / "third-party-skill"
    third_party.mkdir()
    (third_party / "SKILL.md").write_text("do not touch\n", encoding="utf-8")
    entry = make_entry("alpha", workspace["root"])

    run(workspace, [entry])

    assert (third_party / "SKILL.md").read_text(encoding="utf-8") == "do not touch\n"


def test_prune_only_removes_previously_managed_skills(workspace):
    alpha = make_entry("alpha", workspace["root"])
    run(workspace, [alpha])
    keep = workspace["target"] / "manual-skill"
    keep.mkdir()
    (keep / "SKILL.md").write_text("manual\n", encoding="utf-8")

    result = run(workspace, [], prune=True)

    assert [item.name for item in result.items] == ["alpha"]
    assert not (workspace["target"] / "alpha").exists()
    assert keep.exists()


def test_state_file_tracks_deployed_skills(workspace):
    entry = make_entry("alpha", workspace["root"])

    run(workspace, [entry])

    state = json.loads(workspace["state"].read_text(encoding="utf-8"))
    assert state["targets"]["codex"]["skills"]["alpha"]["version"] == "1.0.0"
    assert state["targets"]["codex"]["path"] == str(workspace["target"])


def test_build_excludes_cache_and_build_artifacts(workspace):
    entry = make_entry("alpha", workspace["root"])
    source = workspace["root"] / entry.path
    (source / "scripts" / "__pycache__").mkdir(parents=True)
    (source / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    (source / "dist").mkdir()
    (source / "dist" / "bundle.zip").write_bytes(b"PK")

    run(workspace, [entry])

    deployed = workspace["target"] / "alpha"
    assert not (deployed / "dist").exists()
    assert not (deployed / "scripts" / "__pycache__").exists()
    assert fingerprint(source) == fingerprint(deployed)


def test_symlink_mode_links_to_the_source(workspace):
    entry = make_entry("alpha", workspace["root"])
    try:
        run(workspace, [entry], mode="symlink")
    except SyncError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    deployed = workspace["target"] / "alpha"
    assert deployed.is_symlink()
    assert deployed.resolve() == (workspace["root"] / entry.path).resolve()
    assert [item.action for item in run(workspace, [entry], mode="symlink").items] == ["SKIP"]


def test_deploy_replaces_a_stale_symlink(workspace, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("new\n", encoding="utf-8")
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "SKILL.md").write_text("old\n", encoding="utf-8")

    deploy(source, destination, "copy")

    assert (destination / "SKILL.md").read_text(encoding="utf-8") == "new\n"


def test_deploy_leaves_no_temporary_directories(workspace):
    entry = make_entry("alpha", workspace["root"])
    run(workspace, [entry])
    make_entry("alpha", workspace["root"], body="v2")
    run(workspace, [entry])

    assert [path.name for path in workspace["target"].iterdir()] == ["alpha"]


def test_target_path_is_not_created_silently_for_unverified_targets(workspace, tmp_path):
    entry = make_entry("alpha", workspace["root"])

    result = sync_target("pi", [entry], state_path=workspace["state"])

    assert result.path is None
    assert result.state == "unverified"
    assert not (tmp_path / "pi-skills").exists()


def test_explicit_target_path_is_used(workspace, tmp_path):
    entry = make_entry("alpha", workspace["root"])
    explicit = tmp_path / "custom" / "skills"

    result = sync_target(
        "codex",
        [entry],
        override=explicit,
        state_path=workspace["state"],
        repo_root=workspace["root"],
    )

    assert result.path == explicit
    assert (explicit / "alpha" / "SKILL.md").is_file()


def test_select_entries_filters_by_target_and_status():
    entries = [
        SkillEntry("a", "skills/a", "1.0.0", "stable", ("codex",), "a"),
        SkillEntry("b", "skills/b", "1.0.0", "archived", ("codex",), "b"),
        SkillEntry("c", "skills/c", "1.0.0", "beta", ("claude",), "c"),
    ]

    assert [entry.name for entry in select_entries(entries, "codex")] == ["a"]
    assert [entry.name for entry in select_entries(entries, "codex", include_archived=True)] == ["a", "b"]


def test_load_state_tolerates_a_corrupt_file(workspace):
    workspace["state"].write_text("not json", encoding="utf-8")

    assert load_state(workspace["state"]) == {"version": 1, "targets": {}}


def test_cli_requires_a_target(capsys):
    assert main([]) == 2
    assert "available targets" in capsys.readouterr().out


def test_cli_rejects_target_with_all(capsys):
    assert main(["--target", "codex", "--all"]) == 2
    assert "mutually exclusive" in capsys.readouterr().out


def test_cli_rejects_target_path_with_all(capsys):
    assert main(["--all", "--target-path", "/tmp/x"]) == 2
    assert "--target-path requires exactly one --target" in capsys.readouterr().out


def test_cli_rejects_an_unknown_target(capsys):
    with pytest.raises(SystemExit):
        main(["--target", "emacs"])


def test_cli_dry_run_prints_actions(capsys, monkeypatch, workspace):
    entry = make_entry("alpha", workspace["root"])
    monkeypatch.setattr("tools.sync_skills.load_registry", lambda: [entry])
    monkeypatch.setattr("tools.sync_skills.REPO_ROOT", workspace["root"])
    monkeypatch.setattr("tools.sync_skills.STATE_FILE", workspace["state"])

    assert main(["--target", "codex", "--target-path", str(workspace["target"]), "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "ADD" in output
    assert "dry run" in output
    assert not (workspace["target"] / "alpha").exists()
    assert not workspace["state"].exists()
