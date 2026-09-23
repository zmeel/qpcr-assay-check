"""A fake NCBI for the partitioned-BLAST variant source: ESearch, ESummary, BLAST, EFetch.

Records are plain sequences. The fake BLAST aligns the query amplicon ungapped (both strands) to
each record named in the ENTREZ_QUERY accession list, returns a full-length HSP where it matches
with substitutions only (or a trimmed one for records flagged ``partial``), writes ``hseq`` in the
query's orientation (as real BLAST does), and adds ``leaks`` -- hits outside the list -- the way
the live check saw them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from qpcr_assay_check.oligo import iupac

from .fake_ncbi import FakeResponse, put_text, status_text


@dataclass
class FakeRecord:
    uid: str
    accession: str
    date: str  # YYYY/MM/DD
    seq: str
    title: str = "Organism sequence"
    partial: bool = False  # BLAST reports only part of the amplicon
    in_blast_db: bool = True  # False: too new for the BLAST database (live finding, 2026-09-23)


@dataclass
class FakeNuccore:
    records: list[FakeRecord]
    leaks: list[FakeRecord] = field(default_factory=list)  # hit by BLAST, never listed
    blast_puts: list[str] = field(default_factory=list)
    efetch_ids: list[str] = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    _queries: dict[str, tuple[str, list[str]]] = field(default_factory=dict)

    def request(self, method, url, params=None, data=None, timeout=None, headers=None):
        p = dict(params or {})
        d = dict(data or {})
        if "esearch.fcgi" in url:
            return self._esearch(p)
        if "esummary.fcgi" in url:
            return self._esummary(p)
        if "efetch.fcgi" in url:
            return self._efetch({**p, **d})
        if "Blast.cgi" in url:
            if d.get("CMD") == "Put":
                rid = f"RID{len(self._queries) + 1:04d}"
                accs = re.findall(r"([A-Z0-9_]+\.\d+)\[ACCN\]", d.get("ENTREZ_QUERY", ""))
                lines = d["QUERY"].splitlines()
                if lines[0] != ">amplicon":  # an ordinary tier search: answer with no hits
                    labels = [ln[1:] for ln in lines if ln.startswith(">")]
                    self._queries[rid] = ("", labels)
                    return FakeResponse(200, put_text(rid))
                self._queries[rid] = ("".join(lines[1:]), accs)
                self.blast_puts.append(rid)
                return FakeResponse(200, put_text(rid))
            if p.get("FORMAT_OBJECT") == "SearchInfo":
                return FakeResponse(200, status_text("READY"))
            return FakeResponse(200, self._blast(*self._queries[p["RID"]]))
        return FakeResponse(404, "not found")

    # ---------------------------------------------------------------- E-utilities
    def _year(self, term: str) -> list[FakeRecord]:
        m = re.search(r"(\d{4})/01/01:\d{4}/12/31\[PDAT\]", term)
        recs = sorted(self.records, key=lambda r: int(r.uid))
        return [r for r in recs if not m or r.date.startswith(m.group(1))]

    def _esearch(self, p: dict) -> FakeResponse:
        recs = self._year(str(p.get("term", "")))
        start, n = int(p.get("retstart", 0)), int(p.get("retmax", 20))
        ids = "".join(f"<Id>{r.uid}</Id>" for r in recs[start : start + n])
        return FakeResponse(
            200, f"<eSearchResult><Count>{len(recs)}</Count><IdList>{ids}</IdList></eSearchResult>"
        )

    def _esummary(self, p: dict) -> FakeResponse:
        by_uid = {r.uid: r for r in self.records}
        ids = [i for i in str(p.get("id", "")).split(",") if i in by_uid]
        result: dict = {"uids": ids}
        for uid in ids:
            r = by_uid[uid]
            result[uid] = {"uid": uid, "accessionversion": r.accession, "createdate": r.date,
                           "slen": len(r.seq), "title": r.title}  # fmt: skip
        return FakeResponse(200, json.dumps({"result": result}))

    def _efetch(self, p: dict) -> FakeResponse:
        self.efetch_ids.append(str(p["id"]))
        ids = str(p["id"]).split(",")
        if len(ids) > 1 or "seq_start" not in p:  # whole records, possibly several
            recs = [r for r in self.records if r.accession in ids]
            return FakeResponse(200, "".join(f">{r.accession} {r.title}\n{r.seq}\n" for r in recs))
        r = next(r for r in self.records if r.accession == p["id"])
        lo, hi = int(p.get("seq_start", 1)), int(p.get("seq_stop", len(r.seq)))
        return FakeResponse(200, f">{r.accession} {r.title}\n{r.seq[lo - 1 : hi]}\n")

    # ---------------------------------------------------------------- BLAST
    def _blast(self, query: str, accs: list[str]) -> str:
        if not query:  # labels of an ordinary tier search, each with an empty hit list
            return json.dumps({"BlastOutput2": [{"report": {
                "program": "blastn", "version": "BLASTN 2.16.0+",
                "search_target": {"db": "core_nt"},
                "results": {"search": {"query_id": f"Query_{i}", "query_title": label,
                                       "query_len": 20, "hits": []}},
            }} for i, label in enumerate(accs, 1)]})  # fmt: skip
        hits = []
        wanted = [r for r in self.records if r.accession in accs and r.in_blast_db]
        wanted += list(self.leaks)
        for r in wanted:
            hsp = _ungapped(query, r)
            if hsp is None:
                continue
            hits.append({
                "num": len(hits) + 1,
                "description": [{"id": f"gb|{r.accession}|", "accession": r.accession.split(".")[0],
                                 "title": r.title, "taxid": 1, "sciname": "Organism"}],
                "len": len(r.seq),
                "hsps": [hsp],
            })  # fmt: skip
        doc = {"BlastOutput2": [{"report": {
            "program": "blastn", "version": "BLASTN 2.16.0+", "search_target": {"db": "core_nt"},
            "results": {"search": {"query_id": "Query_1", "query_title": "amplicon",
                                   "query_len": len(query), "hits": hits}},
        }}]}  # fmt: skip
        return json.dumps(doc)


def _ungapped(query: str, r: FakeRecord) -> dict | None:
    """Best ungapped placement of the whole query (at most 3 mismatches), either strand."""
    n = len(query)
    best = None
    for strand, subject in (("Plus", r.seq), ("Minus", iupac.reverse_complement(r.seq))):
        for i in range(len(subject) - n + 1):
            window = subject[i : i + n]
            mm = sum(a != b for a, b in zip(query, window, strict=True))
            if mm <= 3 and (best is None or mm < best[0]):
                best = (mm, strand, i, window)
    if best is None:
        return None
    mm, strand, i, window = best
    q0, q1 = (0, n) if not r.partial else (8, n)  # a partial hit leaves 8 query bases out
    qseq, hseq = query[q0:q1], window[q0:q1]
    if strand == "Plus":
        hit_from, hit_to = i + q0 + 1, i + q1
    else:  # coordinates on the record's forward strand, from > to
        L = len(r.seq)
        hit_from, hit_to = L - (i + q0), L - (i + q1) + 1
    ident = sum(a == b for a, b in zip(qseq, hseq, strict=True))
    return {
        "num": 1, "bit_score": float(ident), "score": ident, "evalue": 1e-20, "identity": ident,
        "query_from": q0 + 1, "query_to": q1, "hit_from": hit_from, "hit_to": hit_to,
        "query_strand": "Plus", "hit_strand": strand, "align_len": len(qseq), "gaps": 0,
        "qseq": qseq, "hseq": hseq,
        "midline": "".join("|" if a == b else " " for a, b in zip(qseq, hseq, strict=True)),
    }  # fmt: skip
