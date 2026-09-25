"""NCBI Datasets v2: list a taxon's genome assemblies and download their genome FASTA.

Endpoints and parameters follow NCBI's published OpenAPI specification (datasets.openapi.yaml,
API v2); their live behaviour was checked with ``scripts/probe_variant_sources.py`` (see
docs/ARCHITECTURE.md, "Verified for the v1.1.0 design"):

* ``GET /genome/taxon/{taxon}/dataset_report`` pages with ``page_size`` (max 1000) and
  ``page_token``; ``total_count`` is the size of the whole result.
* ``filters.exclude_paired_reports=true`` returns one copy of each GenBank (GCA_) / RefSeq (GCF_)
  pair (the RefSeq one when it exists), so an assembly is never counted twice.
* ``filters.first_release_date`` / ``filters.last_release_date`` restrict by release date; the
  listing walks year windows from the newest back, so a per-run budget processes the newest
  assemblies first (the spec does not list the values ``sort.field`` accepts, so it is not used).
* ``GET /genome/accession/{accessions}/download?include_annotation_type=GENOME_FASTA`` (at most
  100 accessions) returns a zip with ``ncbi_dataset/data/<accession>/<...>_genomic.fna``.
"""

from __future__ import annotations

import io
import logging
import zipfile
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote

from ..ncbi.http import NcbiError, NcbiHttp

log = logging.getLogger(__name__)

PAGE_SIZE = 1000  # the documented maximum


@dataclass(frozen=True)
class AssemblyRecord:
    """The fields of one assembly data report this tool uses."""

    accession: str
    release_date: str  # YYYY-MM-DD
    assembly_level: str
    total_length: int
    organism: str
    taxid: int | None

    @property
    def year(self) -> int:
        return int(self.release_date[:4])


def _record(report: dict) -> AssemblyRecord | None:
    acc = report.get("accession")
    info = report.get("assembly_info") or {}
    date = info.get("release_date") or ""
    if not acc or len(date) < 4 or not date[:4].isdigit():
        return None
    org = report.get("organism") or {}
    stats = report.get("assembly_stats") or {}
    try:
        length = int(stats.get("total_sequence_length") or 0)
    except (TypeError, ValueError):
        length = 0
    taxid = org.get("tax_id")
    return AssemblyRecord(
        accession=acc,
        release_date=date[:10],
        assembly_level=info.get("assembly_level") or "",
        total_length=length,
        organism=org.get("organism_name") or "",
        taxid=int(taxid) if isinstance(taxid, int | str) and str(taxid).isdigit() else None,
    )


class DatasetsClient:
    """Throttled access to the two Datasets endpoints the variant analysis needs."""

    def __init__(self, http: NcbiHttp, base_url: str) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def _filters(self, *, current_only: bool, exclude_atypical: bool) -> dict[str, str]:
        return {
            "filters.assembly_version": "current" if current_only else "all_assemblies",
            "filters.exclude_atypical": "true" if exclude_atypical else "false",
            "filters.exclude_paired_reports": "true",
        }

    def count(self, taxon: int | str, *, current_only: bool, exclude_atypical: bool,
              first: str | None = None, last: str | None = None) -> int:  # fmt: skip
        """``total_count`` of a (date-restricted) listing, from a one-report page."""
        params = self._filters(current_only=current_only, exclude_atypical=exclude_atypical)
        params["page_size"] = "1"
        if first:
            params["filters.first_release_date"] = first
        if last:
            params["filters.last_release_date"] = last
        doc = self._get_json(f"/genome/taxon/{quote(str(taxon))}/dataset_report", params)
        return int(doc.get("total_count") or 0)

    def year(self, taxon: int | str, year: int, *, current_only: bool,
             exclude_atypical: bool) -> Iterator[AssemblyRecord]:  # fmt: skip
        """Every assembly of ``taxon`` released in ``year``, page by page."""
        params = self._filters(current_only=current_only, exclude_atypical=exclude_atypical)
        params.update({
            "page_size": str(PAGE_SIZE),
            "filters.first_release_date": f"{year}-01-01",
            "filters.last_release_date": f"{year}-12-31",
        })  # fmt: skip
        path = f"/genome/taxon/{quote(str(taxon))}/dataset_report"
        while True:
            doc = self._get_json(path, params)
            for report in doc.get("reports") or []:
                rec = _record(report)
                if rec is not None:
                    yield rec
            token = doc.get("next_page_token")
            if not token:
                return
            params["page_token"] = token

    def download(self, accessions: list[str]) -> dict[str, str]:
        """Genome FASTA text per assembly accession (missing ones are simply absent)."""
        if not 1 <= len(accessions) <= 100:
            raise ValueError("1-100 accessions per download request")
        resp = self.http.request(
            "GET",
            f"{self.base_url}/genome/accession/{','.join(accessions)}/download",
            service="datasets",
            params={"include_annotation_type": "GENOME_FASTA"},
        )
        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile as exc:
            snippet = resp.text[:200]
            raise NcbiError(f"Datasets download was not a zip archive: {snippet!r}") from exc
        out: dict[str, str] = {}
        try:
            for name in zf.namelist():
                parts = name.split("/")
                if (
                    len(parts) == 4
                    and parts[:2] == ["ncbi_dataset", "data"]
                    and name.endswith(".fna")
                ):
                    out[parts[2]] = zf.read(name).decode("ascii", "replace")
        except (zipfile.BadZipFile, zlib.error, EOFError) as exc:  # a damaged member
            raise NcbiError(f"Datasets download was damaged: {exc}") from exc
        return out

    def _get_json(self, path: str, params: dict[str, str]) -> dict:
        resp = self.http.request("GET", f"{self.base_url}{path}", service="datasets",
                                 params=params)  # fmt: skip
        try:
            doc = resp.json()
        except ValueError as exc:
            raise NcbiError(f"Unexpected Datasets response: {resp.text[:200]!r}") from exc
        if not isinstance(doc, dict):
            raise NcbiError(f"Unexpected Datasets response: {resp.text[:200]!r}")
        return doc


def parse_fasta(text: str) -> dict[str, str]:
    """``{record id: upper-case sequence}`` of a multi-FASTA text."""
    return {name: seq for name, (_desc, seq) in parse_fasta_records(text).items()}


def parse_fasta_records(text: str) -> dict[str, tuple[str, str]]:
    """``{record id: (header description, upper-case sequence)}`` of a multi-FASTA text."""
    out: dict[str, tuple[str, str]] = {}
    name: str | None = None
    desc, chunks = "", []
    for line in text.splitlines():
        if line.startswith(">"):
            if name is not None:
                out[name] = (desc, "".join(chunks).upper())
            parts = line[1:].split(maxsplit=1)
            name, desc, chunks = (
                (parts[0] if parts else ""),
                (parts[1] if len(parts) > 1 else ""),
                [],
            )
        elif name is not None:
            chunks.append(line.strip())
    if name is not None:
        out[name] = (desc, "".join(chunks).upper())
    return out


def is_plasmid(description: str) -> bool:
    """Does a FASTA header description name a plasmid? (INSDC definition lines say "plasmid")."""
    return "plasmid" in description.lower()
