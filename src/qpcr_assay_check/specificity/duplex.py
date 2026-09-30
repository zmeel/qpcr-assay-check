"""Estimate the stability of an oligo bound to a mismatched site.

The estimate uses primer3's nearest-neighbour model for the oligo against the reverse complement of
the subject bases it is aligned to. It is an *estimate of duplex stability only*: a mismatch at the
3'-terminal base is treated as an unpaired overhang, so it hardly changes the melting temperature
even though it usually prevents extension. Priming is therefore judged from the mismatch and
3'-end columns, never from Tm.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

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


def site_duplex(
    reaction: Any,
) -> Callable[[Any], tuple[float | None, float | None, float | None]]:
    """A duplex estimate per site under the reaction conditions (``cfg.reaction``), cached by
    oligo and aligned template: thousands of genomes share few distinct site variants."""
    cond = thermo.Conditions.from_reaction(reaction)
    memo: dict[tuple[str, str, bool], tuple[float | None, float | None, float | None]] = {}

    def estimate(site: Any) -> tuple[float | None, float | None, float | None]:
        if site.source == "blast_partial_worst_case":
            return None, None, None  # unobserved bases: no estimate
        probe = site.role == "probe"
        key = (site.oligo, site.s_aln, probe)
        if key not in memo:
            nM = reaction.probe_nM if probe else reaction.primer_nM
            memo[key] = estimate_duplex(site.oligo, site.s_aln, cond, nM)
        return memo[key]

    return estimate
