"""The quality gates themselves may not be weakened quietly.

Lowering a threshold, or dropping a check from CI, makes this test fail; changing it then
shows up in the diff of a test file, where a human reviews it.
"""
import tomllib

from vn2 import config

PYPROJECT = tomllib.loads((config.REPO / "pyproject.toml").read_text())
CI = (config.REPO / ".github" / "workflows" / "ci.yml").read_text()


def test_complexity_and_size_limits():
    lint = PYPROJECT["tool"]["ruff"]["lint"]
    assert lint["mccabe"]["max-complexity"] <= 10
    assert lint["pylint"]["max-statements"] <= 40
    assert {"C90", "PLR0915"} <= set(lint["select"])


def test_coverage_gate():
    assert "--cov-fail-under=85" in PYPROJECT["tool"]["pytest"]["ini_options"]["addopts"]


def test_ci_runs_every_gate():
    assert "ruff check" in CI
    assert "python -m pytest" in CI
