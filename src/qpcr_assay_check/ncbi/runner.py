"""Run one remote search as a resumable state machine: submit -> poll -> fetch -> cache."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

from ..config import NcbiSettings
from .blast import BlastApi
from .cache import Cache
from .http import NcbiError
from .jobs import Job, JobStore

log = logging.getLogger(__name__)


class SearchTimeout(NcbiError):
    """Waiting for NCBI took longer than allowed. The job stays resumable."""


def _now() -> datetime:
    return datetime.now(UTC)


class BlastRunner:
    """Drives jobs to completion. Every state change is persisted before the next network call."""

    def __init__(
        self,
        api: BlastApi,
        cache: Cache,
        store: JobStore,
        settings: NcbiSettings,
        result_format: str,
        *,
        now: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.api = api
        self.cache = cache
        self.store = store
        self.s = settings
        self.result_format = result_format
        self._now = now or (lambda: _now())
        self._sleep = sleep or (lambda s: time.sleep(s))

    def cached(self, job: Job) -> str | None:
        """The stored raw result for this exact request, if present and still fresh."""
        return self.cache.get("blast", job.key, ttl_days=self.s.blast_cache_ttl_days)

    def _rid_alive(self, job: Job) -> bool:
        if not job.rid or not job.submitted_at:
            return False
        age = self._now() - datetime.fromisoformat(job.submitted_at)
        return age.total_seconds() < self.s.rid_lifetime_hours * 3600 * 0.95

    def _waited(self, job: Job) -> float:
        """Minutes since the job's (latest) submission."""
        if not job.submitted_at:
            return 0.0
        return (self._now() - datetime.fromisoformat(job.submitted_at)).total_seconds() / 60

    def needs_submission(self, job: Job) -> bool:
        """True if running this job would send something to NCBI (so the user is asked first):
        a new search, an expired one, or one waiting so long that it is resubmitted."""
        if self.cached(job) is not None:
            return False
        if not (job.state in ("submitted", "ready") and self._rid_alive(job)):
            return True
        return job.state == "submitted" and self._waited(job) >= self.s.resubmit_after_minutes

    def run(self, job: Job, query_fasta: str, put_params: dict[str, str]) -> str:
        """Return the raw result text for ``job``, submitting/polling/fetching as needed."""
        hit = self.cached(job)
        if hit is not None:
            log.info("Job %s [%s]: served from cache", job.label, job.key[:8])
            if job.state != "fetched":
                job.state, job.finished_at = "fetched", self._now().isoformat()
                self.store.upsert(job)
            return hit

        # a search NCBI keeps WAITING for very long can hang: resubmitting helps (live, user
        # 2026-09-25: one RID stayed WAITING for over 70 min across restarts). A search is
        # resubmitted at most once per run, so a slow but healthy one is not resent in a loop.
        fresh = True
        if not (job.state in ("submitted", "ready") and self._rid_alive(job)):
            self._submit(job, put_params)
        elif job.state == "submitted" and self._waited(job) >= self.s.resubmit_after_minutes:
            log.warning(
                "Job %s: RID %s has waited %.0f min since submission; submitting it anew",
                job.label, job.rid, self._waited(job),
            )  # fmt: skip
            self._submit(job, put_params)
        else:
            log.info("Job %s: resuming RID %s", job.label, job.rid)
            fresh = False

        deadline = self._now().timestamp() + self.s.max_wait_minutes * 60
        first = True
        while True:
            assert job.rid is not None
            if first:
                self._sleep(min(max(job.rtoe_s or 0, 0), self.s.poll_interval_s))
                first = False
            status, _hits = self.api.status(job.rid)
            waited = self._waited(job)
            log.info(
                "Job %s: RID %s is %s (%.0f min since submission)",
                job.label,
                job.rid,
                status,
                waited,
            )
            if status == "READY":
                break
            if status == "FAILED":
                job.state, job.error = "failed", "BLAST reported FAILED"
                self.store.upsert(job)
                raise NcbiError(f"NCBI reported that search {job.label!r} (RID {job.rid}) failed.")
            if status == "UNKNOWN":
                log.warning("Job %s: RID %s is unknown/expired; resubmitting", job.label, job.rid)
                self._submit(job, put_params)
                first = True
                continue
            if not fresh and waited >= self.s.resubmit_after_minutes:
                log.warning(
                    "Job %s: RID %s still %s after %.0f min; submitting it anew",
                    job.label, job.rid, status, waited,
                )  # fmt: skip
                self._submit(job, put_params)
                fresh, first = True, True
                continue
            if self._now().timestamp() >= deadline:
                self.store.upsert(job)
                raise SearchTimeout(
                    f"Gave up waiting for search {job.label!r} after {self.s.max_wait_minutes:g} "
                    f"minutes (RID {job.rid}). Run the same command again to resume."
                )
            self._sleep(self.s.poll_interval_s)

        job.state = "ready"
        self.store.upsert(job)
        raw = self.api.fetch(job.rid, self.result_format)
        self.cache.put("blast", job.key, raw)
        job.state, job.finished_at, job.error = "fetched", self._now().isoformat(), None
        self.store.upsert(job)
        return raw

    def _submit(self, job: Job, put_params: dict[str, str]) -> None:
        rid, rtoe = self.api.submit(put_params)
        job.rid, job.rtoe_s = rid, rtoe
        job.state, job.submitted_at = "submitted", self._now().isoformat()
        job.attempts += 1
        self.store.upsert(job)  # persisted BEFORE polling so a crash can resume this RID
        log.info("Job %s: submitted, RID %s (estimated %d s)", job.label, rid, rtoe)
