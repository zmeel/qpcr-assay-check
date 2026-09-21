"""hits.tsv: every assessed off-target site with its full-length alignment metrics."""

from __future__ import annotations

import csv
from pathlib import Path

from ..results import RunResult

COLUMNS = [
    "tier", "query", "role", "accession", "taxid", "organism", "orientation", "start", "end",
    "level", "source", "mismatches", "gaps", "ambiguous", "unaligned", "mismatches_last5",
    "clean_3prime_nt", "defect_positions", "duplex_tm_c", "delta_tm_c", "duplex_dg_kcal",
    "oligo_alignment", "subject_alignment", "title",
]  # fmt: skip


def write_hits_tsv(result: RunResult, path: Path) -> None:
    """Write one row per stored site (all critical/warning sites plus the closest minor ones)."""
    spec = result.specificity
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(COLUMNS)
        for s in spec.sites if spec else []:
            w.writerow(
                [
                    s.tier, s.query, s.role, s.accession, s.taxid or "", s.organism or "",
                    s.orientation, s.subject_start, s.subject_end, s.level, s.source,
                    s.n_mismatch, s.n_gap, s.n_ambiguous, s.n_unaligned, s.mismatches_last5,
                    s.clean_3prime_nt, ",".join(map(str, s.defect_positions)),
                    "" if s.tm_c is None else round(s.tm_c, 1),
                    "" if s.delta_tm_c is None else round(s.delta_tm_c, 1),
                    "" if s.dg_kcal is None else round(s.dg_kcal, 2),
                    s.q_aln, s.s_aln, s.title,
                ]
            )  # fmt: skip
