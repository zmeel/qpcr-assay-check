from datetime import UTC, datetime, timedelta

import pytest

from qpcr_assay_check.ncbi.blast import BlastApi
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.http import NcbiError, NcbiHttp
from qpcr_assay_check.ncbi.jobs import JobStore
from qpcr_assay_check.ncbi.runner import BlastRunner, SearchTimeout
from qpcr_assay_check.ncbi.settings import Credentials
from qpcr_assay_check.search.orchestrate import _new_job
from qpcr_assay_check.search.planner import plan_searches

from .conftest import make_assay
from .fake_ncbi import FakeClock, FakeNcbi, blast_json, connection_error, hits_for_payload

T0 = datetime(2026, 9, 21, 9, 0, tzinfo=UTC)


class Env:
    """A runner wired to a fake NCBI, a fake clock, and a temporary job store/cache."""

    def __init__(self, cfg, tmp_path, fake: FakeNcbi):
        self.cfg, self.tmp, self.fake = cfg, tmp_path, fake
        self.fc = FakeClock()
        fake.clock = self.fc
        self.plan = plan_searches(make_assay(), cfg)
        self.ps = self.plan.searches[0]
        self.reopen()

    def now(self):
        return T0 + timedelta(seconds=self.fc.t)

    def reopen(self):
        """Simulate a fresh process: new objects, same files on disk."""
        http = NcbiHttp(
            self.cfg.ncbi, Credentials("lab@example.org"), session=self.fake,
            clock=self.fc.monotonic, sleep=self.fc.sleep, jitter=lambda: 0.0,
        )  # fmt: skip
        self.store = JobStore(self.tmp / "jobs.json")
        self.cache = Cache(self.tmp / "cache", now=self.now)
        self.runner = BlastRunner(
            BlastApi(http, self.cfg.ncbi.blast_url), self.cache, self.store, self.cfg.ncbi,
            "JSON2_S", now=self.now, sleep=self.fc.sleep,
        )  # fmt: skip
        self.job = self.store.jobs.get(self.ps.key) or _new_job(self.ps)

    def run(self):
        return self.runner.run(self.job, ps_fasta(self.ps), self.ps.params)


def ps_fasta(ps):
    return ps.fasta


@pytest.fixture
def env(cfg, tmp_path):
    return Env(cfg, tmp_path, FakeNcbi(hits_for_payload, statuses=["WAITING", "WAITING", "READY"]))


def test_happy_path_submits_polls_and_fetches(env):
    raw = env.run()
    assert "BlastOutput2" in raw
    assert env.fake.n_put == 1
    assert env.job.state == "fetched" and env.job.rid == "RID0001" and env.job.finished_at
    assert env.fc.slept[0] == 15  # waited the announced RTOE before the first poll
    polls = [c for c in env.fake.calls if c["payload"].get("FORMAT_OBJECT") == "SearchInfo"]
    assert len(polls) == 3
    times = [c["t"] for c in polls]
    assert all(b - a >= 60 for a, b in zip(times, times[1:], strict=False))  # >= 1 poll/minute
    assert all(
        b - a >= 10
        for a, b in zip(
            [c["t"] for c in env.fake.calls], [c["t"] for c in env.fake.calls][1:], strict=False
        )
    )


def test_job_state_is_persisted_and_survives_a_new_process(env):
    env.run()
    assert JobStore(env.tmp / "jobs.json").jobs[env.ps.key].state == "fetched"


def test_rid_is_saved_before_polling_so_a_crash_can_resume(cfg, tmp_path):
    env = Env(cfg, tmp_path, FakeNcbi(hits_for_payload, crash_on_first_status=True))
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.run()
    on_disk = JobStore(tmp_path / "jobs.json").jobs[env.ps.key]
    assert on_disk.state == "submitted" and on_disk.rid == "RID0001"

    env.reopen()  # new process
    assert not env.runner.needs_submission(env.job)  # would resume, not resubmit
    assert "BlastOutput2" in env.run()
    assert env.fake.n_put == 1  # never submitted twice
    assert env.job.state == "fetched"


def test_expired_rid_is_resubmitted(env):
    env.job.state, env.job.rid = "submitted", "OLD"
    env.job.submitted_at = (T0 - timedelta(hours=40)).isoformat()
    env.store.upsert(env.job)
    assert env.runner.needs_submission(env.job)
    env.run()
    assert env.fake.n_put == 1 and env.job.rid == "RID0001"


