"""Estimate the stability of an oligo bound to a mismatched site.

The estimate uses primer3's nearest-neighbour model for the oligo against the reverse complement of
the subject bases it is aligned to. It is an *estimate of duplex stability only*: a mismatch at the
3'-terminal base is treated as an unpaired overhang, so it hardly changes the melting temperature
even though it usually prevents extension. Priming is therefore judged from the mismatch and
3'-end columns, never from Tm.
"""

from __future__ import annotations

import logging

from ..align import realign
from ..oligo import iupac, thermo

log = logging.getLogger(__name__)


def estimate_duplex(
    oligo: str, s_aln: str, cond: thermo.Conditions, nM: float
) -> tuple[float | None, float | None, float | None]:
    """Return ``(tm_c, dg_kcal, delta_tm_c)``; ``tm_c`` is None if no duplex is predicted."""
    subject = realign.sanitise_subject(s_aln.replace("-", "").replace(".", ""))
    if len(subject) < 8:
        return None, None, None
    try:
        perfect = thermo.heterodimer(oligo, iupac.reverse_complement(oligo), cond, nM=nM)
        actual = thermo.heterodimer(oligo, iupac.reverse_complement(subject), cond, nM=nM)
    except Exception as exc:  # noqa: BLE001 - primer3 raises plain exceptions on odd input
        log.debug("duplex estimate failed for %s: %s", oligo, exc)
        return None, None, None
    if not actual.found or actual.tm_c is None:
        return None, None, None
    delta = actual.tm_c - perfect.tm_c if perfect.found and perfect.tm_c is not None else None
    return actual.tm_c, actual.dg_kcal, delta
