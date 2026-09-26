"""Panel-level escape detection over two assays' region stores.

All sequences are SYNTHETIC (the CDC N1 oligos for assay A, random oligos for assay B, random
spacers), not real genomes or a real panel.
"""

from __future__ import annotations

import json

import yaml
from openpyxl import load_workbook
from typer.testing import CliRunner

from qpcr_assay_check.cli import app
from qpcr_assay_check.config import load_config
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.panel import PanelClass, State, classify, run_panel
from qpcr_assay_check.report.panel import write_panel_outputs
from qpcr_assay_check.variants.exhaustive import run_exhaustive

from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .fake_datasets import FakeAssembly, FakeDatasets
from .test_variants_exhaustive import AMP, NOW, _no_fetch, setup
from .world import filler, mutate

FB, PB, RB = filler(20, 501), filler(22, 502), filler(20, 503)
AMP_B = FB + filler(25, 504) + PB + filler(25, 505) + iupac.reverse_complement(RB)
RC_R = iupac.reverse_complement(R)
BAD_A = AMP.replace(RC_R, mutate(RC_R, [1, 2]))  # two 3'-end mismatches: an escape


def genome(seed: int, *amps: str) -> dict[str, str]:
    parts = [filler(2500, seed)]
    for i, a in enumerate(amps):
        parts += [a, filler(2500, seed + 50 + i)]
    return {f"CTG{seed}.1": "".join(parts)}


GENOMES = {
    "GCA_000000201.1": genome(201, AMP, AMP_B),  # both detect
    "GCA_000000202.1": genome(202, BAD_A, AMP_B),  # only B
    "GCA_000000203.1": genome(203, BAD_A),  # A escapes, B's region is gone: no target
    "GCA_000000204.1": genome(204, AMP),  # only A
    "GCA_000000205.1": genome(205, AMP, AMP_B),  # processed by A only
}


def assay_a():
    return make_assay(assay_name="Target A", reference_amplicon=AMP, target={"taxid": 813})


def assay_b():
    return make_assay(assay_name="Target B", forward=FB, probe=PB, reverse=RB,
                      reference_amplicon=AMP_B, target={"taxid": 813})  # fmt: skip


def run_both(tmp_path):
    for assay, accs in ((assay_a(), list(GENOMES)), (assay_b(), list(GENOMES)[:4])):
        fake = FakeDatasets([FakeAssembly(a, f"2026-0{i + 1}-01", GENOMES[a])
                             for i, a in enumerate(accs)])  # fmt: skip
        cfg, _f, client, _a = setup(tmp_path, fake=fake)
        run_exhaustive(assay, cfg, client, tmp_path / "cache", _no_fetch, now=NOW)
    files = []
    for name, assay in (("a.yaml", assay_a()), ("b.yaml", assay_b())):
        data = json.loads(assay.model_dump_json(exclude={"reference_amplicons"}))
        (tmp_path / name).write_text(yaml.safe_dump(data))
        files.append(name)
    panel = tmp_path / "panel.yaml"
    panel.write_text(yaml.safe_dump({"panel_name": "Synthetic two-target panel", "assays": files}))
    return panel


def load_member(path):
    from qpcr_assay_check.cli import build_assay

    assay = build_assay(path, {})
    return assay, load_config(None, assay.settings)


def test_genomes_are_combined_per_target(tmp_path):
    res = run_panel(run_both(tmp_path), load_member, tmp_path / "cache", _no_fetch, now=NOW)
    assert (res.in_all, res.not_in_all) == (4, 1)
    by_acc = {g.accession: (g.panel_class, g.states) for g in res.genomes}
    assert by_acc["GCA_000000201.1"][0] == PanelClass.ALL.value
    assert by_acc["GCA_000000202.1"] == (PanelClass.SOME.value, ["escape", "detected"])
    assert by_acc["GCA_000000203.1"] == (PanelClass.NONE.value, ["escape", "region not found"])
    assert by_acc["GCA_000000204.1"] == (PanelClass.SOME.value, ["detected", "region not found"])
    assert res.counts[PanelClass.NONE.value] == 1 and res.years[0].year == 2026


def test_outcome_rules():
    D, E, N, U = State.DETECTED, State.ESCAPE, State.NOT_FOUND, State.UNKNOWN
    assert classify([D, D]) is PanelClass.ALL
    assert classify([D, U]) is PanelClass.SOME
    assert classify([E, N]) is PanelClass.NONE  # a genome assembly: a missing region counts
    assert classify([E, E]) is PanelClass.NONE
    assert classify([E, U]) is PanelClass.UNDETERMINED


def test_no_region_found_anywhere_is_not_an_escape():
    """Review finding: a genome without any target region is more often incomplete."""
    N = State.NOT_FOUND
    assert classify([N, N]) is PanelClass.UNDETERMINED


def test_with_nucleotide_records_a_missing_region_is_not_assessable():
    """Review finding: a VP1-only record is 'region not found' for a 5'UTR assay."""
    E, N = State.ESCAPE, State.NOT_FOUND
    assert classify([E, N], partial_records=True) is PanelClass.UNDETERMINED
    assert classify([E, E], partial_records=True) is PanelClass.NONE


