"""Exhaustive variant analysis (v1.1.0): locate, store, collect with a budget, assess, report."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from openpyxl import load_workbook

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import InputError
from qpcr_assay_check.inclusivity.models import fragment_window
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.settings import Credentials
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.report.xlsx import write_workbook
from qpcr_assay_check.variants.chain import Reference, is_copy, locate
from qpcr_assay_check.variants.datasets import DatasetsClient
from qpcr_assay_check.variants.exhaustive import reference_amplicon, run_exhaustive
from qpcr_assay_check.variants.genomestore import GenomeStore
from qpcr_assay_check.variants.locate import find_masked
from qpcr_assay_check.verdict import STATUS_LABEL, Verdict

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .fake_datasets import FakeAssembly, FakeDatasets
from .world import filler, mutate

NOW = datetime(2026, 9, 23, tzinfo=UTC)
# A SYNTHETIC amplicon: the CDC N1 oligos with random spacers. Not a real sequence.
AMP = F + filler(30, 11) + P + filler(30, 12) + iupac.reverse_complement(R)
# a 3'-terminal forward-primer mismatch plus one at -5 (rule R3: likely failure); a single
# terminal T-T is G2, at risk since 2026-10-02, so it would no longer be an escape
F_VARIANT = mutate(F, [16, 20])


def genome(seed: int, amp: str = AMP, *, reverse: bool = False) -> dict[str, str]:
    seq = filler(3000, seed) + amp + filler(3000, seed + 1)
    return {f"CTG{seed}.1": iupac.reverse_complement(seq) if reverse else seq}


def assemblies() -> list[FakeAssembly]:
    variant = AMP.replace(F, F_VARIANT, 1)
    broken = filler(3000, 7) + AMP[:60]
    return [
        FakeAssembly("GCF_000000001.1", "2024-03-01", genome(1)),
        FakeAssembly("GCF_000000002.1", "2025-05-01", genome(2, reverse=True)),
        FakeAssembly("GCA_000000003.1", "2026-01-15", genome(3, variant)),
        FakeAssembly("GCA_000000004.1", "2026-02-01", {"CTG4.1": filler(6000, 4)}),  # absent
        FakeAssembly("GCA_000000005.1", "2026-03-01",
                     {"CTG5a.1": broken, "CTG5b.1": AMP[60:] + filler(3000, 8)}),
    ]  # fmt: skip


def setup(tmp_path, *, budget: int = 20000, fake: FakeDatasets | None = None, key=None):
    cfg = load_config()
    cfg.variants.max_assemblies_per_run = budget
    cfg.ncbi.datasets_batch_size = 2
    fake = fake or FakeDatasets(assemblies())
    http = NcbiHttp(cfg.ncbi, Credentials("lab@example.org", key), session=fake,
                    sleep=lambda s: None, jitter=lambda: 0.0)  # fmt: skip
    client = DatasetsClient(http, cfg.ncbi.datasets_url)
    assay = make_assay(reference_amplicon=AMP, target={"taxid": 813})
    return cfg, fake, client, assay


def run(tmp_path, cfg, client, assay):
    return run_exhaustive(assay, cfg, client, tmp_path / "cache", _no_fetch, now=NOW)


def _no_fetch(acc: str) -> str:
    raise AssertionError("the reference amplicon was given; nothing should be fetched")


# ------------------------------------------------------------------ locate
def test_the_amplicon_is_found_on_either_strand_and_despite_a_primer_mismatch():
    def one(contigs):
        (c,) = [c for c in locate(contigs, [Reference(AMP)]) if is_copy(c)]
        return c

    fwd, rev = one(genome(1)), one(genome(2, reverse=True))
    var = one(genome(3, AMP.replace(F, F_VARIANT, 1)))
    assert not any(c.cut for c in (fwd, rev, var))
    assert fwd.strand == "+" and rev.strand == "-"
    for c in (fwd, rev):  # read in the fragment's sense
        assert c.region[c.start - c.region_start :][: len(AMP)] == AMP
    assert var.region[var.start - var.region_start :][: len(F)] == F_VARIANT


def test_a_contig_break_is_flagged_and_an_absent_region_finds_nothing():
    broken = {"a": filler(3000, 7) + AMP[:60], "b": AMP[60:] + filler(3000, 8)}
    found = [c for c in locate(broken, [Reference(AMP)]) if is_copy(c)]
    assert len(found) == 2 and all(c.cut for c in found)
    assert locate({"x": filler(6000, 4)}, [Reference(AMP)]) == []


# ------------------------------------------------------------------ the whole flow
def test_every_assembly_is_accounted_for_and_the_variant_is_counted(tmp_path):
    cfg, fake, client, assay = setup(tmp_path)
    res = run(tmp_path, cfg, client, assay)
    c = res.coverage
    assert (c.listed_total, c.assessed_total, c.processed_this_run) == (5, 5, 5)
    assert c.complete and (c.found, c.not_found, c.contig_break) == (3, 1, 1)
    assert c.not_found_examples == ["GCA_000000004.1"]
    assert {(y.year, y.listed, y.assessed) for y in c.years} == {
        (2026, 3, 3), (2025, 1, 1), (2024, 1, 1)
    }  # fmt: skip
    fwd = [s for s in res.sites if s.role == "forward"]
    assert sorted(s.n_mismatch for s in fwd) == [0, 0, 2]
    variant = next(s for s in fwd if s.n_mismatch)
    assert variant.accession == "GCA_000000003.1" and variant.terminal_defect
    rev_site = next(
        s for s in res.sites if s.accession == "GCF_000000002.1" and s.role == "forward"
    )
    assert rev_site.orientation == "-" and rev_site.n_mismatch == 0  # genome stored reverse


def test_one_copy_per_genbank_refseq_pair_and_the_api_key_header_are_requested(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, key="secret-key")
    run(tmp_path, cfg, client, assay)
    reports = [c for c in fake.calls if c["url"].endswith("/dataset_report")]
    assert all(c["params"]["filters.exclude_paired_reports"] == "true" for c in reports)
    assert all(c["params"]["filters.assembly_version"] == "current" for c in reports)
    assert all(c["headers"].get("api-key") == "secret-key" for c in fake.calls)
    assert all("email" not in c["params"] for c in fake.calls)


def test_a_budget_processes_the_newest_first_and_the_next_run_resumes(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, budget=3)
    first_result = run(tmp_path, cfg, client, assay)
    first = first_result.coverage
    assert "2025: 1 assembly listed, 0 assessed so far" in " ".join(
        first_result.inclusivity.rationale
    )
    assert "BLAST" not in " ".join(first_result.inclusivity.rationale)
    assert (first.processed_this_run, first.assessed_total, first.complete) == (3, 3, False)
    assert {y.year: y.assessed for y in first.years} == {2026: 3, 2025: 0, 2024: 0}
    n_downloads = len(fake.downloads)
    second = run(tmp_path, cfg, client, assay).coverage
    assert (second.processed_this_run, second.assessed_total, second.complete) == (2, 5, True)
    third = run(tmp_path, cfg, client, assay).coverage
    assert third.processed_this_run == 0
    # one download per release-year window (2025, 2024); nothing is ever downloaded twice
    assert len(fake.downloads) == n_downloads + 2


def test_a_failed_download_is_retried_on_the_next_run(tmp_path):
    fake = FakeDatasets(assemblies(), missing_from_download={"GCF_000000001.1"})
    cfg, fake, client, assay = setup(tmp_path, fake=fake)
    c = run(tmp_path, cfg, client, assay).coverage
    assert (c.download_failed_this_run, c.assessed_total, c.complete) == (1, 4, False)
    fake.missing_from_download.clear()
    assert run(tmp_path, cfg, client, assay).coverage.complete


def test_an_assembly_that_keeps_failing_is_left_out_without_blocking_completion(tmp_path):
    """Live Neisseria runs (user, 2026-09-26): the same 39 downloads failed on every run, so the
    analysis stayed 'incomplete' with 'run again to continue' forever."""
    fake = FakeDatasets(assemblies(), missing_from_download={"GCF_000000001.1"})
    cfg, fake, client, assay = setup(tmp_path, fake=fake)
    first = run(tmp_path, cfg, client, assay).coverage
    assert (first.unavailable, first.complete) == (0, False)  # one failure: try again
    second = run(tmp_path, cfg, client, assay).coverage
    assert second.download_failed_this_run == 1  # still tried
    assert (second.unavailable, second.complete) == (1, True)
    assert second.unavailable_examples == ["GCF_000000001.1"]
    res = run(tmp_path, cfg, client, assay)
    result = evaluate(assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
                      release_dates=res.release_dates, inclusivity=res.inclusivity,
                      specificity=_empty_specificity())  # fmt: skip
    text = " ".join(result.findings) if hasattr(result, "findings") else result.model_dump_json()
    assert "could not be downloaded after repeated attempts" in text
    assert "Run again to continue" not in text
    assert "could not be downloaded after repeated attempts" in render_report(result, cfg)
    fake.missing_from_download.clear()  # available again: stored, no longer unavailable
    third = run(tmp_path, cfg, client, assay).coverage
    assert (third.unavailable, third.assessed_total, third.complete) == (0, 5, True)


def test_the_region_store_survives_a_restart(tmp_path):
    cfg, fake, client, assay = setup(tmp_path)
    run(tmp_path, cfg, client, assay)
    (path,) = (tmp_path / "cache" / "genomes").glob("813-*.jsonl")
    key = json.loads(path.read_text().splitlines()[0])["key"]
    store = GenomeStore(path, key)
    assert len(store.items) == 5 and "GCA_000000004.1" in store
    assert not store.items["GCA_000000004.1"].copies
    assert all(len(c.region) < 400 for r in store.items.values() for c in r.copies)  # no genomes
    downloads = len(fake.downloads)
    run(tmp_path, cfg, client, assay)  # a second run: everything from the store
    assert len(fake.downloads) == downloads
    cfg.variants.min_anchored_bases = 40  # a copy-rule setting: judged again, not re-downloaded
    run(tmp_path, cfg, client, assay)
    assert len(fake.downloads) == downloads
    cfg.variants.seed_step = 3  # a scan setting: another store key, every genome scanned again
    run(tmp_path, cfg, client, assay)
    assert len(fake.downloads) > downloads


def test_no_assemblies_is_an_input_error_not_an_empty_pass(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets([]))
    with pytest.raises(InputError, match="no genome assemblies"):
        run(tmp_path, cfg, client, assay)


def test_the_reference_amplicon_can_be_cut_from_the_target_accession():
    seq = filler(500, 1) + AMP + filler(500, 2)
    assay = make_assay(target={"taxid": 813, "accession": "NC_000117.1"})
    amp, source = reference_amplicon(
        assay, lambda acc: f">{acc}\n{iupac.reverse_complement(seq)}\n"
    )
    assert amp == AMP and "NC_000117.1" in source
    with pytest.raises(InputError, match="reference_amplicon"):
        reference_amplicon(assay, lambda acc: f">{acc}\n{filler(900, 3)}\n")


# ------------------------------------------------------------------ report
def test_the_report_and_workbook_show_coverage_and_first_release_dates(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, budget=3)
    res = run(tmp_path, cfg, client, assay)
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    vs = result.variant_summary
    assert vs.source == "datasets"
    fwd = next(o for o in vs.oligos if o.role == "forward")
    variant = next(r for r in fwd.rows if r.n_mismatch)
    assert variant.first_seen == variant.last_seen == "2026-01-15"
    assert any("3 of 5 genome assemblies" in line for line in result.overall.rationale)
    html = render_report(result, cfg)
    assert "Scope: every genome assembly assessed so far." in html and "incomplete" in html
    assert "First / last release" in html
    write_workbook(result, tmp_path / "r.xlsx")
    rows = list(load_workbook(tmp_path / "r.xlsx")["Variant coverage"].iter_rows(values_only=True))
    assert ("Total", 5, 3) in rows


def _empty_specificity():
    from .test_report_exclusivity import _specificity_with_exclusivity

    return _specificity_with_exclusivity()


# ------------------------------------------------------------------ plasmid-borne targets
CHROM = "chromosome, complete genome"
PLASMID = "plasmid pCT, complete sequence"


def plasmid_assemblies() -> list[FakeAssembly]:
    def asm(acc, date, plasmid_seq):
        # a fixed seed per accession, away from the seeds AMP itself is built from (11, 12):
        # hash(acc) varied per process and, 1 run in about 125, gave a chromosome that begins
        # with 30 bases of the fragment (a real partial copy)
        contigs = {f"{acc}_chr": filler(4000, 500 + int(acc[4:7]))}
        desc = {f"{acc}_chr": f"Chlamydia trachomatis {CHROM}"}
        if plasmid_seq is not None:
            contigs[f"{acc}_pl"] = plasmid_seq
            desc[f"{acc}_pl"] = f"Chlamydia trachomatis {PLASMID}"
        return FakeAssembly(acc, date, contigs, descriptions=desc)

    return [
        asm("GCF_100.1", "2025-01-01", filler(500, 1) + AMP + filler(500, 2)),
        asm("GCF_101.1", "2025-02-01", filler(500, 3) + AMP + filler(500, 4)),
        asm("GCF_102.1", "2025-03-01", None),  # chromosome only: says nothing about the strain
        asm("GCF_103.1", "2026-01-01", filler(1200, 5)),  # plasmid without the region: review
    ]


def test_a_plasmid_target_separates_missing_plasmids_from_a_missing_region(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(plasmid_assemblies()))
    res = run(tmp_path, cfg, client, assay)
    c = res.coverage
    assert c.target_on_plasmid is True and c.found == 2 and c.not_found == 2
    assert (c.not_found_without_plasmid, c.not_found_with_plasmid) == (1, 1)
    assert c.not_found_with_plasmid_examples == ["GCF_103.1"]
    assert any(PLASMID in h for h in c.plasmid_header_examples)
    assert any("plasmid sequence but not the target region" in r for r in res.inclusivity.rationale)
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    assert any("GCF_103.1" in line and "nvCT" in line for line in result.overall.rationale)
    html = render_report(result, cfg)
    assert "labelled as a plasmid but not the target region" in html and "GCF_103.1" in html
    assert "Inclusivity across the intended target (all genome assemblies)" in html
    write_workbook(result, tmp_path / "r.xlsx")
    rows = list(load_workbook(tmp_path / "r.xlsx")["Variant coverage"].iter_rows(values_only=True))
    assert any(
        str(r[0]).strip().startswith("...plasmid sequence present") and r[1] == 1 for r in rows
    )


def test_variant_tables_describe_the_match_in_words(tmp_path):
    cfg, fake, client, assay = setup(tmp_path)
    res = run(tmp_path, cfg, client, assay)
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    html = render_report(result, cfg)
    # per oligo (advisor 2026-09-25): perfect as one line, other variants by their changes
    i = html.index("<h3>Variants per oligo")
    per_oligo = html[i : html.index("<h2>", i)]
    assert "Perfect in <strong>" in per_oligo
    # the 3'-terminal forward mismatch is seen in one record: one row for its class
    assert "other likely failure variant, each seen in 1 record" in per_oligo
    assert html.index("<h3>Whole fragment") < i  # the whole fragment first
    # whole fragment (advisor layout 2026-09-25): the 3'-terminal forward mismatch needs attention
    i = html.index("<h3>Whole fragment")
    frag = html[i : html.index("<h2>", i)]
    assert "Needs attention" in frag and "likely failure" in frag and "Detectable (" in frag
    assert frag.index("likely failure") < frag.index("Detectable (")
    # the frequency of a non-perfect site variant sits next to its class
    assert 'title="this forward site variant, whatever the other sites are"' in frag


def test_exhaustive_inclusivity_explains_assemblies_without_the_region(tmp_path):
    cfg, fake, client, assay = setup(tmp_path)
    res = run(tmp_path, cfg, client, assay)
    # not found (GCA_4) stays out of the counts; cut by a contig end (GCA_5) is undetermined,
    # in the whole fragment as in the channels (user, 2026-10-01)
    assert any(
        "1 of 5 assessed assemblies are not in the counts above" in r
        for r in res.inclusivity.rationale
    )
    assert any(
        "carry the region but no site could be judged (cut by a contig end in 1" in r
        for r in res.inclusivity.rationale
    )
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    html = render_report(result, cfg)
    assert "<th>Assemblies</th><th>With region</th>" in html


# ------------------------------------------------------------------ history: new variants
def _evaluate(assay, cfg, res, now, previous=None):
    return evaluate(
        assay, cfg, now=now, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(), previous_run=previous,
    )  # fmt: skip


# ------------------------------------------------------------------ wholly masked (v1.1.1)
# Live: SARS-CoV-2 records with one run of 1,144 N over the whole N1 region (OZ558241.1) were
# reported as 'not found'. Synthetic stand-ins: the reference around the amplicon is LEFT/RIGHT.
LEFT, RIGHT = filler(1000, 50), filler(1000, 51)
REF = filler(2000, 60) + LEFT + AMP + RIGHT + filler(2000, 61)
HIDDEN = (
    filler(2000, 60) + LEFT[:600] + "N" * (400 + len(AMP) + 300) + RIGHT[300:] + filler(2000, 61)
)
KW = {"seed_length": 16, "flank": 50}


def test_a_region_wholly_hidden_by_n_is_placed_by_the_reference_around_it():
    assert locate({"c": HIDDEN}, [Reference(AMP)]) == []  # no real base of the fragment
    assert find_masked({"c": HIDDEN}, AMP, seed_step=4, **KW) == []
    for seq, strand in ((HIDDEN, "+"), (iupac.reverse_complement(HIDDEN), "-")):
        (c,) = locate({"c": seq}, [Reference(AMP, LEFT, RIGHT)])
        assert c.strand == strand and is_copy(c) and c.n_inside == len(AMP)
        assert c.start == 3000  # the fragment starts after 3000 bases (on its sense strand)


def test_real_bases_between_the_flanks_are_a_copy_to_judge_not_a_masked_one():
    divergent = LEFT + filler(len(AMP), 53) + RIGHT + "N" * 200  # divergent, or deleted
    (c,) = locate({"c": divergent}, [Reference(AMP, LEFT, RIGHT)])
    assert is_copy(c) and c.n_inside == 0 and c.anchored == 0  # judged: likely not detected
    assert locate({"c": HIDDEN}, [Reference(AMP)]) == []  # no context: no call


def _masked_setup(tmp_path):
    fake = FakeDatasets([
        FakeAssembly("GCF_000000001.1", "2024-03-01", genome(1)),
        FakeAssembly("GCA_000000009.1", "2026-04-01", {"CTG9.1": HIDDEN}),
        FakeAssembly("GCA_000000004.1", "2026-02-01", {"CTG4.1": filler(6000, 4)}),  # absent
    ])  # fmt: skip
    cfg, fake, client, _assay = setup(tmp_path, fake=fake)
    assay = make_assay(reference_amplicon=AMP, target={"taxid": 813, "accession": "NC_000117.1"})
    fetched: list[str] = []

    def fetch(acc: str) -> str:
        fetched.append(acc)
        return f">{acc}\n{REF}\n"

    def go():
        return run_exhaustive(assay, cfg, client, tmp_path / "cache", fetch, now=NOW)

    return go, fetched, fake


def test_a_wholly_masked_assembly_is_counted_as_hidden_by_n_not_as_not_found(tmp_path):
    go, fetched, _fake = _masked_setup(tmp_path)
    c = go().coverage
    assert (c.found, c.masked, c.not_found) == (1, 1, 1)
    assert c.masked_examples == ["GCA_000000009.1"] and c.not_found_examples == ["GCA_000000004.1"]
    assert fetched == ["NC_000117.1"]  # the reference, once, only because something was not found
    assert go().coverage.masked == 1 and fetched == ["NC_000117.1"]  # nothing rescanned or fetched


def test_inclusivity_has_a_whole_fragment_row_per_year(tmp_path):
    """User 2026-09-25: next to the per-oligo tables, one table with the genome outcome of the
    three sites together; it agrees with the copy coverage."""
    cfg, fake, client, assay = setup(tmp_path)
    res = run(tmp_path, cfg, client, assay)
    years = res.inclusivity.fragment_years
    assert years and all(
        f.detectable + f.at_risk + f.likely_failure + f.undetermined == f.with_region for f in years
    )
    cc = res.coverage.copies
    assert sum(f.detectable for f in years) == cc.with_detectable_copy
    # plus the genomes with the region but no judged site (cut, or hidden by N)
    assert sum(f.undetermined for f in years) == cc.undetermined + sum(f.unjudged for f in years)
    assert sum(f.unjudged for f in years) == res.coverage.contig_break + res.coverage.masked
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    html = render_report(result, cfg)
    i = html.index('<h2 id="inclusivity">Inclusivity across')
    assert html.index("<h3>Whole fragment (forward + probe + reverse combined)</h3>", i) < (
        html.index("<h3>Forward</h3>", i)
    )
    # the window row uses the verdict's base (undetermined left out), so the numbers agree
    assert "Summary window " in html and "summary window</span>" in html
    assert "the same base as the summary" in html
    # the summary row gives the same figure as the inclusivity rationale
    from qpcr_assay_check.report.summary import summary_rows

    (row,) = [x for x in summary_rows(result, cfg, []) if x.check.startswith("Target detection")]
    w = fragment_window(result.inclusivity.fragment_years, cfg.inclusivity.verdict_window_years)
    assert row.result.startswith(f"{w.percent:.1f}% detectable")
    assert f"{w.n:,} genomes released {w.first}–{w.last}" in row.scope
    # 3 genomes only: too few to judge, and the row says why
    assert row.label == STATUS_LABEL[result.inclusivity.verdict] == "Incomplete"
    assert row.reason.startswith("Too few recent genomes")


def test_the_inclusivity_verdict_uses_the_whole_fragment_over_recent_years():
    """Advisor 2026-09-26 (built on the user's request): whole-fragment outcome pooled over the
    last 3 complete years plus the current one; too few genomes = INCOMPLETE; a single large
    year below the FAIL limit gives at least WARN; small years do not decide."""
    from qpcr_assay_check.inclusivity.models import FragmentYear
    from qpcr_assay_check.variants.exhaustive import fragment_verdict

    rules = load_config().inclusivity

    def year(y, det, risk=0, fail=0, undet=0):
        return FragmentYear(year=y, with_region=det + risk + fail + undet, detectable=det,
                            at_risk=risk, likely_failure=fail, undetermined=undet)  # fmt: skip

    good = [year(2014, 1, fail=4)] + [year(y, 98, risk=2) for y in range(2023, 2027)]
    verdict, lines = fragment_verdict(good, rules)
    assert verdict is Verdict.PASS and "2023-2026" in lines[0] and "98.0% detectable" in lines[0]
    # the old small year 2014 (1 of 5) does not decide; an undetermined genome is not counted
    warn = [year(y, 90, risk=8, fail=2, undet=5) for y in range(2023, 2027)]
    verdict, lines = fragment_verdict(warn, rules)
    assert verdict is Verdict.WARN and "90.0% detectable" in lines[0]
    assert "98.0% including at risk" in lines[0] and "not counted: 20" in lines[0]
    assert fragment_verdict([year(2026, 50, fail=50)], rules)[0] is Verdict.FAIL
    few = fragment_verdict([year(2026, 20)], rules)
    assert few[0] is Verdict.INCOMPLETE and "Too few recent genomes" in few[1][0]
    # one large year drops below the FAIL limit while the window passes: WARN
    drop = [year(y, 400) for y in range(2023, 2026)] + [year(2026, 20, fail=30)]
    verdict, lines = fragment_verdict(drop, rules)
    assert verdict is Verdict.WARN and any("Release year 2026 on its own" in x for x in lines)
    # the summary sentence names the status the section ends with (review 2026-09-27)
    assert "Status: Review (a single release year" in lines[0] and "No flags" not in lines[0]
    # a low year outside the window does not count (review 2026-09-27)
    old_low = [year(2016, 50, fail=150)] + [year(y, 300) for y in range(2023, 2027)]
    verdict, lines = fragment_verdict(old_low, rules)
    assert verdict is Verdict.PASS and len(lines) == 1 and "Status: No flags." in lines[0]
    # a pooled FAIL stays FAIL, without per-year lines
    low = [year(y, 50, fail=50) for y in range(2023, 2027)]
    verdict, lines = fragment_verdict(low, rules)
    assert verdict is Verdict.FAIL and len(lines) == 1 and "Status: Exceeds limit" in lines[0]


def test_unfinished_coverage_keeps_inclusivity_incomplete(tmp_path):
    """Code review 2026-09-27: while genomes are still waiting for the next run (per-run budget),
    target detection is Incomplete, never "no flags" (a figure below the FAIL limit stays FAIL)."""
    cfg, fake, client, assay = setup(tmp_path, budget=2)
    cfg.inclusivity.min_genomes_for_verdict = 1
    cfg.inclusivity.fail_below_percent = 0.0
    cfg.inclusivity.warn_below_percent = 0.0
    res = run(tmp_path, cfg, client, assay)
    assert not res.coverage.complete and res.inclusivity.verdict is Verdict.PASS
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    assert result.inclusivity.verdict is Verdict.INCOMPLETE
    assert "not assessed yet" in result.inclusivity.rationale[-1]


def test_detection_is_shown_per_assembly_level(tmp_path):
    """Advisor 2026-09-28: draft assemblies can leave repeat copies of a multi-copy target
    unassembled (the opa genes of GCF_000156755.1 sit in N gaps), so the coverage and every
    whole-fragment row give the assembly levels of their genomes."""
    from dataclasses import replace

    levels = ["Complete Genome", "Chromosome", "Contig", "Contig", "Scaffold"]
    fake = FakeDatasets([replace(a, level=lv) for a, lv in zip(assemblies(), levels, strict=True)])
    cfg, fake, client, assay = setup(tmp_path, fake=fake)
    res = run(tmp_path, cfg, client, assay)
    by_level = {lv.level: lv for lv in res.coverage.copies.by_level}
    assert list(by_level) == ["Complete Genome", "Chromosome", "Contig"]  # complete first
    assert (
        by_level["Complete Genome"].detectable == 1 and by_level["Complete Genome"].percent == 100
    )
    contig = by_level["Contig"]  # GCA_3 (primer variant); GCA_4 has no region
    assert contig.genomes == 1 and contig.detectable + contig.escapes + contig.undetermined == 1
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    rows = result.variant_summary.fragments
    assert sorted(lv for f in rows for lv, _ in f.levels) == [
        "Chromosome", "Complete Genome", "Contig"
    ]  # fmt: skip
    html = render_report(result, cfg)
    assert "<h4>Detection by assembly level</h4>" in html
    write_workbook(result, tmp_path / "r.xlsx")
    wb = load_workbook(tmp_path / "r.xlsx")
    header = [c.value for c in wb["Fragment variants"][1]]
    assert "Assembly levels" in header
    # one level only (e.g. Nucleotide records): no breakdown
    from qpcr_assay_check.variants.exhaustive import GenomeCall, _level_coverage

    def call(acc, level):
        return GenomeCall(acc, 1, 1, True, 1, {}, {"forward": True}, assembly_level=level)

    assert _level_coverage([call("A", "Nucleotide record"), call("B", "Nucleotide record")]) == []
    assert len(_level_coverage([call("A", "Contig"), call("B", "Scaffold")])) == 2


# ------------------------------------------------------------------ copies possibly unassembled
def _call(acc, level, copies, *, ok=True, contigs=40, truncated=0, sig=("a",)):
    from qpcr_assay_check.variants.exhaustive import GenomeCall

    good = dict.fromkeys(("forward", "reverse", "probe"), ok)
    state = dict.fromkeys(good, "ok" if ok else "fail")
    return GenomeCall(acc, copies, copies if ok else 0, True, copies if ok else 0, {}, good,
                      role_state=state, assembly_level=level, n_truncated=truncated,
                      n_contigs=contigs, signature=sig)  # fmt: skip


def test_a_draft_with_far_fewer_copies_than_complete_genomes_is_not_an_escape():
    """User decision 2026-09-28 (advisor): N. gonorrhoeae GCF_000156755.1 has its opa genes as
    scaffold gaps and was judged by the one divergent copy that was assembled."""
    from qpcr_assay_check.variants.exhaustive import copy_coverage, mark_unassembled

    complete = [_call(f"C{i}", "Complete Genome", 6) for i in range(5)]
    draft = _call("D1", "Contig", 1, ok=False, sig=("divergent",))
    few = _call("D2", "Contig", 3, ok=False, sig=("divergent",))  # 3 of 6: not "far fewer"
    whole = _call("D3", "Contig", 1, ok=False, contigs=1, sig=("divergent",))  # one sequence
    calls = [*complete, draft, few, whole]
    assert mark_unassembled(calls) == 6.0
    assert [c.accession for c in calls if c.unassembled] == ["D1"]
    cc = copy_coverage(calls, make_assay(), "any")
    assert cc.unassembled == 1 and cc.unassembled_accessions == ["D1"] and cc.escapes == 2
    contig = next(lv for lv in cc.by_level if lv.level == "Contig")
    assert (contig.unassembled, contig.escapes, contig.percent) == (1, 2, 0.0)

    # a complete genome failing with the same three sites: the pattern is real, an escape
    calls = [*complete[:4], _call("C9", "Complete Genome", 6, ok=False, sig=("divergent",)),
             _call("D1", "Contig", 1, ok=False, sig=("divergent",))]  # fmt: skip
    mark_unassembled(calls)
    assert not any(c.unassembled for c in calls)


def test_the_unassembled_rule_stays_off_where_it_has_no_basis():
    from qpcr_assay_check.variants.exhaustive import mark_unassembled

    def draft():
        return _call("D", "Contig", 1, ok=False)

    single = [_call(f"C{i}", "Complete Genome", 1) for i in range(5)] + [draft()]
    assert mark_unassembled(single) is None and not single[-1].unassembled  # single-copy target
    few_complete = [_call(f"C{i}", "Complete Genome", 6) for i in range(4)] + [draft()]
    assert mark_unassembled(few_complete) is None  # fewer than 5 complete genomes
    off = [_call(f"C{i}", "Complete Genome", 6) for i in range(5)] + [draft()]
    assert mark_unassembled(off, "off") is None and not off[-1].unassembled


def test_possibly_unassembled_genomes_are_undetermined_in_the_tables(tmp_path):
    cfg, fake, client, assay = setup(tmp_path)
    res = run(tmp_path, cfg, client, assay)
    escape = "GCA_000000003.1"  # the primer variant: likely failure
    from qpcr_assay_check.variants.exhaustive import _fragment_years

    years = _fragment_years(res.sites, {escape: 2026}, {2026: 1}, [2026], False, {escape})
    assert (years[0].undetermined, years[0].unassembled, years[0].likely_failure) == (1, 1, 0)

    res.coverage.copies.unassembled_accessions = [escape]
    res.coverage.copies.unassembled = 1
    res.coverage.copies.typical_copies = 6.0
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    (row,) = [f for f in result.variant_summary.fragments if f.unassembled]
    assert row.example_accession == escape
    from qpcr_assay_check.report.grouping import fragment_view

    fv = fragment_view(result.variant_summary.fragments, result.variant_summary.fragment_total)
    assert fv.records["possibly unassembled"] == 1 and fv.records.get("likely failure", 0) == 0
    html = render_report(result, cfg)
    assert "Copies possibly unassembled" in html and "1 possibly unassembled" in html
    write_workbook(result, tmp_path / "r.xlsx")
    assert "Unassembled" in load_workbook(tmp_path / "r.xlsx").sheetnames


def test_the_unassembled_rule_agrees_across_every_view(tmp_path):
    """Code review 2026-09-28: one real run with the rule active; coverage, the per-level table,
    the per-year table, the fragment rows and the channel counts judge the same genomes the
    same way."""
    from qpcr_assay_check.report.grouping import fragment_view

    variant = AMP.replace(F, F_VARIANT, 1)

    def multi(seed):  # three copies, as a complete genome of a multi-copy target carries
        return {f"CHR{seed}.1": "".join(filler(1500, seed + i) + AMP for i in range(3))
                + filler(1500, seed + 9)}  # fmt: skip

    fakes = [FakeAssembly(f"GCF_00000010{i}.1", "2025-06-01", multi(20 * i),
                          level="Complete Genome" if i < 4 else "Chromosome")
             for i in range(5)]  # fmt: skip
    fakes += [
        # a draft with one failing copy and more than one sequence: possibly unassembled
        FakeAssembly("GCA_000000200.1", "2026-02-01",
                     {"C1.1": filler(2000, 201) + variant + filler(2000, 202),
                      "C2.1": filler(3000, 203)}, level="Contig"),
        # one sequence only: no evidence of an incomplete assembly, a real escape
        FakeAssembly("GCA_000000300.1", "2026-03-01",
                     {"S1.1": filler(2000, 301) + variant + filler(2000, 302)}, level="Scaffold"),
    ]  # fmt: skip
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(fakes))
    res = run(tmp_path, cfg, client, assay)
    cc = res.coverage.copies
    assert cc.typical_copies == 3.0
    assert cc.unassembled_accessions == ["GCA_000000200.1"] and cc.escapes == 1
    by_level = {lv.level: lv for lv in cc.by_level}
    assert (by_level["Contig"].unassembled, by_level["Scaffold"].escapes) == (1, 1)
    assert sum(y.unassembled for y in res.inclusivity.fragment_years) == 1
    assert sum(y.likely_failure for y in res.inclusivity.fragment_years) == 1  # the Scaffold

    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    (row,) = [f for f in result.variant_summary.fragments if f.forward.n_mismatch]
    assert (row.count, row.unassembled) == (2, 1)
    fv = fragment_view(result.variant_summary.fragments, result.variant_summary.fragment_total)
    assert fv.records["possibly unassembled"] == 1 and fv.records["likely failure"] == 1
    write_workbook(result, tmp_path / "r.xlsx")
    rows = [[c.value for c in r] for r in load_workbook(tmp_path / "r.xlsx")["Copies and coverage"]
            .iter_rows() if str(r[0].value).startswith("Assembly level Contig")]  # fmt: skip
    assert rows and "1 possibly unassembled" in rows[0][4]

    (ch,) = res.coverage.channel_results
    assert (ch.undetermined, ch.not_detected) == (1, 1)
    assert ch.not_detected_examples == ["GCA_000000300.1"]


def test_every_reporter_channel_is_shown_on_the_fragment_rows(tmp_path):
    """User 2026-09-28 (Legionella genus VIC + L. pneumophila FAM probe): the fragment rows
    showed only the best-binding probe, so the other channel was invisible."""
    cfg, fake, client, _assay = setup(tmp_path)
    p2 = mutate(P, [3, 8, 13])  # a second channel whose probe differs from the amplicon
    assay = make_assay(
        reference_amplicon=AMP, target={"taxid": 813},
        probe=[{"name": "P1", "sequence": P, "reporter": "FAM"},
               {"name": "P2", "sequence": p2, "reporter": "HEX"}],
    )  # fmt: skip
    res = run(tmp_path, cfg, client, assay)
    probes = [s for s in res.sites if s.role == "probe"]
    assert probes and all(len(s.channel_sites) == 2 for s in probes)
    assert "channel_sites" not in probes[0].model_dump()  # not serialised
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    for f in result.variant_summary.fragments:
        assert [rep for rep, _v in f.channels] == ["FAM", "HEX"]
        fam, hex_ = (v for _r, v in f.channels)
        assert (fam.oligo_name, hex_.oligo_name) == ("P1", "P2") and hex_.n_mismatch == 3
    html = render_report(result, cfg)
    assert '<div class="channel"><span class="meta">HEX</span>' in html
    write_workbook(result, tmp_path / "r.xlsx")
    ws = load_workbook(tmp_path / "r.xlsx")["Fragment variants"]
    col = [c.value for c in ws[1]].index("Probe per channel")
    assert "HEX P2:" in ws[2][col].value

    # one channel only: nothing extra
    single = run(tmp_path, cfg, client, make_assay(reference_amplicon=AMP, target={"taxid": 813}))
    assert not any(s.channel_sites for s in single.sites)


def _split_fixture(right=AMP[60:]):
    """GCA_7: the fragment split over two contigs (as at an rRNA operon in a draft): the forward
    primer and probe whole at the end of one, the reverse primer whole at the start of the other."""
    split = FakeAssembly(
        "GCA_000000007.1",
        "2026-04-01",
        {"L7.1": filler(3000, 71) + AMP[:80], "R7.1": right + filler(3000, 72)},
    )
    return FakeDatasets([*assemblies(), split])  # fmt: skip


def test_a_fragment_split_over_contigs_is_judged_from_its_parts(tmp_path):
    """User decision 2026-09-28 (option 1 of the contig-edge problem; advisor: its own class)."""
    from qpcr_assay_check.report.grouping import fragment_view

    cfg, fake, client, assay = setup(tmp_path, fake=_split_fixture())
    cfg.variants.judge_from_parts = "undetermined"  # the default is "detectable" since 2026-10-01
    res = run(tmp_path, cfg, client, assay)
    cc, split = res.coverage.copies, "GCA_000000007.1"
    assert cc.from_parts_accessions == [split] and not cc.from_parts_counted
    assert res.coverage.contig_break == 1  # GCA_5: its probe site is cut, so still cut
    assert split not in cc.escape_examples and cc.with_detectable_copy == 2
    assert sum(y.from_parts for y in res.inclusivity.fragment_years) == 1
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    fv = fragment_view(result.variant_summary.fragments, result.variant_summary.fragment_total)
    assert fv.records["detectable from parts"] == 1 and fv.records["detectable"] == 2
    html = render_report(result, cfg)
    assert "Detectable from parts" in html and "1 detectable from parts (undetermined)" in html
    write_workbook(result, tmp_path / "r.xlsx")
    assert "From parts" in load_workbook(tmp_path / "r.xlsx").sheetnames


def test_judging_from_parts_follows_its_setting_and_needs_detectable_sites(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, fake=_split_fixture())
    cfg.variants.judge_from_parts = "detectable"
    res = run(tmp_path, cfg, client, assay)
    assert res.coverage.copies.from_parts_counted and res.coverage.copies.with_detectable_copy == 3
    cfg.variants.judge_from_parts = "off"
    assert run(tmp_path, cfg, client, assay).coverage.contig_break == 2

    # the reverse site on the cut copy fails (two mismatches in the 3' end): no judgement from parts
    bad = AMP[60:].replace(
        iupac.reverse_complement(R), iupac.reverse_complement(mutate(R, [20, 22]))
    )
    cfg2, _f, client2, assay2 = setup(tmp_path / "b", fake=_split_fixture(bad))
    res2 = run(tmp_path / "b", cfg2, client2, assay2)
    assert res2.coverage.copies.from_parts == 0 and res2.coverage.contig_break == 2
    # the channel counts judge them the same way (undetermined by default)
    cfg3, _f3, client3, assay3 = setup(tmp_path / "c", fake=_split_fixture())
    (ch,) = run(tmp_path / "c", cfg3, client3, assay3).coverage.channel_results
    assert ch.undetermined >= 1 and "GCA_000000007.1" not in ch.not_detected_examples


# ------------------------------------------------------------------ copy similarity threshold
def _related_region(seed: int) -> str:
    """Unrelated sequence around one 16-base stretch of the amplicon: a chance seed hit (as in
    L. pneumophila GCF_000586155.1, where such a region was judged instead of the target)."""
    return filler(300, seed) + AMP[40:56] + filler(300, seed + 1)


def test_a_region_found_through_one_chance_seed_is_not_a_copy(tmp_path):
    """Advisor 2026-09-28: identity to the reference amplicon >= 0.75 makes a copy."""
    from qpcr_assay_check.variants.locate import amplicon_identity

    (c,) = locate({"X": _related_region(81)}, [Reference(AMP)])
    assert c.anchored < 24 and c.identity < 0.7 and not is_copy(c)
    divergent = "".join(("A" if b != "A" else "C") if i % 5 == 2 else b for i, b in enumerate(AMP))
    ident = amplicon_identity(filler(50, 1) + divergent + filler(50, 2), AMP, 50)[0]
    assert 0.75 <= ident <= 0.85  # a real divergent copy (every 5th base changed) stays a copy

    extra = [
        FakeAssembly("GCA_000000008.1", "2026-05-01", {"U8.1": _related_region(81)}),
        FakeAssembly("GCA_000000009.1", "2026-05-01",  # a real copy next to a related region
                     {"A9.1": _related_region(91) + filler(500, 93) + AMP + filler(500, 94)}),
    ]  # fmt: skip
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets([*assemblies(), *extra]))
    res = run(tmp_path, cfg, client, assay)
    cov = res.coverage
    assert cov.related_only_examples == ["GCA_000000008.1"] and cov.related_ignored == 1
    assert "GCA_000000008.1" not in cov.copies.escape_examples
    assert cov.copies.with_detectable_copy == 3  # GCA_9 judged by its real copy
    assert any("only resembled by related regions in 1" in x for x in res.inclusivity.rationale)
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    assert "Related regions, not the target" in render_report(result, cfg)

    cfg.variants.min_copy_identity = 0.0  # off: the chance region is judged, as before
    assert run(tmp_path, cfg, client, assay).coverage.related_only == 0


def test_every_reference_is_tried_and_the_best_per_place_is_kept():
    other = filler(120, 55)  # a second lineage's fragment, present whole in this genome
    contigs = {"C": _related_region(81) + filler(400, 56) + other + filler(400, 57)}
    found = locate(contigs, [Reference(AMP), Reference(other)])
    copies = [c for c in found if is_copy(c)]
    assert [(c.ref, c.anchored) for c in copies] == [(1, 120)]
    assert any(c.ref == 0 and not is_copy(c) for c in found)  # the chance region: listed only


def test_review_fixes_for_parts_and_the_copy_threshold(tmp_path):
    """Code review of PR #29 (2026-09-28)."""
    import json

    # 1. detectable from parts (undetermined): out of the per-oligo and channel counts as well
    cfg, fake, client, assay = setup(tmp_path, fake=_split_fixture())
    cfg.variants.judge_from_parts = "undetermined"  # the default is "detectable" since 2026-10-01
    res = run(tmp_path, cfg, client, assay)
    cc = res.coverage.copies
    assert cc.from_parts == 1 and cc.with_detectable_copy == 2
    # GCA_3 (forward variant) still covers probe and reverse; GCA_7 is left out (was 4)
    assert {o.role: o.covered for o in cc.oligos} == {"forward": 2, "probe": 3, "reverse": 3}
    assert cc.any_channel == cc.all_channels == 3
    windows = [w for o in res.inclusivity.oligos for w in o.windows]
    # 2026: GCA_3 only (probe and reverse detectable); GCA_7 (from parts) would add 3
    assert sum(w.n_detectable for w in windows if w.year == 2026) == 2

    # 5. every stored copy with fragment bases anchored carries its identity
    (path,) = (tmp_path / "cache" / "genomes").glob("813-*.jsonl")
    last = {}
    for line in path.read_text().splitlines()[1:]:
        item = json.loads(line)
        last[item["accession"]] = item
    assert all(c["identity"] is not None for it in last.values() for c in it["copies"]
               if c["anchored"])  # fmt: skip

    # 3. an N in a cut copy's site is skipped, never chosen (was: the genome became "masked")
    nsplit = AMP[60:].replace(iupac.reverse_complement(R)[5], "N", 1)
    cfg2, _f, client2, assay2 = setup(tmp_path / "n", fake=_split_fixture(nsplit))
    res2 = run(tmp_path / "n", cfg2, client2, assay2)
    assert "GCA_000000007.1" not in res2.coverage.masked_examples

    # 4. a genome with only related regions has no locus (a draft: not an escape)
    extra = FakeAssembly("GCA_000000008.1", "2026-05-01", {"U8.1": _related_region(81)})
    cfg3, _f3, client3, assay3 = setup(tmp_path / "r", fake=FakeDatasets([*assemblies(), extra]))
    res3 = run(tmp_path / "r", cfg3, client3, assay3)
    (ch,) = res3.coverage.channel_results
    assert "GCA_000000008.1" in res3.coverage.related_only_examples
    assert "GCA_000000008.1" not in ch.not_detected_examples and ch.no_locus >= 1

    # 10. a region hidden by N wins over a chance-seed region elsewhere
    masked_amp = "".join("N" if i % 12 == 6 else b for i, b in enumerate(AMP))  # no clean seed
    contigs = {"C": _related_region(81) + filler(300, 5) + masked_amp + filler(300, 6)}
    found = locate(contigs, [Reference(AMP)])
    assert [c.masked for c in found if is_copy(c)] == [True]  # the chance region is no copy


def test_the_verdict_brackets_undetermined_genomes_and_refuses_when_they_dominate():
    """Theory reviews 2026-10-01: print the two extremes the undetermined genomes allow, and give
    no percentage status when they exceed inclusivity.max_undetermined_percent."""
    from qpcr_assay_check.inclusivity.models import FragmentYear
    from qpcr_assay_check.variants.exhaustive import fragment_verdict

    rules = load_config().inclusivity
    few = [FragmentYear(year=2026, with_region=200, detectable=185, at_risk=5,
                        likely_failure=0, undetermined=10)]  # fmt: skip
    verdict, lines = fragment_verdict(few, rules)
    assert verdict is Verdict.PASS
    assert any("92.5% detectable if all of them were escapes, 97.5% if all" in x for x in lines)
    many = [FragmentYear(year=2026, with_region=200, detectable=140, at_risk=0,
                         likely_failure=0, undetermined=60)]  # fmt: skip
    verdict, lines = fragment_verdict(many, rules)
    assert verdict is Verdict.INCOMPLETE and "30.0% of the genomes" in lines[0]
    rules.max_undetermined_percent = 40
    assert fragment_verdict(many, rules)[0] is Verdict.PASS


def test_a_channel_with_mostly_undetermined_genomes_is_incomplete():
    from qpcr_assay_check.variants.exhaustive import channel_verdict
    from qpcr_assay_check.variants.models import ChannelResult

    rules = load_config().inclusivity
    # the live Legionella genus channel (2026-09-30): 4,337 judged, 7,444 undetermined
    r = ChannelResult(name="Legionella", reporter="VIC", probes=["P"], target_taxid=444,
                      target_genomes=11911, detected=4155, not_detected=182,
                      undetermined=7444, no_locus=130)  # fmt: skip
    verdict, why = channel_verdict(r, rules)
    assert verdict is Verdict.INCOMPLETE and "undetermined" in why and "if all were" in why


def test_by_default_a_genome_detectable_from_parts_counts_as_detected(tmp_path):
    """User, 2026-10-01: every site was seen whole on the cut copies, for every assay."""
    cfg, fake, client, assay = setup(tmp_path, fake=_split_fixture())
    assert cfg.variants.judge_from_parts == "detectable"
    res = run(tmp_path, cfg, client, assay)
    cc = res.coverage.copies
    assert cc.from_parts_counted and cc.with_detectable_copy == 3
    years = res.inclusivity.fragment_years
    assert sum(y.from_parts for y in years) == 0  # not undetermined any more


def _split_with_a_bulge():
    """A genome with one whole copy that fails (a 3'-end forward mismatch) and a copy split over
    two contigs whose forward site carries a poly-A run one base longer: judged from parts only
    when run-length differences are tolerated."""
    left = AMP[:80].replace(F, F.replace("AAAA", "AAAAA", 1), 1)
    split = FakeAssembly(
        "GCA_000000008.1",
        "2026-05-01",
        {
            "W8.1": filler(2000, 80) + AMP.replace(F, F_VARIANT, 1) + filler(500, 83),
            "L8.1": filler(3000, 81) + left,
            "R8.1": AMP[60:] + filler(3000, 82),
        },
    )
    return FakeDatasets([*assemblies(), split])


def test_the_bulge_alternative_counts_the_genomes_judged_from_parts(tmp_path):
    """User decision 2026-10-07 (option 2): the figure under the other homopolymer-bulge rule
    judges from parts under that rule too. Without it a genome counted from parts is missing
    from the alternative, which could then fall below the headline - impossible over one
    cohort, since tolerating a run-length difference never loses a genome."""
    cfg, fake, client, assay = setup(tmp_path, fake=_split_fixture())
    assert cfg.variants.judge_from_parts == "detectable"
    res = run(tmp_path, cfg, client, assay)
    win = fragment_window(res.inclusivity.fragment_years, cfg.inclusivity.verdict_window_years)
    # the split genome has no bulge: detectable from parts under either rule, so the two agree
    assert (win.n, win.detectable, win.percent) == (4, 3, 75.0)
    assert res.inclusivity.bulge_alternative == 75.0
    assert not [x for x in res.inclusivity.rationale if x.startswith("Homopolymer setting:")]

    # a genome whose parts are detectable only when the run-length difference is tolerated
    cfg2, fake2, client2, assay2 = setup(tmp_path / "b", fake=_split_with_a_bulge())
    res2 = run(tmp_path / "b", cfg2, client2, assay2)
    cc = res2.coverage.copies
    split = "GCA_000000008.1"
    assert split not in cc.from_parts_accessions  # strict: its parts are not detectable
    assert split in cc.escape_examples  # strict: its whole copy fails, so it is an escape
    # tolerating the run-length difference makes its parts detectable, and that judgement is
    # now made under that rule too: one genome more
    assert cc.with_detectable_copy_bulges == cc.with_detectable_copy_strict + 1
    win2 = fragment_window(res2.inclusivity.fragment_years, cfg2.inclusivity.verdict_window_years)
    assert res2.inclusivity.bulge_alternative > win2.percent


def test_a_crossed_limit_is_held_back_while_genomes_are_still_to_assess():
    """User, 2026-10-07 ("Keep incomplete for now"), from an influenza run that read Exceeds
    limit at 76.9% on 45,000 of 172,768 records: the newest are assessed first, so a partial run
    is weighted to the most recent year and a figure can cross a limit and cross back. The
    sentence still names what the limit would have made it."""
    from qpcr_assay_check.inclusivity.models import FragmentYear
    from qpcr_assay_check.variants.exhaustive import fragment_verdict

    rules = load_config().inclusivity
    assert rules.limits_need_complete_coverage is True

    def year(y, det, fail=0):
        return FragmentYear(year=y, with_region=det + fail, detectable=det, likely_failure=fail)

    failing = [year(y, 70, fail=30) for y in range(2023, 2027)]
    reviewing = [year(y, 90, fail=10) for y in range(2023, 2027)]
    passing = [year(y, 99, fail=1) for y in range(2023, 2027)]
    # complete coverage: the limits decide, as before
    assert fragment_verdict(failing, rules)[0] is Verdict.FAIL
    assert fragment_verdict(reviewing, rules)[0] is Verdict.WARN
    # still assessing: held back, and the sentence says what it would have been
    for rows, label in ((failing, "Exceeds limit"), (reviewing, "Review")):
        verdict, lines = fragment_verdict(rows, rules, coverage_complete=False)
        assert verdict is Verdict.INCOMPLETE
        assert f"Status: Incomplete ({label}" in lines[0]
        assert "held back while genomes are still to assess" in lines[0]
    # the setting is named where it applies, and only there (code review 2026-10-08): it releases
    # an Exceeds limit, while a Review has waited since the code review of 2026-09-27
    fail_line = fragment_verdict(failing, rules, coverage_complete=False)[1][0]
    warn_line = fragment_verdict(reviewing, rules, coverage_complete=False)[1][0]
    assert "limits_need_complete_coverage" in fail_line
    assert "limits_need_complete_coverage" not in warn_line
    # a figure that crosses no limit is not touched, and neither is PASS
    assert fragment_verdict(passing, rules, coverage_complete=False)[0] is Verdict.PASS
    # the setting turns the hold-back off for the Exceeds limit, and only for it
    loose = rules.model_copy(update={"limits_need_complete_coverage": False})
    assert fragment_verdict(failing, loose, coverage_complete=False)[0] is Verdict.FAIL
    assert fragment_verdict(reviewing, loose, coverage_complete=False)[0] is Verdict.INCOMPLETE


def test_a_channel_cannot_file_a_crossed_limit_on_partial_coverage():
    """Code review 2026-10-08: the inclusivity status is the worst of the whole-assay figure and
    every channel, and combine ranks a crossed limit above INCOMPLETE, so a channel judging its
    own limits on a partial run would carry the status straight past the hold-back."""
    from qpcr_assay_check.variants.exhaustive import channel_verdict
    from qpcr_assay_check.variants.models import ChannelResult

    rules = load_config().inclusivity
    low = ChannelResult(name="L. pneumophila", probes=["LEGpneu"], target_taxid=446,
                        target_genomes=1000, detected=600, not_detected=400)  # fmt: skip
    assert channel_verdict(low, rules)[0] is Verdict.FAIL  # complete: the limit decides
    verdict, why = channel_verdict(low, rules, coverage_complete=False)
    assert verdict is Verdict.INCOMPLETE
    assert why.startswith("Exceeds limit on the genomes assessed so far (")
    assert "60.0% detected, below your limit of 80%" in why
    assert "held back while genomes are still to assess" in why
    loose = rules.model_copy(update={"limits_need_complete_coverage": False})
    assert channel_verdict(low, loose, coverage_complete=False)[0] is Verdict.FAIL
    ok = ChannelResult(name="genus", probes=["LEGgenus"], target_taxid=444,
                       target_genomes=1000, detected=1000)  # fmt: skip
    assert channel_verdict(ok, rules, coverage_complete=False) == (Verdict.PASS, "")
