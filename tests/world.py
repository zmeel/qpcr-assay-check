"""A small constructed world for end-to-end tests: genomes, BLAST hits, and an efetch server.

Everything here is CONSTRUCTED. Hit objects follow the real NCBI layout and strand convention
(see tests/fixtures/real_hits_strands.json): for a Minus hit hit_from > hit_to, query_strand is
always Plus and hseq is written in the oligo's orientation.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

from qpcr_assay_check.ncbi.blast import BlastApi
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.jobs import JobStore
from qpcr_assay_check.ncbi.runner import BlastRunner
from qpcr_assay_check.ncbi.settings import Credentials
from qpcr_assay_check.oligo import iupac

from .fake_ncbi import FakeClock, FakeNcbi, FakeResponse

T0 = datetime(2026, 9, 21, 9, 0, tzinfo=UTC)


_SUB = {"A": "C", "C": "G", "G": "T", "T": "A"}


def mutate(seq: str, positions: list[int]) -> str:
    """Substitute the bases at 1-based ``positions`` (A->C, C->G, G->T, T->A)."""
    out = list(seq)
    for p in positions:
        out[p - 1] = _SUB[out[p - 1]]
    return "".join(out)


def filler(n: int, seed: int) -> str:
    """Deterministic pseudo-random sequence that contains no oligo-like sites."""
    import random

    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(n))


def _no_positive_prefix(is_match: list[bool]) -> bool:
    """True if match(+1)/mismatch(-3) never sums positive over any prefix.

    ``is_match`` must be ordered outward from the alignment boundary. If some prefix summed
    positive, BLAST's own extension would have included it and raised the score, so the
    reported alignment could not have stopped where it did.
    """
    score = 0
    for m in is_match:
        score += 1 if m else -3
        if score > 0:
            return False
    return True


class World:
    def __init__(self) -> None:
        self.genomes: dict[str, dict] = {}
        self.hits: dict[int, dict[str, list[dict]]] = {}  # taxid -> label -> hit dicts
        self.missing: set[str] = set()  # accessions whose efetch fails
        self.taxonomy_names: dict[str, int] = {}  # organism name -> taxid, for name resolution
        self.dates: dict[str, str] = {}  # accession.version -> "YYYY/MM/DD", for ESummary

    def name(self, organism_name: str, taxid: int) -> None:
        """Register an organism name that Entrez Taxonomy ESearch should resolve to ``taxid``."""
        self.taxonomy_names[organism_name] = taxid

    def date(self, accession: str, date_str: str) -> None:
        """Register an accession's submission date (``YYYY/MM/DD``) for ESummary."""
        self.dates[accession] = date_str

    def genome(self, acc: str, taxid: int, sciname: str, seq: str, title: str = "") -> None:
        self.genomes[acc] = {
            "taxid": taxid,
            "sciname": sciname,
            "seq": seq,
            "title": title or f"{sciname} chromosome, complete genome",
        }

    def hit(
        self,
        taxid: int,
        label: str,
        oligo: str,
        acc: str,
        start: int,
        strand: str = "+",
        trim5: int = 0,
        trim3: int = 0,
        realistic: bool = True,
    ) -> None:
        """Add a BLAST hit for ``oligo`` placed at 1-based forward-strand ``start``.

        ``trim5``/``trim3`` leave oligo bases unaligned, as BLAST does when extension stops. BLAST
        reports a locally maximal alignment: with match +1 / mismatch -3, no prefix of the
        unaligned flank (read outward from the alignment boundary) can sum to a positive score,
        or BLAST would have extended over it and raised the score. With ``realistic=True`` (the
        default) a hit that violates this is rejected.
        """
        g = self.genomes[acc]
        n = len(oligo)
        segment = g["seq"][start - 1 : start - 1 + n]
        subject = segment if strand == "+" else iupac.reverse_complement(segment)
        if realistic:
            if trim5 and not _no_positive_prefix(
                [oligo[i] == subject[i] for i in range(trim5 - 1, -1, -1)]
            ):
                raise ValueError(
                    "unrealistic BLAST hit: a prefix of the unaligned 5' flank scores positive, "
                    "so BLAST would have extended the alignment over it"
                )
            if trim3 and not _no_positive_prefix(
                [oligo[i] == subject[i] for i in range(n - trim3, n)]
            ):
                raise ValueError(
                    "unrealistic BLAST hit: a prefix of the unaligned 3' flank scores positive, "
                    "so BLAST would have extended the alignment over it"
                )
        qseq = oligo[trim5 : n - trim3]
        hseq = subject[trim5 : n - trim3]
        ident = sum(a == b for a, b in zip(qseq, hseq, strict=True))
        if strand == "+":
            hit_from, hit_to = start + trim5, start + n - trim3 - 1
        else:
            hit_from, hit_to = start + n - 1 - trim5, start + trim3
        self.hits.setdefault(taxid, {}).setdefault(label, []).append(
            {
                "num": len(self.hits.get(taxid, {}).get(label, [])) + 1,
                "description": [
                    {
                        "id": f"gi|1|gb|{acc}|",
                        "accession": acc.split(".")[0],
                        "title": g["title"],
                        "taxid": g["taxid"],
                        "sciname": g["sciname"],
                    }
                ],
                "len": len(g["seq"]),
                "hsps": [
                    {
                        "num": 1,
                        "bit_score": float(ident),
                        "score": ident,
                        "evalue": 1.0 / (1 + ident),
                        "identity": ident,
                        "query_from": trim5 + 1,
                        "query_to": n - trim3,
                        "query_strand": "Plus",
                        "hit_from": hit_from,
                        "hit_to": hit_to,
                        "hit_strand": "Plus" if strand == "+" else "Minus",
                        "align_len": n - trim5 - trim3,
                        "gaps": 0,
                        "qseq": qseq,
                        "hseq": hseq,
                        "midline": "".join(
                            "|" if a == b else " " for a, b in zip(qseq, hseq, strict=True)
                        ),
                    }
                ],
            }
        )

    def result(self, payload: dict[str, str]) -> str:
        labels = [ln[1:] for ln in payload["QUERY"].splitlines() if ln.startswith(">")]
        taxids = [int(t) for t in re.findall(r"txid(\d+)\[ORGN\]", payload.get("ENTREZ_QUERY", ""))]
        reports = []
        for i, label in enumerate(labels):
            hits: list[dict] = []
            for t in taxids:
                hits += self.hits.get(t, {}).get(label, [])
            reports.append(
                {
                    "report": {
                        "program": "blastn",
                        "version": "BLASTN 2.17.0+",
                        "search_target": {"db": "core_nt"},
                        "results": {
                            "search": {
                                "query_id": f"Query_{1830923 + i}",
                                "query_title": label,
                                "query_len": len(payload["QUERY"].splitlines()[2 * i + 1]),
                                "hits": [dict(h, num=n + 1) for n, h in enumerate(hits)],
                            }
                        },
                    }
                }
            )
        return json.dumps({"BlastOutput2": reports})


