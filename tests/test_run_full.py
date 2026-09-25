"""The full `run` command end to end, against the constructed NCBI world."""

import json
import re
import time
from datetime import UTC, datetime

import pytest
import yaml
from openpyxl import load_workbook
from typer.testing import CliRunner

from qpcr_assay_check.cli import app

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import ROOT_EXAMPLE
from .test_assess import F_START, HUMAN, P_START, R_START, TARGET, add_target_hits, offtarget_genome
from .world import WorldFake

runner = CliRunner()
HUMAN_ACC = "NC_000007.14"


@pytest.fixture
def env(tmp_path, monkeypatch):
    conf = tmp_path / "config.yaml"
    conf.write_text(f"ncbi:\n  cache_dir: {tmp_path / 'cache'}\n")
    # the shipped example carries its own settings (variants: blast_partitioned); these tests
    # choose the variant source through --config, so they run a copy without them
    data = yaml.safe_load(ROOT_EXAMPLE.read_text())
    data.pop("settings", None)
    assay = tmp_path / "assay.yaml"
    assay.write_text(yaml.safe_dump(data, sort_keys=False))
    monkeypatch.setenv("NCBI_EMAIL", "lab@example.org")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def install(world):
        fake = WorldFake(world)
        monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
        return fake

    return type("E", (), {"conf": conf, "out": tmp_path / "out", "assay": assay,
                          "install": staticmethod(install)})  # fmt: skip


def world_with(f=(), r=(), p=(), hits="full"):
    w = offtarget_genome(
        f=f, r=r, p=p, acc=HUMAN_ACC, taxid=HUMAN, name="Homo sapiens",
        title="Homo sapiens chromosome 7, GRCh38 reference",
    )  # fmt: skip
    if hits == "full":
        w.hit(HUMAN, "forward", F, HUMAN_ACC, F_START, "+")
        w.hit(HUMAN, "reverse", R, HUMAN_ACC, R_START, "-")
        w.hit(HUMAN, "probe", P, HUMAN_ACC, P_START, "+")
    add_target_hits(w)
    return w


def invoke(env, *extra, **kw):
    return runner.invoke(
        app,
        ["run", str(env.assay), "--config", str(env.conf), "-o", str(env.out), *extra],
        **kw,
    )


def run_dir(env):
    (path,) = env.out.rglob("results.json")
    return path.parent


def test_an_off_target_product_in_the_background_fails_the_run_and_is_documented(env):
    env.install(world_with(f=[10], r=[5], p=[8]))
    r = invoke(env, "--yes")
    assert r.exit_code == 20, r.output
    assert "Verdict: FAIL" in r.output and "predicted off-target product" in r.output
    d = run_dir(env)
    data = json.loads((d / "results.json").read_text())
    spec = data["specificity"]
    assert spec["verdict"] == "FAIL" and spec["amplicons"][0]["classification"] == "likely_detected"
    assert spec["amplicons"][0]["organism"] == "Homo sapiens" and data["network_used"] is True
    assert data["search"]["searches"][0]["rid"]  # RIDs are part of the record

    rows = (d / "hits.tsv").read_text().splitlines()
    assert rows[0].startswith("tier\tquery\trole") and len(rows) == 4  # header + three sites
    assert any("\tcritical\t" in row for row in rows[1:])

    html = (d / "report.html").read_text()
    for needle in (
        "Predicted off-target products", "Closest off-target sites", "likely_detected",
        "Homo sapiens", "In silico analysis does not replace experimental validation",
        "sent the oligo sequences to NCBI", "Taxon restriction check",
    ):  # fmt: skip
        assert needle in html, needle
    assert 'class="aln"' in html and 'class="mm' in html  # alignment with highlighted mismatches
    # self-contained: no tag loads a remote script, stylesheet, image or font
    assert not re.search(r"<(script|link|img|iframe)\b[^>]*\b(src|href)=[\"']?(https?:)?//", html)

    wb = load_workbook(d / "results.xlsx")
    assert {"Off-target sites", "Predicted products", "Searches", "Findings"} <= set(wb.sheetnames)


