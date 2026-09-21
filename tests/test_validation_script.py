"""scripts/validate_assessment.py, run against the constructed world.

The script will be run live once; a bug in it would cost a round trip (and an hour of BLAST), so it
is tested like any other code, including that it really detects a broken assumption.
"""

import importlib.util
import json
import time
from pathlib import Path

import pytest

from .conftest import CDC_N1_F as F
from .conftest import ROOT_EXAMPLE
from .test_assess import F_START, HUMAN, offtarget_genome
from .world import World, WorldFake

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "validate_assessment", ROOT / "scripts" / "validate_assessment.py"
)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    conf = tmp_path / "config.yaml"
    conf.write_text(f"ncbi:\n  cache_dir: {tmp_path / 'cache'}\n")
    monkeypatch.setenv("NCBI_EMAIL", "lab@example.org")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def go(world):
        fake = WorldFake(world)
        monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
        out = tmp_path / "vout"
        code = script.main(
            [
                "--assay",
                str(ROOT_EXAMPLE),
                "--config",
                str(conf),
                "--outdir",
                str(out),
                "--sample",
                "20",
            ]
        )
        return code, json.loads((out / "validation_report.json").read_text()), fake

    return go


def human_world(realistic=True):
    # A 5-base unaligned flank with only one mismatch would let the running match(+1)/mismatch(-3)
    # score end positive (BLAST would have extended over it), so both flanked scenarios need a
    # second mismatch (16, 17) adjacent to the alignment boundary to stay realistic.
    w = World()
    for i, (mutations, trim) in enumerate(
        [([10, 16, 17], 5), ([19], 2), ([12, 16, 17], 5), ([], 0)], start=1
    ):
        acc = f"NC_00000{i}.1"
        offtarget_genome(f=mutations, acc=acc, taxid=HUMAN, name="Homo sapiens", world=w)
        w.hit(HUMAN, "forward", F, acc, F_START, "+", trim3=trim, realistic=realistic)
    return w


def test_real_blast_behaviour_passes_and_the_counts_are_reported(setup):
    code, report, fake = setup(human_world())
    assert code == 0 and report["rules_contradicted"] == 0
    c = report["counts"]
    assert c["relevant_alignments"] == 4 and c["full_length_no_fetch_needed"] == 1
    assert c["partial"] == 3
    assert c["partial_ruled_out_without_fetching"] == 1  # the u3=2 hit
    assert c["partial_needing_a_fetch"] == 2
    assert report["sample"]["checked"] == 3 and report["tier"] == "background"
    assert "no rule contradicted" in report["verdict"]
    # only the background tier was searched
    assert {p["ENTREZ_QUERY"] for p in fake.searches.values()} == {"txid9606[ORGN]"}


def test_a_contradicted_assumption_is_detected_and_listed(setup):
    """A 'partial' hit whose unaligned flank matches is impossible for BLAST: the script must say
    so."""
    w = World()
    offtarget_genome(f=[], acc="NC_000009.1", taxid=HUMAN, name="Homo sapiens", world=w)
    w.hit(HUMAN, "forward", F, "NC_000009.1", F_START, "+", trim3=5, realistic=False)
    code, report, _ = setup(w)
    assert code == 1 and report["rules_contradicted"] >= 1
    checks = {v["check"] for v in report["violations"]}
    assert {"lower_bound", "first_unaligned_base_is_a_mismatch"} <= checks
    assert "CONTRADICTED" in report["verdict"]
    v = report["violations"][0]
    assert v["accession"] == "NC_000009.1" and v["u3"] == 5 and v["hit_strand"] == "Plus"


def test_the_report_holds_no_secrets(setup, tmp_path):
    code, report, _ = setup(human_world())
    text = json.dumps(report)
    assert "lab@example.org" not in text and "lab%40example.org" not in text


def test_an_unusable_assay_yields_an_error_report_and_exit_2(setup, tmp_path, monkeypatch):
    monkeypatch.delenv("NCBI_EMAIL")
    code, report, _ = setup(human_world())
    assert code == 2 and "NCBI_EMAIL" in report["error"]