def test_the_newest_accession_version_is_shown():
    from types import SimpleNamespace as NS

    from qpcr_assay_check.panel import PanelFile, combine

    def item(acc):
        return NS(accession=acc, status="found", release_date="2026-01-01", organism="x")

    call = lambda acc: NS(accession=acc, role_good={"forward": True})  # noqa: E731
    per_member = [([item("X.1")], [call("X.1")], "a"), ([item("X.2")], [call("X.2")], "b")]
    cfg = load_config()
    res = combine(PanelFile(panel_name="p", assays=["a.yaml", "b.yaml"]), [assay_a(), assay_b()],
                  [cfg, cfg], per_member)  # fmt: skip
    assert [g.accession for g in res.genomes] == ["X.2"]


def test_the_report_workbook_and_cli(tmp_path):
    panel = run_both(tmp_path)
    res = run_panel(panel, load_member, tmp_path / "cache", _no_fetch, now=NOW)
    out = write_panel_outputs(res, tmp_path / "results")
    html = (out / "panel.html").read_text()
    assert "1 genome detected by no target" in html and "GCA_000000203.1" in html
    assert "does not replace experimental validation" in html
    wb = load_workbook(out / "panel.xlsx")
    assert [c.value for c in wb["Detected by no target"]["A"]][1:] == ["GCA_000000203.1"]
    cfg = tmp_path / "lab.yaml"
    cfg.write_text(yaml.safe_dump({"ncbi": {"cache_dir": str(tmp_path / "cache")}}))
    r = CliRunner().invoke(app, ["panel", str(panel), "-c", str(cfg), "-o", str(tmp_path / "r")])
    assert r.exit_code == 10, r.output  # at least one genome escapes every target
    assert "detected by no target: 1" in r.output


def test_assays_for_different_targets_are_refused(tmp_path):
    panel = run_both(tmp_path)
    data = yaml.safe_load((tmp_path / "b.yaml").read_text())
    data["target"]["taxid"] = 485
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(data))
    r = CliRunner().invoke(app, ["panel", str(panel)])
    assert r.exit_code == 64 and "same target" in r.output


def test_a_panel_needs_two_assays(tmp_path):
    p = tmp_path / "panel.yaml"
    p.write_text(yaml.safe_dump({"panel_name": "x", "assays": ["a.yaml"]}))
    r = CliRunner().invoke(app, ["panel", str(p)])
    assert r.exit_code == 64 and "at least two assay files" in r.output


def test_assays_with_different_record_filters_are_refused(tmp_path):
    panel = run_both(tmp_path)
    data = yaml.safe_load((tmp_path / "b.yaml").read_text())
    data["settings"] = {"variants": {"exclude_atypical": False}}
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(data))
    r = CliRunner().invoke(app, ["panel", str(panel)])
    assert r.exit_code == 64 and "variants.exclude_atypical" in r.output


def test_exclusions_with_the_datasets_source_are_refused_up_front(tmp_path):
    panel = run_both(tmp_path)
    for name in ("a.yaml", "b.yaml"):
        data = yaml.safe_load((tmp_path / name).read_text())
        data["target"]["exclude_taxids"] = [814]
        (tmp_path / name).write_text(yaml.safe_dump(data))
    r = CliRunner().invoke(app, ["panel", str(panel)])
    assert r.exit_code == 64 and "not supported with variants.source: datasets" in r.output


def test_the_panel_judges_genomes_exactly_as_the_assay_report(tmp_path):
    """Review gap: stored_calls must agree with run_exhaustive, also with bulges tolerated."""
    from qpcr_assay_check.variants.exhaustive import stored_calls

    fake = FakeDatasets([FakeAssembly(a, "2026-02-01", g) for a, g in GENOMES.items()])
    cfg, _f, client, _a = setup(tmp_path, fake=fake)
    cfg.variants.homopolymer_bulges_detectable = True
    res = run_exhaustive(assay_a(), cfg, client, tmp_path / "cache", _no_fetch, now=NOW)
    _items, calls, _p = stored_calls(assay_a(), cfg, tmp_path / "cache", _no_fetch, "datasets")
    detected = sum(all(c.role_good.values()) for c in calls)
    assert len(calls) == res.coverage.copies.genomes
    assert detected == res.coverage.copies.with_detectable_copy


def test_an_undetermined_genome_is_not_a_panel_escape():
    """Review finding: an MGB-probe mismatch (undetermined in the assay report) was an escape."""
    from types import SimpleNamespace as NS

    from qpcr_assay_check.panel import member_states
    from qpcr_assay_check.variants.exhaustive import GenomeCall

    call = GenomeCall(accession="G1.1", n_copies=1, n_detectable=0, best_is_first=True,
                      n_detectable_other_rule=0, oligo_good={}, role_good={"probe": False},
                      role_state={"forward": "ok", "reverse": "ok",
                                  "probe": "undetermined"})  # fmt: skip
    item = NS(accession="G1.1", status="ok")
    ((state, _it),) = member_states([item], [call]).values()
    assert state is State.UNDETERMINED
    assert classify([state, State.NOT_FOUND]) is PanelClass.UNDETERMINED  # not "no target"


def test_assays_differing_only_in_the_reason_text_are_accepted():
    """Review finding: the reason text of target.taxa is not part of the genome collection."""
    from qpcr_assay_check.panel import check_members

    cfg = load_config()
    cfg.variants.source = "blast_partitioned"

    def assay(reason):
        return make_assay(target={"taxid": 100, "taxa": [{"taxid": 200, "reason": reason}]})

    check_members([assay("rhinovirus"), assay("a rhinovirus, not detected")], [cfg, cfg])
