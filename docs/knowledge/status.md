---
type: Status
title: Current status
description: Where the project stands - what is released, what is on main, the latest runs, what is next and what waits on the user. Read first in every session.
tags: [status]
status: draft
generated: { by: claude-code/agent, at: 2026-11-27T14:00:00Z }
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
- The search tiers after the advisor's review of 2026-11-20, all nine findings
  ([search tiers](components/search-tiers.md), [review](../reviews/2026-11-20-tiers-advisor.md)):
  every searched tier assessed, tier waivers with a reason, missing tiers Incomplete above Review,
  tier taxa checked against the target's lineage and each other, balanced searches, lineage in
  the exclusivity table and the restriction check, a probe budget of its own, "not detected
  (bounded)" and a bounded cut at `max_amplicons`, near neighbours read cautiously, the eukaryote
  note by lineage. **Specificity results change**: most searches are new submissions.
- The report after the advisor's review of 2026-11-20: three parts (a two-page sign-off with
  small figures, the evidence, an appendix), everything printable (closed sections did not
  print), shorter prose, mismatch maps per oligo, the Needs-attention rows in their coloured
  layout (user decision).

- The report since 2026-11-20, in four review rounds and the user's own comments
  ([report](components/report.md)):
  - **Findings:** condensed, the specificity findings as one table per tier.
  - **Wording:** plain words ("amplicon", "check for the opposite primer").
  - **Figures:** year figures by release and collection year side by side, an off-target map
    with numbered organisms, a hairpin/dimer strip, a coverage accounting figure.
  - **Print:** long tables break between rows.
  - **Length:** HSV-1 from 30 to about 15 pages, with a 2-page sign-off.
- A run can carry the oligo design over from an earlier record with the same oligos, reaction
  conditions and limits (`--skip-oligo-design`; GUI option "Evaluate oligo design").
- The Needs-attention table has a cut-off (user and advisor, 2026-11-27,
  [decision](decisions/2026-11-27-needs-attention-cutoff.md)): the top 3 per outcome, others
  from 0.1% and 2 records (likely failure 0.01%), at most 20 rows; the workbook says why each
  combination is listed or not. Part A: the status table breaks between rows, strain names are
  grouped, shares below 1% keep two digits. Confirmed on the influenza A rerun of 2026-11-27
  08:46Z: 9 of 272 combinations listed, 16 pages (25 before). Since then the table fits A4, Part
  A shows 2 rows and the sign-off lines are shorter; simulated on that record: 14 pages, the
  decision box back on page 2. To be confirmed on the next influenza A run.
- A code review for redundant code (2026-11-26) was taken up:
  - two bugs fixed: the workbook sheets "Findings" and "Specificity findings" were both named
    "Findings", and a carried-over oligo design did not record its source commit;
  - one rule for "closest site";
  - about 300 lines of dead code removed.

HSV-1, HSV-2 (2026-11-25/26) and influenza A (2026-11-26 15:21Z, report only:
[session](sessions/2026-11-27-01-needs-attention-cutoff.md)) have been rerun on the new code.
Influenza A on that run: the clinical organism list Exceeds limit (the ON845595.1 amplicon,
read as detected), background Review, near neighbours not searched, inclusivity No flags
(99.5% of 73,327 collected 2023-2026), coverage No flags; 25 pages. VZV and the older assays ran
on code from before the tiers review, so their specificity results need a rerun.

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
| HSV-1 (gG) | [2026-11-25 13:33Z](runs/hsv1-2026-11-25.md) | `max_amplicons: 1000`, `partner_scan_max_windows: 2000`: near neighbours Review (634 HSV-2 amplicons, none detected), the opposite-primer check complete; only gap left: human background cut at 2,000 sites; Exceeds limit on oligo QC only; sign-off 2 pages, record 19. Earlier that day 07:33Z: sign-off 2 A4 pages, record 22. Previous [2026-11-19 11:41Z](runs/hsv1-2026-11-19.md): near neighbours and release axis, Exceeds limit on oligo QC only; inclusivity No flags (96.0% of 223 genomes released 2023-2026); HSV-2 amplified, not detected (500 records, the cap, near-neighbour tier Incomplete); no product in the exclusivity list or human DNA (background Incomplete, 2,000-site cap) |
| HSV-2 (gD) | [2026-11-26 11:40Z](runs/hsv2-2026-11-26.md) | newest code, oligo design carried over: Review from off-target primer sites without an amplicon only (clinical list, human); near neighbours, inclusivity (100.0% of 181 released 2023-2026) and coverage No flags; 12 pages. Previous [2026-11-19 10:45Z](runs/hsv2-2026-11-19b.md): | near neighbours and release axis: Review, from off-target primer sites without a product only (*Listeria*, human); near neighbours No flags (HSV-1 probe sites only, not amplified); inclusivity No flags, 100.0% of 181 genomes released 2023-2026; oligo QC No flags. First run [09:19Z](runs/hsv2-2026-11-19.md): Incomplete |
| Influenza A (matrix) | [2026-11-18 08:15Z](runs/influenza-a-2026-11-18b.md) | v2.2.0 with the re-alignment fix: Exceeds limit, a 141 bp product on ON845595.1 read as detected (a record labelled influenza B whose M fragment is 95% identical to influenza A: most likely mislabelled); inclusivity No flags (99.5% of 72,698) |

