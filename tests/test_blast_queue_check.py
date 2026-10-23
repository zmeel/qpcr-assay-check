"""scripts/blast_queue_check.py: the control search's timing and its report (no network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qpcr_assay_check.config import load_config

ROOT = Path(__file__).resolve().parent.parent


def load_script():
    spec = importlib.util.spec_from_file_location(
        "blast_queue_check_script", ROOT / "scripts" / "blast_queue_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look their module up while it loads
    spec.loader.exec_module(module)
    return module


class FakeApi:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.n_status = 0

    def submit(self, params):
        return "RID1", 30

    def status(self, rid):
        self.n_status += 1
        return self.statuses.pop(0), None


class FailingCount:
    def esearch_count(self, db, term):
        from qpcr_assay_check.ncbi.http import NcbiError

        raise NcbiError("HTTP 502")


def run_control(monkeypatch, statuses, minutes_per_sleep):
    mod = load_script()
    clock = {"t": 0.0}
    sleeps: list[float] = []

    def sleep(s):
        sleeps.append(s)
        clock["t"] += minutes_per_sleep * 60

    monkeypatch.setattr(mod.time, "sleep", sleep)
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock["t"])
    report = mod.Report()
    api = FakeApi(statuses)
    mod._run_control(api, load_config(), FailingCount(), 20, 20.0, report, lambda t: t)
    return report, api, sleeps


def test_the_first_poll_waits_for_the_estimate_and_a_first_unknown_is_asked_again(
    monkeypatch, tmp_path
):
    """Polled the moment it was issued, a RID could read UNKNOWN and waste the one submission
    the script makes (review 2026-10-23)."""
    monkeypatch.chdir(tmp_path)
    report, api, sleeps = run_control(monkeypatch, ["UNKNOWN", "READY"], 0.5)
    assert sleeps[0] == 30  # NCBI's estimate, below the 60 s poll interval
    assert api.n_status == 2 and report.verdict == "queue_looks_healthy"


def test_a_failed_count_reads_as_an_estimate_not_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    report, _, _ = run_control(monkeypatch, ["WAITING", "READY"], 4)
    assert report.verdict == "inconclusive"
    assert "about 10,000 records" in report.verdict_reason and "None" not in report.verdict_reason
