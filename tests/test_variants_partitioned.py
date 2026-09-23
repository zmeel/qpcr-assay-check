"""Partitioned-BLAST variant source (v1.1.0): every Nucleotide record, BLASTed in lists."""

from __future__ import annotations

from datetime import UTC, datetime

from qpcr_assay_check.config import load_config
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.search.planner import plan_searches
from qpcr_assay_check.variants.exhaustive import run_exhaustive
from qpcr_assay_check.variants.partitioned import collect_partitioned

from .conftest import CDC_N1_F as F
from .conftest import make_assay
from .fake_nuccore import FakeNuccore, FakeRecord
from .test_variants_exhaustive import AMP, F_VARIANT, HIDDEN, REF
from .world import filler, make_runner

NOW = datetime(2026, 9, 23, tzinfo=UTC)


def records() -> list[FakeRecord]:
    def rec(uid, date, amp, *, minus=False, partial=False, seq=None):
        s = seq or filler(300, int(uid)) + amp + filler(300, int(uid) + 50)
        return FakeRecord(uid, f"MZ{uid:0>6}.1", date,
                          iupac.reverse_complement(s) if minus else s, partial=partial)  # fmt: skip

    return [
        rec("1", "2026/03/01", AMP),
        rec("2", "2026/05/01", AMP.replace(F, F_VARIANT, 1), minus=True),
        rec("3", "2025/02/01", AMP, partial=True),
        rec("4", "2025/07/01", "", seq=filler(900, 4)),  # another gene: no hit
        rec("5", "2024/01/01", AMP),
    ]


def setup(tmp_path, fake, *, assay=None, fetch_fasta=lambda a: "", **variants):
    cfg = load_config()
    cfg.variants.source = "blast_partitioned"
    for k, v in variants.items():
        setattr(cfg.variants, k, v)
    runner, jobs, fetcher = make_runner(cfg, tmp_path, fake)
    assay = assay or make_assay(reference_amplicon=AMP, target={"taxid": 2697049})

    def collector(store, taxon, amplicon, context):
        return collect_partitioned(
            fetcher.eutils, runner, jobs, fetcher, store, taxon, amplicon, cfg, now=NOW,
            context=context,
        )  # fmt: skip

    def run():
        return run_exhaustive(assay, cfg, None, tmp_path / "cache", fetch_fasta, now=NOW,
                              collector=collector, source="blast_partitioned")  # fmt: skip

    return run


def test_every_record_is_blasted_in_accession_lists_and_leaks_are_ignored(tmp_path):
    leak = FakeRecord("99", "OT999999.1", "2026/01/01", filler(200, 9) + AMP + filler(200, 10))
    fake = FakeNuccore(records(), leaks=[leak])
    res = setup(tmp_path, fake, direct_scan_max_length=0)()  # every record through BLAST
    c = res.coverage
    assert c.source == "blast_partitioned" and (c.listed_total, c.assessed_total) == (5, 5)
    assert (c.found, c.not_found) == (4, 1) and c.not_found_examples == ["MZ000004.1"]
    assert len(fake.blast_puts) == 3  # one list per publication year here (2026, 2025, 2024)
    assert "OT999999.1" not in res.release_dates  # the leak never enters the analysis
    fwd = sorted((s.accession, s.n_mismatch) for s in res.sites if s.role == "forward")
    assert fwd == [("MZ000001.1", 0), ("MZ000002.1", 1), ("MZ000003.1", 0), ("MZ000005.1", 0)]
    assert res.release_dates["MZ000002.1"] == "2026-05-01"  # createdate, not just the year
    assert "Nucleotide record" in res.inclusivity.sample_scheme


def test_a_partial_hit_is_completed_from_the_record(tmp_path):
    res = setup(tmp_path, FakeNuccore(records()), direct_scan_max_length=0)()
    site = next(s for s in res.sites if s.accession == "MZ000003.1" and s.role == "forward")
    assert site.n_mismatch == 0 and site.source == "realigned"  # the trimmed 8 bases re-aligned


def test_the_record_budget_and_list_size_are_honoured_and_runs_resume(tmp_path):
    fake = FakeNuccore(records())
    run = setup(tmp_path, fake, blast_max_records_per_run=2, blast_records_per_search=1,
                direct_scan_max_length=0)  # fmt: skip
    first = run().coverage
    assert (first.processed_this_run, first.assessed_total, first.complete) == (2, 2, False)
    assert len(fake.blast_puts) == 2  # one record per search
    second = run().coverage
    assert (second.processed_this_run, second.assessed_total) == (2, 4)
    third = run().coverage
    assert third.complete and third.processed_this_run == 1
    assert run().coverage.processed_this_run == 0 and len(fake.blast_puts) == 5


def test_the_search_plan_says_the_amplicon_is_sent_to_blast():
    cfg = load_config()
    cfg.variants.source = "blast_partitioned"
    plan = plan_searches(make_assay(), cfg)
    assert any("sending the reference amplicon to NCBI BLAST" in n for n in plan.notes)