def test_a_clean_assay_gives_a_passing_specificity_but_an_incomplete_overall_verdict(env):
    env.install(world_with(hits="none"))
    r = invoke(env, "--yes")
    # exclusivity, inclusivity and history (first run) all have no evidence: INCOMPLETE overall.
    assert r.exit_code == 30, r.output
    data = json.loads((run_dir(env) / "results.json").read_text())
    assert data["specificity"]["verdict"] == "PASS"
    states = {s["key"]: s["state"] for s in data["sections"]}
    assert states["specificity"] == states["amplicon_prediction"] == "evaluated"
    # exclusivity is implemented (v0.4.0), but this fake never resolves organism names, so its
    # own tier was never searched: missing evidence, so INCOMPLETE rather than a false PASS.
    assert states["exclusivity"] == "evaluated" and data["exclusivity"]["verdict"] == "INCOMPLETE"
    # inclusivity is implemented (v0.4.0) and the target tier was searched, but this fake never
    # registers a submission date for the target hit, so there is no dated evidence: INCOMPLETE.
    assert states["inclusivity"] == "evaluated" and data["inclusivity"]["verdict"] == "INCOMPLETE"
    # history is implemented (v1.0.0); this is the first run for this assay, so there is nothing
    # to compare against yet: also evaluated (not skipped), also honestly INCOMPLETE.
    assert states["history"] == "evaluated" and data["history"]["verdict"] == "INCOMPLETE"
    assert data["history"]["has_previous"] is False
    # every section was genuinely evaluated (even if some concluded INCOMPLETE), so nothing is
    # truly "not yet evaluated" in this run -- that heading must not appear.
    html = (run_dir(env) / "report.html").read_text()
    assert "Not yet evaluated" not in html
    assert "first recorded run for this assay" in html


def test_inclusivity_end_to_end_with_a_dated_target_hit(env):
    """The target tier's own hit gets a submission date, so inclusivity has real evidence."""
    w = world_with(hits="none")  # human background stays clean; only inclusivity matters here
    w.date("NC_045512.2", "2023/05/01")
    env.install(w)

    r = invoke(env, "--yes")
    assert r.exit_code == 30, r.output  # exclusivity has no evidence, history is not implemented

    data = json.loads((run_dir(env) / "results.json").read_text())
    incl = data["inclusivity"]
    assert incl["tier_searched"] is True and incl["target_taxid"] == 2697049
    forward = next(o for o in incl["oligos"] if o["role"] == "forward")
    by_year = {win["year"]: win for win in forward["windows"]}
    assert by_year[2023]["sample_size"] == 1 and by_year[2023]["n_perfect"] == 1
    states = {s["key"]: s["state"] for s in data["sections"]}
    assert states["inclusivity"] == "evaluated"

    html = (run_dir(env) / "report.html").read_text()
    assert "Inclusivity across the intended target (sampled)" in html and "2023" in html
    wb = load_workbook(run_dir(env) / "results.xlsx")
    assert "Inclusivity" in wb.sheetnames


def test_dry_run_sends_nothing(env):
    fake = env.install(world_with())
    r = invoke(env, "--dry-run")
    assert r.exit_code == 0 and "Dry run" in r.output
    assert fake.calls == [] and fake.efetch_calls == []


def test_declining_the_confirmation_sends_nothing(env):
    fake = env.install(world_with())
    r = invoke(env, input="n\n")
    assert r.exit_code == 64 and "Nothing was sent to NCBI" in r.output
    # Taxonomy name resolution (the exclusivity tier) runs before the confirmation prompt, since
    # it never sends the oligo sequences -- only organism names from the (reviewable) organism
    # list -- so declining still leaves it having made ESearch calls; no BLAST submission.
    assert fake.n_put == 0
    assert all("Blast.cgi" not in c["url"] for c in fake.calls)


