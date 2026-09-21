#!/usr/bin/env python3
"""Live smoke test for qpcr-assay-check's NCBI assumptions.  (v0.2.1)

WHY THIS EXISTS
    The developer of this tool could not reach NCBI while writing the BLAST client. Several
    behaviours were therefore taken from documentation or memory and are UNVERIFIED (see
    docs/ARCHITECTURE.md). This script checks them against the real servers and writes a single
    report, smoke_out/smoke_report.json, which contains no secrets and can be pasted back.

WHAT IT SENDS TO NCBI
    * the three CDC 2019-nCoV N1 oligo sequences (published sequences, not proprietary)
    * a few E-utilities queries; up to six BLAST searches (use --quick for two)
    Your NCBI_EMAIL is sent to NCBI as NCBI requires. Neither it nor NCBI_API_KEY is written to
    any output file.

HOW TO RUN (from the repository root, after `pip install -e .`)
    export NCBI_EMAIL="your.name@example.org"
    export NCBI_API_KEY="..."            # optional
    mkdir -p smoke_out
    nohup python scripts/smoke_test.py > smoke_out/run.log 2>&1 &
    tail -f smoke_out/run.log

    Options:
      --quick               only the core searches (SARS-CoV-2 control + a restriction check)
      --max-wait-minutes N  give up on one search after N minutes (default 30); it stays
                            resumable, and the next step still runs
      --human               also run the human-background search with the default settings
                            (this one is SLOW; see below)
      --probe-databases     try alternative databases for a faster human background search

    The report smoke_out/smoke_report.json is rewritten after EVERY step, so you can paste it
    back at any time, even while the script is still running or after you stopped it.
    Interrupted or stopped? Run the same command again: finished searches come from the cache and
    running ones are resumed (RIDs are valid for about 36 hours).

    Why the human search is opt-in: in a first live run, a human-restricted search with the
    default settings (database core_nt, word size 7, E-value 1000) was still WAITING after
    45+ minutes. That is a finding about the design, not necessarily a bug.

WHAT TO PASTE BACK
    The contents of smoke_out/smoke_report.json (typically < 100 KB). Nothing else is needed.
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qpcr_assay_check import __version__
from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import QpcrAssayCheckError
from qpcr_assay_check.models import Assay
from qpcr_assay_check.ncbi import blast
from qpcr_assay_check.ncbi.blast import BlastApi
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiError, NcbiHttp
from qpcr_assay_check.ncbi.jobs import Job, JobStore
from qpcr_assay_check.ncbi.parser import parse_blast_json
from qpcr_assay_check.ncbi.runner import BlastRunner
from qpcr_assay_check.ncbi.settings import credentials_from_env
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.search.assess import assess_saturation, summarise_restriction
from qpcr_assay_check.search.planner import plan_searches

log = logging.getLogger("smoke")

# Published CDC 2019-nCoV N1 oligos (see examples/cdc_2019-nCoV_N1.yaml for their provenance).
OLIGOS = {
    "forward": "GACCCCAAAATCAGCGAAAT",
    "reverse": "TCTGGTTACTGCCAGTTGAATCTG",
    "probe": "ACCCCGCATTACGTTTGGTGGACC",
}
REFERENCE = "NC_045512.2"
SARS2, HUMAN = 2697049, 9606
NAMES_TO_RESOLVE = [
    "Homo sapiens",
    "Mus musculus",
    "Severe acute respiratory syndrome coronavirus 2",
    "Escherichia coli",
    "Staphylococcus aureus",
    "Mycobacterium tuberculosis",
    "Chlamydia trachomatis",
    "Neisseria gonorrhoeae",
    "Mycoplasma pneumoniae",
    "Legionella pneumophila",
    "Bordetella pertussis",
    "Streptococcus pneumoniae",
    "Human immunodeficiency virus 1",
    "Influenza A virus",
]


# ------------------------------------------------------------------ helpers
class Report:
    """Collects the outcome of every step plus the headline findings.

    ``sink`` is called after every step so that a partial report always exists on disk.
    """

    def __init__(self, sink: Callable[[], None] | None = None) -> None:
        self.steps: dict[str, dict[str, Any]] = {}
        self.findings: dict[str, Any] = {}
        self._sink = sink

    def step(self, name: str) -> Callable[[Callable[[], dict[str, Any]]], None]:
        def run(fn: Callable[[], dict[str, Any]]) -> None:
            t0 = time.monotonic()
            log.info("== %s", name)
            try:
                detail = fn()
                self.steps[name] = {
                    "ok": True,
                    "seconds": round(time.monotonic() - t0, 1),
                    **detail,
                }
            except (QpcrAssayCheckError, Exception) as exc:  # noqa: BLE001 - report, never abort
                log.error("step %s failed: %s", name, exc)
                self.steps[name] = {
                    "ok": False,
                    "seconds": round(time.monotonic() - t0, 1),
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback_tail": traceback.format_exc().splitlines()[-4:],
                }
            if self._sink:
                self._sink()

        return run


def shape(obj: Any, depth: int = 0) -> Any:
    """Compact structure of a JSON document: keys and value types, first list element only."""
    if depth > 8:
        return "..."
    if isinstance(obj, dict):
        return {k: shape(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [shape(obj[0], depth + 1), f"(list of {len(obj)})"] if obj else ["(empty list)"]
    return type(obj).__name__


def trim(obj: Any, depth: int = 0) -> Any:
    """A copy of ``obj`` with long strings cut and lists limited to 2 items (for the report)."""
    if isinstance(obj, dict):
        return {k: trim(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [trim(v, depth + 1) for v in obj[:2]] + (
            [f"...(+{len(obj) - 2} more)"] if len(obj) > 2 else []
        )
    if isinstance(obj, str) and len(obj) > 160:
        return obj[:160] + "..."
    return obj


def save_raw(out: Path, name: str, text: str) -> None:
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw / f"{name}.txt.gz", "wt", encoding="utf-8") as fh:
        fh.write(text)
    (raw / f"{name}.head.txt").write_text(text[:20000], encoding="utf-8")


def esearch(http: NcbiHttp, base: str, db: str, term: str, **extra: Any) -> dict[str, Any]:
    """ESearch returning count, ids and any error text (never raises on NCBI-level errors)."""
    params = {"db": db, "term": term, **extra}
    resp = http.request("GET", f"{base}/esearch.fcgi", service="eutils", params=params)
    text = resp.text
    out: dict[str, Any] = {"http": resp.status_code, "head": text[:300]}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return out
    out["count"] = int(root.findtext("Count") or -1)
    out["ids"] = [e.text for e in root.iter("Id")]
    err = root.findtext("ERROR")
    if err:
        out["error"] = err
    return out


def lineage_check(
    http: NcbiHttp, base: str, results: list[Any], requested: list[int], *, cap: int = 300
) -> dict[str, Any]:
    """Strict check of a taxon restriction: is every hit's taxon inside the requested subtree?

    Hit taxa are often strains (descendants) of the requested taxon, so comparing taxon IDs is not
    enough; the lineage of each distinct hit taxon is fetched from Entrez Taxonomy instead.
    """
    taxids = sorted(
        {d.taxid for q in results for h in q.hits for d in h.descriptions if d.taxid is not None}
    )[:cap]
    want = {str(t) for t in requested}
    inside, outside = 0, []
    for i in range(0, len(taxids), 100):
        chunk = taxids[i : i + 100]
        resp = http.request(
            "GET",
            f"{base}/efetch.fcgi",
            service="eutils",
            params={"db": "taxonomy", "id": ",".join(map(str, chunk)), "retmode": "xml"},
        )
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return {"error": "unparseable taxonomy response", "head": resp.text[:200]}
        for tax in root.findall("Taxon"):
            tid = tax.findtext("TaxId")
            ids = {tid} | {t.findtext("TaxId") for t in tax.findall("LineageEx/Taxon")}
            if ids & want:
                inside += 1
            else:
                outside.append({"taxid": tid, "name": tax.findtext("ScientificName")})
    return {
        "n_checked": inside + len(outside),
        "fraction_in_requested_subtree": (inside / (inside + len(outside)))
        if (inside + len(outside))
        else None,
        "n_in_requested_subtree": inside,
        "n_outside": len(outside),
        "outside_examples": outside[:5],
        "capped_at": cap if len(taxids) >= cap else None,
    }


def run_blast(
    runner: BlastRunner, store: JobStore, tier: str, label: str, taxids: list[int],
    entrez: str | None, params: dict[str, str], labels: list[str],
) -> tuple[Job, str]:  # fmt: skip
    """Run one search through the package's own runner (submit, poll, fetch, resume)."""
    key = blast.request_key(params)
    job = store.jobs.get(key) or Job(
        key=key, tier=tier, label=label, taxids=taxids, entrez_query=entrez,
        params={k: v for k, v in params.items() if k != "QUERY"}, query_labels=labels,
    )  # fmt: skip
    store.upsert(job)
    raw = runner.run(job, params["QUERY"], params)
    return job, raw


