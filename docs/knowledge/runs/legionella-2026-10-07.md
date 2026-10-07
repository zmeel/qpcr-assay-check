---
type: Run
title: Legionella, 2026-10-07 (09:48Z)
description: First Legionella run with the new R9 probe ladder; the headline does not move, the LEGpneu rows now read likely failure, and the bracketing bulge figure is wrong.
tags: [run, legionella]
status: draft
stale_after: 2027-01-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-07T15:00:00Z }
sources:
  - id: report
    resource: the user's report of run 2026-10-07T09:48:31Z (uploaded in the session of 2026-10-07, not in the repository)
    title: Report of the 09:48Z run
  - id: assay
    resource: ../assays/legionella-genus-pneumophila.md
    title: Legionella genus + L. pneumophila
  - id: previous
    resource: legionella-2026-10-02.md
    title: "Legionella, 2026-10-02"
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: bug
    resource: ../open/bulge-alternative-from-parts.md
    title: The bracketing bulge figure drops the from-parts genomes
  - id: session
    resource: ../sessions/2026-10-07-02-influenza-a-assay.md
    title: "Session 2026-10-07: Influenza A assay file"
---

# Run

[Assay](../assays/legionella-genus-pneumophila.md), qpcr-assay-check v2.1.0, status axis
`collection`; the first Legionella run with the probe-rule change of the same day.[^report]

# Key numbers

**Incomplete**: 2 of 8 checks flagged, 5 with evidence incomplete or not assessed.

- **Whole fragment, collected 2023-2026**: 1,690 genomes judged, **94.0% detectable**, 94.1%
  including at risk, 5.9% likely failure; 1,443 undetermined and not counted (1 possibly
  unassembled, 1,441 with the region cut or hidden by N). Incomplete because 46.1% of the
  genomes with the region are undetermined, over the 25% limit. 8 distinct site patterns, 50.0%
  of them detectable (information).
- **Per channel**: Legionella genus (VIC) 97.1% detected (7,062 of 7,270), 4,396 undetermined,
  286 drafts without the region; L. pneumophila (FAM) 99.7% (6,881 of 6,903), 4,135
  undetermined, 157 drafts, and signal in 2 of 757 non-pneumophila genomes. Both Incomplete on
  the undetermined share (37.7% and 37.5%).
- **Coverage**: all 11,952 assemblies NCBI listed that day were assessed; region found in 7,362,
  not found in 261, hidden by N in 7, cut by a contig end in 4,297, only related regions in 25.
  No flags.
- **Release years, all shown**: 11,051 with the region, 97.5% detectable, 0.1% at risk, 2.3%
  likely failure, 4,362 undetermined.
- **Oligo QC**: 0 outside the limit, 4 outside the preferred range (LEGgenus Tm 5.5 C below the
  mean primer Tm; LEGgenus Tm unreliable because of MGB; LEGpneu 35 nt; amplicon 260 bp); 0 of
  22 hairpins and dimers flagged.
- **Specificity**: clinical organism list 3/3 names resolved, no predicted product, 85 critical
  primer sites but none facing each other; background Incomplete (LEGgenus had 5,011 relevant
  alignments and only the 2,000 strongest were assessed, `max_sites_per_query`); near
  neighbours not searched in this run.

# What the probe-rule change did

Nothing to the headline, as expected: `at risk` and `likely failure` both count as not
detectable, so the detectability boundary did not move.[^r9] Against the
[13:16Z run of 2026-10-02](legionella-2026-10-02.md) the window went from 93.9% of 1,669 to
94.0% of 1,690 and undetermined stayed at 46.1%; the assemblies listed grew from 11,174 to
11,952, which accounts for the difference.[^previous]

What did change is the class on the rows. The row the user questioned - 7 *Legionella micdadei*
genomes, GCF_000953635.1, the unmodified 35-nt LEGpneu probe with 11 mismatches and 2 gaps -
now reads **likely failure**, with the note "11 mismatches in an unmodified probe: no stable
probe duplex expected from 3 mismatches on; expert judgement, no quantitative source (user
decision 2026-10-07; Klungthong 2010 measured two, still detected)". Every LEGpneu entry in
"Needs attention" (104 combinations) is now likely failure. Five rows still read `at risk`
overall: there LEGgenus is perfect or indeterminate and the reverse primer carries the at-risk
site, so the row is not decided by the probe.

R5c never appears in this report: every probe deletion here sits at a probe end (counted as a
mismatch) or accompanies three or more mismatches, so R9 decides first and the new scope flags
have nothing to mark.

# A figure in this report is wrong

The summary reads "44.7% if single-base run-length differences were tolerated" against 94.0%
with them not tolerated. Tolerating more cannot lower detectability over a fixed cohort, and it
does not: the bracketing figure dropped every genome judged from parts (2,928 in this run).
Fixed the same day;[^bug] this report still carries the understated figure, and nothing else in
it is affected - the headline, the per-year table, the channel figures and every class were
computed on the configured rule and stand.

[^report]: Report of the 09:48Z run
[^previous]: "Legionella, 2026-10-02"
[^r9]: R9 - probe mismatches
[^bug]: The bracketing bulge figure drops the from-parts genomes
[^session]: "Session 2026-10-07: Influenza A assay file"
