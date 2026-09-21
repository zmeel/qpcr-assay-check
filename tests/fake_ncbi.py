"""A scriptable stand-in for NCBI, used instead of the network in tests.

Everything returned here is CONSTRUCTED by hand from the documented formats. It is not real NCBI
output. Real captures from ``scripts/smoke_test.py`` should replace or extend these fixtures.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import requests


class FakeResponse:
    def __init__(
        self, status_code: int = 200, text: str = "", headers: dict[str, str] | None = None
    ):
        self.status_code, self.text, self.headers = status_code, text, headers or {}


def blast_json(
    queries: dict[str, list[dict[str, Any]]], *, single_dict: bool = False, by_title: bool = True
) -> str:
    """A constructed JSON2_S-style report. ``queries`` maps label -> list of hit specs."""
    reports = []
    for i, (label, hits) in enumerate(queries.items(), start=1):
        rep_hits = []
        for n, h in enumerate(hits, start=1):
            rep_hits.append(
                {
                    "num": n,
                    "description": [
                        {
                            "id": f"gb|{h['acc']}.1|",
                            "accession": h["acc"],
                            "title": h.get("title", f"{h.get('sciname', 'Organism')} sequence"),
                            "taxid": h.get("taxid"),
                            "sciname": h.get("sciname"),
                        }
                    ]
                    + [
                        {
                            "id": f"gb|{a}.1|",
                            "accession": a,
                            "title": "merged",
                            "taxid": h.get("taxid"),
                            "sciname": h.get("sciname"),
                        }
                        for a in h.get("merged", [])
                    ],
                    "len": h.get("len", 30000),
                    "hsps": [
                        {
                            "num": 1,
                            "bit_score": float(h.get("identity", 20)),
                            "score": h.get("identity", 20),
                            "evalue": h.get("evalue", 0.001),
                            "identity": h.get("identity", 20),
                            "query_from": 1,
                            "query_to": h.get("identity", 20),
                            "hit_from": 100 * n,
                            "hit_to": 100 * n + h.get("identity", 20) - 1,
                            "query_strand": "Plus",
                            "hit_strand": h.get("strand", "Plus"),
                            "align_len": h.get("identity", 20),
                            "gaps": 0,
                            "qseq": "A" * h.get("identity", 20),
                            "hseq": "A" * h.get("identity", 20),
                            "midline": "|" * h.get("identity", 20),
                        }
                    ],
                }
            )
        reports.append(
            {
                "report": {
                    "program": "blastn",
                    "version": "BLASTN 2.16.0+",
                    "search_target": {"db": "core_nt"},
                    "results": {
                        "search": {
                            "query_id": f"Query_{1830922 + i}",
                            "query_title": label if by_title else "",
                            "query_len": 24,
                            "hits": rep_hits,
                        }
                    },
                }
            }
        )
    if single_dict and len(reports) == 1:
        return json.dumps({"BlastOutput2": reports[0]})
    return json.dumps({"BlastOutput2": reports})


def put_text(rid: str, rtoe: int = 15) -> str:
    return (
        f"<html>\n<!--QBlastInfoBegin\n    RID = {rid}\n    RTOE = {rtoe}\n"
        "QBlastInfoEnd\n-->\n</html>"
    )


def status_text(status: str, hits: str = "yes") -> str:
    return (
        f"<html><!--QBlastInfoBegin\n\tStatus={status}\n\tThereAreHits={hits}\n"
        "QBlastInfoEnd\n--></html>"
    )


class FakeNcbi:
    """Duck-types ``requests.Session``: records every call and answers like NCBI would."""

    def __init__(
        self,
        result: Callable[[dict[str, str]], str] | str,
        statuses: list[str] | None = None,
        put_failures: list[Any] | None = None,
        status_scripts: list[list[str]] | None = None,
        crash_on_first_status: bool = False,
    ) -> None:
        self.headers: dict[str, str] = {}
        self.result = result
        self.statuses = list(statuses if statuses is not None else ["READY"])
        self.put_failures = list(put_failures or [])
        self.status_scripts = list(status_scripts or [])
        self.crash_on_first_status = crash_on_first_status
        self.clock: FakeClock | None = None
        self.calls: list[dict[str, Any]] = []
        self.searches: dict[str, dict[str, str]] = {}
        self.n_put = 0
        self.status_by_rid: dict[str, list[str]] = {}

    def request(self, method, url, params=None, data=None, timeout=None):
        payload = dict(data if data is not None else params or {})
        t = self.clock.t if self.clock else None
        self.calls.append({"method": method, "url": url, "payload": payload, "t": t})
        if "Blast.cgi" in url:
            cmd = payload.get("CMD")
            if cmd == "Put":
                if self.put_failures:
                    failure = self.put_failures.pop(0)
                    if isinstance(failure, Exception):
                        raise failure
                    return FakeResponse(int(failure), "simulated server error")
                self.n_put += 1
                rid = f"RID{self.n_put:04d}"
                self.searches[rid] = payload
                script = self.status_scripts.pop(0) if self.status_scripts else self.statuses
                self.status_by_rid[rid] = list(script)
                return FakeResponse(200, put_text(rid))
            if payload.get("FORMAT_OBJECT") == "SearchInfo":
                if self.crash_on_first_status:
                    self.crash_on_first_status = False
                    raise RuntimeError("simulated crash while polling")
                queue = self.status_by_rid.setdefault(payload["RID"], list(self.statuses))
                st = queue.pop(0) if len(queue) > 1 else queue[0]
                return FakeResponse(200, status_text(st))
            if "FORMAT_TYPE" in payload:
                body = (
                    self.result(self.searches[payload["RID"]])
                    if callable(self.result)
                    else self.result
                )
                return FakeResponse(200, body)
        if "esearch" in url:
            return FakeResponse(200, "<eSearchResult><Count>1234</Count></eSearchResult>")
        if "efetch" in url:
            return FakeResponse(200, f">{payload.get('id')}\nACGTACGT\n")
        return FakeResponse(404, "not found")


def connection_error() -> Exception:
    return requests.ConnectionError("simulated connection reset")


class FakeClock:
    """Deterministic time: ``sleep`` advances the clock instead of waiting."""

    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


class ScriptedSession:
    """Returns the queued responses/exceptions in order (for HTTP-layer tests)."""

    def __init__(self, script: list[Any]) -> None:
        self.headers: dict[str, str] = {}
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []

    def request(self, method, url, params=None, data=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": params, "data": data})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def hits_for_payload(payload: dict[str, str]) -> str:
    """Constructed result for any submitted FASTA: three 20-base hits per query."""
    import re

    labels = [ln[1:] for ln in payload["QUERY"].splitlines() if ln.startswith(">")]
    taxids = [
        int(t) for t in re.findall(r"txid(\d+)\[ORGN\]", payload.get("ENTREZ_QUERY", ""))
    ] or [0]
    spec = [
        {
            "acc": f"AB{100000 + i}",
            "taxid": taxids[i % len(taxids)],
            "sciname": f"Organism {taxids[i % len(taxids)]}",
            "identity": 20,
        }
        for i in range(3)
    ]
    return blast_json(dict.fromkeys(labels, spec))
