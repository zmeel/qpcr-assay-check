"""Submission year per accession, via ESummary (batched, cached).

Two things about this are unverified against live NCBI output (see docs/ARCHITECTURE.md and
``scripts/smoke_test.py``):

1. Accession.version identifiers are accepted by ``esummary.fcgi`` for ``db=nuccore``
   interchangeably with numeric UIDs, the same way they already are for ``efetch.fcgi``.
2. The document-summary field that carries a usable date. Several plausible field names (NCBI's
   nuccore ESummary schema has used ``CreateDate``/``UpdateDate`` historically) are tried in
   order; only the leading four-digit year is extracted, since that is all inclusivity windows
   need and it is robust to exact date-format differences.

Because NCBI's ESummary result is keyed by the UID it resolved each identifier to -- not by the
accession string that was sent -- results are re-indexed here by the document summary's own
``accessionversion``/``caption`` field rather than trusting response order.
"""

from __future__ import annotations

import logging
import re

from ..ncbi.cache import Cache, content_key
from ..ncbi.eutils import Eutils

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"(\d{4})")
_DATE_FIELDS = ("createdate", "CreateDate", "updatedate", "UpdateDate", "sortpubdate", "PubDate")


def year_from_docsum(docsum: dict) -> int | None:
    """Best-effort submission year from one ESummary document summary."""
    for field in _DATE_FIELDS:
        value = docsum.get(field)
        if isinstance(value, str):
            m = _YEAR_RE.search(value)
            if m:
                return int(m.group(1))
    return None


def fetch_years(
    eutils: Eutils, cache: Cache, accessions: list[str], *, ttl_days: float, batch_size: int = 300
) -> dict[str, int | None]:
    """Submission year per accession.version, cached; ``None`` where it could not be determined."""
    out: dict[str, int | None] = {}
    missing: list[str] = []
    for acc in accessions:
        key = content_key({"kind": "accession_year", "accession": acc})
        cached = cache.get("accession_year", key, ttl_days=ttl_days)
        if cached is not None:
            out[acc] = None if cached == "" else int(cached)
        else:
            missing.append(acc)
    for i in range(0, len(missing), batch_size):
        chunk = missing[i : i + batch_size]
        docsums = eutils.esummary("nuccore", chunk)
        by_accession: dict[str, dict] = {}
        for docsum in docsums.values():
            acc = docsum.get("accessionversion") or docsum.get("caption")
            if acc:
                by_accession[acc] = docsum
        for acc in chunk:
            docsum = by_accession.get(acc)
            year = year_from_docsum(docsum) if docsum else None
            if docsum is None:
                log.warning("ESummary returned nothing matching accession %s", acc)
            out[acc] = year
            cache.put(
                "accession_year",
                content_key({"kind": "accession_year", "accession": acc}),
                "" if year is None else str(year),
            )
    return out