def analyse_search(
    raw: str, labels: list[str], cfg: Any, taxids: list[int], out: Path, name: str
) -> dict[str, Any]:
    """Parse a raw result and summarise everything the design depends on."""
    save_raw(out, name, raw)
    info: dict[str, Any] = {"raw_bytes": len(raw), "raw_starts_with": raw[:80]}
    try:
        doc = json.loads(raw)
        info["json_shape"] = shape(doc)
        hits = _first_hit(doc)
        if hits is not None:
            info["first_hit_example"] = trim(hits)
    except json.JSONDecodeError as exc:
        info["json_error"] = str(exc)
    parsed = parse_blast_json(raw, labels)  # ParseError propagates: it is a finding
    info.update(program=parsed.program, blast_version=parsed.version, database=parsed.database)
    per_query: dict[str, Any] = {}
    for label, q in parsed.queries.items():
        idents = [h.best_identity for h in q.hits]
        sat = assess_saturation(
            q, cfg.search.hitlist_size, cfg.search.relevance.min_identical_bases
        )
        per_query[label] = {
            "n_hits": len(q.hits),
            "query_id": q.query_id,
            "query_len": q.query_len,
            "max_identity": max(idents, default=None),
            "min_identity": min(idents, default=None),
            "n_descriptions_total": sum(len(h.descriptions) for h in q.hits),
            "max_descriptions_in_one_hit": max((len(h.descriptions) for h in q.hits), default=0),
            "hit_strands": sorted({s.hit_strand for h in q.hits for s in h.hsps}),
            "has_alignment_strings": all(s.qseq and s.hseq for h in q.hits[:50] for s in h.hsps),
            "list_full": sat.list_full,
            "saturated": sat.saturated,
        }
    info["per_query"] = per_query
    results = list(parsed.queries.values())
    info["description_fields_present"] = {
        "taxid": all(
            d.taxid is not None for q in results for h in q.hits[:200] for d in h.descriptions
        ),
        "sciname": all(d.sciname for q in results for h in q.hits[:200] for d in h.descriptions),
        "accession_with_version": all(
            d.accession_version and "." in d.accession_version
            for q in results for h in q.hits[:200] for d in h.descriptions
        ),
    }  # fmt: skip
    if taxids:
        r = summarise_restriction(results, taxids)
        info["restriction"] = r.model_dump()
    return info


