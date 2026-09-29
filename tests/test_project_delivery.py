import pytest
from conftest import load_skill_module

init_run_log = load_skill_module(
    "skills/project-delivery/scripts/init_run_log.py", "project_delivery_init_run_log"
)


def create(tmp_path, **kwargs):
    params = {
        "task_type": "bug-fix",
        "title": "pagination fails on page 3",
        "runs_dir": tmp_path / ".ai-runs",
        "day": "2026-09-29",
    }
    params.update(kwargs)
    return init_run_log.create_run_log(**params)


def names(run_dir):
    return sorted(path.name for path in run_dir.iterdir())


def test_standard_task_logs_every_stage_but_ui_review(tmp_path):
    run_dir = create(tmp_path)

    assert names(run_dir) == [
        "00-request.md",
        "01-analysis.md",
        "02-plan.md",
        "03-implementation.md",
        "04-functional-test.md",
        "06-code-review.md",
        "07-fixes.md",
        "08-regression.md",
        "09-final-report.md",
    ]


def test_ui_task_adds_ui_review(tmp_path):
    run_dir = create(tmp_path, task_type="ui-redesign", title="history redesign")

    assert "05-ui-review.md" in names(run_dir)
    assert len(names(run_dir)) == len(init_run_log.FULL_STAGES)


def test_ui_feature_task_adds_ui_review(tmp_path):
    run_dir = create(tmp_path, task_type="ui-feature", title="filter dialog")

    assert "05-ui-review.md" in names(run_dir)


def test_small_scale_keeps_request_analysis_and_final_report(tmp_path):
    run_dir = create(tmp_path, scale="small", title="typo in README")

    assert names(run_dir) == ["00-request.md", "01-analysis.md", "09-final-report.md"]


def test_single_file_mode_writes_one_run_file(tmp_path):
    run_dir = create(tmp_path, single_file=True, title="fix a comment")

    assert names(run_dir) == ["run.md"]


def test_request_file_carries_run_metadata(tmp_path):
    run_dir = create(tmp_path, title="pagination fails on page 3")
    content = (run_dir / "00-request.md").read_text(encoding="utf-8")

    assert "run-date: 2026-09-29" in content
    assert "task-type: bug-fix" in content
    assert "Original Request" in content


def test_duplicate_run_name_gets_a_suffix_and_keeps_the_original(tmp_path):
    first = create(tmp_path, title="history redesign", task_type="ui-redesign")
    marker = first / "00-request.md"
    marker.write_text("kept", encoding="utf-8")

    second = create(tmp_path, title="history redesign", task_type="ui-redesign")
    third = create(tmp_path, title="history redesign", task_type="ui-redesign")

    assert first.name == "2026-09-29-history-redesign"
    assert second.name == "2026-09-29-history-redesign-2"
    assert third.name == "2026-09-29-history-redesign-3"
    assert marker.read_text(encoding="utf-8") == "kept"


def test_dry_run_writes_nothing(tmp_path):
    runs_dir = tmp_path / ".ai-runs"
    run_dir = create(tmp_path, dry_run=True, runs_dir=runs_dir)

    assert run_dir.name == "2026-09-29-pagination-fails-on-page-3"
    assert not runs_dir.exists()


def test_invalid_task_type_is_rejected(tmp_path):
    with pytest.raises(init_run_log.RunLogError) as excinfo:
        create(tmp_path, task_type="architecture")

    assert "invalid task type: 'architecture'" in str(excinfo.value)


def test_invalid_date_is_rejected(tmp_path):
    with pytest.raises(init_run_log.RunLogError) as excinfo:
        create(tmp_path, day="2026/09/29")

    assert "invalid date" in str(excinfo.value)


def test_empty_title_falls_back_to_the_task_type(tmp_path):
    run_dir = create(tmp_path, title="   ")

    assert run_dir.name == "2026-09-29-bug-fix"


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("History Redesign", "history-redesign"),
        ("修复分页 bug", "bug"),
        ("a  b__c--d", "a-b-c-d"),
    ],
)
def test_slugify(title, slug):
    assert init_run_log.slugify(title) == slug


def test_cli_prints_the_created_directory(tmp_path, capsys):
    runs_dir = tmp_path / ".ai-runs"
    exit_code = init_run_log.main(
        [
            "--task-type",
            "maintenance",
            "--title",
            "upgrade playwright",
            "--runs-dir",
            str(runs_dir),
            "--date",
            "2026-09-29",
        ]
    )

    assert exit_code == 0
    assert "2026-09-29-upgrade-playwright" in capsys.readouterr().out
    assert (runs_dir / "2026-09-29-upgrade-playwright" / "00-request.md").exists()


def test_cli_reports_an_invalid_task_type_without_a_traceback(capsys):
    exit_code = init_run_log.main(["--task-type", "release", "--title", "ship it"])

    assert exit_code == 1
    assert "invalid task type: 'release'" in capsys.readouterr().err
