"""Minimal E-utilities client (ESearch counts/UIDs, ESummary, EFetch sequence windows/taxonomy)."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .http import NcbiError, NcbiHttp

_COUNT_RE = re.compile(r"<Count>(\d+)</Count>")
_ID_RE = re.compile(r"<Id>(\d+)</Id>")


@dataclass
class Eutils:
    """Thin wrapper; all politeness (identification, throttling, backoff) lives in NcbiHttp."""

    http: NcbiHttp
    base_url: str

    def esearch_count(self, db: str, term: str) -> int:
        """Number of records matching ``term`` (retmax=0: no identifiers are downloaded)."""
        resp = self.http.request(
            "GET",
            f"{self.base_url}/esearch.fcgi",
            service="eutils",
            params={"db": db, "term": term, "retmax": 0},
        )
        m = _COUNT_RE.search(resp.text)
        if not m:
            raise NcbiError(f"Unexpected ESearch response: {resp.text[:200]!r}")
        return int(m.group(1))

    def esearch_ids(self, db: str, term: str, *, retmax: int = 20) -> list[int]:
        """UIDs matching ``term``. More than ``retmax`` hits still means "more than one", not a
        silently truncated list: callers must treat that as ambiguous rather than complete."""
        resp = self.http.request(
            "GET",
            f"{self.base_url}/esearch.fcgi",
            service="eutils",
            params={"db": db, "term": term, "retmax": retmax},
        )
        if "<eSearchResult" not in resp.text:
            raise NcbiError(f"Unexpected ESearch response: {resp.text[:200]!r}")
        return [int(i) for i in _ID_RE.findall(resp.text)]

    def esummary(self, db: str, ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        """ESummary (JSON, version 2.0) document summaries for ``ids``, keyed by the ID string.

        NCBI accepts accession.version identifiers for ``nuccore`` interchangeably with numeric
        UIDs; this project always passes accession.version (already on hand from a BLAST hit),
        never a separately-looked-up UID. The exact document-summary field names below (see
        ``inclusivity/dates.py``) have not been checked against live output; see
        docs/ARCHITECTURE.md.
        """
        resp = self.http.request(
            "GET",
            f"{self.base_url}/esummary.fcgi",
            service="eutils",
            params={"db": db, "id": ",".join(ids), "retmode": "json"},
        )
        try:
            data = json.loads(resp.text)
        except json.JSONDecodeError as exc:
            raise NcbiError(f"Unexpected ESummary response: {resp.text[:200]!r}") from exc
        result = data.get("result") if isinstance(data, dict) else None
        if not isinstance(result, dict) or "uids" not in result:
            raise NcbiError(f"Unexpected ESummary response shape: {resp.text[:200]!r}")
        return {uid: result[uid] for uid in result["uids"] if isinstance(result.get(uid), dict)}

    def fetch_taxonomy(self, taxids: Sequence[int]) -> str:
        """Taxonomy EFetch XML (``TaxaSet``) for one or more taxonomy IDs."""
        resp = self.http.request(
            "GET",
            f"{self.base_url}/efetch.fcgi",
            service="eutils",
            params={"db": "taxonomy", "id": ",".join(str(t) for t in taxids), "retmode": "xml"},
        )
        if "<TaxaSet" not in resp.text:
            raise NcbiError(f"Unexpected Taxonomy EFetch response: {resp.text[:200]!r}")
        return resp.text

    def fetch_fasta(
        self, accession: str, *, start: int | None = None, stop: int | None = None, strand: int = 1
    ) -> str:
        """FASTA of a nucleotide record or of a 1-based window (``seq_start``/``seq_stop``)."""
        params: dict[str, str | int] = {
            "db": "nuccore",
            "id": accession,
            "rettype": "fasta",
            "retmode": "text",
        }
        if start is not None and stop is not None:
            params.update({"seq_start": start, "seq_stop": stop, "strand": strand})
        resp = self.http.request(
            "GET", f"{self.base_url}/efetch.fcgi", service="eutils", params=params
        )
        text = resp.text
        if not text.startswith(">"):
            raise NcbiError(f"Unexpected EFetch response for {accession}: {text[:200]!r}")
        return text
