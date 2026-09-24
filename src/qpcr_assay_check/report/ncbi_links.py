"""Links from accessions and taxonomy IDs in the report to their NCBI pages.

URL forms checked live on 2026-09-24, on the page content and not only the HTTP status:
``/nucleotide/<accession>`` for Nucleotide records (GenBank, RefSeq, WGS contigs),
``/datasets/genome/<GCA_/GCF_ accession>/`` for genome assemblies, and
``/Taxonomy/Browser/wwwtax.cgi?id=<taxid>`` for taxonomy. ``/nuccore/<accession>`` opens the same
record but answered every request with a reCAPTCHA "Checking your browser" page, which looped
endlessly in the user's browser; ``/nucleotide/`` served the record page directly (3 of 3
accessions). A link fetches nothing until it is clicked, so the report stays self-contained.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

NCBI = "https://www.ncbi.nlm.nih.gov"
# A versioned accession: an assembly (GCA_/GCF_ + 9 digits) or a Nucleotide record (a RefSeq
# prefix + 0-6 letters, or 1-6 letters, then 5-12 digits: NC_045512.2, NZ_CP012345.1,
# MN908947.3, JAAAAA010000001.1). The version is required, so words and numbers never match.
ASSEMBLY = r"GC[AF]_\d{9}\.\d+"
NUCLEOTIDE = r"(?:[A-Z]{2}_[A-Z]{0,6}|[A-Z]{1,6})\d{5,12}\.\d+"
ACCESSION_RE = re.compile(rf"(?<![\w.])({ASSEMBLY}|{NUCLEOTIDE})(?![\w.])")
_FULL = re.compile(rf"^(?:{ASSEMBLY}|{NUCLEOTIDE})$")


def accession_url(accession: str) -> str | None:
    """The NCBI page of a versioned accession, or None if it does not look like one."""
    acc = accession.strip()
    if not _FULL.match(acc):
        return None
    if acc.startswith(("GCA_", "GCF_")):
        return f"{NCBI}/datasets/genome/{acc}/"
    return f"{NCBI}/nucleotide/{acc}"


def taxon_url(taxid: int | str) -> str | None:
    s = str(taxid).strip()
    return f"{NCBI}/Taxonomy/Browser/wwwtax.cgi?id={s}" if s.isdigit() else None


def _a(url: str, text: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}</a>'


def linkify(value: object) -> Markup:
    """Escape ``value`` (unless it is already markup) and link every accession in it."""
    if value is None:
        return Markup("")
    text = str(value) if isinstance(value, Markup) else str(escape(str(value)))

    def repl(m: re.Match[str]) -> str:
        url = accession_url(m.group(1))
        return _a(url, m.group(1)) if url else m.group(1)

    return Markup(ACCESSION_RE.sub(repl, text))  # noqa: S704 - escaped above; only links added


def taxon_link(taxid: object) -> Markup:
    if taxid is None or taxid == "":
        return Markup("")
    url = taxon_url(str(taxid))
    text = str(escape(str(taxid)))
    return Markup(_a(url, text) if url else text)  # noqa: S704 - escaped text, fixed URL form
