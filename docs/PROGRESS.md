# Progress log

Read this alongside `docs/SPEC.md` (authoritative spec) and `docs/ARCHITECTURE.md` (design and
verified NCBI facts) at the start of every session. Newest entry first.

## 2026-09-22 — Docker image built and run successfully by the user

The user built the image on their Synology NAS (Docker running as root) and ran it: `--version`
and `--help` worked immediately. `init` failed on the first try with a `PermissionError` writing
into the bind-mounted `/work` directory -- the image's default user is non-root (uid 1000), which
does not own a directory created/owned by root on the host. Gave two fixes (`--user
"$(id -u):$(id -g)"` on `docker run`, or `chown` the host directory to uid 1000 first); the user
used `--user` and it worked. `run --qc-only` then produced the exact same verdict and rationale
message as the plain-virtualenv install this was first checked against in-sandbox, confirming the
image installs and runs the real package correctly end to end for the offline path.

Updated README.md (Docker section now shows `--user` in every example, explains why, and states
what's confirmed vs. not — a full NCBI network run through the container specifically hasn't been
separately exercised, only through the plain-virtualenv install), docs/ARCHITECTURE.md (moved
Docker from "still unverified" to a new "Verified for v1.0.0" section), and CHANGELOG.md (Known
limitations updated to describe the uid-1000 permission behavior rather than "not built at all").

