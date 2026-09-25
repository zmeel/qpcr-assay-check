"""NCBI BLAST URL API: build a request, submit it (Put), poll for it, and fetch the result (Get).

Parameters follow the documented Common URL API. ``ENTREZ_QUERY`` (used to restrict a search to
taxa) is *not* part of that documented parameter table; it is widely used but unsupported, so every
restricted search is verified afterwards (see :mod:`qpcr_assay_check.search.canary`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ..config import Config
from .cache import content_key
from .http import NcbiError, NcbiHttp

BlastStatus = Literal["WAITING", "READY", "FAILED", "UNKNOWN"]

_RID_RE = re.compile(r"^\s*RID\s*=\s*(\S+)", re.MULTILINE)
_RTOE_RE = re.compile(r"^\s*RTOE\s*=\s*(\d+)", re.MULTILINE)
_STATUS_RE = re.compile(r"Status\s*=\s*(\w+)")
_HITS_RE = re.compile(r"ThereAreHits\s*=\s*(\w+)")


def build_query_fasta(oligos: dict[str, str]) -> str:
    """One multi-FASTA batch for all oligos (NCBI recommends merging short queries)."""
    return "".join(f">{label}\n{seq}\n" for label, seq in oligos.items())


def build_entrez_query(taxids: list[int], exclude: list[int] | None = None) -> str | None:
    """Restrict a search to the given taxa (and their descendants) using ``txid<ID>[ORGN]``.

    ``exclude``: taxa (with their descendants) left out with ``NOT``, e.g. the rhinovirus
    species inside the genus Enterovirus. Checked live for ESearch and BLAST (docs/ARCHITECTURE.md).
    """
    if not taxids:
        return None
    terms = " OR ".join(f"txid{t}[ORGN]" for t in taxids)
    query = f"({terms})" if len(taxids) > 1 else terms
    if exclude:
        query = f"({query} NOT ({' OR '.join(f'txid{t}[ORGN]' for t in exclude)}))"
    return query


def build_put_params(cfg: Config, fasta: str, entrez_query: str | None) -> dict[str, str]:
    """All BLAST parameters for one submission, except identification (added by the HTTP layer)."""
    s = cfg.search
    params = {
        "CMD": "Put",
        "PROGRAM": s.program,
        "DATABASE": s.database,
        "QUERY": fasta,
        "WORD_SIZE": str(s.word_size),
        "EXPECT": f"{s.expect:g}",
        "FILTER": s.filter,
        "NUCL_REWARD": str(s.reward),
        "NUCL_PENALTY": str(s.penalty),
        "GAPCOSTS": f"{s.gap_open} {s.gap_extend}",
        "HITLIST_SIZE": str(s.hitlist_size),
    }
    if entrez_query:
        params["ENTREZ_QUERY"] = entrez_query
    return params


def request_key(params: dict[str, str]) -> str:
    """Content-address of a request (the query sequences are part of ``params``)."""
    return content_key(params)


def parse_put_response(text: str) -> tuple[str, int]:
    """Extract ``(RID, RTOE seconds)`` from the Put response."""
    rid, rtoe = _RID_RE.search(text), _RTOE_RE.search(text)
    if not rid:
        raise NcbiError(
            "The BLAST server did not return a request ID (RID). Response began: "
            + text[:200].strip().replace("\n", " ")
        )
    return rid.group(1), int(rtoe.group(1)) if rtoe else 30


def parse_status_response(text: str) -> tuple[BlastStatus, bool | None]:
    """Extract ``(status, there_are_hits)`` from a SearchInfo response."""
    m = _STATUS_RE.search(text)
    status = m.group(1).upper() if m else "UNKNOWN"
    if status not in ("WAITING", "READY", "FAILED", "UNKNOWN"):
        status = "UNKNOWN"
    h = _HITS_RE.search(text)
    hits = None if not h else h.group(1).lower() == "yes"
    return status, hits  # type: ignore[return-value]


@dataclass
class BlastApi:
    """Thin wrapper over the three BLAST URL API commands."""

    http: NcbiHttp
    url: str

    def submit(self, params: dict[str, str]) -> tuple[str, int]:
        """Submit a search; returns ``(RID, estimated seconds until ready)``."""
        resp = self.http.request("POST", self.url, service="blast", data=params)
        return parse_put_response(resp.text)

    def status(self, rid: str) -> tuple[BlastStatus, bool | None]:
        """Ask for the status of a request."""
        resp = self.http.request(
            "GET",
            self.url,
            service="blast",
            params={"CMD": "Get", "FORMAT_OBJECT": "SearchInfo", "RID": rid},
        )
        return parse_status_response(resp.text)

    def fetch(self, rid: str, result_format: str) -> str:
        """Fetch the finished result in the given report format."""
        resp = self.http.request(
            "GET",
            self.url,
            service="blast",
            params={"CMD": "Get", "RID": rid, "FORMAT_TYPE": result_format},
        )
        return resp.text
