"""Architecture rules, checked by reading the source code (hard rules H3, H4 and H11).

- Only vn2/data.py reads the competition files; everything else goes through `as_of`
  (the t0 script reads only the cleaned CSV, which holds weeks up to week 0).
- Only scripts/final_score.py may load the demand of weeks 1 to 8 (vn2_simulate.load) or use
  vn2_play; nothing in the project may name a test week or a test file.
- No Seeker licence file is ever tracked by git.
"""
import ast
import re
import subprocess

import pandas as pd
import pytest

from vn2 import config

PROJECT_FILES = sorted(
    path for folder in ("vn2", "scripts", "forecasting")
    for path in (config.REPO / folder).rglob("*.py"))
FINAL_SCORE = config.REPO / "scripts" / "final_score.py"
# vn2/data.py reads the competition files; the t0 script reads only the cleaned CSV, whose
# content is pinned by tests/test_t0_forecast_inputs.py (history up to week 0).
DATA_READERS = {config.REPO / "vn2" / "data.py", config.REPO / "forecasting" / "t0_forecast.py"}
FILE_READERS = {"read_csv", "read_table", "read_parquet", "read_excel"}


def names_used(path):
    """Every imported name and every called function or attribute name in a file."""
    tree = ast.parse(path.read_text())
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            used.add(node.module or "")
            used.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            used.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
            if isinstance(node.value, ast.Name):
                used.add(f"{node.value.id}.{node.attr}")
        elif isinstance(node, ast.Name):
            used.add(node.id)
    return used


def relative(path):
    return path.relative_to(config.REPO).as_posix()


@pytest.mark.parametrize("path", PROJECT_FILES, ids=relative)
def test_only_the_final_score_touches_the_test_demand(path):
    if path == FINAL_SCORE:
        return
    used = names_used(path)
    assert "vn2_simulate.load" not in used, "vn2_simulate.load reads the demand of weeks 1 to 8."
    assert "vn2_play" not in used, "vn2_play plays the test weeks."


@pytest.mark.parametrize("path", PROJECT_FILES, ids=relative)
def test_only_the_data_module_reads_files(path):
    if path in DATA_READERS:
        return
    readers = FILE_READERS & names_used(path)
    assert not readers, f"Read data through vn2.data.as_of, not {readers}."


@pytest.mark.parametrize("path", PROJECT_FILES, ids=relative)
def test_no_test_week_is_named_in_the_code(path):
    text = path.read_text()
    for date in re.findall(r"20\d\d-\d\d-\d\d", text):
        assert pd.Timestamp(date) <= config.LAST_HISTORY_WEEK, f"{date} is a test week."
    assert not re.search(r"Week [1-8] - ", text), "Test-week files are named in the code."


def test_the_rules_above_really_detect_violations(tmp_path):
    """Guards the guards: a file that breaks every rule must be caught."""
    bad = tmp_path / "bad.py"
    bad.write_text("import vn2_play\nfrom vn2_simulate import load\nimport pandas as pd\n"
                   "pd.read_csv('Data/Week 8 - 2024-06-03 - Sales.csv')\nvn2_simulate.load()\n")
    used = names_used(bad)
    assert {"vn2_play", "vn2_simulate.load", "read_csv"} <= used
    assert re.search(r"Week [1-8] - ", bad.read_text())


def test_no_licence_file_is_tracked():
    tracked = subprocess.run(["git", "ls-files"], cwd=config.REPO, capture_output=True,
                             text=True, check=True).stdout.split()
    assert not [path for path in tracked if path.endswith(".sio")]
    assert "*.sio" in (config.REPO / ".gitignore").read_text().split()
