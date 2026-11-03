"""H4: weeks 1 to 8 are the final exam; the final score comes from committed code, logged."""
import csv
import importlib.util

import pandas as pd
import pytest

from vn2 import config
from vn2.guards import LookAheadError, git_tree_is_clean, require_history_only
from vn2.report import append_final_run


def test_history_weeks_are_allowed():
    require_history_only("2023-06-05")
    require_history_only(config.LAST_HISTORY_WEEK)


def test_test_weeks_are_refused_for_tuning():
    with pytest.raises(LookAheadError):
        require_history_only(config.FIRST_TEST_WEEK)
    with pytest.raises(LookAheadError):
        require_history_only(config.LAST_HISTORY_WEEK + pd.Timedelta(weeks=8))


def test_a_clean_tree_is_recognised():
    assert git_tree_is_clean("")
    assert git_tree_is_clean("\n")
    assert not git_tree_is_clean(" M vn2/data.py\n")
    assert not git_tree_is_clean("?? notes.txt\n")


def load_final_score_script():
    path = config.REPO / "scripts" / "final_score.py"
    spec = importlib.util.spec_from_file_location("final_score", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_final_score_refuses_uncommitted_changes(tmp_path):
    final_score = load_final_score_script()
    log = tmp_path / "final_runs.csv"
    with pytest.raises(SystemExit):
        final_score.run_final("vn2_benchmark.py", git_status=" M vn2/data.py\n", log_path=log)
    assert not log.exists()


def test_the_final_score_logs_every_run(tmp_path):
    final_score = load_final_score_script()
    log = tmp_path / "final_runs.csv"
    policy = config.REPO / "vn2_benchmark.py"
    for _ in range(2):
        assert final_score.run_final(policy, git_status="", log_path=log) == config.BENCHMARK_SCORE
    rows = list(csv.DictReader(log.open()))
    assert len(rows) == 2
    assert rows[0]["policy"] == "vn2_benchmark.py" and float(rows[1]["score"]) == 4334.0


def test_the_log_only_grows(tmp_path):
    log = tmp_path / "final_runs.csv"
    row = {"timestamp": "t", "commit": "c", "policy": "p", "setup": 1.0, "score": 2.0}
    append_final_run(log, row)
    append_final_run(log, {**row, "score": 3.0})
    assert [r["score"] for r in csv.DictReader(log.open())] == ["2.0", "3.0"]
