---
type: Session
title: "v1.0.0 started: run history + diff implemented; Docker written but unverified"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: v1.0.0 started: run history + diff implemented; Docker written but unverified

User said "Start v1.0.0". Before writing code, checked in on one consequential design decision
(the "history" section's scope): confirmed making it required, like every other section, so a
brand-new assay's first run is honestly `INCOMPLETE` (nothing to compare against yet) rather than
letting history be informational-only and let a first run reach a clean PASS. Recommended and
chosen: required, INCOMPLETE on first run.

Built `history/` (`store.py` finds the previous run by scanning `results/<slug>/*/results.json`
for the most recent `generated_at`, no separate index; `diff.py` compares sections/sites/amplicons/
inclusivity by natural key, not run-local IDs). Wired into `pipeline.evaluate()` (new `history`
field, its own required section, `PLANNED_SECTIONS` removed since it was history's only remaining
entry) and `cli.py` (`find_previous_run()` called before `evaluate()`). Added a "Changes since the
previous run" report section and a "History" xlsx sheet. 13 new tests (natural-key matching unit
tests plus a full two-run CLI end-to-end scenario); found and fixed a real bug along the way in
`report/html.py`'s `pending` filter (`verdict is None` no longer means "not evaluated" now that a
genuinely-evaluated INCOMPLETE section exists) that broke two existing tests, and moved the
"oligos were/were not sent to NCBI" disclosure out of the now-sometimes-empty pending block so it
always renders.

**Near-miss worth remembering**: `.gitignore` had a stale, unscoped `history/` rule from early
project scaffolding (apparently meant for a separate run-history output directory that this
phase's "files, no separate index" design never ended up needing) that was silently ignoring the
entire new `src/qpcr_assay_check/history/` source package the moment it was created. Caught by
running `git status` before the first commit of this phase (a `git status --short --ignored`
specifically, prompted by habit rather than suspicion) and fixed immediately -- nothing was lost,
but it would have quietly excluded the whole feature from every future commit if it had gone
unnoticed. Worth a standing lesson: check `git status --ignored` after creating a new top-level
package directory, especially one whose name might collide with an older, unrelated `.gitignore`
entry.

Wrote `Dockerfile`/`.dockerignore` and attempted to build/run the image in this sandbox. Docker's
CLI and daemon binaries are present but the daemon isn't running by default; started it manually,
then hit the sandbox's outbound-proxy restriction pulling `python:3.12-slim` from Docker Hub's CDN
(`production.cloudfront.docker.com`, HTTP 403). Followed the environment's own documented
workaround for `docker build` exactly (installed `/root/.ccr/ca-bundle.crt` into the system trust
store, passed `HTTPS_PROXY`/`HTTP_PROXY` to the `dockerd` process) and retried both `docker pull`
and `docker build` -- identical failure both times, concluded to be a genuine restriction on this
CDN through the proxy rather than a fixable misconfiguration, so stopped rather than trying further
workarounds (matching the "report, do not work around" guidance for this class of proxy failure).
Reverted the system CA change and stopped the daemon afterward to leave the sandbox as found.
Validated what could be validated instead: `pip install .` into a clean virtualenv (the same
command the Dockerfile's build stage runs) followed by `init` → `validate` → `run --qc-only`
through the installed console-script entry point, end to end, correct output files and exit code.
The Dockerfile itself is therefore unverified as a built image and should be built and run by the
user (or in CI) before being relied on.

Bumped version to 1.0.0 is NOT yet done (deliberately -- CHANGELOG.md's `[Unreleased]` section
holds this phase's work; tagging v1.0.0 is expected to wait for documentation polish, the other
open item in SPEC.md's v1.0.0 phase, and/or explicit user confirmation the Docker image was built
and works).

# Related

* [Run history as a required section (withdrawn)](../decisions/2026-09-22-history-section-required.md)
