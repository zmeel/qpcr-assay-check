"""scripts/measure_borderline.py: the borderline candidates of a locator measurement report."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "measure_borderline", ROOT / "scripts" / "measure_borderline.py"
)
bl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl)


def test_borderline_lists_whole_and_cut_candidates():
    cut = {"M_amp": {"1": 26}, "identity_chain": 1.0, "context_only": False, "cut_left": True,
           "cut_right": False, "length_diff": 0, "amp_start": -234, "contig_len": 900,
           "sites": [{"oligo": "R", "mm_chain": 0}]}  # fmt: skip
    whole = dict(cut, **{"M_amp": {"1": 130}, "cut_left": False})  # not borderline
    chance = dict(cut, **{"M_amp": {"1": 17}, "identity_chain": 0.57, "cut_left": False})
    report = {"genomes": [{"accession": "GCF_1.1", "organism": "Legionella x",
                           "candidates": [cut, whole, chance]}]}  # fmt: skip
    (line,) = bl.borderline(report)
    assert line.startswith("GCF_1.1 Legionella_x 26 1.0 0 cut -234 900 - - R:0")


def test_context_only_candidates_are_listed_separately():
    ctx = {"M_amp": {"1": 0}, "context_only": True, "cut_left": False, "cut_right": True,
           "length_diff": 3, "amp_start": 880, "contig_len": 900, "M_ctx_left": 640,
           "M_ctx_right": 0, "N_inside": 0}  # fmt: skip
    report = {"genomes": [{"accession": "GCA_2.1", "organism": "Legionella y",
                           "candidates": [ctx]}]}  # fmt: skip
    assert list(bl.borderline(report)) == []
    assert list(bl.context_only(report)) == ["GCA_2.1 Legionella_y 640 0 3 cut 880 900 0"]