def test_a_second_run_reuses_the_cache_and_sends_no_new_searches(env):
    fake = env.install(world_with(f=[10, 16, 17], hits="partial"))
    w = fake.world
    w.hit(HUMAN, "forward", F, HUMAN_ACC, F_START, "+", trim3=5)
    first = invoke(env, "--yes")
    assert first.exit_code in (20, 30)
    puts, fetches = fake.n_put, len(fake.efetch_calls)
    assert puts == 2 and fetches == 1
    second = invoke(env, "--yes")
    assert second.exit_code == first.exit_code
    assert (
        fake.n_put == puts and len(fake.efetch_calls) == fetches
    )  # everything came from the cache


def test_the_email_never_appears_in_the_record(env):
    env.install(world_with(f=[10], r=[5], p=[8]))
    invoke(env, "--yes")
    for path in env.out.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".tsv", ".html", ".log"}:
            text = path.read_text(errors="ignore")
            assert "lab@example.org" not in text and "lab%40example.org" not in text, path


def test_exclusivity_end_to_end_with_a_real_organism_list(env, tmp_path):
    """One organism resolves with a hit, one resolves with none, one does not resolve at all."""
    CT, NG = 813, 485
    organisms = tmp_path / "organisms.yaml"
    organisms.write_text(
        "categories:\n"
        "  - name: Test panel\n"
        "    organisms: [Chlamydia trachomatis, Neisseria gonorrhoeae, Mycoplasma pneumoniae]\n"
    )
    env.conf.write_text(
        f"ncbi:\n  cache_dir: {tmp_path / 'cache'}\norganisms:\n  list_file: {organisms}\n"
    )
    w = world_with(hits="none")  # human background stays clean; only exclusivity matters here
    w.name("Chlamydia trachomatis", CT)
    w.name("Neisseria gonorrhoeae", NG)  # left unregistered on purpose: Mycoplasma stays unresolved
    offtarget_genome(taxid=CT, acc="OT_CT.1", name="Chlamydia trachomatis", world=w)
    w.hit(CT, "forward", F, "OT_CT.1", F_START, "+")
    offtarget_genome(taxid=NG, acc="OT_NG.1", name="Neisseria gonorrhoeae", world=w)
    env.install(w)

    r = invoke(env, "--yes")
    # a critical primer-only site in the exclusivity tier forms no product: WARN, not FAIL
    # (primer_site_critical_no_product); the run is INCOMPLETE for other reasons here
    assert r.exit_code != 20, r.output
    assert "forming no predicted product" in r.output

    data = json.loads((run_dir(env) / "results.json").read_text())
    excl = data["exclusivity"]
    assert excl["tier_searched"] is True
    assert excl["n_organisms"] == 3 and excl["n_resolved"] == 2
    by_name = {row["organism"]: row for row in excl["rows"]}
    assert by_name["Chlamydia trachomatis"]["n_sites"] >= 1
    assert by_name["Chlamydia trachomatis"]["best_site_level"] == "critical"
    assert by_name["Neisseria gonorrhoeae"]["n_sites"] == 0
    assert by_name["Neisseria gonorrhoeae"]["resolution"] == "resolved"
    assert by_name["Mycoplasma pneumoniae"]["resolution"] == "unresolved"
    assert [u["name"] for u in excl["unresolved"]] == ["Mycoplasma pneumoniae"]

    html = (run_dir(env) / "report.html").read_text()
    assert "Exclusivity against the clinical organism list" in html
    assert "Chlamydia trachomatis" in html and "Mycoplasma pneumoniae" in html
    wb = load_workbook(run_dir(env) / "results.xlsx")
    assert "Exclusivity" in wb.sheetnames


