"""Honest score reports (hard rule H10) and the log of final runs (hard rule H4)."""
import csv
from pathlib import Path

from vn2 import config

FINAL_LOG_COLUMNS = ["timestamp", "commit", "policy", "setup", "score"]


def score_report(score, label="Your policy"):
    """The score beside the benchmark and the winner, with the gap to each in EUR and %."""
    benchmark, winner = config.BENCHMARK_SCORE, config.WINNER_SCORE
    lines = [
        f"{label}: {score:,.1f} EUR (cost of weeks 3 to 8)",
        f"  Benchmark: {benchmark:,.1f} EUR  ->  {_gap(score, benchmark)}",
        f"  Winner:    {winner:,.1f} EUR  ->  {_gap(score, winner)}",
    ]
    return "\n".join(lines)


def _gap(score, reference):
    """'x EUR (y%) below/above' the reference."""
    gap = reference - score
    side = "below" if gap > 0 else "above"
    if gap == 0:
        return "equal"
    return f"{abs(gap):,.1f} EUR ({abs(gap) / reference:.1%}) {side}"


def append_final_run(log_path, row):
    """Add one final run to the log. Rows are only ever added, never rewritten."""
    log_path = Path(log_path)
    is_new = not log_path.exists()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINAL_LOG_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow({column: row[column] for column in FINAL_LOG_COLUMNS})
