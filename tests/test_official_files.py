"""H1 and H2: the official files stay as published; the benchmark still scores 4,334.0."""
import hashlib

from vn2 import config
from vn2_benchmark import policy as benchmark_policy
from vn2_play import play
from vn2_simulate import load, score, setup, summarize

MANIFEST = config.REPO / "tests" / "official_manifest.sha256"


def read_manifest():
    """{relative path: sha256} from the committed manifest (sha256sum format)."""
    entries = {}
    for line in MANIFEST.read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        entries[path] = digest
    return entries


def test_official_files_are_unchanged():
    for path, digest in read_manifest().items():
        actual = hashlib.sha256((config.REPO / path).read_bytes()).hexdigest()
        assert actual == digest, f"{path} was changed. The official files must stay as published."


def test_no_data_file_was_added_or_removed():
    listed = {path for path in read_manifest() if path.startswith("Data/")}
    present = {f"Data/{p.name}" for p in config.DATA_DIR.iterdir() if p.is_file()}
    assert present == listed


def test_the_benchmark_still_scores_4334():
    _, states = play(benchmark_policy, load())
    weekly = summarize(states)
    assert setup(weekly) == config.SETUP_COST
    assert score(weekly) == config.BENCHMARK_SCORE
