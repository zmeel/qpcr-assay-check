#!/usr/bin/env python3
"""Live checks for the v1.1.0 exhaustive variant analysis design.  (v1.1.0 verification step)

WHY THIS EXISTS
    v1.1.0 replaces the saturated target-tier BLAST search as the source of the variant summary
    and inclusivity with two exhaustive sources (see docs/PROGRESS.md, 2026-09-23):

      Option 2  NCBI Datasets: list every genome assembly of the target taxon, download them one
                by one, scan each locally for the amplicon and keep only that region.
      Option 1  Partitioned remote BLAST: list the target's records with ESearch and BLAST the
                reference amplicon restricted to small accession lists, so no search fills the
                hit list.

    Both rely on NCBI behaviour the developer could not check (ncbi.nlm.nih.gov and
    api.ncbi.nlm.nih.gov are unreachable from the development sandbox). The Datasets endpoints
    below come from NCBI's published OpenAPI specification (github.com/ncbi/datasets,
    datasets.openapi.yaml, API v2); their real behaviour, sizes, speed and rate limits do not.
    This script measures them and writes probe_out/probe_report.json, which contains no secrets.

WHAT IT SENDS TO NCBI
    * NCBI Datasets: genome assembly reports for a few bacterial species (by scientific name) and
      one or two small genome downloads (the first assembly of --species, default Chlamydia
      trachomatis, about 1 Mb). NCBI_API_KEY is sent as the documented `api-key` header when set;
      your e-mail is NOT sent to Datasets.
    * E-utilities: ESearch/EFetch queries as the main smoke test makes (e-mail and tool name as
      NCBI requires).
    * BLAST: the published CDC 2019-nCoV N1 amplicon (fetched from NC_045512.2, not typed in),
      restricted to 100 SARS-CoV-2 accessions; and a 300 bp stretch fetched from a RefSeq
      record of --species, searched against the WGS database restricted to that species.

HOW TO RUN (from the repository root, after `pip install -e .`)
    export NCBI_EMAIL="your.name@example.org"
    export NCBI_API_KEY="..."            # optional, recommended
    mkdir -p probe_out
    nohup python scripts/probe_variant_sources.py > probe_out/run.log 2>&1 &
    tail -f probe_out/run.log

    Options:
      --species NAME        bacterial species for the Datasets and WGS checks
                            (default "Chlamydia trachomatis")
      --count-species NAME  extra species to count assemblies for (repeatable)
      --skip-blast          only the Datasets and E-utilities checks (a few minutes)
      --max-wait-minutes N  give up on one BLAST search after N minutes (default 60)

    probe_out/probe_report.json is rewritten after every step. Run the same command again after
    an interruption: finished BLAST searches come from the cache.

WHAT TO PASTE BACK
    The contents of probe_out/probe_report.json. Nothing else is needed.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import random
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from qpcr_assay_check import __version__
from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import QpcrAssayCheckError
from qpcr_assay_check.ncbi import blast
from qpcr_assay_check.ncbi.blast import BlastApi
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.jobs import JobStore
from qpcr_assay_check.ncbi.parser import parse_blast_json
from qpcr_assay_check.ncbi.runner import BlastRunner
from qpcr_assay_check.ncbi.settings import credentials_from_env

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_test import Report, esearch, run_blast, trim  # noqa: E402

log = logging.getLogger("probe")

DATASETS = "https://api.ncbi.nlm.nih.gov/datasets/v2"  # servers[0].url in datasets.openapi.yaml
DATASETS_INTERVAL_S = 0.5  # deliberately conservative: the published spec states no rate limit
REFERENCE, AMPLICON = "NC_045512.2", (28287, 28358)  # CDC N1, verified in the first smoke run
SARS2 = 2697049
COUNT_SPECIES = [
    "Chlamydia trachomatis",
    "Neisseria gonorrhoeae",
    "Streptococcus pneumoniae",
    "Mycobacterium tuberculosis",
    "Escherichia coli",
]


class Datasets:
    """Minimal, throttled NCBI Datasets v2 client for this probe (records every response)."""

    def __init__(self, api_key: str | None) -> None:
        self.s = requests.Session()
        self.s.headers["User-Agent"] = f"qpcr-assay-check/{__version__} (probe_variant_sources)"
        if api_key:
            self.s.headers["api-key"] = api_key  # securitySchemes.ApiKeyAuthHeader
        self._last = 0.0
        self.n_requests = 0
        self.n_429 = 0
        self.rate_headers: dict[str, str] = {}

    def get(self, path: str, **kw: Any) -> requests.Response:
        for attempt in range(5):
            wait = self._last + DATASETS_INTERVAL_S - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.n_requests += 1
            resp = self.s.get(f"{DATASETS}{path}", timeout=300, **kw)
            self.rate_headers.update(
                {k: v for k, v in resp.headers.items() if "rate" in k.lower() or k == "Retry-After"}
            )
            if resp.status_code != 429:
                return resp
            self.n_429 += 1
            time.sleep(2 ** (attempt + 1))
        return resp


def _report_page(ds: Datasets, taxon: str, **params: Any) -> dict[str, Any]:
    t0 = time.monotonic()
    resp = ds.get(f"/genome/taxon/{requests.utils.quote(taxon)}/dataset_report", params=params)
    out: dict[str, Any] = {
        "http": resp.status_code,
        "seconds": round(time.monotonic() - t0, 2),
        "bytes": len(resp.content),
    }
    try:
        doc = resp.json()
    except ValueError:
        out["head"] = resp.text[:300]
        return out
    out["total_count"] = doc.get("total_count")
    out["n_reports"] = len(doc.get("reports", []))
    out["has_next_page_token"] = bool(doc.get("next_page_token"))
    out["messages"] = trim(doc.get("messages"))
    out["_doc"] = doc
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=Path("probe_out"))
    ap.add_argument("--species", default="Chlamydia trachomatis")
    ap.add_argument("--count-species", action="append", default=[])
    ap.add_argument("--skip-blast", action="store_true")
    ap.add_argument("--max-wait-minutes", type=float, default=60.0)
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
    eu = Eutils(http, cfg.ncbi.eutils_url)
    base = cfg.ncbi.eutils_url
    store = JobStore(out / "jobs.json")
    runner = BlastRunner(
        BlastApi(http, cfg.ncbi.blast_url), Cache(cfg.ncbi.cache_dir), store, cfg.ncbi,
        cfg.search.result_format,
    )  # fmt: skip
    ds = Datasets(creds.api_key)
    started = datetime.now(UTC).isoformat()
    ctx: dict[str, Any] = {}

    def write_report(complete: bool) -> None:
        report = {
            "probe_version": "1.1.0-verify",
            "started": started,
            "updated": datetime.now(UTC).isoformat(),
            "complete": complete,
            "options": {"species": args.species, "skip_blast": args.skip_blast},
            "datasets_client": {
                "requests": ds.n_requests,
                "http_429": ds.n_429,
                "interval_s": DATASETS_INTERVAL_S,
                "rate_headers_seen": ds.rate_headers,
            },
            "findings": rep.findings,
            "steps": rep.steps,
        }
        text = creds.redact(json.dumps(report, indent=2, default=str))
        (out / "probe_report.json").write_text(text, encoding="utf-8")

    rep = Report(lambda: write_report(False))

    @rep.step("00_environment")
    def _env() -> dict[str, Any]:
        return {"python": sys.version.split()[0], "tool_version": __version__,
                "api_key_set": bool(creds.api_key)}  # fmt: skip

    # ------------------------------------------------------------ Option 2: NCBI Datasets
    @rep.step("D1_assembly_counts_per_species")
    def _counts() -> dict[str, Any]:
        res = {}
        for name in dict.fromkeys(COUNT_SPECIES + args.count_species + [args.species]):
            page = _report_page(
                ds, name, page_size=1, **{"filters.assembly_version": "all_assemblies"}
            )
            page.pop("_doc", None)
            current = _report_page(
                ds, name, page_size=1, **{"filters.assembly_version": "current",
                                           "filters.exclude_atypical": "true"}
            )  # fmt: skip
            current.pop("_doc", None)
            res[name] = {"all": page, "current_not_atypical": current}
        rep.findings["datasets_total_count_by_species"] = {
            k: (v["all"].get("total_count"), v["current_not_atypical"].get("total_count"))
            for k, v in res.items()
        }
        return res

    @rep.step("D2_report_paging_and_fields")
    def _paging() -> dict[str, Any]:
        first = _report_page(ds, args.species, page_size=1000, returned_content="COMPLETE")
        doc = first.pop("_doc", {})
        reports = doc.get("reports", [])
        info: dict[str, Any] = {"first_page": first}
        if reports:
            r0 = reports[0]
            info["report_top_level_keys"] = sorted(r0)
            info["assembly_info_keys"] = sorted(r0.get("assembly_info", {}))
            info["assembly_stats_keys"] = sorted(r0.get("assembly_stats", {}))
            info["example"] = trim({k: r0.get(k) for k in ("accession", "organism")})
            info["assembly_levels"] = sorted(
                {r.get("assembly_info", {}).get("assembly_level") for r in reports} - {None}
            )
            sizes = [
                int(r.get("assembly_stats", {}).get("total_sequence_length", 0) or 0)
                for r in reports
            ]
            info["total_sequence_length_first_page"] = {
                "min": min(sizes), "max": max(sizes), "sum": sum(sizes), "n": len(sizes)
            }  # fmt: skip
            ctx["accessions"] = [r["accession"] for r in reports if r.get("accession")]
            smallest = min(
                reports,
                key=lambda r: int(
                    r.get("assembly_stats", {}).get("total_sequence_length", 0) or 1 << 60
                ),
            )
            ctx["small_accession"] = smallest.get("accession")
        if doc.get("next_page_token"):
            nxt = _report_page(ds, args.species, page_size=1000, page_token=doc["next_page_token"])
            nxt.pop("_doc", None)
            info["second_page"] = nxt
        rep.findings["datasets_report_paging_works"] = bool(reports) and (
            not doc.get("next_page_token") or info.get("second_page", {}).get("n_reports", 0) > 0
        )
        return info

    @rep.step("D3_hydrated_genome_fasta_download")
    def _download() -> dict[str, Any]:
        acc = ctx.get("small_accession")
        if not acc:
            return {"skipped": "no accession from D2"}
        t0 = time.monotonic()
        resp = ds.get(
            f"/genome/accession/{acc}/download",
            params={"include_annotation_type": "GENOME_FASTA"},
        )
        info: dict[str, Any] = {
            "accession": acc, "http": resp.status_code, "bytes": len(resp.content),
            "seconds": round(time.monotonic() - t0, 2),
            "content_type": resp.headers.get("Content-Type"),
        }  # fmt: skip
        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile:
            info["head"] = resp.text[:300]
            return info
        info["zip_members"] = [(m.filename, m.file_size) for m in zf.infolist()]
        fasta = [m for m in zf.namelist() if m.endswith((".fna", ".fa", ".fasta"))]
        if fasta:
            text = zf.read(fasta[0]).decode("ascii", "replace")
            headers = [line for line in text.splitlines() if line.startswith(">")]
            info["fasta_member"] = fasta[0]
            info["n_fasta_records"] = len(headers)
            info["fasta_header_examples"] = headers[:3]
            info["n_bases"] = sum(
                len(line) for line in text.splitlines() if not line.startswith(">")
            )
        rep.findings["datasets_download_zip_contains_genome_fasta"] = bool(fasta)
        return info

    @rep.step("D4_dehydrated_package_and_fetch_txt")
    def _dehydrated() -> dict[str, Any]:
        accs = (ctx.get("accessions") or [])[:2]
        if not accs:
            return {"skipped": "no accessions from D2"}
        resp = ds.get(
            f"/genome/accession/{','.join(accs)}/download",
            params={"include_annotation_type": "GENOME_FASTA", "hydrated": "DATA_REPORT_ONLY"},
        )
        info: dict[str, Any] = {"accessions": accs, "http": resp.status_code,
                                "bytes": len(resp.content)}  # fmt: skip
        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile:
            info["head"] = resp.text[:300]
            return info
        info["zip_members"] = zf.namelist()
        fetch = next((m for m in zf.namelist() if m.endswith("fetch.txt")), None)
        if fetch:
            lines = zf.read(fetch).decode().splitlines()
            info["fetch_txt_lines"] = lines[:4]
            url = lines[0].split("\t")[0] if lines else ""
            if url.startswith("http"):
                t0 = time.monotonic()
                f = requests.get(url, timeout=300)
                info["direct_file"] = {
                    "http": f.status_code, "bytes": len(f.content),
                    "seconds": round(time.monotonic() - t0, 2),
                    "content_type": f.headers.get("Content-Type"),
                    "gzip_magic": f.content[:2] == b"\x1f\x8b",
                }  # fmt: skip
                rep.findings["dehydrated_fetch_url_downloadable"] = f.status_code == 200
        return info

    # ------------------------------------------------------------ Option 1: E-utilities + BLAST
    @rep.step("E1_esearch_deep_random_retstart")
    def _deep() -> dict[str, Any]:
        term = f"txid{SARS2}[ORGN] AND 2022/01/01:2022/12/31[PDAT]"
        total = esearch(http, base, "nuccore", term, retmax=0).get("count", 0)
        rng = random.Random(20260923)
        probes = {}
        for start in sorted(rng.sample(range(max(total, 1)), 3)) + [max(total - 1, 0)]:
            r = esearch(http, base, "nuccore", term, retstart=start, retmax=1)
            probes[str(start)] = {"n_ids": len(r.get("ids", [])), "error": r.get("error")}
        block = esearch(http, base, "nuccore", term, retstart=rng.randrange(total), retmax=100)
        ctx["sars2_uids"] = block.get("ids", [])
        rep.findings["esearch_deep_retstart_works"] = all(p["n_ids"] == 1 for p in probes.values())
        return {"count_2022": total, "probes": probes, "block_of_100": len(ctx["sars2_uids"])}

    @rep.step("E2_efetch_uids_to_accessions")
    def _accs() -> dict[str, Any]:
        uids = ctx.get("sars2_uids") or []
        if not uids:
            return {"skipped": "no UIDs from E1"}
        resp = http.request(
            "POST", f"{base}/efetch.fcgi", service="eutils",
            data={"db": "nuccore", "id": ",".join(uids), "rettype": "acc", "retmode": "text"},
        )  # fmt: skip
        accs = [line.strip() for line in resp.text.splitlines() if line.strip()]
        ctx["sars2_accs"] = accs
        rep.findings["efetch_rettype_acc_returns_one_per_uid"] = len(accs) == len(uids)
        return {"n_uids": len(uids), "n_accessions": len(accs), "examples": accs[:3]}

    if not args.skip_blast:

        @rep.step("E3_blast_amplicon_restricted_to_100_accessions")
        def _accn_blast() -> dict[str, Any]:
            accs = ctx.get("sars2_accs") or []
            if not accs:
                return {"skipped": "no accessions from E2"}
            fasta = eu.fetch_fasta(REFERENCE, start=AMPLICON[0], stop=AMPLICON[1])
            amp = "".join(fasta.splitlines()[1:])
            entrez = "(" + " OR ".join(f"{a}[ACCN]" for a in accs) + ")"
            params = blast.build_put_params(cfg, f">amplicon\n{amp}\n", entrez)
            params.update(WORD_SIZE="11", EXPECT="10", HITLIST_SIZE="500")
            job, raw = run_blast(runner, store, "probe", "accession list", [SARS2], entrez,
                                 params, ["amplicon"])  # fmt: skip
            parsed = parse_blast_json(raw, ["amplicon"])
            hit_accs = {
                d.accession_version for h in parsed.queries["amplicon"].hits
                for d in h.descriptions if d.accession_version
            }  # fmt: skip
            want = set(accs)
            found, leaked = want & hit_accs, hit_accs - want
            rep.findings["blast_accession_list_restriction"] = {
                "accepted": True, "requested": len(want), "found": len(found),
                "leaked_outside_list": len(leaked),
            }  # fmt: skip
            return {"rid": job.rid, "entrez_query_chars": len(entrez), "amplicon_len": len(amp),
                    "n_hit_accessions": len(hit_accs), "found": len(found),
                    "missing_examples": sorted(want - hit_accs)[:5],
                    "leaked_examples": sorted(leaked)[:5]}  # fmt: skip

        @rep.step("E4_blast_wgs_database_species_restricted")
        def _wgs() -> dict[str, Any]:
            ref = esearch(http, base, "nuccore",
                          f"{args.species}[ORGN] AND refseq[filter]", retmax=1)  # fmt: skip
            if not ref.get("ids"):
                return {"skipped": f"no RefSeq record found for {args.species}", "esearch": ref}
            fasta = eu.fetch_fasta(ref["ids"][0], start=10001, stop=10300)
            seq = "".join(fasta.splitlines()[1:])
            entrez = f"{args.species}[ORGN]"
            params = blast.build_put_params(cfg, f">probe_region\n{seq}\n", entrez)
            params.update(DATABASE="wgs", WORD_SIZE="11", EXPECT="10", HITLIST_SIZE="100")
            job, raw = run_blast(runner, store, "probe", "wgs", [], entrez, params,
                                 ["probe_region"])  # fmt: skip
            parsed = parse_blast_json(raw, ["probe_region"])
            q = parsed.queries["probe_region"]
            names = sorted({d.sciname for h in q.hits for d in h.descriptions if d.sciname})
            rep.findings["blast_wgs_database_with_entrez_query"] = {
                "database_reported": parsed.database, "n_hits": len(q.hits),
                "organisms": names[:5],
            }  # fmt: skip
            return {"rid": job.rid, "source_record": fasta.splitlines()[0][:120],
                    "database": parsed.database, "n_hits": len(q.hits),
                    "example_hits": [h.descriptions[0].accession_version
                                     for h in q.hits[:5] if h.descriptions]}  # fmt: skip

    write_report(True)
    log.info("Done: %s", out / "probe_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
