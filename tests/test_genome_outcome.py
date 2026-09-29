"""One precedence for every genome count (overhaul step 2): coverage, assembly levels, the
escape and undetermined lists, the whole-fragment years and the channel counts all use
genome_outcome."""

import pytest

from qpcr_assay_check.variants.exhaustive import (
    GenomeCall,
    GenomeOutcome,
    _level_coverage,
    copy_coverage,
    genome_outcome,
)
from qpcr_assay_check.variants.store import StoredAssembly

from .conftest import make_assay

GOOD = {"forward": True, "reverse": True, "probe": True}
BAD_F = {"forward": False, "reverse": True, "probe": True}


def call(acc, *, detectable=0, roles=None, states=None, level="Contig", **kw):
    return GenomeCall(
        accession=acc, n_copies=1, n_detectable=detectable, best_is_first=True,
        n_detectable_other_rule=detectable, oligo_good={}, role_good=roles or BAD_F,
        role_state=states or {"forward": "fail", "reverse": "ok", "probe": "ok"},
        assembly_level=level, **kw,
    )  # fmt: skip


UNDET = {"forward": "undetermined", "reverse": "ok", "probe": "ok"}


@pytest.mark.parametrize(
    ("c", "expected"),
    [
        (call("a", detectable=1, roles=GOOD), GenomeOutcome.DETECTED),
        (call("b"), GenomeOutcome.NOT_DETECTED),
        (call("c", states=UNDET), GenomeOutcome.UNDETERMINED),
        (call("d", unassembled=True), GenomeOutcome.UNASSEMBLED),
        (call("e", from_parts=True), GenomeOutcome.FROM_PARTS),
        # counted from parts (judge_from_parts: detectable) is simply detected
        (call("f", detectable=1, roles=GOOD, from_parts=True), GenomeOutcome.DETECTED),
        # a site rule wins over a possibly unassembled draft
        (call("g", states=UNDET, unassembled=True), GenomeOutcome.UNDETERMINED),
        (call("h", roles={}), GenomeOutcome.NOT_DETECTED),  # no roles: never "detected"
    ],
)
def test_the_precedence(c, expected):
    assert genome_outcome(c) is expected


def test_every_count_uses_the_same_outcome():
    calls = [
        call("A", detectable=1, roles=GOOD, level="Complete Genome"),
        call("B", level="Complete Genome"),
        call("C", states=UNDET),
        call("D", unassembled=True),
        call("E", from_parts=True),
    ]
    cov = copy_coverage(calls, make_assay(), "any")
    assert (cov.escapes, cov.undetermined, cov.unassembled) == (1, 1, 1)
    assert cov.escape_examples == ["B"] and cov.unassembled_accessions == ["D"]
    levels = {r.level: r for r in _level_coverage(calls)}
    c = levels["Contig"]
    assert (c.detectable, c.escapes, c.undetermined, c.unassembled, c.from_parts) == (0, 0, 1, 1, 1)
    assert (levels["Complete Genome"].detectable, levels["Complete Genome"].escapes) == (1, 1)
    from qpcr_assay_check.variants.exhaustive import _genome_channel_state

    items = {x.accession: StoredAssembly(accession=x.accession, release_date="2024-01-01",
                                         status="found") for x in calls}  # fmt: skip
    for x in calls:  # one channel ("FAM"): its state per genome follows the same outcome
        x.channel_state = {"FAM": "ok" if x.accession == "A" else "fail"}
    states = {x.accession: _genome_channel_state(items[x.accession], x, "FAM") for x in calls}
    assert states == {"A": "ok", "B": "fail", "C": "fail", "D": "undetermined",
                      "E": "undetermined"}  # fmt: skip
