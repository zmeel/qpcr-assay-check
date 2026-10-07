---
type: Status
title: Current status
description: Where the project stands - what is released, what is on main, the latest runs, what is next and what waits on the user. Read first in every session.
tags: [status]
status: draft
generated: { by: claude-code/agent, at: 2026-10-05T08:30:00Z }
sources:
  - id: changelog
    resource: ../../CHANGELOG.md
    title: CHANGELOG.md
  - id: sessions
    resource: sessions/index.md
    title: Session logs
  - id: open
    resource: open/index.md
    title: Open items
---

# Read this first

At the start of a session read this page, [docs/SPEC.md](../SPEC.md) (authoritative) and the
newest [session pages](sessions/index.md).[^sessions] Before ending a session, update this page and add a
session page (see [About this bundle](about.md)).

# Released

v2.1.0 (2026-10-02): the browser interface on top of the v2.0.0 analysis. Tags are pushed by the
user; this environment cannot push tags.[^changelog]

# On main, not yet released

From CHANGELOG "Unreleased":[^changelog] why each escape fails; distinct site patterns; the
collection year as an optional status axis with the 25% undated limit; why a cut genome has no
judged site; a fragment not in the assembly counts as region not found; terminal G2 at risk;
one mismatch under the MGB likely failure; narrower whole-fragment tables; search limits, RNA
note and homopolymer range in the report; this knowledge bundle. No release has been decided.

# Latest runs

| Assay | Run | Result |
|---|---|---|
| Neisseria | [2026-10-02 21:13Z](runs/neisseria-2026-10-02.md) | all 51,545 genomes; 85.8% by collection year, 89.0% by release; Review |
| Legionella | [2026-10-07 09:48Z](runs/legionella-2026-10-07.md) | Incomplete: 46.1% undetermined; 94.0% of 1,690 collected 2023-2026; first run with the new R9 ladder |
| Legionella | [2026-10-02 13:16Z](runs/legionella-2026-10-02.md) | Incomplete: 46.1% undetermined, mostly regions cut by contig ends |
| Enterovirus | [2026-09-30](runs/enterovirus-2026-09-30.md) | 91.6% detectable; Review; specificity Exceeds limit; predates the MGB rule |
| Entamoeba histolytica | [2026-10-05 12:49Z](runs/entamoeba-2026-10-05-complete.md) | Exceeds limit: products in other Entamoeba species; target 86.4% of 81 records; all 2,345 records assessed, inclusivity Incomplete (few dated records) |
| Influenza A (matrix) | [2026-10-07 14:01Z](runs/influenza-a-2026-10-07-corrected.md) | 83.6% detectable of 17,058 records; Incomplete, 152,768 records left to assess. ΔTm figures predate the degenerate-oligo fix |

# Next, waiting on the user

- Influenza A (matrix): keep running to work through the remaining 152,768 records; a rerun
  also picks up the corrected ΔTm figures ([assay](assays/influenza-a-matrix.md)).
- Entamoeba histolytica: a decision on the 62
  predicted products in other Entamoeba species (a wet-lab check against E. dispar and
  E. moshkovskii is the way to settle the probe's discrimination).
- Which remaining review items to take up; [open items](open/index.md) lists them.[^open]
- An enterovirus rerun with the MGB region rule ([open](open/enterovirus-rerun.md)).
- The Stadhouders PDF for the Table 1 check, if available.
- Confirm the licence (Apache-2.0 in pyproject.toml; CLAUDE.md still says to ask)
  ([open](open/license-note.md)).
- Read and mark concepts in this bundle as verified.

# Working setup

- The user runs the tool on a Synology NAS: `scripts/run_assay.sh` (mounts `src/`, no rebuild)
  and the browser interface with Docker compose (`.env` with NCBI_EMAIL, NCBI_API_KEY, QAC_UID,
  QAC_GID, QAC_PORT=8880); the GUI container runs the image's code, so every update needs
  `docker compose build`.
- This environment cannot reach NCBI's API hosts or the GitHub wiki; the user runs live checks
  (`scripts/smoke_test.py`) and publishes `docs/wiki/`.
- Carried over from the old progress log: the note that the smoke test was not re-run since 0.2.1
  is outdated (the user ran it with `--quick --expect-sweep` on 2026-09-30); a full smoke run
  before the next release is still worthwhile. Git tags v0.1.0 to v2.1.0 exist on the remote.

[^changelog]: CHANGELOG.md
[^sessions]: Session logs
[^open]: Open items
