---
type: Status
title: Current status
description: Where the project stands - what is released, what is on main, the latest runs, what is next and what waits on the user. Read first in every session.
tags: [status]
status: draft
generated: { by: claude-code/agent, at: 2026-11-19T10:30:00Z }
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

v2.2.0 (2026-11-17): the analysis after two code reviews and the whole-project evaluation of
2026-11-17; every record names its code (code fingerprint
`b68fa8fe6c8946a15c1bc1bc7a49362b868c1484327fbb56ad9c3d9348e44455`). Off-target and inclusivity
results change against 2.1.0. Tags are set and pushed by the user.[^changelog]

v2.1.0 (2026-10-02): the browser interface on top of the v2.0.0 analysis.

# On main, not yet released

Since v2.2.0 (CHANGELOG `[Unreleased]`):[^changelog]

- Fixed: a partial BLAST hit that can only stay "minor" by the mismatch counts is re-aligned
  and graded after all when the graded classes decide (`specificity.sites.worth_realigning`,
  formerly `can_reach_warning`); found on the influenza A run of 2026-11-18, confirmed by its
  rerun. More windows are fetched per run (cached).
- Fixed: the report's sentence on predicted products names the graded rule instead of "at least
  warning level".
- Changed: the HSV-1 example sets `inclusivity.status_axis: release`.

The influenza A rerun of 2026-11-18 08:15Z and the first HSV-2 run of 2026-11-19 ran on this
code, not on v2.2.0 as released.

# Latest runs

| Assay | Run | Result |
|---|---|---|
| Neisseria | [2026-10-02 21:13Z](runs/neisseria-2026-10-02.md) | all 51,545 genomes; 85.8% by collection year, 89.0% by release; Review |
| Legionella | [2026-10-07 09:48Z](runs/legionella-2026-10-07.md) | Incomplete: 46.1% undetermined; 94.0% of 1,690 collected 2023-2026; first run with the new R9 ladder |
| Legionella | [2026-10-02 13:16Z](runs/legionella-2026-10-02.md) | Incomplete: 46.1% undetermined, mostly regions cut by contig ends |
| Enterovirus | [2026-09-30](runs/enterovirus-2026-09-30.md) | 91.6% detectable; Review; specificity Exceeds limit; predates the MGB rule |
| Entamoeba histolytica | [2026-10-05 12:49Z](runs/entamoeba-2026-10-05-complete.md) | Exceeds limit: products in other Entamoeba species; target 86.4% of 81 records; all 2,345 records assessed, inclusivity Incomplete (few dated records) |
| Giardia lamblia | [2026-10-09 09:45Z](runs/giardia-2026-10-09.md) | complete: all 2,791 records. Exceeds limit, the probe detects G. microti and G. psittaci; 96.0% of 202 records collected 2023-2026, Incomplete on undated records |
| VZV (ORF38) | [2026-11-17 14:31Z](runs/vzv-2026-11-17.md) | coverage complete (2,831 assessed, 1 unavailable); 99.7% of 599 with the region detectable; no off-target product; Exceeds limit on oligo QC only (probe G-form hairpin); inclusivity Incomplete (75 collected 2023-2026) |
| HSV-1 (gG) | [2026-11-17 15:55Z](runs/hsv1-2026-11-17.md) | v2.2.0: 96.1% of 614 genomes detectable; no human product; HSV-2 amplified, not detected (500 records, the cap); Exceeds limit on oligo QC only; inclusivity Incomplete (collection axis; release axis set since) |
| HSV-2 (gD) | [2026-11-19 09:19Z](runs/hsv2-2026-11-19.md) | first run (main with the re-alignment fix): 561 of 561 genomes detectable (100.0%); no off-target product, HSV-1 not amplified; oligo QC No flags; Incomplete: near neighbours not searched, 6 records collected 2023-2026 (181 released, all detectable) |
| Influenza A (matrix) | [2026-11-18 08:15Z](runs/influenza-a-2026-11-18b.md) | v2.2.0 with the re-alignment fix: Exceeds limit, a 141 bp product on ON845595.1 read as detected (a record labelled influenza B whose M fragment is 95% identical to influenza A: most likely mislabelled); inclusivity No flags (99.5% of 72,698) |

# Next, waiting on the user

- VZV (ORF38): runs 2026-10-23 and 2026-11-17 ([latest](runs/vzv-2026-11-17.md)): 99.7% detectable, no
  off-target product. The probe's G form (Oka lineage, 10.5% of the records, the vaccine strain
  among them) folds into a hairpin: worth a wet-lab check on an Oka template. Decide on
  `status_axis: release` (109 records released 2023-2026, 75 collected).
- HSV-2 detection (gD): first run 2026-11-19 ([run](runs/hsv2-2026-11-19.md)): 100.0% of 561
  genomes detectable, no off-target product. Decide on `status_axis: release` (6 records
  collected 2023-2026, 181 released; 46.5% without a collection year), as for HSV-1, and on the
  near-neighbour tier (no taxa given, as for VZV: name taxa or drop the tier for these assays).
- HSV-1 detection (gG, Ryncarz 1999 oligos): rerun on v2.2.0 2026-11-17 ([run](runs/hsv1-2026-11-17.md)):
  96.1% detectable, HSV-2 amplified but not detected, no human product. The assay file now sets
  `status_axis: release`; the GUI's copy needs the same setting. Check the forward primer's 2nd
  base (C in the paper, T in both reference genomes) against the laboratory's order sheet.

- Giardia lamblia: decide what the predicted detection of G. microti and G. psittaci means for
  the laboratory, and whether to put this assay on `status_axis: release` (two thirds of the
  records have no collection year) ([run](runs/giardia-2026-10-09.md)). The oligos still want
  confirming against Verweij 2004: they were supplied, not read out of the paper.

- Influenza A (matrix): rerun 2026-11-18 08:15Z ([run](runs/influenza-a-2026-11-18b.md)): inclusivity
  No flags, but Exceeds limit on a predicted 141 bp product in ON845595.1. Decide what to do with
  that record once NCBI answers: its sequence is influenza A filed under influenza B (M1
  translation 99.2% identical to influenza A M1, 25.0% to influenza B M1), reported to NCBI on
  2026-11-18 ([open item](open/on845595-mislabelled.md)).

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
