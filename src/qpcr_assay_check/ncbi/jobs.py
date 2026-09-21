"""Persistent job state so an interrupted run resumes instead of starting over."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

JobState = Literal["planned", "submitted", "ready", "fetched", "failed"]


class Job(BaseModel):
    """One remote search (one BLAST submission) and everything needed to resume it."""

    key: str = Field(description="Content hash of the request; also the cache key")
    tier: str
    label: str
    taxids: list[int]
    entrez_query: str | None
    params: dict[str, str] = Field(description="BLAST parameters (without the query sequences)")
    query_labels: list[str]
    state: JobState = "planned"
    rid: str | None = None
    rtoe_s: int | None = None
    submitted_at: str | None = None
    finished_at: str | None = None
    attempts: int = 0
    error: str | None = None


class JobStore:
    """A small JSON file holding all jobs of one search, written atomically after every change."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.jobs: dict[str, Job] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.jobs = {j["key"]: Job.model_validate(j) for j in data.get("jobs", [])}

    def upsert(self, job: Job) -> None:
        """Insert or replace a job and persist immediately."""
        self.jobs[job.key] = job
        self.save()

    def save(self) -> None:
        """Write atomically so a crash never leaves a half-written state file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "jobs": [j.model_dump(mode="json") for j in self.jobs.values()],
        }
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
