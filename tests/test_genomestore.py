"""Store v2 (overhaul step 4) and the Datasets sequence report client, on SYNTHETIC genomes."""

import json

from qpcr_assay_check.config import load_config
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.settings import Credentials
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.variants.chain import Reference, is_copy
from qpcr_assay_check.variants.datasets import AssemblyRecord, DatasetsClient, SequenceRole
from qpcr_assay_check.variants.genomestore import (
    GenomeStore,
    ScanSettings,
    scan_genome,
    sequence_stats,
    store_file,
    store_key,
)

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .fake_datasets import FakeAssembly, FakeDatasets
from .world import filler

AMP = F + filler(30, 11) + P + filler(30, 12) + iupac.reverse_complement(R)
REFS = [Reference(AMP)]
REC = AssemblyRecord("GCF_000000001.1", "2025-03-01", "Contig", 0, "Chlamydia trachomatis", 813)


def key(**kw):
    return store_key(REFS, ScanSettings(**kw), taxon=813, source="datasets")


def records():
    return {
        "c1": ("chromosome, whole genome", filler(2000, 1) + AMP + filler(40, 2) + "N" * 12
               + filler(500, 3)),
        "p1": ("plasmid pX", filler(300, 4) + AMP[:60]),
    }  # fmt: skip


def test_a_scan_keeps_every_candidate_with_its_evidence_and_molecule():
    rec = scan_genome(REC, records(), REFS, ScanSettings())
    assert (rec.n_sequences, rec.total_n, rec.gaps) == (2, 12, 1)
    by_contig = {c.contig: c for c in rec.copies}
    whole, cut = by_contig["c1"], by_contig["p1"]
    assert whole.molecule is None and cut.molecule == "Plasmid"  # from the FASTA description
    assert cut.end > cut.contig_length and is_copy(cut.candidate())
    assert whole.candidate().place(0) == 2000
    roles = {"c1": SequenceRole("assembled-molecule", "Chromosome")}
    again = scan_genome(REC, records(), REFS, ScanSettings(), roles)
    assert {c.contig: c.molecule for c in again.copies} == {"c1": "Chromosome", "p1": "Plasmid"}


def test_the_store_reloads_and_sets_aside_a_file_with_another_key(tmp_path):
    k = key()
    path = store_file(tmp_path, k)
    store = GenomeStore(path, k)
    store.add(scan_genome(REC, records(), REFS, ScanSettings()))
    again = GenomeStore(path, k)
    assert REC.accession in again and again.items[REC.accession].copies[0].anchored > 0
    header = json.loads(path.read_text().splitlines()[0])
    assert header["schema"] == 3 and header["key"] == k
    other = key(step=4)  # a different method: a different key
    assert store_file(tmp_path, other) != path
    moved = GenomeStore(path, other)  # same file, other key (e.g. an edited header)
    assert not moved.items and path.with_suffix(".old").exists()
    assert json.loads(path.read_text().splitlines()[0])["key"] == other


def test_a_file_without_a_header_is_set_aside(tmp_path):
    path = tmp_path / "genomes" / "813-x.jsonl"
    path.parent.mkdir()
    path.write_text('{"accession": "old line of the v1 store"}\n')
    store = GenomeStore(path, key())
    assert not store.items and path.with_suffix(".old").exists()


def test_failures_count_with_their_reason_and_clear_on_success(tmp_path):
    k = key()
    store = GenomeStore(store_file(tmp_path, k), k)
    store.record_failure(REC.accession, "zip damaged")
    assert not store.unavailable(REC.accession)
    store.record_failure(REC.accession, "timeout")
    again = GenomeStore(store_file(tmp_path, k), k)
    assert again.unavailable(REC.accession)
    assert again.failures[REC.accession] == {"count": 2, "reason": "timeout"}
    again.add(scan_genome(REC, records(), REFS, ScanSettings()))
    assert not again.unavailable(REC.accession)


def test_sequence_stats_count_gaps_of_ten_n_or_more():
    assert sequence_stats({"a": "ACGT" + "N" * 9 + "A" + "N" * 10, "b": "nnnnnnnnnnnn"}) == (
        2, 36, 31, 2)  # fmt: skip


def test_sequence_roles_are_paged_and_keyed_by_both_accessions():
    contigs = {f"NZ_C{i}.1": filler(50, i) for i in range(5)}
    fake = FakeDatasets([FakeAssembly("GCF_1.1", "2025-01-01", contigs,
                                      molecules={"NZ_C4.1": "Plasmid"})])  # fmt: skip
    cfg = load_config()
    http = NcbiHttp(cfg.ncbi, Credentials("lab@example.org"), session=fake,
                    sleep=lambda s: None, jitter=lambda: 0.0)  # fmt: skip
    client = DatasetsClient(http, cfg.ncbi.datasets_url)
    import qpcr_assay_check.variants.datasets as ds

    old, ds.PAGE_SIZE = ds.PAGE_SIZE, 2  # three pages
    try:
        roles = client.sequence_roles("GCF_1.1")
    finally:
        ds.PAGE_SIZE = old
    assert len(roles) == 10  # RefSeq and GenBank accession of each of the 5 sequences
    assert roles["NZ_C4.1"].plasmid and roles["GB_NZ_C4.1"].plasmid
    assert not roles["NZ_C0.1"].plasmid and roles["NZ_C0.1"].role == "unplaced-scaffold"
    assert sum("sequence_reports" in c["url"] for c in fake.calls) == 3
