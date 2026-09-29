"""The analysis on the chain locator and store v2 (overhaul step 5), SYNTHETIC genomes."""

from qpcr_assay_check.oligo import iupac

from .fake_datasets import FakeAssembly, FakeDatasets
from .test_variants_exhaustive import AMP, run, setup
from .world import filler


def test_a_copy_with_a_long_insertion_is_judged_at_the_right_sites(tmp_path):
    """The old locator split such a copy and placed the far oligos 40 nt off (a false escape;
    measured live: 518 of 1,132 Legionella sites)."""
    longer = AMP[:30] + filler(40, 7) + AMP[30:]  # 40 nt in the spacer before the probe
    shorter = AMP[:24] + AMP[48:]  # 24 nt out of the same spacer
    one = {"c1": filler(900, 1) + longer + filler(900, 2)}
    two = {"c2": iupac.reverse_complement(filler(900, 3) + shorter + filler(900, 4))}
    fake = FakeDatasets(
        [
            FakeAssembly("GCF_000000001.1", "2025-01-01", one),
            FakeAssembly("GCF_000000002.1", "2025-02-01", two),
        ]
    )
    cfg, _f, client, assay = setup(tmp_path, fake=fake)
    res = run(tmp_path, cfg, client, assay)
    assert res.coverage.found == 2 and res.coverage.copies.escapes == 0
    assert all(s.n_mismatch == 0 and s.n_gap == 0 for s in res.sites)


def test_a_failed_batch_is_tried_again_in_halves(tmp_path):
    genomes = [FakeAssembly(f"GCF_00000000{i}.1", f"2025-0{i}-01",
                            {f"c{i}": filler(500, i) + AMP + filler(500, i + 10)})
               for i in range(1, 5)]  # fmt: skip
    fake = FakeDatasets(genomes, breaks_download={"GCF_000000003.1"})
    cfg, _f, client, assay = setup(tmp_path, fake=fake)
    cfg.ncbi.datasets_batch_size = 4
    res = run(tmp_path, cfg, client, assay)
    assert res.coverage.found == 3 and res.coverage.download_failed_this_run == 1
    store_failures = (tmp_path / "cache" / "genomes").glob("*.failures.json")
    (path,) = store_failures
    assert '"GCF_000000003.1"' in path.read_text()


def test_the_sequence_report_is_fetched_only_for_genomes_with_several_sequences(tmp_path):
    one = {"c1": filler(500, 1) + AMP + filler(500, 2)}
    two = {"c2": filler(500, 3) + AMP + filler(500, 4), "p2": filler(900, 5)}
    fake = FakeDatasets(
        [
            FakeAssembly("GCF_000000001.1", "2025-01-01", one),
            FakeAssembly("GCF_000000002.1", "2025-02-01", two, molecules={"p2": "Plasmid"}),
        ]
    )
    cfg, _f, client, assay = setup(tmp_path, fake=fake)
    res = run(tmp_path, cfg, client, assay)
    reports = [c["url"] for c in fake.calls if c["url"].endswith("/sequence_reports")]
    assert len(reports) == 1 and "GCF_000000002.1" in reports[0]
    assert res.coverage.found == 2


def test_nothing_is_downloaded_again_on_a_second_run(tmp_path):
    cfg, fake, client, assay = setup(tmp_path)
    first = run(tmp_path, cfg, client, assay)
    n = len(fake.downloads)
    second = run(tmp_path, cfg, client, assay)
    assert len(fake.downloads) == n
    assert [s.model_dump() for s in first.sites] == [s.model_dump() for s in second.sites]
