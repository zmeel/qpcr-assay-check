"""Collection dates: when the sample was taken, as its submitter recorded it.

The variant analysis groups genomes by NCBI release (or publication) year. A batch of old
samples uploaded late then looks new, so the collection date is shown as a second axis.

Where it comes from (both checked live on 2026-09-30):

* genome assemblies: ``assembly_info.biosample.collection_date`` in the NCBI Datasets v2
  dataset report (values such as ``2019-05-12``, ``2019``, ``missing``, ``not applicable``);
* Nucleotide records: the ESummary ``subtype`` / ``subname`` pair, two ``|``-separated lists
  of source qualifiers and their values (e.g. ``isolate|host|country|collection_date`` and
  ``EVE/CEP-209/JPN/2022/E5|Bos taurus|Japan|2022-02-08``).

INSDC dates come as ``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD``, ``Mmm-YYYY``, ``DD-Mmm-YYYY`` or a
range of two such dates joined by ``/``. The year is the first four-digit year in the value
(for a range, its start); anything without one (``missing``, ``not collected``, ``unknown``)
has no collection year.
"""

from __future__ import annotations

import re
from typing import Any

_YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)")


def collection_year(value: str | None, latest: int | None = None) -> int | None:
    """The year a sample was collected, or None when the value names none. A year after
    ``latest`` (e.g. the current one) is not a collection year."""
    if not value:
        return None
    m = _YEAR.search(value)
    if m is None:
        return None
    year = int(m.group(1))
    return None if latest is not None and year > latest else year


def from_biosample(report: dict[str, Any]) -> str:
    """The collection date of a Datasets assembly report ('' when none is given)."""
    bio = (report.get("assembly_info") or {}).get("biosample") or {}
    value = bio.get("collection_date")
    if not value:
        for attr in bio.get("attributes") or []:
            if attr.get("name") == "collection_date":
                value = attr.get("value")
                break
    return str(value or "").strip()[:40]


def from_docsum(docsum: dict[str, Any]) -> str:
    """The collection date of a Nucleotide ESummary document ('' when none is given)."""
    names = str(docsum.get("subtype") or "").split("|")
    values = str(docsum.get("subname") or "").split("|")
    if len(names) != len(values):
        return ""  # a value containing '|' would shift the pairs: do not guess
    for name, value in zip(names, values, strict=True):
        if name == "collection_date":
            return value.strip()[:40]
    return ""
