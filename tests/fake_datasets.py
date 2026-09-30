"""A fake NCBI Datasets v2 server: assembly data reports (paged, date-filtered) and zip downloads.

Mirrors the response shapes measured live (docs/ARCHITECTURE.md, "Verified for the v1.1.0
design"): ``total_count``/``reports``/``next_page_token`` pages and a zip with
``ncbi_dataset/data/<accession>/<accession>_<name>_genomic.fna``.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field


@dataclass
class FakeAssembly:
    accession: str
    release_date: str
    contigs: dict[str, str]
    level: str = "Contig"
    organism: str = "Chlamydia trachomatis"
    taxid: int = 813
    descriptions: dict[str, str] = field(default_factory=dict)  # contig -> FASTA description
    molecules: dict[str, str] = field(
        default_factory=dict
    )  # contig -> Plasmid (default Chromosome)
    collection_date: str | None = None  # BioSample collection_date; None: no biosample


class FakeResponse:
    def __init__(self, status: int, body: bytes, content_type: str) -> None:
        self.status_code = status
        self.content = body
        self.headers = {"Content-Type": content_type}

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "replace")

    def json(self):  # noqa: ANN201 - mirrors requests.Response.json
        return json.loads(self.content)


@dataclass
class FakeDatasets:
    assemblies: list[FakeAssembly]
    page_size_cap: int = 1000
    missing_from_download: set[str] = field(default_factory=set)
    breaks_download: set[str] = field(default_factory=set)  # any batch with one fails whole
    calls: list[dict] = field(default_factory=list)
    headers: dict = field(default_factory=dict)

    def request(self, method, url, params=None, data=None, timeout=None, headers=None):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": headers or {}})
        path = url.split("/datasets/v2", 1)[1]
        if path.endswith("/dataset_report"):
            return self._report(params or {})
        if path.endswith("/sequence_reports"):
            acc = path.split("/genome/accession/", 1)[1].rsplit("/sequence_reports", 1)[0]
            return self._sequences(acc, params or {})
        if path.endswith("/download"):
            accs = path.split("/genome/accession/", 1)[1].rsplit("/download", 1)[0].split(",")
            return self._download(accs)
        return FakeResponse(404, b"not found", "text/plain")

    def _report(self, params: dict) -> FakeResponse:
        items = sorted(self.assemblies, key=lambda a: a.accession)
        first, last = (
            params.get("filters.first_release_date"),
            params.get("filters.last_release_date"),
        )
        if first:
            items = [a for a in items if a.release_date >= first]
        if last:
            items = [a for a in items if a.release_date <= last]
        size = min(int(params.get("page_size", 20)), self.page_size_cap)
        start = int(params.get("page_token", 0))
        page = items[start : start + size]
        doc = {
            "total_count": len(items),
            "reports": [
                {
                    "accession": a.accession,
                    "organism": {"tax_id": a.taxid, "organism_name": a.organism},
                    "assembly_info": {
                        "release_date": a.release_date,
                        "assembly_level": a.level,
                        **(
                            {"biosample": {"collection_date": a.collection_date}}
                            if a.collection_date is not None
                            else {}
                        ),
                    },
                    "assembly_stats": {
                        "total_sequence_length": str(sum(map(len, a.contigs.values())))
                    },
                }
                for a in page
            ],
        }
        if start + size < len(items):
            doc["next_page_token"] = str(start + size)
        return FakeResponse(200, json.dumps(doc).encode(), "application/json")

    def _sequences(self, acc: str, params: dict) -> FakeResponse:
        """Sequence reports as measured live: one assembly per request (a list gives nothing),
        paged by page_size / page_token."""
        a = next((x for x in self.assemblies if x.accession == acc), None)
        if a is None:
            return FakeResponse(200, b"{}", "application/json")
        names = list(a.contigs)
        size = int(params.get("page_size", 1000))
        start = int(params.get("page_token", 0))
        complete = a.level in ("Complete Genome", "Chromosome")
        doc: dict = {
            "total_count": len(names),
            "reports": [
                {"refseq_accession": n, "genbank_accession": "GB_" + n,
                 "role": "assembled-molecule" if complete else "unplaced-scaffold",
                 "assigned_molecule_location_type": a.molecules.get(n) or (
                     "Plasmid" if "plasmid" in a.descriptions.get(n, "").lower()
                     else "Chromosome"),
                 "chr_name": n}
                for n in names[start : start + size]
            ],
        }  # fmt: skip
        if start + size < len(names):
            doc["next_page_token"] = str(start + size)
        return FakeResponse(200, json.dumps(doc).encode(), "application/json")

    def _download(self, accessions: list[str]) -> FakeResponse:
        if self.breaks_download & set(accessions):
            return FakeResponse(200, b"<html>gateway timeout</html>", "text/html")
        by_acc = {a.accession: a for a in self.assemblies}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("README.md", "fake")
            for acc in accessions:
                a = by_acc.get(acc)
                if a is None or acc in self.missing_from_download:
                    continue
                fasta = "".join(
                    f">{name} {a.descriptions.get(name, 'fake contig')}\n{seq}\n"
                    for name, seq in a.contigs.items()
                )
                zf.writestr(f"ncbi_dataset/data/{acc}/{acc}_fake_genomic.fna", fasta)
        return FakeResponse(200, buf.getvalue(), "application/zip")

    @property
    def downloads(self) -> list[str]:
        return [c["url"] for c in self.calls if c["url"].endswith("/download")]