def test_exclusivity_uses_the_assay_s_own_list_by_default(env, tmp_path):
    """organisms.source defaults to "assay": an assay with its own exclusivity_organisms is
    searched against that list instead of the global one, with no organisms.list_file needed."""
    CT = 813
    assay_yaml = tmp_path / "assay.yaml"
    assay_yaml.write_text(
        ROOT_EXAMPLE.read_text() + "\nexclusivity_organisms:\n  - Chlamydia trachomatis\n"
    )
    w = world_with(hits="none")
    w.name("Chlamydia trachomatis", CT)
    offtarget_genome(taxid=CT, acc="OT_CT.1", name="Chlamydia trachomatis", world=w)
    w.hit(CT, "forward", F, "OT_CT.1", F_START, "+")
    env.install(w)

    r = runner.invoke(
        app, ["run", str(assay_yaml), "--config", str(env.conf), "-o", str(env.out), "--yes"]
    )
    # a critical primer-only site in the exclusivity tier forms no product: WARN, not FAIL
    # (primer_site_critical_no_product); the run is INCOMPLETE for other reasons here
    assert r.exit_code != 20, r.output
    assert "forming no predicted product" in r.output

    data = json.loads((run_dir(env) / "results.json").read_text())
    excl = data["exclusivity"]
    assert excl["source"] == "assay"
    assert excl["n_organisms"] == 1
    by_name = {row["organism"]: row for row in excl["rows"]}
    assert by_name["Chlamydia trachomatis"]["n_sites"] >= 1

    html = (run_dir(env) / "report.html").read_text()
    assert "Source: this assay" in html


def test_organisms_source_global_ignores_the_assay_s_own_list(env, tmp_path):
    """organisms.source: global always uses the configured global list, even when the assay
    defines its own exclusivity_organisms."""
    NG = 485
    organisms = tmp_path / "organisms.yaml"
    organisms.write_text(
        "categories:\n  - name: Global panel\n    organisms: [Neisseria gonorrhoeae]\n"
    )
    env.conf.write_text(
        f"ncbi:\n  cache_dir: {tmp_path / 'cache'}\n"
        f"organisms:\n  source: global\n  list_file: {organisms}\n"
    )
    assay_yaml = tmp_path / "assay.yaml"
    assay_yaml.write_text(
        ROOT_EXAMPLE.read_text() + "\nexclusivity_organisms:\n  - Chlamydia trachomatis\n"
    )
    w = world_with(hits="none")
    w.name("Neisseria gonorrhoeae", NG)
    env.install(w)

    r = runner.invoke(
        app, ["run", str(assay_yaml), "--config", str(env.conf), "-o", str(env.out), "--yes"]
    )
    assert r.exit_code == 30, r.output  # clean but INCOMPLETE: first run, no evidence anywhere

    data = json.loads((run_dir(env) / "results.json").read_text())
    excl = data["exclusivity"]
    assert excl["source"] == "global"
    assert [row["organism"] for row in excl["rows"]] == ["Neisseria gonorrhoeae"]

    html = (run_dir(env) / "report.html").read_text()
    assert "Source: the global list" in html