def test_records_missing_from_the_blast_database_are_found_by_a_direct_scan(tmp_path):
    """Live finding: all 300 newest SARS-CoV-2 records had no BLAST hit (not in core_nt yet)."""
    recs = records()
    for r in recs:
        r.in_blast_db = False
    fake = FakeNuccore(recs)
    res = setup(tmp_path, fake)()
    c = res.coverage
    assert (c.found, c.not_found, c.found_by_direct_scan, c.not_checked_directly) == (4, 1, 4, 0)
    fwd = sorted((s.accession, s.n_mismatch) for s in res.sites if s.role == "forward")
    assert fwd == [("MZ000001.1", 0), ("MZ000002.1", 1), ("MZ000003.1", 0), ("MZ000005.1", 0)]
    assert any("," in ids for ids in fake.efetch_ids)  # several records per EFetch request


def test_old_not_found_records_without_a_direct_check_are_scanned_again(tmp_path):
    import json

    recs = records()
    for r in recs:
        r.in_blast_db = False
    fake = FakeNuccore(recs)
    run = setup(tmp_path, fake)
    run()
    (path,) = (tmp_path / "cache" / "variants").glob("*-blast_partitioned.jsonl")
    lines = []
    for line in path.read_text().splitlines():  # as the first live run stored them
        item = json.loads(line)
        item.update(status="not_found", loci=[], n_loci=0, found_by=None)
        item.pop("direct_checked")
        lines.append(json.dumps(item))
    path.write_text("\n".join(lines) + "\n")
    c = run().coverage
    assert c.processed_this_run == 5 and c.found == 4


def test_the_report_shows_coverage_even_when_no_region_was_found(tmp_path):
    from qpcr_assay_check.pipeline import evaluate
    from qpcr_assay_check.report.html import render_report

    from .test_variants_exhaustive import _empty_specificity

    recs = [FakeRecord("4", "MZ000004.1", "2025/07/01", filler(900, 4))]
    res = setup(tmp_path, FakeNuccore(recs))()
    cfg = load_config()
    cfg.variants.source = "blast_partitioned"
    result = evaluate(
        make_assay(reference_amplicon=AMP, target={"taxid": 2697049}), cfg, now=NOW,
        target_sites=res.sites, variant_coverage=res.coverage, release_dates=res.release_dates,
        inclusivity=res.inclusivity, specificity=_empty_specificity(),
    )  # fmt: skip
    html = render_report(result, cfg)
    assert "Scope: every NCBI Nucleotide record" in html
    assert "No oligo site could be assessed" in html and "How records were checked" in html
    assert "NCBI Datasets' genome collection" not in html


def test_small_records_are_scanned_directly_without_any_blast_search(tmp_path):
    """Live finding: BLAST found none of the newest 286 genomes that a direct scan found."""
    fake = FakeNuccore(records())
    res = setup(tmp_path, fake)()  # default direct_scan_max_length covers these records
    assert fake.blast_puts == [] and res.coverage.found == 4
    assert res.coverage.found_by_direct_scan == 4


def test_a_region_hidden_by_n_is_reported_as_masked_not_as_a_perfect_match(tmp_path):
    # AMP = forward (1-20) + spacer (21-50) + probe (51-74) + spacer + reverse
    in_spacer = AMP[:30] + "N" * 15 + AMP[45:]  # Ns between the oligos: still assessable
    in_probe = AMP[:55] + "N" * 10 + AMP[65:]  # the probe site reads N: masked
    speckled = "".join("N" if i % 6 == 5 else b for i, b in enumerate(AMP))  # no exact seed left
    recs = [
        FakeRecord(
            str(i),
            f"MZ00000{i}.1",
            f"2026/03/0{i}",
            filler(300, 2 * i) + amp + filler(300, 2 * i + 1),
        )
        for i, amp in ((1, AMP), (2, in_spacer), (3, in_probe), (4, speckled))
    ] + [FakeRecord("5", "MZ000005.1", "2026/03/05", filler(300, 9) + "N" * 200 + filler(300, 8))]
    c = setup(tmp_path, FakeNuccore(recs))().coverage
    assert c.found == 2  # the clean record and the one with Ns only between the oligos
    assert c.masked == 2 and set(c.masked_examples) == {"MZ000003.1", "MZ000004.1"}
    assert c.not_found == 1  # a plain N-run with no real bases of the amplicon: not "masked"


def test_a_record_wholly_masked_by_n_is_reported_as_hidden_by_n(tmp_path):
    """Live (v1.1.0): OZ558241.1 and similar, 1,144 N over the N1 region, called 'not found'."""
    recs = records() + [FakeRecord("6", "OZ000006.1", "2026/06/01", HIDDEN)]
    assay = make_assay(
        reference_amplicon=AMP, target={"taxid": 2697049, "accession": "NC_045512.2"}
    )
    run = setup(tmp_path, FakeNuccore(recs), assay=assay, fetch_fasta=lambda a: f">{a}\n{REF}\n")
    c = run().coverage
    assert (c.found, c.masked, c.not_found) == (4, 1, 1)
    assert c.masked_examples == ["OZ000006.1"] and c.not_found_examples == ["MZ000004.1"]
