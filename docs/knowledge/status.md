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
| Giardia lamblia | [2026-10-09 09:45Z](runs/giardia-2026-10-09.md) | complete: all 2,791 records. Exceeds limit, the probe detects G. microti and G. psittaci; 96.0% of 202 records collected 2023-2026, Incomplete on undated records |
| Influenza A (matrix) | [2026-10-21 15:42Z](runs/influenza-a-2026-10-21.md) | complete: all 173,689 records, both reverse primers. Review, no limit crossed: 99.6% of 70,606 collected 2023-2026 (69.0% with infa_rev alone); infa_rev2 alone covers 13.6% |

# Next, waiting on the user

- VZV (ORF38): assay file ready, no run yet ([assay](assays/vzv-orf38.md)). The probe's G form
  (Oka lineage) folds into a hairpin; the user may give the probe's dyes and the cycling.
- HSV-1 (gG, Ryncarz 1999): first run 2026-10-23 ([run](runs/hsv1-2026-10-23.md)): HSV-2
  amplified but not detected, 96.1% detectable, inclusivity Incomplete (26 dated recent genomes).
  Decide on `status_axis: release` and on raising the partner-scan limit for the HSV-2 products.
  Check the forward primer's 2nd base (C in the paper, T in both reference genomes) against the
  laboratory's order sheet, and change the exclusivity panel if wanted.

- Giardia lamblia: decide what the predicted detection of G. microti and G. psittaci means for
  the laboratory, and whether to put this assay on `status_axis: release` (two thirds of the
  records have no collection year) ([run](runs/giardia-2026-10-09.md)). The oligos still want
  confirming against Verweij 2004: they were supplied, not read out of the paper.

- Influenza A (matrix): with `infa_rev2` the terminal G-A failures are covered: 99.6%
  detectable, no limit crossed ([run](runs/influenza-a-2026-10-21.md)). Nothing waits on it.
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