One thing to note for next time: the first copy-pasted `docker run` command with a trailing `\`
line continuation failed with "docker: invalid reference format" in the user's terminal --
resolved by giving the same command as one line instead. Multi-line backslash-continued shell
commands are apparently not safe to assume will paste correctly into every terminal; prefer
single-line commands (or a documented heredoc, as used for the git tag commands earlier in this
session) when giving copy-paste instructions to run remotely, since round-tripping a fix through
chat is slow.

## 2026-09-22 — v1.0.0 started: run history + diff implemented; Docker written but unverified

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

## 2026-09-22 — v0.4.0 tagged; phase 4b's ESummary date lookup verified live

The user ran `scripts/smoke_test.py` again and pasted back a new `smoke_report.json` (all steps
`ok: true`, including the new `08b_esummary_inclusivity_dates`). Also bumped the version to 0.4.0,
closed out the CHANGELOG's Unreleased section into a dated `[0.4.0]` entry, and created an
annotated tag `v0.4.0`. Pushing the branch commit worked; pushing the tag itself hit the same
HTTP 403 from the agent proxy seen in an earlier session for tag pushes (an organisation policy
restriction on tag refs, not transient) -- gave the user the exact commands to recreate and push
the tag from their own machine rather than retrying or routing around it.

Key results from the live run:
- **The renamed organism `Mycoplasmoides pneumoniae` now resolves live.** Organism-list resolution
  went from 38/40 (previous run) to 39/40; only `Mycobacterium chelonae` remains unresolved. This
  confirms the phase-4a fix (renaming "Mycoplasma pneumoniae" directly rather than relying on the
  `[All Names]` synonym fallback, which does not catch this rename) actually works.
- **Inclusivity's ESummary-based date lookup works for the common case.** `Eutils.esummary()`'s
  JSON shape matched a real response (`result.uids` + one object per UID); the nuccore docsum's
  date field is `createdate` (format `"YYYY/MM/DD"`), the first candidate `year_from_docsum()`
  tries; and NCBI does key the result by its own resolved UID, not the input accession (confirmed
  directly -- the response for `id=NC_045512.2,NC_000007.14` came back keyed `"1798174254"`/
  `"568815591"`). `fetch_years()` correctly recovered both years (2020, 2002) despite this.
- **Found and fixed a bug in the smoke-test script itself, not in shipped code.** Step `08b`'s own
  findings computation (`esummary_docsum_keys`, `esummary_reindexed_by_accession_correctly`)
  naively indexed the UID-keyed `esummary()` response by accession directly -- the same mistake the
  production `fetch_years()` code was specifically written to avoid. This silently produced empty
  findings (`{}`) even though `fetch_years_result` itself was correct throughout, since
  `fetch_years()` does its own correct re-indexing internally and never went through the buggy
  path. Fixed the smoke-test step to re-index the same way, and tightened the constructed test
  fakes (`tests/world.py`'s `WorldFake`, `tests/test_smoke_script.py`'s `SmokeFake`) to use a
  synthetic UID that deliberately differs from the accession, so a UID/accession mix-up like this
  would now fail the test suite too, not only surface on a live run. All 295 tests still pass after
  this tightening -- confirming `inclusivity/dates.py` was already correct.
- `blast_date_window_restriction_honoured: false` reconfirmed (BLAST+`[PDAT]` still unreliable, as
  in the previous run) -- expected, not a new finding, just re-verifying the ruled-out design stays
  ruled out.

Updated `docs/ARCHITECTURE.md` (moved phase 4b's ESummary items from "Still unverified" to a new
"Verified" section, updated the top status line to drop "not yet tagged/released"), `CHANGELOG.md`
(closed `[0.4.0]`, updated Known limitations/Fixed), `README.md` (status blurb, third-live-run
paragraph, Limitations bullets, dropped "in progress" from the Exclusivity/Inclusivity section
headers and fixed the now-changed anchor link).

## 2026-09-22 — Phase 4b implemented: inclusivity via target-tier reuse + ESummary date-bucketing

Built inclusivity (SPEC.md step 9) on the redesign forced by the previous session's live finding
(BLAST cannot reliably combine `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter):
instead of a separate, date-windowed BLAST search, inclusivity reuses the "target" tier search
every run already makes, and buckets its own hits into years afterwards via a new `esummary()`
E-utility client method plus `inclusivity/dates.py` (which re-indexes ESummary's UID-keyed JSON
response by each docsum's own `accessionversion`/`caption` field, not by input order). Per year:
sample deterministically (evenly spread, one per accession, capped by `sample_per_window`),
re-align over the full oligo length (`inclusivity/sites.py`, reusing `specificity/sites.py`'s
candidate/window machinery), and aggregate perfect/1-mismatch/2+-mismatch/3'-mismatch counts plus
a per-position mismatch profile (`inclusivity/aggregate.py`). Population size per year comes from
an independent ESearch count, reported next to (never instead of) the sample size. Wired through
`pipeline.py` (new `inclusivity` field on `RunResult`, its own `SectionResult`, rationale lines),
`cli.py` (`keep_tiers` now always includes `"target"`; `compute_inclusivity()` call wrapped in
`try/except NcbiError` so a date-lookup failure degrades gracefully rather than discarding an
otherwise-complete run, matching the `taxonomy_breakdown` fix from phase 4a), the HTML report
(new per-oligo, per-year table) and the xlsx writer (new Inclusivity sheet). 295 tests pass
(`pytest -m "not live"`), `ruff check .` clean.

**Honesty points carried through deliberately**: inclusivity's sample is not a controlled random
sample (it depends on where each year's records fall in BLAST's own hit-list ranking, which is
capped) — stated explicitly in `InclusivityResult.limitations` on every result, not just in docs.
A year with zero sampled hits is reported as zero, not omitted. No target-tier search at all (or
no assay target taxid) gives INCOMPLETE, never a false PASS.

**Still unverified, flagged for the next live smoke test** (`scripts/smoke_test.py` step
`08b_esummary_inclusivity_dates`, added but not yet run): the real nuccore ESummary docsum date
field name (the code tries several candidates from memory of the docs, not an observed response),
and whether the accession re-indexing logic holds for more than one accession in a real response
(only checked against the constructed test world so far). Do not treat inclusivity's date
attribution as confirmed until that step comes back `ok: true` with a sane `esummary_docsum_keys`.

## 2026-09-22 — Phase 4a verified live; inclusivity's planned design ruled out

The user ran `scripts/smoke_test.py` and pasted back `smoke_report.json` (all steps `ok: true`).
Updated README.md, `docs/ARCHITECTURE.md`, `CHANGELOG.md` and `data/clinical_organisms.yaml` to
reflect the real results rather than leave them marked "unverified." Also clarified for the user
that no pull request exists (none was requested) and re-verified branch/tag/version sync between
local and `origin/claude/brave-dirac-1vppye` before this.

Key results:
- **Taxonomy lineage parsing works**: 5/5 sampled lineages (Homo sapiens, Mus musculus, SARS-CoV-2,
  E. coli, S. aureus) came back with a populated genus and family through the real `resolve.py`
  code, not ad-hoc smoke-test code. One real subtlety worth remembering: SARS-CoV-2's own Taxonomy
  `Rank` is `"no rank"`, not `"species"` -- its species comes from its `LineageEx` ancestor
  (`Betacoronavirus pandemicum`). `Lineage.species` handles this correctly already.
- **The organism-list resolution path works**: 38/40 packaged names resolved through the real
  `resolve_organism_list` function (not a mock). Unresolved: "Mycoplasma pneumoniae" and
  "Mycobacterium chelonae".
- **A hypothesis from the previous session was wrong, and worth remembering as a lesson**: I
  assumed (docs/ARCHITECTURE.md, `taxonomy/resolve.py`'s docstring) that the `[All Names]` synonym
  fallback would catch "Mycoplasma pneumoniae"'s 2018 genus rename to *Mycoplasmoides*. It does
  not -- both terms returned zero hits. Fixed by renaming the organism-list entry to
  "Mycoplasmoides pneumoniae" directly (itself not yet confirmed live) rather than relying on the
  fallback. Updated the docstring and ARCHITECTURE.md to stop claiming the fallback would catch
  this, and to note synonym resolution is not as complete as assumed.
- **Significant, unprompted finding from a pre-existing smoke-test check (step 08, not written this
  session): combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST call
  does not reliably restrict by date** (`blast_date_window_restriction_honoured: false` -- 4 of 20
  checked hit accessions fell outside the requested window). This directly rules out the inclusivity
  design SPEC.md step 7 describes and this project had assumed for phase 4b ("BLAST the reference
  amplicon against nt restricted to the target taxid, stratified into time windows via `ENTREZ_QUERY`
  date filters"). ESearch's own `[PDAT]` filtering is independently confirmed reliable, so phase 4b
  must get each window's accession list from ESearch and work from that list directly, not lean on
  BLAST for the date filtering. This is a design-level finding that must be read before starting 4b.
- Also newly confirmed: Entrez queries with 11/40/100 taxids are all accepted by the BLAST URL API
  (true upper limit still unknown, but 100 is now a safe planning number).
- Did not bump `pyproject.toml` or tag anything: phase 4a's *code* was already committed and pushed
  in the previous session; this session only updated documentation to match the live results, plus
  one data fix (the organism-list rename). Committed and pushed (user asked directly both times).

Left for the user / next session:
- **"Mycoplasmoides pneumoniae" and "Mycobacterium chelonae" still need a live re-check** (a
  smaller, targeted smoke-test run, or just watch the next full run's `exclusivity.unresolved`).
- **Phase 4b (inclusivity) needs a redesign before implementation starts**, per the `[PDAT]`+BLAST
  finding above -- do not start coding phase 4b against the old SPEC.md step 7 description without
  first working out the ESearch-based alternative.
- `--human`/`--probe-databases` smoke-test options still not run; alternative database timing for
  the human background tier remains unmeasured beyond the original 61-minute `core_nt` figure.

## 2026-09-21 — v0.4.0 phase 4a: taxonomy resolution, organism list, exclusivity

Started v0.4.0 on the user's go-ahead ("start v0.4.0"). Given the real size of the phase (taxonomy,
organism list, inclusivity, exclusivity), split it into two sub-phases rather than attempting all of
it at once: **4a** (this session) covers taxonomy name resolution, the clinical organism list, a
real exclusivity search tier and report, and a species/genus/family rollup of off-target hits.
**4b** (inclusivity) is deliberately deferred: it needs a new time-windowed search scheme whose core
assumption (combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST
search) is explicitly flagged as unverified in `docs/ARCHITECTURE.md`, and deserved its own,
separately-scoped session rather than being rushed alongside 4a.

What this session built, in dependency order:
- `taxonomy/resolve.py` (Entrez Taxonomy name resolution + lineage parsing) and
  `taxonomy/organisms.py` (the organism-list YAML loader) -- reused the exact ESearch/EFetch query
  shapes the v0.2.1 smoke test already validated live (`f"{name}[Scientific Name]"`, then
  `[All Names]` for synonyms), rather than guessing a new format.
- `data/clinical_organisms.yaml`: a starter list, clearly labelled non-authoritative per SPEC.md's
  explicit requirement.
- Wired organism-list resolution into `search/execute.py` (`_resolve_and_plan`) so the exclusivity
  tier's taxids are resolved once and the confirmation preview (`on_plan`) shows the real,
  resolved plan rather than a stale pre-resolution one. Discovered along the way that resolving
  organism names does not need the same "confirm before sending" gate as oligo sequences (it never
  sends anything proprietary), and adjusted the `declining sends nothing` test accordingly (it now
  checks no BLAST submission happened, not "zero network calls").
- `taxonomy/exclusivity.py`: deliberately reuses the existing v0.3.0 specificity assessment for the
  exclusivity tier's sites/amplicons (just another tier in `specificity.off_target_tiers`) instead
  of a parallel implementation, and only adds the per-organism table view SPEC.md step 8 asks for.
- `taxonomy/rollup.py`: species/genus/family aggregation (SPEC step 6), generic across all
  off-target tiers. Made its failure non-fatal after discovering the naive wiring turned any
  taxonomy EFetch hiccup into a full run-ending `NCBI problem` exit code, even though QC and
  specificity had already produced a valid, complete verdict -- a lineage lookup failure now just
  leaves the breakdown empty.
- Wired both into `pipeline.py`, `report.html.j2`, `report/xlsx.py`, and `results.json`.
- Extended `tests/world.py` with controllable organism-name-to-taxid resolution
  (`World.name(...)`) so a real end-to-end CLI test could exercise resolved-with-a-hit,
  resolved-with-no-hit, and unresolved organisms together, not just the "nothing resolves" default.
- Added `scripts/smoke_test.py` steps `03b` (lineage parsing, the real `resolve_name` synonym
  fallback for "Mycoplasma pneumoniae") and `03c` (the actual packaged-organism-list resolution
  path) -- not yet run live.
- 30 new tests, 280 total; `ruff check` and `ruff format --check` both clean throughout.
- Updated README, `docs/ARCHITECTURE.md`, `CHANGELOG.md` (Unreleased, not tagged: this is a
  sub-phase, not a complete v0.4.0). Did not bump `pyproject.toml`'s version.

Left for the user / next session:
- **Run `scripts/smoke_test.py`** (steps `03b`/`03c` are new) and paste back the report. Lineage
  parsing (`Rank`, `LineageEx`) has never been checked against real NCBI output; only the
  `ScientificName`-only regex check from v0.2.1 has been.
- Local commit(s) on `claude/brave-dirac-1vppye`; not pushed. Ask before pushing, per CLAUDE.md.
- Phase 4b (inclusivity) is next, once 4a is validated live and the user is ready.

## 2026-09-21 — v0.3.0 pushed; pruning bounds validated live

- Pushed the v0.3.0 commit to `origin/claude/brave-dirac-1vppye` (user confirmed).
- Created an annotated `v0.3.0` tag locally, but **pushing it was blocked**: the sandbox's egress
  proxy returned an HTTP 403 specifically for the tag ref (the branch push to the same host had just
  succeeded), which the proxy's own guidance identifies as an organization policy denial, not a
  transient failure — so it was not retried or routed around. Also discovered the "no git tags
  exist" note from the previous session was wrong: v0.1.0/v0.2.0/v0.2.1 tags do exist on the remote;
  this sandbox's clone had just never fetched them. Told the user to pull the branch and push (and
  tag) themselves from their own machine (a Synology NAS running code-server in Docker), where the
  restriction likely doesn't apply.
- The user ran `scripts/validate_assessment.py` live (CDC N1 example, `--tier background`) and
  pasted back `validation_out/validation_report.json`: 905 relevant alignments, 244 ruled out
  without fetching, 661 needing a fetch (replaces the earlier unmeasured "about 1,500" guess),
  80-hit sample checked (40 fetchable, 40 ruled out), **0 contradictions**. Updated README.md,
  `docs/ARCHITECTURE.md` and `CHANGELOG.md` to reflect this: the pruning bounds are no longer
  described as "unverified," but as checked once, on a sample, for one assay's background tier —
  not exhaustive proof, and worth re-running for other tiers/assays or after logic changes.
- `scripts/smoke_test.py` still has not been re-run since 0.2.1 — still open.

## 2026-09-21 — v0.3.0: specificity assessment integrated

Picked up a work-in-progress snapshot (`qpcr-assay-check-v0.3.0-WIP-snapshot.zip`, built in a
separate sandbox without NCBI access) that implemented phase 3 of the roadmap: full-length
re-alignment (`align/realign.py`), amplicon pairing and site classification (`specificity/`), and
wired them into `run`. State at handoff: 249/250 tests passing, one ruff E501.

What this session did:
- Diffed the snapshot against the repo, scanned it for anything suspicious (network calls, eval/exec,
  unexpected URLs) before integrating — clean — then copied it in file by file.
- Fixed the one failing test. Root cause: `tests/world.py`'s "realistic BLAST hit" guard only checked
  that the first base beyond a partial alignment mismatched. That is too weak — with match +1 /
  mismatch -3 scoring, BLAST's alignment is locally maximal, so *no prefix* of the unaligned flank
  (read outward from the alignment boundary) may sum to a positive score, or BLAST would have
  extended over it. Rewrote the guard to check every prefix, and fixed the handful of test scenarios
  (`f=[10,16]`+`trim3=5`, `r=[7,23]`+`trim5=7`, and two `human_world()` cases) that had relied on the
  weaker check — each needed one more mismatch placed adjacent to the alignment boundary to stay
  realistic. Confirmed the fix by re-deriving each affected assertion (n_mismatch, defect_positions,
  clean_3prime_nt, level) from `specificity/sites.py`'s actual classification rules rather than
  guessing.
- Fixed the ruff E501 (a docstring line in `tests/test_validation_script.py`).
- `ruff check .` and `pytest -m "not live"` are both clean: 250 passed.
- Updated README.md (status banner, privacy note — `run` now sends oligos and hit accessions to
  NCBI, not just `search`; new Specificity assessment and live-validation sections; limitations;
  roadmap), `docs/ARCHITECTURE.md` (status, v0.3.0 design decisions, moved the now-verified
  minus-strand coordinate fact out of "still unverified", added the v0.3.0 unverified-pruning-bounds
  note), and `CHANGELOG.md` (0.3.0 entry).
- Did not run `scripts/smoke_test.py` or `scripts/validate_assessment.py` live — this sandbox has no
  NCBI access, per CLAUDE.md. Both need to be run locally and their output pasted back (see below).
- Applied the user's go-ahead on the license question: proceeded with the already-committed
  Apache-2.0 (`LICENSE`, `pyproject.toml`) rather than treating it as still open.

Left for the user / next session:
- **Run `scripts/validate_assessment.py` live** (needs `NCBI_EMAIL`; background tier can take about
  an hour, cached 7 days after). Paste back `validation_out/validation_report.json`. If it reports a
  contradicted rule, the pruning in `specificity/sites.py` (`can_reach_warning` / `Candidate.lower_bound`)
  needs fixing before the specificity verdict can be trusted — do not treat the "world" as necessarily
  wrong this time; the script tests the rule, not just the constructed data.
- `scripts/smoke_test.py` is unchanged (wire protocol only) but has not been re-run since 0.2.1.
- Local commit created on `claude/brave-dirac-1vppye`; not pushed. CLAUDE.md requires asking before
  any push — waiting for that go-ahead.
- Still open from the previous session: no git tags exist locally even though CHANGELOG documents
  0.1.0–0.2.1 as released — worth reconciling before the next tag is cut.
- No annotated tag has been cut for 0.3.0 yet.

## 2026-09-20/21 — v0.1.0–v0.2.1 (prior sessions, summarized from CHANGELOG.md)

- v0.1.0: skeleton, input parsing, oligo QC (primer3-py), report skeleton. No network use.
- v0.2.0: remote BLAST backend (own `requests` client, not `qblast`, so RIDs can be persisted and
  resumed), throttling/backoff, content-addressed cache, tiered taxon-restricted search planning,
  JSON2 parser, `scripts/smoke_test.py`. Validated only against a simulated NCBI.
- v0.2.1: fixes from the first live run of `scripts/smoke_test.py` — most notably a redaction bug
  (the e-mail could leak into logs in its URL-encoded form during a transient error) and several
  NCBI facts confirmed for the first time (see `docs/ARCHITECTURE.md`'s "Verified in the first live
  smoke run" section): short-oligo BLAST parameters accepted as configured, `JSON2_S` report shape,
  `ENTREZ_QUERY` taxon restriction effective but not airtight, human-restricted `core_nt` searches
  take about an hour.

## Open questions carried across sessions

- License: resolved — proceed with Apache-2.0 (already committed). CLAUDE.md's "Open items" note
  that it was unchosen is stale.
- Git tags: resolved — v0.1.0/v0.2.0/v0.2.1 exist on the remote; a prior session's local clone had
  just never fetched them. **v0.3.0 needs the user to tag and push it themselves** (this sandbox's
  egress policy blocks tag pushes even though branch pushes work).
- `scripts/smoke_test.py` has not been re-run since 0.2.1; the wire protocol is unchanged but this
  is still worth doing before the next release.
