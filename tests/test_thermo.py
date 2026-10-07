import math

import primer3
import pytest

from qpcr_assay_check.oligo import thermo

from .conftest import CDC_N1_F, CDC_N1_P


@pytest.fixture
def cond(cfg):
    return thermo.Conditions.from_reaction(cfg.reaction)


def test_nn_dg37_matches_hand_calculation():
    # GC + CG + GC + CG steps: 2 * (-2.24) + 2 * (-2.17)
    assert thermo.nn_dg37("GCGCG") == pytest.approx(-8.82)
    assert thermo.nn_dg37("AAAAA") == pytest.approx(-4.00)
    # the table is direction-consistent: a duplex and its reverse complement have equal ΔG
    assert thermo.nn_dg37("ACCGT") == pytest.approx(thermo.nn_dg37("ACGGT"))


def test_melting_temp_is_the_primer3_value(cond, cfg):
    expected = primer3.calc_tm(
        CDC_N1_F, mv_conc=50, dv_conc=3.0, dntp_conc=0.8, dna_conc=400,
        tm_method="santalucia", salt_corrections_method="santalucia",
    )  # fmt: skip
    assert thermo.melting_temp(CDC_N1_F, cond, nM=400) == pytest.approx(expected)


def test_dg_is_reported_in_kcal_per_mol_and_is_self_consistent(cond):
    """primer3 reports cal/mol; ΔG must equal ΔH - TΔS after conversion to kcal/mol."""
    r = thermo.heterodimer(CDC_N1_F, CDC_N1_P, cond, nM=200)
    assert r.found
    t_kelvin = cond.temp_c + 273.15
    assert r.dg_kcal == pytest.approx(r.dh_kcal - t_kelvin * r.ds_cal_per_k / 1000, abs=0.05)
    assert abs(r.dg_kcal) < 50  # would be ~1000+ if cal/mol leaked through


def test_strong_hairpin_is_found(cond):
    r = thermo.hairpin("GCGCGCGCAAAAGCGCGCGC", cond, nM=400)
    assert r.found and r.tm_c > 60
    assert r.ascii_lines


def test_palindromic_oligo_forms_a_stable_homodimer_with_extendable_3prime_end(cond):
    s = "GGATCCGGATCCGGATCC"
    assert thermo.homodimer(s, cond, nM=400).tm_c > 60
    assert thermo.end_dimer(s, s, cond, nM=400).tm_c > 60


def test_no_structure_gives_none_not_zero(cond):
    r = thermo.hairpin(CDC_N1_F, cond, nM=400)
    assert not r.found and r.tm_c is None and r.dg_kcal is None
    assert not math.isnan(thermo.melting_temp(CDC_N1_F, cond, nM=400))


def test_a_degenerate_oligo_is_resolved_against_the_template_for_its_duplex_estimate():
    """User, 2026-10-07, from two influenza rows that looked identical but had ΔTm -3.6 and
    +0.0 C: primer3 cannot pair a degenerate code with its own complement, so leaving the Y in
    made the perfect-match baseline about 15 C too low and the ΔTm of a site depend on which
    member of the mix the template happened to take."""
    from qpcr_assay_check.config import load_config
    from qpcr_assay_check.oligo import thermo
    from qpcr_assay_check.specificity.duplex import estimate_duplex, resolved_oligos

    oligo = "TCTTGTCTTTAGCCAYTCCATGAG"  # influenza A RfluA: one Y
    # the two templates: the same site but for the base under the Y, and a 3'-terminal mismatch
    with_t = "TCTTGTCTTTAGCCATTCCATGAT"  # PZ... with T there (A:T pair)
    with_c = "TCTTGTCTTTAGCCACTCCATGAT"  # PZ... with C there (G:C pair)
    assert resolved_oligos(oligo, oligo, with_t) == ["TCTTGTCTTTAGCCATTCCATGAG"]
    assert resolved_oligos(oligo, oligo, with_c) == ["TCTTGTCTTTAGCCACTCCATGAG"]
    # an incompatible base under the Y: both members are offered, so the caller takes the best
    assert len(resolved_oligos(oligo, oligo, "TCTTGTCTTTAGCCAATCCATGAT")) == 2
    assert resolved_oligos("ACGT", "ACGT", "ACGT") == ["ACGT"]  # nothing to resolve

    cfg = load_config()
    cond = thermo.Conditions.from_reaction(cfg.reaction)
    nM = cfg.reaction.primer_nM
    out = {}
    for name, tpl in (("T", with_t), ("C", with_c)):
        tm, _dg, dtm = estimate_duplex(oligo, tpl, cond, nM, oligo)
        out[name] = (tm, dtm)
    # the same site apart from which member binds: the same ΔTm, and a plausible absolute Tm for
    # a 24-mer whose only defect is a 3'-terminal mismatch
    assert round(out["T"][1], 1) == round(out["C"][1], 1)
    assert -2.0 < out["T"][1] < 0.0
    assert all(55.0 < tm < 70.0 for tm, _d in out.values())
    # without the alignment the old behaviour stands (a degenerate oligo used as written)
    tm_old, _dg, dtm_old = estimate_duplex(oligo, with_t, cond, nM)
    assert tm_old < 55.0 and dtm_old < out["T"][1] - 1.0
