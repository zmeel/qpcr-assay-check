"""scripts/run_summary.py: the compact summary of a results.json to paste back (step 8)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run_summary", ROOT / "scripts" / "run_summary.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


def test_the_summary_keeps_counts_and_cuts_accession_lists():
    row = {"q_aln": "ACGT", "s_aln": "ACGA", "n_mismatch": 1, "grade": "minor"}
    data = {
        "run_id": "r1", "tool": {"version": "x"},
        "overall": {"review_status": "review", "verdict": "WARN", "rationale": ["a"]},
        "sections": [{"key": "inclusivity", "state": "evaluated", "verdict": "WARN"}],
        "config": {"variants": {"source": "datasets"}, "ncbi": {"cache_dir": "/secret"}},
        "variant_summary": {
            "coverage": {"found": 5, "not_found_examples": [f"GCA_{i}.1" for i in range(12)],
                         "copies": {"escapes": 1, "oligos": []}, "channel_results": [{"name": "V"}],
                         "years": [{"year": 2026}]},
            "fragments": [{"count": 3, "percent": 60.0, "level": "minor",
                           "example_accession": "GCA_1.1", "forward": row}],
        },
        "inclusivity": {"verdict": "WARN", "rationale": [], "fragment_years": []},
    }  # fmt: skip
    out = rs.summary(data)
    assert out["coverage"]["found"] == 5 and out["copies"]["escapes"] == 1
    assert out["coverage"]["not_found_examples"][-1] == "... 12 in all"
    assert out["channels"] == [{"name": "V"}]
    assert out["fragment_variants"][0]["forward"] == [1, "minor"]
    assert "ACGA" not in str(out) and "/secret" not in str(out)  # no sequences, no ncbi settings
