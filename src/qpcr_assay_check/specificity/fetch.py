"""Fetch (and cache) small subject windows with E-utilities efetch."""

from __future__ import annotations

import logging

from ..ncbi.cache import Cache, content_key
from ..ncbi.eutils import Eutils
from ..ncbi.http import NcbiError

log = logging.getLogger(__name__)


class WindowFetcher:
    """Returns forward-strand sequence windows; records how many came from the network.

    Windows of an ``accession.version`` never change, so they are cached without expiry.
    A failed fetch yields ``None`` (and is counted) instead of stopping the whole assessment.
    """

    def __init__(self, eutils: Eutils, cache: Cache) -> None:
        self.eutils = eutils
        self.cache = cache
        self.n_network = 0
        self.n_cached = 0
        self.n_failed = 0

    def get(self, accession: str, start: int, stop: int) -> str | None:
        """Sequence of ``accession`` from ``start`` to ``stop`` (1-based, inclusive), or None."""
        key = content_key({"acc": accession, "start": start, "stop": stop, "strand": 1})
        text = self.cache.get("seqwindow", key, ttl_days=None)
        if text is not None:
            self.n_cached += 1
        else:
            try:
                text = self.eutils.fetch_fasta(accession, start=start, stop=stop)
            except NcbiError as exc:
                self.n_failed += 1
                log.warning("Could not fetch %s:%d-%d: %s", accession, start, stop, exc)
                return None
            self.cache.put("seqwindow", key, text)
            self.n_network += 1
        lines = text.strip().splitlines()
        seq = "".join(lines[1:]).upper()
        return seq or None