def test_exclusivity_excludes_the_assay_s_own_target_even_when_listed(env, tmp_path):
    """A live full run found: the packaged organism list includes SARS-CoV-2 itself (a
    respiratory panel commonly tests for it alongside other pathogens), which for a SARS-CoV-2
    assay meant the exclusivity tier found the assay's own perfect, intended match and reported
    it as a critical off-target site -- a false FAIL that has nothing to do with specificity."""
    CT = 813
    organisms = tmp_path / "organisms.yaml"
    organisms.write_text(
        "categories:\n"
        "  - name: Test panel\n"
        "    organisms: [Chlamydia trachomatis, Severe acute respiratory syndrome coronavirus 2]\n"
    )
    env.conf.write_text(
        f"ncbi:\n  cache_dir: {tmp_path / 'cache'}\norganisms:\n  list_file: {organisms}\n"
    )
    w = world_with(hits="none")  # add_target_hits() already registered perfect hits at TARGET
    w.name("Chlamydia trachomatis", CT)
    w.name("Severe acute respiratory syndrome coronavirus 2", TARGET)
    offtarget_genome(taxid=CT, acc="OT_CT.1", name="Chlamydia trachomatis", world=w)
    w.hit(CT, "forward", F, "OT_CT.1", F_START, "+")
    env.install(w)

    invoke(env, "--yes")

    data = json.loads((run_dir(env) / "results.json").read_text())
    excl = data["exclusivity"]
    assert excl["tier_searched"] is True  # Chlamydia trachomatis alone still gets it searched
    by_name = {row["organism"]: row for row in excl["rows"]}
    target_row = by_name["Severe acute respiratory syndrome coronavirus 2"]
    assert target_row["is_target"] is True
    assert target_row["n_sites"] == 0
    assert target_row["best_site_level"] is None
    assert by_name["Chlamydia trachomatis"]["is_target"] is False
    assert by_name["Chlamydia trachomatis"]["n_sites"] >= 1
    # the real regression check: no exclusivity-tier evidence at all for the target's own taxid,
    # regardless of what the (unrelated) Chlamydia finding does to the overall verdict
    assert not any(
        s["tier"] == "exclusivity" and s["taxid"] == TARGET for s in data["specificity"]["sites"]
    )
    amplicons = data["specificity"]["amplicons"]
    assert not any(a["tier"] == "exclusivity" and a["taxid"] == TARGET for a in amplicons)

    html = (run_dir(env) / "report.html").read_text()
    assert "excluded from this search" in html


def test_history_diff_across_two_runs(env, tmp_path, monkeypatch):
    """Run the same assay twice; the second run must see and report what changed."""
    # A controlled, strictly increasing clock: real wall-clock resolution (whole seconds) could
    # tie two fast in-process runs to the same generated_at, which would make "which run is the
    # previous one" ambiguous -- something that cannot happen for a real yearly re-evaluation.
    times = iter([datetime(2025, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)])
    monkeypatch.setattr(
        "qpcr_assay_check.pipeline.datetime",
        type("_Clock", (), {"now": staticmethod(lambda tz=None: next(times))}),
    )

    env.install(world_with(hits="none"))
    first = invoke(env, "--yes")
    # clean, but INCOMPLETE: exclusivity/inclusivity/history all lack evidence on a first run
    assert first.exit_code == 30, first.output
    (first_path,) = env.out.rglob("results.json")
    run1_id = json.loads(first_path.read_text())["run_id"]

    # A fresh cache for the second run: otherwise the identical BLAST queries would be served
    # from run 1's on-disk cache instead of reaching the (now different) fake world.
    env.conf.write_text(f"ncbi:\n  cache_dir: {tmp_path / 'cache2'}\n")
    env.install(world_with(f=[10], r=[5], p=[8]))  # a new critical off-target site appears
    second = invoke(env, "--yes")
    assert second.exit_code == 20, second.output  # the new off-target product now fails the run

    run2_path = next(p for p in env.out.rglob("results.json") if p != first_path)
    data2 = json.loads(run2_path.read_text())
    hist = data2["history"]
    assert hist["has_previous"] is True
    assert hist["previous_run_id"] == run1_id
    assert hist["inputs_changed"] is False  # same assay file both times
    assert hist["verdict"] == "WARN"  # the "history" section itself just flags the change
    assert len(hist["new_sites"]) >= 1
    assert any(s["level_after"] == "critical" for s in hist["new_sites"])
    states = {s["key"]: s["state"] for s in data2["sections"]}
    assert states["history"] == "evaluated"

    html = run2_path.parent.joinpath("report.html").read_text()
    assert "Changes since the previous run" in html
    assert run1_id in html
    wb = load_workbook(run2_path.parent / "results.xlsx")
    assert "History" in wb.sheetnames


