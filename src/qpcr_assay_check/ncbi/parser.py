"""Parser for BLAST JSON2 reports (``JSON2_S`` / ``JSON2``).

Written against the documented BLAST JSON2 layout. It has NOT yet been validated against real NCBI
output; the smoke test captures real responses for that. The parser therefore fails loudly with a
:class:`ParseError` when the structure differs from what it expects, instead of guessing.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from .http import NcbiError

_ACC_VER_RE = re.compile(r"\|([A-Za-z]{1,6}_?\d+\.\d+)\|")


class ParseError(NcbiError):
    """The BLAST response does not have the expected structure."""


class HitDescription(BaseModel):
    """One subject record merged into a hit (identical sequences share one hit in core_nt)."""

    id: str | None = None
    accession: str | None = None
    title: str = ""
    taxid: int | None = None
    sciname: str | None = None

    @property
    def accession_version(self) -> str | None:
        """``accession.version`` when the ID carries one (needed to fetch sequence windows)."""
        if self.id:
            m = _ACC_VER_RE.search(self.id)
            if m:
                return m.group(1)
        return self.accession


class Hsp(BaseModel):
    """One local alignment between a query oligo and a subject."""

    num: int
    bit_score: float
    score: float | None = None
    evalue: float
    identity: int
    align_len: int
    gaps: int = 0
    query_from: int
    query_to: int
    hit_from: int
    hit_to: int
    query_strand: str = "Plus"
    hit_strand: str = "Plus"
    qseq: str | None = None
    hseq: str | None = None
    midline: str | None = None


class Hit(BaseModel):
    """A subject sequence (group) with its alignments to one query."""

    num: int
    length: int | None = None
    descriptions: list[HitDescription]
    hsps: list[Hsp]

    @property
    def best_identity(self) -> int:
        """Most identical bases in any single alignment of this hit."""
        return max((h.identity for h in self.hsps), default=0)


class SearchStat(BaseModel):
    """Karlin-Altschul statistics NCBI reports for one query (``search.stat`` in JSON2).

    With them the smallest raw score an alignment needs to be reported follows from
    ``E = kappa * eff_space * exp(-lambda * S)``.
    """

    eff_space: float = Field(description="the search space the E-values were computed with")
    kappa: float
    lambda_: float = Field(description="'lambda' in the report")
    space_source: Literal["reported", "from_hits", "upper_bound"] = Field(
        default="reported",
        description="reported: NCBI's eff_space; from_hits: derived from the reported "
        "alignments (NCBI reports eff_space 0 for multi-query searches, live 2026-09-30); "
        "upper_bound: query length x database length (no hits to derive it from)",
    )


class QueryResult(BaseModel):
    """All hits for one query oligo."""

    label: str
    query_id: str
    query_len: int | None = None
    hits: list[Hit] = Field(default_factory=list)
    message: str | None = None
    stat: SearchStat | None = None


class ParsedSearch(BaseModel):
    """A parsed BLAST result for one submission."""

    program: str | None = None
    version: str | None = None
    database: str | None = None
    queries: dict[str, QueryResult]


def _need(obj: dict[str, Any], key: str, where: str) -> Any:
    if not isinstance(obj, dict) or key not in obj:
        raise ParseError(
            f"Unexpected BLAST JSON: '{key}' missing in {where}. The report format may have "
            "changed; run scripts/smoke_test.py and share its output."
        )
    return obj[key]


def _strand(value: Any) -> str:
    return "Minus" if str(value).lower().startswith(("minus", "-")) else "Plus"


def _hsp(raw: dict[str, Any], where: str) -> Hsp:
    return Hsp(
        num=int(raw.get("num", 1)),
        bit_score=float(_need(raw, "bit_score", where)),
        score=float(raw["score"]) if "score" in raw else None,
        evalue=float(_need(raw, "evalue", where)),
        identity=int(_need(raw, "identity", where)),
        align_len=int(_need(raw, "align_len", where)),
        gaps=int(raw.get("gaps", 0)),
        query_from=int(_need(raw, "query_from", where)),
        query_to=int(_need(raw, "query_to", where)),
        hit_from=int(_need(raw, "hit_from", where)),
        hit_to=int(_need(raw, "hit_to", where)),
        query_strand=_strand(raw.get("query_strand", "Plus")),
        hit_strand=_strand(raw.get("hit_strand", "Plus")),
        qseq=raw.get("qseq"),
        hseq=raw.get("hseq"),
        midline=raw.get("midline"),
    )


def _description(raw: dict[str, Any]) -> HitDescription:
    taxid = raw.get("taxid")
    return HitDescription(
        id=raw.get("id"),
        accession=raw.get("accession"),
        title=str(raw.get("title", "")),
        taxid=int(taxid) if taxid not in (None, "") else None,
        sciname=raw.get("sciname"),
    )


def _stat(raw: Any, hits: list[Hit], query_len: int | None) -> SearchStat | None:
    """The search statistics, or None when the report lacks usable ones (they are optional).

    NCBI reports ``eff_space`` 0 (and ``hsp_len`` 0) for each query of a multi-query search
    (live cache check, 2026-09-30), while kappa and lambda are given. The space it used is then
    derived from the reported alignments, ``E = kappa * space * exp(-lambda * score)``, taking
    the largest value over the alignments (the cautious one: a larger space means a higher
    score floor). Checked on the single-query E-value sweep: the largest E-value, 621.94 at
    score 10, gives 8.12e8 against the reported 811,905,916. Without hits, query length x
    database length bounds the space from above.
    """
    if not isinstance(raw, dict):
        return None
    try:
        kappa, lam = float(raw["kappa"]), float(raw["lambda"])
        space = float(raw.get("eff_space") or 0)
        db_len = float(raw.get("db_len") or 0)
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(v) and v > 0 for v in (kappa, lam)):
        return None
    if math.isfinite(space) and space > 0:
        return SearchStat(eff_space=space, kappa=kappa, lambda_=lam)
    derived = [
        h.evalue / (kappa * math.exp(-lam * h.score))
        for hit in hits
        for h in hit.hsps
        if h.score is not None and h.evalue > 0 and math.isfinite(h.evalue)
    ]
    if derived:
        return SearchStat(eff_space=max(derived), kappa=kappa, lambda_=lam,
                          space_source="from_hits")  # fmt: skip
    if query_len and math.isfinite(db_len) and db_len > 0:
        return SearchStat(eff_space=query_len * db_len, kappa=kappa, lambda_=lam,
                          space_source="upper_bound")  # fmt: skip
    return None


def _label_for(title: str, query_id: str, labels: list[str]) -> str:
    """Match a BLAST query to a submitted oligo by the title NCBI echoes back.

    Real reports number queries with a global counter (``Query_1830923``), never 1, 2, 3, so
    position is not a usable fallback; guessing could silently swap primers. No match is an error.
    """
    words = title.split()
    first = words[0].removeprefix("lcl|") if words else ""
    if first in labels:
        return first
    raise ParseError(
        f"Cannot match BLAST query '{query_id}' ({title!r}) to the submitted oligos {labels}."
    )


def parse_blast_json(text: str, labels: list[str]) -> ParsedSearch:
    """Parse a JSON2 report; ``labels`` are the FASTA identifiers of the submitted queries."""
    stripped = text.lstrip()
    if not stripped.startswith(("{", "[")):
        raise ParseError(
            "The response is not JSON (it may be an HTML error page or a different format): "
            + stripped[:160].replace("\n", " ")
        )
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"The response is not valid JSON: {exc}") from exc

    outputs = _need(doc, "BlastOutput2", "document root")
    outputs = outputs if isinstance(outputs, list) else [outputs]
    queries: dict[str, QueryResult] = {}
    program = version = database = None
    for i, out in enumerate(outputs):
        report = _need(out, "report", f"BlastOutput2[{i}]")
        program = report.get("program", program)
        version = report.get("version", version)
        database = (report.get("search_target") or {}).get("db", database)
        search = _need(_need(report, "results", "report"), "search", "results")
        qid = str(_need(search, "query_id", "search"))
        title = str(search.get("query_title", ""))
        label = _label_for(title, qid, labels)
        hits: list[Hit] = []
        for h in search.get("hits", []) or []:
            where = f"hit {h.get('num', '?')} of {label}"
            hits.append(
                Hit(
                    num=int(h.get("num", len(hits) + 1)),
                    length=int(h["len"]) if "len" in h else None,
                    descriptions=[_description(d) for d in _need(h, "description", where)],
                    hsps=[_hsp(x, where) for x in _need(h, "hsps", where)],
                )
            )
        queries[label] = QueryResult(
            label=label,
            query_id=qid,
            query_len=int(search["query_len"]) if "query_len" in search else None,
            hits=hits,
            message=search.get("message"),
            stat=_stat(
                search.get("stat"),
                hits,
                int(search["query_len"]) if "query_len" in search else None,
            ),
        )
    missing = [x for x in labels if x not in queries]
    if missing:
        raise ParseError(f"The report contains no section for query {missing}.")
    return ParsedSearch(program=program, version=version, database=database, queries=queries)