# Next, waiting on the user

- VZV (ORF38): runs 2026-10-23 and 2026-11-17 ([latest](runs/vzv-2026-11-17.md)): 99.7% detectable, no
  off-target product. The probe's G form (Oka lineage, 10.5% of the records, the vaccine strain
  among them) folds into a hairpin: worth a wet-lab check on an Oka template. Since 2026-11-19
  `status_axis: release` (user, in the GUI; mirrored in the assay file: 109 records released
  2023-2026, 75 collected) and near neighbours named; not yet rerun.
- HSV-2 detection (gD): rerun 2026-11-26 on the newest code ([run](runs/hsv2-2026-11-26.md)):
  Review, from off-target primer sites without an amplicon only; every other row No flags. For
  the laboratory to review and sign.
- HSV-1 detection (gG, Ryncarz 1999 oligos): rerun on the newest code
  ([run](runs/hsv1-2026-11-25.md)), with `max_amplicons: 1000` and
  `partner_scan_max_windows: 2000`.
  - **Exceeds limit:** on primer Tm only.
  - **Near neighbours:** Review (634 HSV-2 amplicons, none detected).
  - **Inclusivity:** No flags.
  - **Only gap:** the human background, where two queries are cut at 2,000 sites. Raise
    `max_sites_per_query`, or accept the gap in the reviewer's decision.
  - **Still to check:** the forward primer's 2nd base (C in the paper, T in both reference
    genomes) against the laboratory's order sheet.

- Tiers review taken up in full (2026-11-20). Rerun HSV-1, HSV-2 and VZV on the new code (the
  NAS needs `git pull` and the GUI `scripts/build_gui.sh`). Expected for HSV-1: the 500 HSV-2
  products now get their probe re-aligned (own budget), but the near-neighbour tier stays
  Incomplete at the 500-product cap, as near neighbours are a cautious tier where a gapped probe
  site could bind unreported; raise `max_amplicons` for HSV-1, or take near neighbours out of
  `cautious_tiers`, if that is not wanted. The new `eukaryote_taxids` default 2759 is Eukaryota
  (confirmed by the user, 2026-11-20). Not built: an exhaustive analysis of a near
  neighbour's own records, specimen panels, taxonomy-derived near-neighbour suggestions.
- Report: the user's comments on the first HSV-1 record and the advisor's second review taken up
  (2026-11-20; [report](components/report.md)). The HSV-1 record of 16:52Z: 22 pages, nothing
  cut off, but a three-page sign-off. Since then specificity gaps are short lines, the site maps
  are in Part B and oligos are listed forward, probe, reverse
  ([decision](decisions/2026-11-20-sign-off-two-pages-amplicon-order.md)). Confirmed on the
  user's HSV-1 run of 2026-11-25: sign-off 2 pages, record 22
  ([run](runs/hsv1-2026-11-25.md)). The findings have since been condensed (no repeated list,
  specificity as one table per tier, shorter QC messages;
  [decision](decisions/2026-11-25-findings-condensed.md)). The user's run of 08:21Z confirmed
  19 pages, with a 2-page sign-off. Three small faults found in it are fixed (the closest site
  can now only be a site at warning or critical level, no repeated information lines, words
  instead of raw labels), confirmed by the user's run of 09:18Z. HSV-2 and VZV are not yet
  rerun on this code. The third report review is built, except M3
  ([decision](decisions/2026-11-25-report-round3-built.md)): rerun HSV-1 to see the figures and
  count its pages. First record with them (2026-11-25 17:00Z): 15 pages. The figures were then
  made larger at the user's request (2026-11-26), and the map now places each organism at its
  highest-level site. Since 2026-11-26 a run can carry the oligo design over from an earlier
  record (`--skip-oligo-design`; GUI option "Evaluate oligo design";
  [decision](decisions/2026-11-26-oligo-design-carried-over.md)).
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
