"""The final exam (hard rule H4): play the six official rounds once and log the result.

Usage, from the repository root:
    python scripts/final_score.py path/to/policy.py

This is the only project file allowed to load the demand of weeks 1 to 8. It refuses to run
with uncommitted changes, so every score can be traced to one commit, and it appends every
run to results/final_runs.csv. The log itself is a change: commit it before the next run, so
no final run can quietly disappear.
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the repository root

from vn2 import config  # noqa: E402
from vn2.guards import git_tree_is_clean  # noqa: E402
from vn2.report import append_final_run, score_report  # noqa: E402
from vn2_play import load_policy, play  # noqa: E402
from vn2_simulate import load, score, setup, summarize  # noqa: E402

LOG = config.RESULTS_DIR / "final_runs.csv"


def git(*args):
    """Run a git command in the repository and return its output."""
    return subprocess.run(["git", *args], cwd=config.REPO, capture_output=True, text=True,
                          check=True).stdout


def run_final(policy_path, git_status=None, log_path=LOG):
    """Play the six rounds with the policy, log the run and return the score."""
    git_status = git("status", "--porcelain") if git_status is None else git_status
    if not git_tree_is_clean(git_status):
        raise SystemExit("Commit every change first: the final score must come from a commit.")

    _, states = play(load_policy(policy_path), load())
    weekly = summarize(states)
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": git("rev-parse", "HEAD").strip(),
        "policy": Path(policy_path).name,
        "setup": setup(weekly),
        "score": score(weekly),
    }
    append_final_run(log_path, result)
    print(score_report(result["score"], label=result["policy"]))
    return result["score"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/final_score.py path/to/policy.py")
    run_final(sys.argv[1])
