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


def _s(query, grade, mm=0, gap=0, last5=0, note="", rule=""):
    from types import SimpleNamespace as NS

    return NS(query=query, grade=grade, n_mismatch=mm, n_gap=gap, mismatches_last5=last5,
              note=note, grade_rule=rule)  # fmt: skip


def test_escape_reason_kinds():
    from qpcr_assay_check.variants.exhaustive import escape_reason

    ok = _s("x", "perfect")
    fail = {"forward": "ok", "reverse": "fail", "probe": "ok"}
    bulge = _s("R", "at_risk", note="poly-A run 7→8", rule="R5b")
    kind, detail = escape_reason({"forward": ok, "reverse": bulge, "probe": ok}, fail,
                                 rescued_by_bulges=True)  # fmt: skip
    assert kind == "run_length" and detail == "reverse R: at risk, poly-A run 7→8"
    gap = _s("R", "likely_failure", mm=1, gap=1)
    assert escape_reason({"forward": ok, "reverse": gap, "probe": ok}, fail)[0] == "gap"
    mm = _s("R", "likely_failure", mm=2, last5=2)
    kind, detail = escape_reason({"forward": ok, "reverse": mm, "probe": ok}, fail)
    assert kind == "mismatch" and "2 change(s) in the last 5 nt" in detail
    # the pair rule: each primer alone is detectable, both fail together (R8)
    tol = _s("F", "tolerated", mm=1)
    both = {"forward": "fail", "reverse": "fail", "probe": "ok"}
    kind, detail = escape_reason({"forward": tol, "reverse": _s("R", "tolerated", mm=1),
                                  "probe": ok}, both)  # fmt: skip
    assert kind == "pair" and "R8" in detail
    assert escape_reason(
        {"forward": ok, "reverse": ok, "probe": ok},
        {"forward": "ok", "reverse": "ok", "probe": "ok"},
    ) == ("", "")


def test_copy_coverage_lists_escapes_with_reasons():
    a = call("A", escape_kind="run_length", escape_detail="reverse R: at risk, poly-A 7→8")
    b = call("B", escape_kind="mismatch", escape_detail="forward F: likely failure (2 ...)")
    c = call("C", escape_kind="run_length", escape_detail="reverse R: at risk, poly-A 7→9")
    cov = copy_coverage([a, b, c], make_assay(), "any")
    assert [(r.kind, r.genomes) for r in cov.escape_reasons] == [("run_length", 2),
                                                                 ("mismatch", 1)]  # fmt: skip
    assert cov.escape_reasons[0].examples == ["A", "C"]
    assert [e.accession for e in cov.escape_rows] == ["A", "B", "C"]
    assert cov.escape_rows[1].detail.startswith("forward F")