def test_a_full_run_fills_the_variant_summary_from_the_target_tier(env):
    """Live finding: the section was always empty, because no target-tier site was ever built."""
    env.install(world_with(hits="none"))
    invoke(env, "--yes")
    d = run_dir(env)
    vs = json.loads((d / "results.json").read_text())["variant_summary"]
    by_role = {o["role"]: o for o in vs["oligos"]}
    assert all(by_role[role]["total_measured"] >= 1 for role in ("forward", "probe", "reverse"))
    assert vs["fragment_total"] >= 1
    assert "Variant summary (assay's own target)" in (d / "report.html").read_text()
    sheets = set(load_workbook(d / "results.xlsx").sheetnames)
    assert {"Oligo variants", "Fragment variants"} <= sheets


def test_a_full_run_uses_every_genome_assembly_for_the_variant_summary(env, monkeypatch):
    """v1.1.0: with variants.source datasets (the default) the CLI wires in the exhaustive path."""
    from qpcr_assay_check.cli import build_assay
    from qpcr_assay_check.oligo import iupac

    from .fake_datasets import FakeAssembly, FakeDatasets
    from .world import filler, mutate

    amp = build_assay(ROOT_EXAMPLE, {}).reference_amplicon
    variant = amp.replace(F, mutate(F, [20]), 1)
    datasets = FakeDatasets([
        FakeAssembly("GCF_1.1", "2025-01-01", {"c1": filler(2000, 1) + amp + filler(2000, 2)}),
        FakeAssembly("GCA_2.1", "2026-01-01",
                     {"c2": iupac.reverse_complement(filler(2000, 3) + variant + filler(2000, 4))}),
    ])  # fmt: skip
    world = WorldFake(world_with(hits="none"))

    class Both:
        headers: dict = {}

        def request(self, method, url, **kw):
            fake = datasets if "/datasets/v2" in url else world
            return fake.request(method, url, **kw)

    monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", Both)
    invoke(env, "--yes")
    data = json.loads((run_dir(env) / "results.json").read_text())
    vs = data["variant_summary"]
    assert vs["source"] == "datasets" and vs["coverage"]["assessed_total"] == 2
    fwd = next(o for o in vs["oligos"] if o["role"] == "forward")
    assert sorted(r["count"] for r in fwd["rows"]) == [1, 1]
    assert data["inclusivity"]["sample_scheme"].startswith("Every genome assembly")
    assert "Scope: every genome assembly" in (run_dir(env) / "report.html").read_text()


def test_a_full_run_can_use_partitioned_blast_for_the_variant_summary(env, monkeypatch):
    """v1.1.0: variants.source blast_partitioned is wired through the CLI."""
    from qpcr_assay_check.cli import build_assay

    from .fake_nuccore import FakeNuccore, FakeRecord
    from .world import filler

    amp = build_assay(ROOT_EXAMPLE, {}).reference_amplicon
    fake = FakeNuccore([
        FakeRecord("1", "MZ000001.1", "2026/01/02", filler(300, 1) + amp + filler(300, 2)),
        FakeRecord("2", "MZ000002.1", "2025/03/04", filler(900, 3)),
    ])  # fmt: skip
    monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
    env.conf.write_text(
        env.conf.read_text() + "variants:\n  source: blast_partitioned\n"
        "search:\n  background_taxids: []\n"
    )
    r = invoke(env, "--yes")
    assert "sending the reference amplicon to NCBI BLAST" in r.output, (r.output, r.exception)
    assert r.exception is None or isinstance(r.exception, SystemExit), repr(r.exception)
    data = json.loads((run_dir(env) / "results.json").read_text())
    vs = data["variant_summary"]
    assert vs["source"] == "blast_partitioned"
    assert (vs["coverage"]["assessed_total"], vs["coverage"]["found"]) == (2, 1)
    assert "Scope: every NCBI Nucleotide record" in (run_dir(env) / "report.html").read_text()
