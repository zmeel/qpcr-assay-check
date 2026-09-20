"""Amplicon tests use SYNTHETIC amplicons built from the oligos plus filler bases."""

from qpcr_assay_check.models import Status
from qpcr_assay_check.oligo import amplicon as amp
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.oligo.qc import run_oligo_qc

from .conftest import CDC_N1_F, CDC_N1_P, CDC_N1_R, make_assay, synthetic_amplicon


def check(qc, check_id):
    return next(c for c in qc.checks if c.id == check_id)


def test_well_formed_amplicon(cfg):
    a = make_assay(reference_amplicon=synthetic_amplicon())
    qc = run_oligo_qc(a, cfg)
    s = qc.amplicon
    assert s.forward_site.start == 1 and s.forward_site.strand == "+"
    assert s.reverse_site.strand == "-" and s.reverse_site.end == s.input_length_nt
    assert s.probe_site.start == len(CDC_N1_F) + 3
    assert s.product_length_nt == len(CDC_N1_F) + 2 + len(CDC_N1_P) + 2 + len(CDC_N1_R)
    assert (s.overlap_forward_nt, s.overlap_reverse_nt) == (0, 0)
    assert (s.gap_forward_probe_nt, s.gap_probe_reverse_nt) == (2, 2)
    assert check(qc, "amplicon.length").status is Status.PASS
    assert check(qc, "probe.within_amplicon").status is Status.PASS
    assert qc.amplicon_note == ""


def test_probe_overlapping_forward_primer_warns(cfg):
    probe = CDC_N1_F[-8:] + "GATCAGTC"
    amplicon = CDC_N1_F + "GATCAGTC" + iupac.reverse_complement(CDC_N1_R)
    qc = run_oligo_qc(make_assay(probe=probe, reference_amplicon=amplicon), cfg)
    c = check(qc, "probe.primer_overlap")
    assert c.status is Status.WARN
    assert qc.amplicon.overlap_forward_nt == 8


def test_overlap_allowed_by_configuration(tmp_path):
    from qpcr_assay_check.config import load_config

    p = tmp_path / "c.yaml"
    p.write_text("thresholds:\n  amplicon:\n    allow_probe_primer_overlap: true\n")
    probe = CDC_N1_F[-8:] + "GATCAGTC"
    amplicon = CDC_N1_F + "GATCAGTC" + iupac.reverse_complement(CDC_N1_R)
    qc = run_oligo_qc(make_assay(probe=probe, reference_amplicon=amplicon), load_config(p))
    assert check(qc, "probe.primer_overlap").status is Status.PASS


def test_probe_outside_the_primer_defined_product_fails(cfg):
    amplicon = CDC_N1_P + "TT" + CDC_N1_F + "TT" + iupac.reverse_complement(CDC_N1_R)
    qc = run_oligo_qc(make_assay(reference_amplicon=amplicon), cfg)
    assert check(qc, "probe.within_amplicon").status is Status.FAIL
    assert check(qc, "amplicon.flanks").status is Status.INFO
    assert qc.amplicon.flank_5_nt == len(CDC_N1_P) + 2


def test_missing_primer_site_fails_and_stops_geometry(cfg):
    amplicon = CDC_N1_F + "TT" + CDC_N1_P + "AATTTTTTTTTTTTTTTTTTTTTTTTTT"
    qc = run_oligo_qc(make_assay(reference_amplicon=amplicon), cfg)
    assert check(qc, "reverse.site").status is Status.FAIL
    assert not any(c.id == "amplicon.length" for c in qc.checks)


def test_primers_not_facing_each_other_fail(cfg):
    amplicon = iupac.reverse_complement(CDC_N1_R) + "TT" + CDC_N1_F + "AA" + CDC_N1_P
    qc = run_oligo_qc(make_assay(reference_amplicon=amplicon), cfg)
    assert check(qc, "amplicon.orientation").status is Status.FAIL


def test_single_mismatch_is_located_and_warned(cfg):
    amplicon = synthetic_amplicon()
    mutated = amplicon[:5] + ("A" if amplicon[5] != "A" else "C") + amplicon[6:]
    qc = run_oligo_qc(make_assay(reference_amplicon=mutated), cfg)
    c = check(qc, "forward.site")
    assert c.status is Status.WARN and "1 mismatch" in c.display
    assert qc.amplicon.forward_site.mismatches == 1


def test_degenerate_primer_matches_through_iupac(cfg):
    a = make_assay(forward="GACCCCAAAATCAGCGAAAW", reference_amplicon=synthetic_amplicon())
    qc = run_oligo_qc(a, cfg)
    assert qc.amplicon.forward_site.mismatches == 0


def test_find_sites_reports_both_strands_best_first():
    target = "TTTT" + "ACGTACGTAC" + "GGGG" + iupac.reverse_complement("ACGTACGTAC") + "TTTT"
    sites = amp.find_sites(target, "ACGTACGTAC", "x", max_mismatches=0)
    assert [(s.strand, s.start) for s in sites] == [("+", 5), ("-", 19)]


def test_degenerate_code_that_excludes_the_target_base_is_a_mismatch(cfg):
    """R (A/G) cannot match the T in the amplicon, so this is a real mismatch."""
    a = make_assay(forward="GACCCCAAAATCAGCGAAAR", reference_amplicon=synthetic_amplicon())
    qc = run_oligo_qc(a, cfg)
    assert qc.amplicon.forward_site.mismatches == 1
