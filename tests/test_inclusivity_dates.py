"""Accession -> submission year lookup via ESummary."""

from __future__ import annotations

import json

from qpcr_assay_check.config import load_config
from qpcr_assay_check.inclusivity.dates import fetch_years, year_from_docsum
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.settings import Credentials

from .fake_ncbi import FakeClock
from .test_taxonomy import ScriptedSession


def make_http(script: list[str]) -> tuple[NcbiHttp, ScriptedSession]:
    fake = ScriptedSession(script)
    fc = FakeClock()
    http = NcbiHttp(
        load_config().ncbi, Credentials("lab@example.org"),
        session=fake, clock=fc.monotonic, sleep=fc.sleep, jitter=lambda: 0.0,
    )  # fmt: skip
    return http, fake


def esummary_json(entries: list[dict]) -> str:
    """entries: [{"uid": ..., accessionversion: ..., createdate: ...}, ...]"""
    result = {"uids": [str(e["uid"]) for e in entries]}
    for e in entries:
        result[str(e["uid"])] = {k: v for k, v in e.items() if k != "uid"}
    return json.dumps({"header": {"type": "esummary"}, "result": result})


def test_year_from_docsum_tries_several_fields():
    assert year_from_docsum({"createdate": "2021/03/15"}) == 2021
    assert year_from_docsum({"CreateDate": "2019/11/01 00:00"}) == 2019
    assert year_from_docsum({"updatedate": "2020/01/01"}) == 2020
    assert year_from_docsum({}) is None
    assert year_from_docsum({"createdate": 12345}) is None  # not a string: ignored, not crashed


def test_fetch_years_maps_by_accession_not_response_order(tmp_path):
    # NCBI's own uid order need not match the accessions we asked about; re-indexed by the
    # docsum's own accessionversion field instead of trusting order.
    body = esummary_json(
        [
            {"uid": 999, "accessionversion": "MN908947.3", "createdate": "2020/01/05"},
            {"uid": 111, "accessionversion": "OX417460.1", "createdate": "2022/06/20"},
        ]
    )
    http, fake = make_http([body])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    years = fetch_years(eu, cache, ["MN908947.3", "OX417460.1"], ttl_days=30)
    assert years == {"MN908947.3": 2020, "OX417460.1": 2022}
    assert fake.calls[0]["params"]["id"] == "MN908947.3,OX417460.1"


def test_an_accession_missing_from_the_response_is_none_not_a_crash(tmp_path):
    body = esummary_json(
        [{"uid": 999, "accessionversion": "MN908947.3", "createdate": "2020/01/05"}]
    )
    http, fake = make_http([body])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    years = fetch_years(eu, cache, ["MN908947.3", "AB999999.1"], ttl_days=30)
    assert years == {"MN908947.3": 2020, "AB999999.1": None}


def test_cached_years_make_no_second_request(tmp_path):
    body = esummary_json(
        [{"uid": 999, "accessionversion": "MN908947.3", "createdate": "2020/01/05"}]
    )
    http, fake = make_http([body])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    fetch_years(eu, cache, ["MN908947.3"], ttl_days=30)

    http2, fake2 = make_http([])  # nothing queued: a second request would raise
    eu2 = Eutils(http2, "https://eutils.example/entrez/eutils")
    years2 = fetch_years(eu2, cache, ["MN908947.3"], ttl_days=30)
    assert years2 == {"MN908947.3": 2020} and fake2.calls == []


def test_batches_are_capped(tmp_path):
    accs = [f"AB{i:06d}.1" for i in range(5)]

    def body_for(sub: list[str]) -> str:
        return esummary_json(
            [
                {"uid": i, "accessionversion": a, "createdate": "2021/01/01"}
                for i, a in enumerate(sub)
            ]
        )

    # batch_size=2 over 5 accessions: three batches of 2, 2, 1
    http, fake = make_http([body_for(accs[0:2]), body_for(accs[2:4]), body_for(accs[4:5])])
    eu = Eutils(http, "https://eutils.example/entrez/eutils")
    cache = Cache(tmp_path / "cache")
    years = fetch_years(eu, cache, accs, ttl_days=30, batch_size=2)
    assert len(years) == 5 and len(fake.calls) == 3
