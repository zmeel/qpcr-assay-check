"""Species/genus/family aggregation of off-target sites (SPEC step 6)."""

from __future__ import annotations

from qpcr_assay_check.config import load_config
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.settings import Credentials
from qpcr_assay_check.specificity.models import SiteResult
from qpcr_assay_check.taxonomy.rollup import taxonomy_breakdown

from .fake_ncbi import FakeClock
from .test_taxonomy import ScriptedSession

# One EFetch call returns every requested taxon: combines the Chlamydia trachomatis and Neisseria
# gonorrhoeae fixtures used in tests/test_taxonomy.py into a single TaxaSet, matching how
# fetch_lineages batches one request for every taxid missing from the cache.
COMBINED_XML = """<?xml version="1.0"?>
<TaxaSet>
<Taxon>
<TaxId>813</TaxId><ScientificName>Chlamydia trachomatis</ScientificName><Rank>species</Rank>
<LineageEx>
<Taxon><TaxId>809</TaxId><ScientificName>Chlamydiaceae</ScientificName><Rank>family</Rank></Taxon>
<Taxon><TaxId>810</TaxId><ScientificName>Chlamydia</ScientificName><Rank>genus</Rank></Taxon>
</LineageEx>
</Taxon>
<Taxon>
<TaxId>485</TaxId><ScientificName>Neisseria gonorrhoeae</ScientificName><Rank>species</Rank>
<LineageEx>
<Taxon><TaxId>481</TaxId><ScientificName>Neisseriaceae</ScientificName><Rank>family</Rank></Taxon>
<Taxon><TaxId>482</TaxId><ScientificName>Neisseria</ScientificName><Rank>genus</Rank></Taxon>
</LineageEx>
</Taxon>
</TaxaSet>"""


def make_http(script: list[str]) -> tuple[NcbiHttp, ScriptedSession]:
    fake = ScriptedSession(script)
    fc = FakeClock()
    http = NcbiHttp(
        load_config().ncbi, Credentials("lab@example.org"),
        session=fake, clock=fc.monotonic, sleep=fc.sleep, jitter=lambda: 0.0,
    )  # fmt: skip
    return http, fake


def site(taxid: int, organism: str, site_id: str) -> SiteResult:
    return SiteResult(
        id=site_id, tier="exclusivity", query="forward", role="forward", oligo="A" * 20,
        accession="AB000001.1", taxid=taxid, organism=organism, orientation="+",
        subject_start=1, subject_end=20, source="blast_full", q_aln="A" * 20, s_aln="A" * 20,
        midline="|" * 20, n_match=20, n_mismatch=0, n_gap=0, n_ambiguous=0,
        defect_positions=[], mismatches_last5=0, mismatches_last3=0, terminal_defect=False,
        clean_3prime_nt=20, level="critical",
    )  # fmt: skip


def test_no_taxids_gives_an_empty_breakdown_and_makes_no_request(tmp_path):
    http, fake = make_http([])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    assert taxonomy_breakdown([], eu, cache, ttl_days=30) == []
    assert fake.calls == []


def test_counts_and_lineages_per_distinct_taxid(tmp_path):
    sites = [
        site(813, "Chlamydia trachomatis", "S1"),
        site(813, "Chlamydia trachomatis", "S2"),
        site(485, "Neisseria gonorrhoeae", "S3"),
    ]
    http, fake = make_http([COMBINED_XML])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    out = taxonomy_breakdown(sites, eu, cache, ttl_days=30)
    assert [(c.taxid, c.n_sites, c.genus, c.family) for c in out] == [
        (813, 2, "Chlamydia", "Chlamydiaceae"),
        (485, 1, "Neisseria", "Neisseriaceae"),
    ]
    assert len(fake.calls) == 1  # every taxid missing from the cache batched into one EFetch


def test_sites_without_a_taxid_are_ignored(tmp_path):
    s = site(813, "Chlamydia trachomatis", "S1")
    s.taxid = None
    http, fake = make_http([])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    assert taxonomy_breakdown([s], eu, cache, ttl_days=30) == []
