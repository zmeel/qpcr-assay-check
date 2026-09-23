"""Taxonomy name resolution and lineage fetching, against constructed Entrez responses.

ESearch/EFetch XML shapes here follow docs/ARCHITECTURE.md's "Verified in the first live smoke
run" notes; the taxonomy IDs and lineages (Chlamydia trachomatis 813, family Chlamydiaceae, genus
Chlamydia) are real, stable NCBI Taxonomy facts used only as realistic constructed fixtures.
"""

from __future__ import annotations

from qpcr_assay_check.config import load_config
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.settings import Credentials
from qpcr_assay_check.taxonomy.resolve import (
    fetch_lineages,
    parse_taxonomy_xml,
    resolve_name,
    resolve_names,
)

from .fake_ncbi import FakeClock, FakeResponse

CT_XML = """<?xml version="1.0"?>
<TaxaSet><Taxon>
<TaxId>813</TaxId><ScientificName>Chlamydia trachomatis</ScientificName><Rank>species</Rank>
<LineageEx>
<Taxon><TaxId>2</TaxId><ScientificName>Bacteria</ScientificName><Rank>superkingdom</Rank></Taxon>
<Taxon><TaxId>809</TaxId><ScientificName>Chlamydiaceae</ScientificName><Rank>family</Rank></Taxon>
<Taxon><TaxId>810</TaxId><ScientificName>Chlamydia</ScientificName><Rank>genus</Rank></Taxon>
</LineageEx>
</Taxon></TaxaSet>"""

NG_XML = """<?xml version="1.0"?>
<TaxaSet><Taxon>
<TaxId>485</TaxId><ScientificName>Neisseria gonorrhoeae</ScientificName><Rank>species</Rank>
<LineageEx>
<Taxon><TaxId>482</TaxId><ScientificName>Neisseriaceae</ScientificName><Rank>family</Rank></Taxon>
<Taxon><TaxId>482</TaxId><ScientificName>Neisseria</ScientificName><Rank>genus</Rank></Taxon>
</LineageEx>
</Taxon></TaxaSet>"""


def esearch_xml(*ids: int) -> str:
    body = "".join(f"<Id>{i}</Id>" for i in ids)
    return (
        f"<?xml version='1.0'?><eSearchResult><Count>{len(ids)}</Count>"
        f"<IdList>{body}</IdList></eSearchResult>"
    )


class ScriptedSession:
    """Queued responses in call order; asserts nothing is called beyond the script."""

    def __init__(self, script: list[str]) -> None:
        self.headers: dict[str, str] = {}
        self.script = list(script)
        self.calls: list[dict] = []

    def request(self, method, url, params=None, data=None, timeout=None, headers=None):
        self.calls.append({"url": url, "params": dict(params or {})})
        assert self.script, f"unexpected request beyond the script: {url} {params}"
        return FakeResponse(200, self.script.pop(0))


def make_http(script: list[str]) -> tuple[NcbiHttp, ScriptedSession]:
    fake = ScriptedSession(script)
    fc = FakeClock()
    http = NcbiHttp(
        load_config().ncbi,
        Credentials("lab@example.org"),
        session=fake,
        clock=fc.monotonic,
        sleep=fc.sleep,
        jitter=lambda: 0.0,
    )
    return http, fake


def test_a_unique_name_resolves(tmp_path):
    http, fake = make_http([esearch_xml(813)])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    r = resolve_name(eu, cache, "Chlamydia trachomatis", ttl_days=30, synonyms=True)
    assert r.status == "resolved" and r.taxid == 813
    assert fake.calls[0]["params"]["term"] == "Chlamydia trachomatis[Scientific Name]"


def test_zero_then_synonym_resolves(tmp_path):
    http, fake = make_http([esearch_xml(), esearch_xml(2097)])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    r = resolve_name(eu, cache, "Mycoplasma pneumoniae", ttl_days=30, synonyms=True)
    assert r.status == "resolved" and r.taxid == 2097 and r.matched_term.endswith("[All Names]")
    assert len(fake.calls) == 2


def test_unresolved_without_synonyms_does_not_try_all_names(tmp_path):
    http, fake = make_http([esearch_xml()])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    r = resolve_name(eu, cache, "Nonexistent organism", ttl_days=30, synonyms=False)
    assert r.status == "unresolved" and len(fake.calls) == 1


def test_multiple_ids_is_ambiguous_not_a_guess(tmp_path):
    http, fake = make_http([esearch_xml(111, 222)])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    r = resolve_name(eu, cache, "Some genus sp.", ttl_days=30, synonyms=True)
    assert r.status == "ambiguous" and r.taxid is None and r.candidates == [111, 222]


def test_a_cached_resolution_makes_no_second_request(tmp_path):
    http, fake = make_http([esearch_xml(813)])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    resolve_name(eu, cache, "Chlamydia trachomatis", ttl_days=30, synonyms=True)
    http2, fake2 = make_http([])  # nothing queued: a second network call would raise
    eu2 = Eutils(http2, "https://eutils.example/entrez/eutils")
    r2 = resolve_name(eu2, cache, "Chlamydia trachomatis", ttl_days=30, synonyms=True)
    assert r2.status == "resolved" and r2.taxid == 813 and fake2.calls == []


def test_resolve_names_keeps_order_and_handles_each_independently(tmp_path):
    http, fake = make_http([esearch_xml(813), esearch_xml()])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    results = resolve_names(
        eu, cache, ["Chlamydia trachomatis", "Nonexistent organism"], ttl_days=30, synonyms=False
    )
    assert [r.status for r in results] == ["resolved", "unresolved"]


def test_parse_taxonomy_xml_extracts_species_genus_family():
    lineages = parse_taxonomy_xml(CT_XML)
    lin = lineages[813]
    assert lin.scientific_name == "Chlamydia trachomatis" and lin.rank == "species"
    assert lin.species == "Chlamydia trachomatis"
    assert lin.genus == "Chlamydia" and lin.family == "Chlamydiaceae"


def test_fetch_lineages_batches_and_caches_per_taxid(tmp_path):
    http, fake = make_http([CT_XML])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    out = fetch_lineages(eu, cache, [813], ttl_days=30)
    assert out[813].genus == "Chlamydia"
    assert len(fake.calls) == 1

    # a second taxid not yet cached triggers exactly one more EFetch, for the missing one only
    http2, fake2 = make_http([NG_XML])
    eu2 = Eutils(http2, "https://eutils.example/entrez/eutils")
    out2 = fetch_lineages(eu2, cache, [813, 485], ttl_days=30)
    assert out2[813].genus == "Chlamydia" and out2[485].genus == "Neisseria"
    assert len(fake2.calls) == 1
    assert fake2.calls[0]["params"]["id"] == "485"
