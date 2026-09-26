"""Condensed report tables (user request 2026-09-25: the report was too long to read).

All records, taxids and alignments below are SYNTHETIC."""

from __future__ import annotations

from types import SimpleNamespace as NS

from qpcr_assay_check.report.grouping import group_products, group_sites, species_of
from qpcr_assay_check.specificity.models import AmpliconResult

from .test_exclusivity import site


def product(pid, tier, acc, taxid, organism, cls="likely_detected", start=10, roles="F/R"):
    return AmpliconResult(id=pid, tier=tier, accession=acc, taxid=taxid, organism=organism,
                          roles=roles, left_site="L", right_site="R", start=start,
                          end=start + 73, length=74, classification=cls,
                          record_type="genomic")  # fmt: skip


def test_products_are_counted_once_and_grouped_per_tier_and_species():
    species = species_of([NS(taxid=11, species="Enterovirus G", scientific_name="EV-G 1"),
                          NS(taxid=12, species="Enterovirus G", scientific_name="EV-G 2"),
                          NS(taxid=21, species=None, scientific_name="Rhinovirus B")])  # fmt: skip
    amps = [
        product("A1", "out_of_scope", "X1", 11, "EV-G 1"),
        product("A2", "out_of_scope", "X1", 11, "EV-G 1"),  # the same product again (_v2)
        product("A3", "out_of_scope", "X2", 12, "EV-G 2"),
        product("A4", "near_neighbours", "R1", 21, "Rhinovirus B", cls="amplified_not_detected"),
    ]
    sites = {"L": site(11, "forward", "critical"), "R": site(11, "reverse", "critical")}
    groups = group_products(amps, sites, species)
    assert [(g.tier, g.species, g.n_products, g.n_records) for g in groups] == [
        ("near_neighbours", "Rhinovirus B", 1, 1),  # must-not-detect first
        ("out_of_scope", "Enterovirus G", 2, 2),  # two taxa, one species; duplicate dropped
    ]
    assert groups[1].names == {"EV-G 1": 1, "EV-G 2": 1}


def test_sites_are_grouped_per_species_closest_first():
    s1 = site(21, "reverse", "critical", tier="near_neighbours", site_id="S1")
    s2 = site(21, "probe", "warning", tier="near_neighbours", site_id="S2").model_copy(
        update={"n_mismatch": 2}
    )
    s3 = site(9606, "reverse", "minor", tier="background", site_id="S3")  # minor: not shown
    groups = group_sites([s2, s1, s3], {21: "Rhinovirus B"})
    (g,) = groups
    assert (g.species, g.n_sites, g.levels["critical"], g.best.id) == ("Rhinovirus B", 2, 1, "S1")


def test_per_oligo_lists_problems_and_only_the_most_frequent_tolerated_variants(tmp_path):
    """Advisor 2026-09-25 (user: the whole-fragment table is the main view): per oligo only the
    variants that are not perfect; risky ones always, tolerated ones the 5 most frequent."""
    from qpcr_assay_check.config import load_config
    from qpcr_assay_check.report.html import render_report

    from .test_multi_copy import run_report_result

    result, cfg = run_report_result(tmp_path), load_config()
    vs = result.variant_summary
    fwd = vs.oligos[0]
    base = fwd.rows[0]
    extra = [base.model_copy(update={"percent": 0.05, "count": 10 - i, "grade": g,
                                     "example_accession": f"VAR{i}.1"})
             for i, g in enumerate(["tolerated"] * 7 + ["likely_failure"])]  # fmt: skip
    oligos = [fwd.model_copy(update={"rows": [*fwd.rows, *extra]}), *vs.oligos[1:]]
    result = result.model_copy(update={"variant_summary": vs.model_copy(update={"oligos": oligos})})
    html = render_report(result, cfg)
    i = html.index("<h3>Variants per oligo")
    per_oligo = html[i : html.index("<h2>", i)]
    assert "VAR7.1" in per_oligo  # the likely failure, although the rarest
    assert all(f"VAR{k}.1" in per_oligo for k in range(5))  # 5 most frequent tolerated
    assert "VAR5.1" not in per_oligo and "VAR6.1" not in per_oligo
    assert "2 other tolerated variants" in per_oligo
    assert per_oligo.index("VAR7.1") < per_oligo.index("VAR0.1")  # worst class first


def test_site_changes_are_written_from_the_3prime_end():
    from qpcr_assay_check.report.grouping import site_changes

    row = NS(q_aln="ACGTACGTAC", s_aln="ACGTACGTAA")  # site A facing oligo C at -1
    assert site_changes(row) == "-1 C-T"  # oligo base - template base (complement of A)
    assert site_changes(NS(q_aln="ACGTA", s_aln="AC-TA")) == "-3 deleted"
    assert site_changes(NS(q_aln="ACGTR", s_aln="ACGTG")) == "none"  # degenerate base matches
    assert site_changes(NS(q_aln="ACGTA", s_aln="ACGTA")) == "none"
    assert site_changes(NS(q_aln="AC-GTA", s_aln="ACAGTA")) == "insertion between -4 and -3"


