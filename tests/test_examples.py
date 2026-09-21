from importlib import resources
from pathlib import Path

import pytest

from qpcr_assay_check.cli import build_assay
from qpcr_assay_check.config import load_config

from .conftest import CDC_N1_F, CDC_N1_P, CDC_N1_R

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["cdc_2019-nCoV_N1.yaml", "config_annealing_55C.yaml"]


@pytest.mark.parametrize("name", NAMES)
def test_repo_examples_match_the_packaged_copies(name):
    packaged = (resources.files("qpcr_assay_check") / "data" / "examples" / name).read_text()
    assert (ROOT / "examples" / name).read_text() == packaged


def test_example_assay_is_valid_and_matches_the_verified_sequences():
    a = build_assay(ROOT / "examples" / "cdc_2019-nCoV_N1.yaml", {})
    assert (a.forward, a.reverse, a.probe) == (CDC_N1_F, CDC_N1_R, CDC_N1_P)
    assert a.target.taxid == 2697049
    # verified against NC_045512.2:28287-28358 by the live smoke test (see the example's header)
    assert a.reference_amplicon == (
        "GACCCCAAAATCAGCGAAATGCACCCCGCATTACGTTTGGTGGACCCTCAGATTCAACTGGCAGTAACCAGA"
    )
    assert len(a.reference_amplicon) == 72


def test_example_config_loads():
    assert (
        load_config(ROOT / "examples" / "config_annealing_55C.yaml").reaction.annealing_temp_C
        == 55.0
    )


def test_example_amplicon_qc_matches_the_live_reference_geometry():
    """Positions come from the real genome record, not from this tool's own logic."""
    from qpcr_assay_check.oligo.qc import run_oligo_qc

    a = build_assay(ROOT / "examples" / "cdc_2019-nCoV_N1.yaml", {})
    qc = run_oligo_qc(a, load_config())
    s = qc.amplicon
    # genome coordinates 28287.. minus 28286 => positions in the amplicon
    assert (s.forward_site.start, s.forward_site.end) == (1, 20)
    assert (s.probe_site.start, s.probe_site.end, s.probe_site.strand) == (23, 46, "+")
    assert (s.reverse_site.start, s.reverse_site.end, s.reverse_site.strand) == (49, 72, "-")
    assert s.product_length_nt == 72
    assert (s.overlap_forward_nt, s.overlap_reverse_nt) == (0, 0)
    assert (s.gap_forward_probe_nt, s.gap_probe_reverse_nt) == (2, 2)
    amp_checks = {c.id: c.status.value for c in qc.checks if c.subject in ("amplicon", "probe")}
    assert amp_checks["amplicon.length"] == "PASS" and amp_checks["probe.within_amplicon"] == "PASS"
    assert not any(
        c.subject == "amplicon" and c.status.value in ("WARN", "FAIL") for c in qc.checks
    )
