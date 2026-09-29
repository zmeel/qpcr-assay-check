"""scripts/measure_locator.py (step 0 of the locator overhaul), on SYNTHETIC genomes.

The script is run live by the user on thousands of downloads; a bug in it costs a night, so its
prototype chain locator and its report are tested like any other code.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from qpcr_assay_check.config import load_config
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.variants.store import StoredAssembly, StoredLocus

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .world import filler

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "measure_locator", ROOT / "scripts" / "measure_locator.py"
)
script = importlib.util.module_from_spec(spec)
sys.modules["measure_locator"] = script  # dataclasses look their module up
spec.loader.exec_module(script)

# A SYNTHETIC amplicon: the CDC N1 oligos with random spacers. Not a real sequence.
AMP = F + filler(30, 11) + P + filler(30, 12) + iupac.reverse_complement(R)
ASSAY = make_assay(reference_amplicon=AMP, target={"taxid": 813})


def measure(contigs, **kw):
    cfg = load_config()
    opts = {"k": 16, "current_step": 4, "flank": 50, "max_indel": 150, "n_null": 1,
            "rule_m": 32, "rule_identity": 0.75, "min_copy_identity": 0.75}  # fmt: skip
    opts.update(kw)
    oligos = [script.oligo_sites(ASSAY, AMP, cfg.thresholds.amplicon.max_site_mismatches)]
    return script.measure_genome(contigs, [AMP], ("", ""), oligos, **opts)


def copies(row):
    return [c for c in row["candidates"] if c["copy_by_rule"]]


def test_a_plain_copy_is_one_chain_with_every_base_anchored():
    row = measure({"C1": filler(3000, 1) + AMP + filler(3000, 2)})
    (c,) = copies(row)
    assert c["M_amp"][1] == len(AMP) and c["length_diff"] == 0 and c["identity_chain"] == 1.0
    assert c["strand"] == "+" and c["amp_start"] == 3000 and not c["current_split"]
    assert all(s["mm_chain"] == 0 and s["mm_current"] == 0 for s in c["sites"])
    assert row["copy_current"] and row["copy_chain"]


def test_an_insertion_longer_than_the_indel_tolerance_splits_the_current_locus_not_the_chain():
    ins = AMP[:40] + filler(40, 5) + AMP[40:]  # in the spacer before the probe
    row = measure({"C1": filler(3000, 1) + ins + filler(3000, 2)})
    (c,) = copies(row)
    assert c["length_diff"] == 40 and c["current_split"]
    assert c["M_amp"][1] == len(AMP)
    assert all(s["mm_chain"] == 0 for s in c["sites"])
    # the current single offset puts one oligo 40 nt off: a false escape
    assert any(s["mm_current"] is None or s["mm_current"] > 0 for s in c["sites"])


def test_a_copy_cut_by_the_contig_start_gets_a_negative_start():
    row = measure({"C1": AMP[50:] + filler(3000, 3)})
    (c,) = copies(row)
    assert c["amp_start"] == -50 and c["cut_left"] and not c["cut_right"]
    assert c["M_amp"][1] == len(AMP) - 50


def test_the_reverse_strand_and_n_next_to_a_copy():
    seq = filler(2000, 1) + "N" * 30 + AMP + filler(2000, 2)
    row = measure({"C1": iupac.reverse_complement(seq)})
    (c,) = copies(row)
    assert c["strand"] == "-" and c["N_left"] == 30 and c["N_right"] == 0
    assert all(s["mm_chain"] == 0 for s in c["sites"])


def test_a_single_chance_seed_is_not_a_copy():
    row = measure({"C1": filler(3000, 1) + AMP[40:56] + filler(3000, 2)})
    assert row["n_candidates"] == 1 and not copies(row)
    assert 16 <= row["candidates"][0]["M_amp"][1] < 24 and not row["copy_chain"]


def test_two_copies_far_apart_are_two_chains_and_the_null_finds_little():
    row = measure({"C1": filler(3000, 1) + AMP + filler(3000, 2) + AMP + filler(500, 3)})
    assert len(copies(row)) == 2
    assert all(m < 32 for m in row["null_max_M"])


def test_select_picks_related_and_organism_groups():
    def item(acc, identity, organism="Legionella pneumophila", seeds=5):
        lc = StoredLocus(contig="c", strand="+", start=1, end=10, region="A" * 10, offset=0,
                         n_seeds=seeds, truncated=False, identity=identity)  # fmt: skip
        return StoredAssembly(accession=acc, release_date="2024-01-01", organism=organism,
                              status="found", n_loci=1, loci=[lc])  # fmt: skip

    items = [
        item("A1", 0.99),
        item("A2", 0.63, "Legionella longbeachae"),
        item("A3", 0.57, seeds=1),
    ]
    got = script.select(items, ["related", "single-seed", "organism:longbeachae"], [AMP], 16,
                        0.75, 10)  # fmt: skip
    assert sorted(got["related"]) == ["A2", "A3"]
    assert got["single-seed"] == ["A3"] and got["organism:longbeachae"] == ["A2"]


def test_run_writes_a_report_without_the_email(tmp_path, monkeypatch):
    monkeypatch.setenv("NCBI_EMAIL", "lab@example.org")
    genomes = {"GCF_1.1": {"C1": filler(3000, 1) + AMP + filler(3000, 2)},
               "GCF_2.1": {"C2": filler(3000, 4)}}  # fmt: skip
    args = argparse.Namespace(
        group=[],
        accessions="GCF_1.1,GCF_2.1,GCF_9.1",
        per_group=5,
        max_genomes=10,
        batch=2,
        max_indel=150,
        null=1,
        rule_m=32,
        rule_identity=0.75,
        context_accession="",
        probe_sequence_report="",
        outdir=tmp_path / "out",
        cache_root=tmp_path / "cache",
    )
    report = script.run(args, ASSAY, load_config(), lambda accs: {a: genomes[a] for a in accs
                                                                  if a in genomes})  # fmt: skip
    text = (tmp_path / "out" / "measure_report.json").read_text()
    assert "lab@example.org" not in text and json.loads(text)["summary"]["genomes_measured"] == 2
    rows = {g["accession"]: g for g in report["genomes"]}
    assert rows["GCF_1.1"]["copy_chain"] and not rows["GCF_2.1"]["copy_chain"]
    assert rows["GCF_9.1"]["error"] == "not downloaded"
    assert report["summary"]["per_group"]["named"]["genomes"] == 2


def test_nucleotide_fasta_is_split_per_accession():
    text = ">OR000001.1 enterovirus D68\nACGT\n>OR000002.1 x\nGGCC\n"
    assert script._by_accession(text, ["OR000001.1", "OR000002"]) == {
        "OR000001.1": {"OR000001.1": "ACGT"}, "OR000002": {"OR000002.1": "GGCC"}}  # fmt: skip


def test_groups_without_a_store_stop_with_a_clear_message(tmp_path):
    import pytest

    args = argparse.Namespace(
        group=["related"],
        accessions="",
        per_group=5,
        max_genomes=10,
        batch=2,
        max_indel=150,
        null=1,
        rule_m=32,
        rule_identity=0.75,
        context_accession="",
        probe_sequence_report="",
        outdir=tmp_path / "out",
        cache_root=tmp_path / "cache",
    )
    with pytest.raises(SystemExit, match="No region store"):
        script.run(args, ASSAY, load_config(), lambda accs: {})


def test_borderline_lists_whole_and_cut_candidates(tmp_path):
    spec2 = importlib.util.spec_from_file_location(
        "measure_borderline", ROOT / "scripts" / "measure_borderline.py"
    )
    bl = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(bl)
    cut = {"M_amp": {"1": 26}, "identity_chain": 1.0, "context_only": False, "cut_left": True,
           "cut_right": False, "length_diff": 0, "amp_start": -234, "contig_len": 900,
           "sites": [{"oligo": "R", "mm_chain": 0}]}  # fmt: skip
    whole = dict(cut, **{"M_amp": {"1": 130}, "cut_left": False})  # not borderline
    chance = dict(cut, **{"M_amp": {"1": 17}, "identity_chain": 0.57, "cut_left": False})
    report = {"genomes": [{"accession": "GCF_1.1", "organism": "Legionella x",
                           "candidates": [cut, whole, chance]}]}  # fmt: skip
    (line,) = bl.borderline(report)
    assert line.startswith("GCF_1.1 Legionella_x 26 1.0 0 cut -234 900 R:0")