def _site(grade, mm=0, rule="", note=""):
    return NS(grade=grade, n_mismatch=mm, grade_rule=rule, note=note)


def _frag(f, p, r, count, org="EV-A71"):
    return NS(forward=f, probe=p, reverse=r, count=count, organisms=[(org, count)])


def test_fragment_outcome_is_the_worst_site_and_the_pair_rule():
    from qpcr_assay_check.report.grouping import fragment_outcome

    ok, tol = _site("perfect"), _site("tolerated", 1)
    assert fragment_outcome(_frag(ok, ok, tol, 1)) == ("detectable", False)
    assert fragment_outcome(_frag(_site("likely_failure", 1), ok, ok, 1))[0] == "likely failure"
    assert fragment_outcome(_frag(ok, _site("indeterminate", 1, "R9"), ok, 1))[0] == "undetermined"
    bulge = _site("indeterminate", 0, "R5", note="poly-A run 7->8")
    assert fragment_outcome(_frag(bulge, ok, ok, 1))[0] == "at risk"  # strict
    assert fragment_outcome(_frag(bulge, ok, ok, 1), bulges=True)[0] == "detectable"
    # 3 + 2 tolerated-looking mismatches: the primer-pair rule decides (Lefever 2013)
    three, two = _site("at_risk", 3), _site("at_risk", 2)
    assert fragment_outcome(_frag(three, ok, two, 1)) == ("likely failure", True)


def test_fragment_view_lists_every_problem_and_lumps_only_detectable():
    from qpcr_assay_check.report.grouping import fragment_view

    ok, bad = _site("perfect"), _site("likely_failure", 1)
    frags = [_frag(ok, ok, ok, 100 - i, org=f"T{i}") for i in range(15)]
    frags += [_frag(bad, ok, ok, 2, org="EV-D68") for _ in range(35)]
    total = sum(f.count for f in frags)
    v = fragment_view(frags, total)
    assert len(v.attention) == 30
    assert v.attention_grouped == [("likely failure", [("EV-D68", 10)], 5, 10, 1)]
    assert len(v.detectable_top) == 10 and v.detectable_rest == 5
    assert v.records["likely failure"] == 70 and v.records["detectable"] == total - 70


def test_ungraded_combinations_are_never_shown_as_detectable():
    """Review finding: rows without a class ('') were lumped into 'Detectable'."""
    from qpcr_assay_check.report.grouping import fragment_view

    ungraded = _site(None, 1)
    v = fragment_view([_frag(ungraded, ungraded, ungraded, 5)], 5)
    assert not v.detectable_top and v.detectable_rest == 0
    assert [o for _f, o, _p in v.attention] == [""] and v.records["not classified"] == 5


def test_rows_that_can_fail_are_always_shown():
    """Review finding: products the probe would detect beyond 15 rows were only in the workbook."""
    from qpcr_assay_check.report.grouping import shown_rows

    groups = [NS(tier="background", n_detected=0, name=i) for i in range(20)]
    groups += [NS(tier="exclusivity", n_detected=1, name=f"D{i}") for i in range(5)]
    groups += [NS(tier="out_of_scope", n_detected=3, name="O")]
    shown, hidden = shown_rows(groups, "n_detected", 15)
    assert hidden == 5 and len(shown) == 20
    assert all(g in shown for g in groups[20:25]) and groups[-1] not in shown


def test_fragment_outcome_reads_real_variant_rows():
    """Live-run crash (2026-09-25): VariantRow had no grade_rule, so an indeterminate site in the
    whole-fragment table raised AttributeError. Built from real rows, not stand-ins."""
    from qpcr_assay_check.report.grouping import fragment_outcome
    from qpcr_assay_check.specificity.variants import _variant_row

    from .test_exclusivity import site

    def row(role, grade, rule="", n_mismatch=0):
        s = site(1, role, "critical").model_copy(
            update={"grade": grade, "grade_rule": rule, "n_mismatch": n_mismatch}
        )
        return _variant_row(s, 1, 1)

    ok_f, ok_r = row("forward", "perfect"), row("reverse", "perfect")
    mgb = row("probe", "indeterminate", "R9", 1)
    assert mgb.grade_rule == "R9"
    assert fragment_outcome(_frag(ok_f, mgb, ok_r, 1))[0] == "undetermined"
    gap = row("probe", "indeterminate", "R5")
    assert fragment_outcome(_frag(ok_f, gap, ok_r, 1))[0] == "at risk"


