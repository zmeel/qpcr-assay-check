"""Why a genome with the region has no judged site (user, 2026-10-02: the breakdown of the
Legionella genomes cut by a contig end). Information only: they stay undetermined."""

from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.variants.exhaustive import CUT_KINDS, cut_kind
from qpcr_assay_check.variants.store import StoredAssembly, StoredLocus

from .fake_datasets import FakeAssembly, FakeDatasets
from .test_variants_exhaustive import (
    AMP,
    F_VARIANT,
    NOW,
    F,
    P,
    _empty_specificity,
    assemblies,
    run,
    setup,
)
from .world import filler

# the forward site and the probe on one contig, the reverse site on the next (SYNTHETIC)
SPLIT = len(F) + 30 + len(P) + 10


def _split(seed: int, amp: str = AMP, at: int = SPLIT) -> dict[str, str]:
    return {f"CTG{seed}a.1": filler(3000, seed) + amp[:at],
            f"CTG{seed}b.1": amp[at:] + filler(3000, seed + 1)}  # fmt: skip


def _kinds(tmp_path, extra):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(assemblies() + extra))
    res = run(tmp_path, cfg, client, assay)
    return cfg, assay, res, {r.kind: r for r in res.coverage.cut_reasons}


def test_each_genome_without_a_judged_site_says_why(tmp_path):
    variant = AMP.replace(F, F_VARIANT, 1)
    extra = [
        # every site whole on the parts, but the forward one fails: not detectable from parts
        FakeAssembly("GCA_000000020.1", "2026-04-01", _split(20, variant)),
        # the reverse site cut off, the forward site whole but failing
        FakeAssembly(
            "GCA_000000021.1", "2026-04-01", _split(21, variant, len(AMP) - 10)
        ),  # fmt: skip
    ]
    cfg, assay, res, kinds = _kinds(tmp_path, extra)
    # GCA_5 of the shared fixture: cut at base 60, through the probe
    assert kinds["site_cut_ok:probe"].examples == ["GCA_000000005.1"]
    assert kinds["site_cut_ok:probe"].label.startswith("the probe site cut off")
    assert kinds["sites_fail"].examples == ["GCA_000000020.1"]
    assert kinds["site_cut_fail:reverse"].examples == ["GCA_000000021.1"]
    assert sum(r.genomes for r in res.coverage.cut_reasons) == res.coverage.contig_break == 3
    # still undetermined: the breakdown changes no count
    assert sum(f.unjudged for f in res.inclusivity.fragment_years) == 3
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    html = render_report(result, cfg)
    assert "Why no site could be judged" in html and "All of them stay undetermined" in html


def test_a_fragment_missing_from_the_assembly_and_a_copy_not_cut():
    def locus(truncated: bool, seeds: int) -> StoredLocus:
        return StoredLocus(contig="c", strand="+", start=1, end=40, region="A" * 40,
                           offset=30, n_seeds=seeds, truncated=truncated)  # fmt: skip

    def item(*loci):
        return StoredAssembly(accession="X.1", release_date="2026-01-01", status="found",
                              loci=list(loci))  # fmt: skip

    args = ([], None, None, None, {}, "any", False)
    assert cut_kind(item(locus(True, 0)), *args) == (
        "not_assembled", CUT_KINDS["not_assembled"]
    )  # fmt: skip
    assert cut_kind(item(locus(False, 40)), *args)[0] == "other"


def test_a_fragment_not_in_the_assembly_counts_as_not_found():
    from qpcr_assay_check.variants.exhaustive import fragment_not_assembled

    def locus(truncated: bool, seeds: int) -> StoredLocus:
        return StoredLocus(contig="c", strand="+", start=1, end=40, region="A" * 40,
                           offset=30, n_seeds=seeds, truncated=truncated)  # fmt: skip

    def item(acc, *loci):
        return StoredAssembly(accession=acc, release_date="2026-01-01", status="found",
                              n_loci=len(loci), loci=list(loci))  # fmt: skip

    items = [
        item("FLANK.1", locus(True, 0), locus(True, 0)),  # only flanks at contig ends
        item("PART.1", locus(True, 0), locus(True, 20)),  # part of the fragment assembled
        item("WHOLE.1", locus(False, 60)),
    ]
    out, moved = fragment_not_assembled(items)
    assert moved == ["FLANK.1"]
    assert [(it.status, it.n_loci) for it in out] == [("not_found", 0), ("found", 2),
                                                      ("found", 1)]  # fmt: skip
