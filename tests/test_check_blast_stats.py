"""scripts/check_blast_stats.py: reads cached BLAST results and shows their statistics."""

import gzip
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "check_blast_stats", ROOT / "scripts" / "check_blast_stats.py"
)
cbs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cbs)


def test_it_shows_the_statistics_and_their_absence(tmp_path, caplog):
    d = tmp_path / "blast" / "ab"
    d.mkdir(parents=True)
    with_stat = {"BlastOutput2": [{"report": {"results": {"search": {
        "query_title": "forward", "hits": [], "stat": {"eff_space": 8}}}}}]}  # fmt: skip
    without = {"BlastOutput2": [{"report": {"results": {"search": {"query_title": "probe"}}}}]}
    for name, doc in (("ab1.json.gz", with_stat), ("ab2.json.gz", without)):
        with gzip.open(d / name, "wt", encoding="utf-8") as fh:  # the cache's envelope
            json.dump({"created": "2026-09-30T10:00:00+00:00", "text": json.dumps(doc)}, fh)
    caplog.set_level("INFO")
    assert cbs.main(["x", str(tmp_path), "5"]) == 0
    text = caplog.text
    assert "'forward'" in text and "{'eff_space': 8}" in text
    assert "'probe'" in text and "stat None" in text