def test_a_frequent_problem_is_never_pushed_out_by_single_genome_failures():
    """Live enterovirus run: 30 one-genome likely failures filled Part A and an at-risk
    combination in 283 genomes (Poliovirus 2) ended up in a grouped row."""
    from qpcr_assay_check.report.grouping import fragment_view

    ok, bad, risk = _site("perfect"), _site("likely_failure", 1), _site("at_risk", 2)
    frags = [_frag(bad, ok, ok, 1, org=f"EV{i}") for i in range(40)]
    frags += [_frag(risk, ok, ok, 283, org="Poliovirus 2"), _frag(risk, ok, ok, 2, org="CVA6")]
    v = fragment_view(frags, sum(f.count for f in frags))
    listed = [(o, f.count) for f, o, _p in v.attention]
    assert len(listed) == 30 and ("at risk", 283) in listed and ("at risk", 2) in listed
    assert listed[0][0] == "likely failure"  # shown worst outcome first
    # the 12 single-genome failures not listed: one row, with its main types
    ((outcome, kinds, n, c, n_kinds),) = v.attention_grouped
    assert (outcome, n, c, n_kinds, len(kinds)) == ("likely failure", 12, 12, 12, 3)


def test_risky_variants_seen_once_are_one_row_per_class():
    """Live enterovirus run (user, 2026-09-25): 30-52 rows per oligo, mostly single records."""
    from qpcr_assay_check.report.grouping import oligo_view

    def row(grade, count, org="EV"):
        return NS(grade=grade, count=count, n_mismatch=1, n_gap=0, example_organism=org)

    rows = [row("perfect", 90), row("at_risk", 5), row("likely_failure", 1, "PV1"),
            row("likely_failure", 1, "PV2"), row("at_risk", 1),
            row("indeterminate", 2)]  # fmt: skip
    rows[0].n_mismatch = 0
    v = oligo_view(NS(role="forward", total_measured=100, rows=rows))
    assert [(r.grade, r.count) for r in v.rows] == [("at_risk", 5), ("indeterminate", 2)]
    assert [(g, n) for g, n, _o in v.singles] == [("likely_failure", 2), ("at_risk", 1)]
    assert v.n_perfect == 90


def test_spec_overview_names_the_discriminating_primer_and_its_completeness():
    """Advisor 2026-09-25: per tier, products yes/no, which primer discriminates, its closest
    site, and whether a cut can concern that primer (enterovirus: F1/F2 vs rhinovirus)."""
    from qpcr_assay_check.report.grouping import spec_overview

    from .test_exclusivity import site

    fwd = site(1, "forward", "warning", tier="near_neighbours", site_id="S1").model_copy(
        update={"n_mismatch": 2, "clean_3prime_nt": 4}
    )
    rev = site(1, "reverse", "critical", tier="near_neighbours", site_id="S2")
    prb = site(1, "probe", "critical", tier="near_neighbours", site_id="S3")
    counts = [NS(tier="near_neighbours", query="R", truncated=True),
              NS(tier="near_neighbours", query="F", truncated=False)]  # fmt: skip
    spec = NS(amplicons=[], sites=[fwd, rev, prb], counts=counts)
    assay = NS(target=NS(must_not_detect_taxids=[1]),
               role_of=lambda q: {"F": "forward", "R": "reverse", "P": "probe"}[q])  # fmt: skip
    rows = [{"tier": "near_neighbours", "taxids": [1, 2], "saturated": ["P"]}]
    (t,) = spec_overview(spec, assay, rows)
    assert (t.title, t.products, t.discriminating) == ("Must not detect", 0, ["forward"])
    assert set(t.by_design) == {"reverse", "probe"} and t.closest["forward"] is fwd
    assert t.incomplete == ["P", "R"] and t.discriminating_complete


def test_history_site_changes_are_grouped_and_minor_ones_only_counted():
    """Live Neisseria run (user, 2026-09-25): 1,450 single rows of mostly minor human sites made
    the report 800 kB."""
    from qpcr_assay_check.report.grouping import site_change_view

    def ch(kind, level, acc, org="Homo sapiens", tier="background", role="forward"):
        before = level if kind != "new" else None
        after = level if kind != "resolved" else None
        return NS(kind=kind, tier=tier, role=role, accession=acc, orientation="+",
                  subject_start=1, subject_end=17, organism=org, level_before=before,
                  level_after=after, n_mismatch_before=1, n_mismatch_after=1)  # fmt: skip

    new = [ch("new", "minor", f"M{i}") for i in range(1400)]
    new += [ch("new", "critical", "C1"), ch("new", "warning", "W1"), ch("new", "warning", "W2")]
    new += [ch("new", "critical", "N1", org="Neisseria meningitidis", tier="exclusivity")]
    resolved = [ch("resolved", "minor", "R1"), ch("resolved", "warning", "R2")]
    v = site_change_view(new, resolved, [])
    assert v.minor == {"new": 1400, "resolved": 1}
    rows = [(g.kind, g.tier, g.organism, g.n_sites) for g in v.groups]
    assert rows == [("new", "exclusivity", "Neisseria meningitidis", 1),
                    ("new", "background", "Homo sapiens", 3),
                    ("resolved", "background", "Homo sapiens", 1)]  # fmt: skip
    assert v.groups[1].example.accession == "C1"  # the critical one is the example