class WorldFake(FakeNcbi):
    """FakeNcbi plus an efetch server backed by the world's genomes."""

    def __init__(self, world: World, **kw) -> None:
        super().__init__(world.result, **kw)
        self.world = world
        self.efetch_calls: list[dict] = []

    def request(self, method, url, params=None, data=None, timeout=None):
        if "esearch.fcgi" in url and dict(params or {}).get("db") == "taxonomy":
            term = str(dict(params or {}).get("term", ""))
            name = term.rsplit("[", 1)[0]  # strip the "[Scientific Name]"/"[All Names]" field tag
            taxid = self.world.taxonomy_names.get(name)
            ids = f"<Id>{taxid}</Id>" if taxid is not None else ""
            count = 1 if taxid is not None else 0
            return FakeResponse(
                200, f"<eSearchResult><Count>{count}</Count><IdList>{ids}</IdList></eSearchResult>"
            )
        if "esearch.fcgi" in url and dict(params or {}).get("db") == "nuccore":
            term = str(dict(params or {}).get("term", ""))
            m = re.search(r"(\d{4})/01/01:\d{4}/12/31\[PDAT\]", term)
            if m:
                count = sum(1 for d in self.world.dates.values() if d.startswith(m.group(1)))
            else:
                count = len(self.world.dates)
            return FakeResponse(200, f"<eSearchResult><Count>{count}</Count></eSearchResult>")
        if "esummary.fcgi" in url:
            p = dict(params or {})
            ids = [i for i in str(p.get("id", "")).split(",") if i]
            result: dict = {"uids": []}
            for n, acc in enumerate(ids):
                if acc in self.world.dates:
                    # NCBI keys the result by its own resolved UID, never by the accession string
                    # given as input -- use a UID that deliberately differs from the accession.
                    uid = f"999{n}"
                    result["uids"].append(uid)
                    result[uid] = {"accessionversion": acc, "createdate": self.world.dates[acc]}
            return FakeResponse(200, json.dumps({"header": {"type": "esummary"}, "result": result}))
        if "efetch.fcgi" in url:
            p = dict(params or {})
            if p.get("db") == "taxonomy":
                # Not modelled: an empty (but valid) TaxaSet, so a taxonomy_breakdown lookup
                # degrades to "no lineage" instead of erroring; not a sequence-window fetch, so
                # it is not counted in efetch_calls (that counter is about specificity windows).
                return FakeResponse(200, "<?xml version='1.0'?><TaxaSet></TaxaSet>")
            self.efetch_calls.append(p)
            acc = str(p["id"])
            if acc in self.world.missing or acc not in self.world.genomes:
                return FakeResponse(400, "Error: record not found")
            seq = self.world.genomes[acc]["seq"]
            start, stop = int(p.get("seq_start", 1)), int(p.get("seq_stop", len(seq)))
            window = seq[start - 1 : stop]
            return FakeResponse(200, f">{acc}:{start}-{stop} constructed\n{window}\n")
        return super().request(method, url, params, data, timeout)


def make_runner(cfg, tmp_path, fake):
    fc = FakeClock()
    fake.clock = fc
    http = NcbiHttp(
        cfg.ncbi, Credentials("lab@example.org"), session=fake,
        clock=fc.monotonic, sleep=fc.sleep, jitter=lambda: 0.0,
    )  # fmt: skip
    now = lambda: T0 + timedelta(seconds=fc.t)  # noqa: E731
    store = JobStore(tmp_path / "jobs.json")
    cache = Cache(tmp_path / "cache", now=now)
    runner = BlastRunner(
        BlastApi(http, cfg.ncbi.blast_url),
        cache,
        store,
        cfg.ncbi,
        "JSON2_S",
        now=now,
        sleep=fc.sleep,
    )
    from qpcr_assay_check.ncbi.eutils import Eutils
    from qpcr_assay_check.specificity.fetch import WindowFetcher

    fetcher = WindowFetcher(Eutils(http, cfg.ncbi.eutils_url), cache)
    return runner, store, fetcher
