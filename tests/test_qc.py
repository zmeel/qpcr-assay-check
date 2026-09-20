import pytest

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import InputError
from qpcr_assay_check.models import Status
from qpcr_assay_check.oligo.qc import run_oligo_qc

from .conftest import CDC_N1_F, make_assay


def by_id(qc, check_id):
    return next(c for c in qc.checks if c.id == check_id)


def test_published_cdc_n1_oligos_regression(cfg, n1):
    """Pins today's behaviour for a real, working assay: one WARN, no structure flagged."""
    qc = run_oligo_qc(n1, cfg)
    flagged = [c.id for c in qc.checks if c.status in (Status.WARN, Status.FAIL)]
    assert flagged == ["pair.primer_tm_diff"]
    assert not [s for s in qc.structures if s.status in (Status.WARN, Status.FAIL)]
    assert qc.status is Status.WARN
    assert by_id(qc, "forward.length").value == 20
    assert by_id(qc, "probe.five_prime_g").status is Status.PASS
    assert by_id(qc, "forward.gc").value == pytest.approx(45.0)
    assert by_id(qc, "probe.gc").value == pytest.approx(100 * 14 / 24)
    # informational values never score
    assert by_id(qc, "forward.three_prime_dg").status is Status.INFO


def test_terrible_primer_fails(cfg):
    a = make_assay(forward="GGGGGGCCCCCCGGGGGGCC")
    qc = run_oligo_qc(a, cfg)
    assert by_id(qc, "forward.gc").status is Status.FAIL
    assert by_id(qc, "forward.max_g_run").status is Status.FAIL
    assert by_id(qc, "forward.gc_last5").status is Status.WARN
    assert qc.status is Status.FAIL
    hp = next(s for s in qc.structures if s.label == "forward hairpin")
    assert hp.status is Status.FAIL and hp.ascii_lines


def test_no_gc_clamp_message(cfg):
    a = make_assay(
        forward="GACCCCAAAATCAGCGAAAAAATA"[:20] + "TTAT"
    )  # ends AATA-style, no G/C at 3'
    qc = run_oligo_qc(a, cfg)
    c = by_id(qc, "forward.gc_last5")
    assert c.status is Status.WARN
    assert "no GC clamp" in c.message


def test_degenerate_primer_is_expanded_and_worst_variant_counts(cfg):
    a = make_assay(forward="GACCCCAAAATCAGCGAAAR")
    qc = run_oligo_qc(a, cfg)
    info = next(o for o in qc.oligos if o.role == "forward")
    assert info.degenerate and info.n_variants == 2
    assert info.variants == ["GACCCCAAAATCAGCGAAAA", "GACCCCAAAATCAGCGAAAG"]
    tm = by_id(qc, "forward.tm")
    assert tm.value is None and tm.value_min < tm.value_max
    assert "–" in tm.display


def test_degenerate_cap_is_enforced(cfg):
    a = make_assay(forward="N" * 20)
    with pytest.raises(InputError, match="cap"):
        run_oligo_qc(a, cfg)


def test_five_prime_g_rule_depends_on_reporter(cfg):
    g_probe = "GACCCCGCATTACGTTTGGTGGAC"
    assert (
        by_id(run_oligo_qc(make_assay(probe=g_probe), cfg), "probe.five_prime_g").status
        is Status.WARN
    )
    cy5 = make_assay(probe=g_probe, probe_reporter="Cy5")
    assert by_id(run_oligo_qc(cy5, cfg), "probe.five_prime_g").status is Status.INFO
    unknown = make_assay(probe=g_probe, probe_reporter=None)
    c = by_id(run_oligo_qc(unknown, cfg), "probe.five_prime_g")
    assert c.status is Status.WARN and "no reporter" in c.message


def test_modified_probe_triggers_tm_reliability_warning_and_caps_the_tm_check(cfg):
    short = "ACCCCGCATTAC"  # 12 nt: Tm far below the primers
    plain = run_oligo_qc(make_assay(probe=short), cfg)
    mgb = run_oligo_qc(make_assay(probe=short, probe_quencher="MGB-NFQ"), cfg)
    assert by_id(plain, "probe.tm_minus_primers").status is Status.FAIL
    assert by_id(mgb, "probe.tm_minus_primers").status is Status.WARN
    rel = by_id(mgb, "probe.tm_reliability")
    assert rel.status is Status.WARN and "MGB" in rel.message
    assert mgb.tm_unreliable_reasons == ["MGB"]
    assert not any(c.id == "probe.tm_reliability" for c in plain.checks)


def test_stronger_gc_probe_rule(cfg):
    qc = run_oligo_qc(make_assay(probe="ACGGGGTACGGGTTTAGGCA"), cfg)
    assert by_id(qc, "probe.g_minus_c").status is Status.WARN


def test_strong_primer_dimer_is_flagged_including_3prime_extension(cfg):
    pal = "GGATCCGGATCCGGATCC"
    qc = run_oligo_qc(make_assay(forward=pal, reverse=pal), cfg)
    kinds = {(s.kind, s.status) for s in qc.structures}
    assert ("homodimer", Status.FAIL) in kinds
    assert ("end_dimer", Status.FAIL) in kinds


def test_structure_thresholds_follow_configuration(tmp_path, n1):
    p = tmp_path / "c.yaml"
    p.write_text("thresholds:\n  structures:\n    warn_tm_c: 5\n    fail_tm_c: 500\n")
    qc = run_oligo_qc(n1, load_config(p))
    assert any(s.status is Status.WARN for s in qc.structures)
    assert not any(s.status is Status.FAIL for s in qc.structures)


def test_missing_reference_amplicon_is_stated_not_hidden(cfg, n1):
    qc = run_oligo_qc(n1, cfg)
    assert qc.amplicon is None
    assert "not evaluated" in qc.amplicon_note
    assert not any(c.subject == "amplicon" for c in qc.checks)


def test_primer_sequence_is_not_mutated(cfg):
    a = make_assay(forward=CDC_N1_F)
    run_oligo_qc(a, cfg)
    assert a.forward == CDC_N1_F
