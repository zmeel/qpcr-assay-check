"""Minimal E-utilities client (ESearch counts, EFetch sequence windows)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .http import NcbiError, NcbiHttp

_COUNT_RE = re.compile(r"<Count>(\d+)</Count>")


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
