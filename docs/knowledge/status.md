---
type: Status
title: Current status
description: Where the project stands - what is released, what is on main, the latest runs, what is next and what waits on the user. Read first in every session.
tags: [status]
status: draft
generated: { by: claude-code/agent, at: 2026-11-20T10:00:00Z }
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
- Changed: the HSV-1, HSV-2 and VZV examples set `inclusivity.status_axis: release`.
- Changed: HSV-1, HSV-2 and VZV name their closest relatives as near neighbours
  (`near_neighbour_taxids`), moved from the exclusivity list.

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
| HSV-1 (gG) | [2026-11-19 11:41Z](runs/hsv1-2026-11-19.md) | near neighbours and release axis: Exceeds limit on oligo QC only; inclusivity No flags (96.0% of 223 genomes released 2023-2026); HSV-2 amplified, not detected (500 records, the cap, near-neighbour tier Incomplete); no product in the exclusivity list or human DNA (background Incomplete, 2,000-site cap) |
| HSV-2 (gD) | [2026-11-19 10:45Z](runs/hsv2-2026-11-19b.md) | near neighbours and release axis: Review, from off-target primer sites without a product only (*Listeria*, human); near neighbours No flags (HSV-1 probe sites only, not amplified); inclusivity No flags, 100.0% of 181 genomes released 2023-2026; oligo QC No flags. First run [09:19Z](runs/hsv2-2026-11-19.md): Incomplete |
| Influenza A (matrix) | [2026-11-18 08:15Z](runs/influenza-a-2026-11-18b.md) | v2.2.0 with the re-alignment fix: Exceeds limit, a 141 bp product on ON845595.1 read as detected (a record labelled influenza B whose M fragment is 95% identical to influenza A: most likely mislabelled); inclusivity No flags (99.5% of 72,698) |

# Next, waiting on the user

- VZV (ORF38): runs 2026-10-23 and 2026-11-17 ([latest](runs/vzv-2026-11-17.md)): 99.7% detectable, no
  off-target product. The probe's G form (Oka lineage, 10.5% of the records, the vaccine strain
  among them) folds into a hairpin: worth a wet-lab check on an Oka template. Since 2026-11-19
  `status_axis: release` (user, in the GUI; mirrored in the assay file: 109 records released
  2023-2026, 75 collected) and near neighbours named; not yet rerun.
- HSV-2 detection (gD): rerun 2026-11-19 10:45Z with near neighbours and the release axis
  ([run](runs/hsv2-2026-11-19b.md)): Review, from off-target primer sites without a product only;
  every other row No flags. For the laboratory to review and sign. VZV names its near
  neighbours too, not yet rerun; its GUI copy needs the repository file.
- HSV-1 detection (gG, Ryncarz 1999 oligos): rerun 2026-11-19 11:41Z with near neighbours and
  the release axis ([run](runs/hsv1-2026-11-19.md)): Exceeds limit on oligo QC only, inclusivity
  No flags, HSV-2 amplified but not detected. The GUI's copy matches the repository file. Check
  the forward primer's 2nd base (C in the paper, T in both reference genomes) against the
  laboratory's order sheet.

- Advisor review of the search tiers (2026-11-20, [review](../reviews/2026-11-20-tiers-advisor.md)):
  nine findings, F1-F3, F5 and F7 checked against the code and confirmed. Most urgent, F1: a tier
  left out of `specificity.off_target_tiers` is still searched but not assessed, and its row
  reads No flags. Decide what to take up; no code changed.
- VZV rerun with near neighbours and the release axis: failed twice on 2026-11-19 (NCBI returned
  an HTML page without a request ID); the user retries later.

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
- The GUI's configuration (its work folder's `config.yaml`) sets `inclusivity.status_axis:
  collection`; HSV-1, HSV-2 and VZV override it in their own assay files (the user set it in the
  GUI's copies on 2026-11-19). A record with `ncbi.resubmit_after_minutes: 0` comes from a run
  with the GUI's "Submit unfinished BLAST searches anew" box ticked (`--resubmit`), as the HSV-2
  runs at 09:19Z and 10:04Z; operational only, outside the inputs hash.
- This environment cannot reach NCBI's API hosts or the GitHub wiki; the user runs live checks
  (`scripts/smoke_test.py`) and publishes `docs/wiki/`.
- Carried over from the old progress log: the note that the smoke test was not re-run since 0.2.1
  is outdated (the user ran it with `--quick --expect-sweep` on 2026-09-30); a full smoke run
  before the next release is still worthwhile. Git tags v0.1.0 to v2.1.0 exist on the remote.

[^changelog]: CHANGELOG.md
[^sessions]: Session logs
[^open]: Open items