def _first_hit(doc: Any) -> Any:
    try:
        out = doc["BlastOutput2"]
        rep = (out[0] if isinstance(out, list) else out)["report"]
        return rep["results"]["search"]["hits"][0]
    except (KeyError, IndexError, TypeError):
        return None


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=Path("smoke_out"), help="output directory")
    ap.add_argument("--quick", action="store_true", help="only the core BLAST searches")
    ap.add_argument("--human", action="store_true", help="also run the (slow) human search")
    ap.add_argument(
        "--probe-databases", action="store_true", help="try alternative databases for human"
    )
    ap.add_argument(
        "--max-wait-minutes", type=float, default=30.0, help="per-search wait limit (default 30)"
    )
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", stream=sys.stdout
    )

    try:
        creds = credentials_from_env()
    except QpcrAssayCheckError as exc:
        log.error("%s", exc)
        return 2

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    cfg.ncbi.cache_dir = str(out / "cache")
    cfg.ncbi.max_wait_minutes = args.max_wait_minutes
    http = NcbiHttp(cfg.ncbi, creds)
    eu, api = Eutils(http, cfg.ncbi.eutils_url), BlastApi(http, cfg.ncbi.blast_url)
    store = JobStore(out / "jobs.json")
    runner = BlastRunner(api, Cache(cfg.ncbi.cache_dir), store, cfg.ncbi, cfg.search.result_format)
    base = cfg.ncbi.eutils_url
    started = datetime.now(UTC).isoformat()
    ctx: dict[str, Any] = {}

    def write_report(complete: bool) -> None:
        report = {
            "smoke_test_version": "0.2.1",
            "started": started,
            "updated": datetime.now(UTC).isoformat(),
            "complete": complete,
            "options": {
                "quick": args.quick,
                "human": args.human,
                "probe_databases": args.probe_databases,
                "max_wait_minutes": args.max_wait_minutes,
            },
            "findings": rep.findings,
            "steps": rep.steps,
        }
        text = creds.redact(json.dumps(report, indent=2, default=str))
        (out / "smoke_report.json").write_text(text, encoding="utf-8")

    rep = Report(lambda: write_report(False))

    @rep.step("00_environment")
    def _env() -> dict[str, Any]:
        return {
            "python": sys.version.split()[0],
            "tool_version": __version__,
            "email_set": True,
            "api_key_set": bool(creds.api_key),
            "quick": args.quick,
        }

    @rep.step("01_esearch_counts")
    def _counts() -> dict[str, Any]:
        res = {
            "sars2_all": esearch(http, base, "nuccore", f"txid{SARS2}[ORGN]", retmax=0),
            "sars2_2022": esearch(
                http,
                base,
                "nuccore",
                f"txid{SARS2}[ORGN] AND 2022/01/01:2022/12/31[PDAT]",
                retmax=0,
            ),
            "sars2_2020_january": esearch(
                http,
                base,
                "nuccore",
                f"txid{SARS2}[ORGN] AND 2020/01/01:2020/01/31[PDAT]",
                retmax=0,
            ),
        }
        rep.findings["esearch_date_filter_pdat_works"] = res["sars2_2022"].get(
            "count", 0
        ) > 0 and res["sars2_2022"].get("count", 0) < res["sars2_all"].get("count", 0)
        return {k: {kk: vv for kk, vv in v.items() if kk != "ids"} for k, v in res.items()}

    @rep.step("02_esearch_uid_cap")
    def _cap() -> dict[str, Any]:
        probes = {}
        for start in (0, 9999, 10000, 99999, 100000):
            r = esearch(http, base, "nuccore", f"txid{SARS2}[ORGN]", retstart=start, retmax=1)
            probes[str(start)] = {
                "n_ids_returned": len(r.get("ids", [])),
                "error": r.get("error"),
                "head": r.get("head", "")[:200] if r.get("error") or not r.get("ids") else "",
            }
        rep.findings["esearch_retstart_10000_works"] = bool(probes["10000"]["n_ids_returned"])
        rep.findings["esearch_retstart_100000_works"] = bool(probes["100000"]["n_ids_returned"])
        return {"retstart_probes": probes}

    @rep.step("03_taxonomy_name_resolution")
    def _tax() -> dict[str, Any]:
        table: dict[str, Any] = {}
        for name in NAMES_TO_RESOLVE:
            r = esearch(http, base, "taxonomy", f"{name}[Scientific Name]")
            table[name] = {"count": r.get("count"), "ids": r.get("ids", [])[:5]}
        ctx["resolved"] = [int(v["ids"][0]) for v in table.values() if v["count"] == 1]
        ctx["by_name"] = {k: int(v["ids"][0]) for k, v in table.items() if v["count"] == 1}
        rep.findings["taxonomy_names_resolved_uniquely"] = f"{len(ctx['resolved'])}/{len(table)}"
        resp = http.request(
            "GET", f"{base}/efetch.fcgi", service="eutils",
            params={"db": "taxonomy", "id": SARS2, "retmode": "xml"},
        )  # fmt: skip
        m = re.search(r"<ScientificName>([^<]+)</ScientificName>", resp.text)
        return {"resolution": table, "taxid_2697049_scientific_name": m.group(1) if m else None}

    @rep.step("04_reference_check_against_NC_045512.2")
    def _reference() -> dict[str, Any]:
        fasta = eu.fetch_fasta(REFERENCE)
        header, seq = fasta.split("\n", 1)[0], "".join(fasta.split("\n")[1:]).upper()
        f, r_rc, p = OLIGOS["forward"], iupac.reverse_complement(OLIGOS["reverse"]), OLIGOS["probe"]
        pos = {
            "forward_start": seq.find(f) + 1 if f in seq else None,
            "reverse_rc_start": seq.find(r_rc) + 1 if r_rc in seq else None,
            "probe_start_plus": seq.find(p) + 1 if p in seq else None,
            "probe_start_minus": seq.find(iupac.reverse_complement(p)) + 1
            if iupac.reverse_complement(p) in seq
            else None,
        }
        detail: dict[str, Any] = {
            "fasta_header": header,
            "sequence_length": len(seq),
            "positions": pos,
        }
        fs, rs = pos["forward_start"], pos["reverse_rc_start"]
        if fs and rs:
            end = rs + len(r_rc) - 1
            amplicon = seq[fs - 1 : end]
            detail.update(
                amplicon_start=fs,
                amplicon_end=end,
                amplicon_length=len(amplicon),
                amplicon_sequence=amplicon,
            )
            rep.findings["cdc_n1_oligos_match_reference_exactly"] = bool(
                (pos["probe_start_plus"] or pos["probe_start_minus"]) and len(amplicon) == 72
            )
            win = eu.fetch_fasta(REFERENCE, start=fs, stop=end)
            win_seq = "".join(win.split("\n")[1:]).upper()
            rc_win = eu.fetch_fasta(REFERENCE, start=fs, stop=end, strand=2)
            rc_seq = "".join(rc_win.split("\n")[1:]).upper()
            detail["efetch_window_matches"] = win_seq == amplicon
            detail["efetch_strand2_is_reverse_complement"] = rc_seq == iupac.reverse_complement(
                amplicon
            )
            detail["window_header"] = win.split("\n", 1)[0]
        else:
            rep.findings["cdc_n1_oligos_match_reference_exactly"] = False
        return detail

    # ---- BLAST core searches through the package's own planner/runner ------------------------
    assay = Assay.model_validate(
        {
            "assay_name": "smoke", **OLIGOS, "probe_reporter": "FAM", "probe_quencher": "BHQ1",
            "template_type": "RNA", "target": {"taxid": SARS2, "accession": REFERENCE},
        }
    )  # fmt: skip
    plan = plan_searches(assay, cfg)
    by_tier = {s.tier: s for s in plan.searches}
    labels = list(OLIGOS)

    @rep.step("05_blast_positive_control_sars2")
    def _t1() -> dict[str, Any]:
        ps = by_tier["target"]
        t0 = time.monotonic()
        job, raw = run_blast(
            runner, store, "target", "smoke target", ps.taxids, ps.entrez_query, ps.params, labels
        )
        info = analyse_search(raw, labels, cfg, ps.taxids, out, "t1_sars2")
        results = list(parse_blast_json(raw, labels).queries.values())
        info["lineage_check"] = lineage_check(http, base, results, ps.taxids)
        frac = info["lineage_check"].get("fraction_in_requested_subtree")
        rep.findings["sars2_search_fraction_of_hit_taxa_inside_subtree"] = frac
        rep.findings["sars2_search_restriction_effective"] = bool(frac is not None and frac >= 0.99)
        info.update(
            rid=job.rid,
            seconds_total=round(time.monotonic() - t0),
            hitlist_requested=cfg.search.hitlist_size,
        )
        # Reaching this line means the server accepted word size 7, E-value 1000, gap costs 5/2 and
        # HITLIST_SIZE 5000 together with ENTREZ_QUERY, and returned a parseable report.
        rep.findings["blast_parameters_accepted_and_report_parsed"] = True
        expected = {k: len(v) for k, v in OLIGOS.items()}
        rep.findings["positive_control_full_length_hits"] = {
            k: info["per_query"][k]["max_identity"] == expected[k] for k in labels
        }
        rep.findings["hitlist_returned_for_5000_requested"] = {
            k: info["per_query"][k]["n_hits"] for k in labels
        }
        return info

    @rep.step("06_blast_restriction_check_influenza_A_and_formats")
    def _t2() -> dict[str, Any]:
        flu = ctx.get("by_name", {}).get("Influenza A virus")
        if not flu:
            return {"skipped": "Influenza A virus did not resolve to one taxonomy ID (step 03)"}
        q = blast.build_entrez_query([flu])
        params = blast.build_put_params(cfg, by_tier["target"].fasta, q)
        t0 = time.monotonic()
        job, raw = run_blast(
            runner, store, "restriction", "smoke influenza", [flu], q, params, labels
        )
        info = analyse_search(raw, labels, cfg, [flu], out, "t2_influenza")
        results = list(parse_blast_json(raw, labels).queries.values())
        lin = lineage_check(http, base, results, [flu])
        info.update(rid=job.rid, seconds_total=round(time.monotonic() - t0), lineage_check=lin)
        frac = lin.get("fraction_in_requested_subtree")
        rep.findings["entrez_query_restriction_effective"] = bool(frac is not None and frac >= 0.99)
        rep.findings["entrez_query_restriction_fraction_inside"] = frac
        rep.findings["entrez_query_restriction_outside_examples"] = lin.get("outside_examples")
        rep.findings["restriction_check_taxa_checked"] = lin.get("n_checked")
        # Report-format probes on the finished search (cheap GETs, no new search).
        fmts: dict[str, Any] = {}
        for fmt in ("JSON2", "XML2_S", "XML2", "XML", "Text"):
            try:
                text = api.fetch(job.rid, fmt)  # type: ignore[arg-type]
                fmts[fmt] = {"ok": True, "bytes": len(text), "head": text[:300]}
            except NcbiError as exc:
                fmts[fmt] = {"ok": False, "error": str(exc)[:300]}
        info["report_format_probes"] = fmts
        return info

    if not args.quick:

        @rep.step("07_blast_multi_taxa_lists")
        def _multi() -> dict[str, Any]:
            # Human and mouse are left out: this step tests taxon-LIST handling, not genome size,
            # and a human-restricted search was still waiting after 45+ minutes in the first run.
            heavy = {HUMAN, ctx.get("by_name", {}).get("Mus musculus")}
            resolved = [t for t in (ctx.get("resolved") or [SARS2]) if t not in heavy]
            extra = esearch(
                http, base, "taxonomy", "Bacteria[Organism] AND species[Rank]", retmax=100
            )
            pool = [int(i) for i in extra.get("ids", [])]
            results: dict[str, Any] = {}
            for size, mode in ((len(resolved), "full"), (40, "accept-only"), (100, "accept-only")):
                taxa = (resolved + pool)[:size] if size > len(resolved) else resolved
                q = blast.build_entrez_query(sorted(set(taxa)))
                params = blast.build_put_params(cfg, ps_fasta(plan), q)
                entry: dict[str, Any] = {
                    "n_taxa": len(set(taxa)),
                    "entrez_query_chars": len(q or ""),
                    "mode": mode,
                }
                try:
                    if mode == "full":
                        job, raw = run_blast(
                            runner,
                            store,
                            "multi",
                            f"smoke {size} taxa",
                            sorted(set(taxa)),
                            q,
                            params,
                            labels,
                        )
                        info = analyse_search(
                            raw, labels, cfg, sorted(set(taxa)), out, f"t3_taxa_{size}"
                        )
                        counts = {k: v["n_hits"] for k, v in info["per_query"].items()}
                        top = info["restriction"]["top_organisms"]
                        hit_results = list(parse_blast_json(raw, labels).queries.values())
                        lin = lineage_check(http, base, hit_results, sorted(set(taxa)))
                        rep.findings["multi_taxa_lineage_check"] = lin
                        entry.update(accepted=True, top_organisms=top, n_hits=counts, lineage=lin)
                    else:
                        rid, rtoe = api.submit(params)
                        time.sleep(min(rtoe, 60))
                        status, _ = api.status(rid)
                        entry.update(
                            accepted=status != "FAILED", rid=rid, status_after_first_wait=status
                        )
                except NcbiError as exc:
                    entry.update(accepted=False, error=str(exc)[:400])
                results[f"taxa_{size}"] = entry
            rep.findings["multi_taxa_entrez_query_accepted"] = {
                k: v.get("accepted") for k, v in results.items()
            }
            return results

        @rep.step("08_blast_date_window_restriction")
        def _date() -> dict[str, Any]:
            amp = rep.steps.get("04_reference_check_against_NC_045512.2", {}).get(
                "amplicon_sequence"
            )
            if not amp:
                return {"skipped": "reference amplicon unavailable (step 04 failed)"}
            window = "2020/01/01:2020/01/31[PDAT]"
            q = f"txid{SARS2}[ORGN] AND {window}"
            params = blast.build_put_params(cfg, f">amplicon\n{amp}\n", q)
            params.update(
                WORD_SIZE="11",
                EXPECT="10",
                HITLIST_SIZE="100",
                GAPCOSTS="5 2",
                NUCL_REWARD="1",
                NUCL_PENALTY="-3",
            )
            job, raw = run_blast(
                runner, store, "date", "smoke date window", [SARS2], q, params, ["amplicon"]
            )
            info = analyse_search(raw, ["amplicon"], cfg, [SARS2], out, "t4_date_window")
            parsed = parse_blast_json(raw, ["amplicon"])
            accs = sorted(
                {
                    d.accession_version
                    for h in parsed.queries["amplicon"].hits
                    for d in h.descriptions
                    if d.accession_version
                }
            )[:20]
            check: dict[str, Any] = {"n_accessions_checked": len(accs)}
            if accs:
                term = "(" + " OR ".join(f"{a}[ACCN]" for a in accs) + f") AND {window}"
                r = esearch(http, base, "nuccore", term, retmax=0)
                check["esearch_count_of_those_accessions_in_window"] = r.get("count")
                rep.findings["blast_date_window_restriction_honoured"] = r.get("count") == len(accs)
            info["window_check"] = check
            return info

    if args.human:

        @rep.step("09_blast_human_background_core_nt")
        def _human() -> dict[str, Any]:
            ps = by_tier["background"]
            job, raw = run_blast(
                runner,
                store,
                "background",
                "smoke human",
                ps.taxids,
                ps.entrez_query,
                ps.params,
                labels,
            )
            info = analyse_search(raw, labels, cfg, ps.taxids, out, "t9_human")
            results = list(parse_blast_json(raw, labels).queries.values())
            info["lineage_check"] = lineage_check(http, base, results, ps.taxids)
            minutes = None
            if job.submitted_at:
                minutes = round(
                    (datetime.now(UTC) - datetime.fromisoformat(job.submitted_at)).total_seconds()
                    / 60
                )
            info.update(rid=job.rid, minutes_since_submission=minutes)
            rep.findings["human_core_nt_search_minutes_since_submission"] = minutes
            return info

    if args.probe_databases:

        @rep.step("10_blast_database_probes_human")
        def _dbs() -> dict[str, Any]:
            found: dict[str, Any] = {}
            for db in ("human_genomic", "refseq_genomic", "refseq_rna"):
                params = blast.build_put_params(cfg, by_tier["background"].fasta, "txid9606[ORGN]")
                params["DATABASE"] = db
                t0 = time.monotonic()
                try:
                    job, raw = run_blast(
                        runner,
                        store,
                        "dbprobe",
                        f"smoke {db}",
                        [HUMAN],
                        "txid9606[ORGN]",
                        params,
                        labels,
                    )
                    info = analyse_search(raw, labels, cfg, [HUMAN], out, f"t10_{db}")
                    found[db] = {
                        "ok": True,
                        "seconds": round(time.monotonic() - t0),
                        "rid": job.rid,
                        "database_reported": info.get("database"),
                        "n_hits": {k: v["n_hits"] for k, v in info["per_query"].items()},
                        "max_identity": {
                            k: v["max_identity"] for k, v in info["per_query"].items()
                        },
                    }
                except NcbiError as exc:
                    found[db] = {
                        "ok": False,
                        "seconds": round(time.monotonic() - t0),
                        "error": str(exc)[:400],
                    }
            rep.findings["database_probe_results"] = {k: v["ok"] for k, v in found.items()}
            return {"databases": found}

    write_report(True)
    failed = [n for n, st in rep.steps.items() if not st.get("ok")]
    sys.stdout.write(
        f"\nDone. Report: {out / 'smoke_report.json'}\n"
        f"Steps failed: {failed or 'none'}\nPaste the contents of smoke_report.json back.\n"
    )
    return 1 if failed else 0


def ps_fasta(plan: Any) -> str:
    return plan.searches[0].fasta


if __name__ == "__main__":
    raise SystemExit(main())