def test_unknown_status_triggers_one_resubmission(cfg, tmp_path):
    fake = FakeNcbi(hits_for_payload, status_scripts=[["UNKNOWN"], ["READY"]])
    env = Env(cfg, tmp_path, fake)
    env.run()
    assert fake.n_put == 2 and env.job.rid == "RID0002" and env.job.attempts == 2


def test_failed_search_raises_and_is_recorded(cfg, tmp_path):
    env = Env(cfg, tmp_path, FakeNcbi(hits_for_payload, statuses=["FAILED"]))
    with pytest.raises(NcbiError, match="failed"):
        env.run()
    assert env.job.state == "failed" and env.job.error


def test_timeout_keeps_the_job_resumable(cfg, tmp_path):
    env = Env(cfg, tmp_path, FakeNcbi(hits_for_payload, statuses=["WAITING"]))
    with pytest.raises(SearchTimeout, match="resume"):
        env.run()
    on_disk = JobStore(tmp_path / "jobs.json").jobs[env.ps.key]
    assert on_disk.state == "submitted" and on_disk.rid == "RID0001"
    assert env.fc.t >= cfg.ncbi.max_wait_minutes * 60


def test_cached_result_means_no_network_at_all(env):
    env.run()
    calls_before = len(env.fake.calls)
    env.reopen()
    assert not env.runner.needs_submission(env.job)
    assert env.run() == env.runner.cached(env.job)
    assert len(env.fake.calls) == calls_before


def test_stale_cache_is_not_reused_a_year_later(env):
    env.run()
    env.fc.t += 8 * 24 * 3600  # beyond blast_cache_ttl_days (7)
    env.reopen()
    assert env.runner.needs_submission(env.job)
    env.run()
    assert env.fake.n_put == 2


def test_transient_submit_failures_are_retried_by_the_http_layer(cfg, tmp_path):
    fake = FakeNcbi(hits_for_payload, put_failures=[503, connection_error()])
    env = Env(cfg, tmp_path, fake)
    env.run()
    assert fake.n_put == 1 and env.job.state == "fetched"


def test_response_without_rid_is_an_error_not_a_hang(cfg, tmp_path):
    env = Env(cfg, tmp_path, FakeNcbi(blast_json({}), statuses=["READY"]))
    env.fake.request = lambda *a, **k: type(
        "R", (), {"status_code": 200, "text": "<html>oops</html>", "headers": {}}
    )()
    with pytest.raises(NcbiError, match="request ID"):
        env.run()


def _resumable(env, minutes_ago: float) -> None:
    env.job.state, env.job.rid = "submitted", "OLD"
    env.job.submitted_at = (T0 - timedelta(minutes=minutes_ago)).isoformat()
    env.store.upsert(env.job)


def test_a_search_waiting_too_long_is_submitted_anew_when_resumed(env):
    """Live 2026-09-25: one RID stayed WAITING for over 70 min across restarts."""
    _resumable(env, env.cfg.ncbi.resubmit_after_minutes + 10)
    assert "BlastOutput2" in env.run()
    assert env.fake.n_put == 1 and env.job.rid == "RID0001"


def test_a_resumed_search_is_resubmitted_once_when_it_crosses_the_limit(cfg, tmp_path):
    env = Env(cfg, tmp_path, FakeNcbi(hits_for_payload, statuses=["WAITING"]))
    _resumable(env, cfg.ncbi.resubmit_after_minutes - 20)
    with pytest.raises(SearchTimeout):
        env.run()
    assert env.fake.n_put == 1 and env.job.rid == "RID0001"  # once, not every 90 min


def test_a_recent_search_is_resumed_not_resent(env):
    _resumable(env, 5)
    env.fake.searches["OLD"] = env.ps.params  # the fake NCBI knows the resumed RID
    env.run()
    assert env.fake.n_put == 0 and env.job.rid == "OLD"


def test_resubmit_flag_sends_a_waiting_search_again_at_once(env):
    env.cfg.ncbi.resubmit_after_minutes = 0  # what `--resubmit` sets
    _resumable(env, 5)
    env.run()
    assert env.fake.n_put == 1 and env.job.rid == "RID0001"
