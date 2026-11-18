---
type: Session
title: "Whole-project code review: seven fixes"
description: "Session log of 2026-11-17."
tags: [session]
session_date: 2026-11-17
session_label: "2026-11-17"
generated: { by: claude-code/agent, at: 2026-11-17T12:00:00Z }
---

# 2026-11-17: code review of the whole project, seven fixes

- Correction: the HSV-1 run and assay pages said the status was judged on genomes collected
  2023-2026; the report says 2020-2023 ([run](../runs/hsv1-2026-10-23.md)).
- The code review of `src/`, `scripts/` and `tests/` found seven defects; the user asked to fix
  all seven ("fix 1-7"):
  1. A RID NCBI called UNKNOWN was resubmitted with no limit and no deadline; UNKNOWN is also
     what a status page without a status reads as, so a persistent error page meant a new search
     every minute. Now one resubmission per run, then an error
     ([etiquette](../ncbi/etiquette.md)).
  2. Each degenerate variant of a primer is a query of its own, so one off-target product was
     counted once per pair of variants (up to 64 times with the HSV-1 primers) and filled
     `max_amplicons` and the partner-scan windows. The variants at one site are now one site
     ([specificity](../components/specificity.md)).
  3. `variants.nucleotide_query` is not in the variant store key, and completeness compared counts:
     a narrowed query (as the VZV file suggests) reused the full store and read as complete;
     withdrawn records stayed in the figures. The figures now count the stored records listed in
     this run, and the report says how many were left out
     ([exhaustive analysis](../components/exhaustive-analysis.md)). The store key is unchanged on
     purpose: adding the query would have forced a full rescan of every stored assay, influenza A
     with 173,689 records among them.
  4. In an MGB probe an ambiguity code at -6 or -7 read as a match although one mismatch there is
     likely failure; R6 now grades a code anywhere in an MGB probe both ways
     ([R6](../rules/r6-ambiguity-codes.md), back to draft).
  5. A failed window fetch around a BLAST hit stored the record as "not found" for good; it is now
     left for the next run and counts as unavailable after two failed runs.
  6. Every run summarised every listed record again (ESummary); UID lookups are now kept beside
     the store.
  7. The status window ended at the last year with data, not at the current year as the rule and
     the report say ([inclusivity status](../rules/inclusivity-status.md)). A target no longer
     sequenced now reads Incomplete for want of recent genomes. Window spans in the report now
     name the whole window (e.g. 2023-2026) rather than the years that had data.
- A candidate finding was dropped on checking: N bases in re-aligned partial hits are already
  measured as mismatches.
- The advisor's whole-project evaluation stopped twice on the usage limit and then because the
  model asked for needs usage credits. Restarted on another model at the user's request, it
  reported ten problems ([review](../../reviews/2026-11-17-whole-project-advisor.md), kept
  verbatim). The user asked to fix P1, P2, P4 and P5: every record names its code (a fingerprint
  of the package and the git commit); an unsearched configured tier or an unresolved organism
  name never reads as No flags; R6 grades codes over a primer's 16 nt and the whole probe; MGB
  is recognised from the dye names, LNA probes are said to be graded as unmodified. Not done:
  P3 (off-target rules), P6-P10, the stale texts.
- A rules review on another model was asked for, then called off by the user.
- The VZV run of 2026-10-23 recorded ([run](../runs/vzv-2026-10-23.md)): 99.7% detectable, no
  off-target product, Exceeds limit on the probe's G-form hairpin only. The HSV-1 report the
  user uploaded again is the run already recorded.
- Then the remaining review problems (user: "fix the remaining issue brought up by the
  advisor"): P3 off-target sites graded by R1-R9 together with the levels (a primer site graded
  likely failure never primes, one graded perfect or tolerated always does; detection, not
  priming, gives Exceeds limit); P6 possible deletions counted as likely failure and a cap on
  unavailable records; P7 core_nt in the limitations; P8 the window ends at the run's year; P9
  RNA reverse-primer-only failures named; P10 2 + 2 pairs flagged. The specificity rule page is
  back to draft (its rule changed). Stale statements corrected; the HSV-1 run page marked as made
  before these fixes. A first version of P3 let a run of N, and a distant site with 6 mismatches
  and a gap, prime; both caught by tests and fixed before the push.
- The user's VZV rerun on the new code stopped with "zip() argument 2 is longer than argument
  1": a worst-case site from a gapped partial BLAST hit had strings of different length, which
  the P3 grading did not expect. Fixed: the strings line up, worst-case sites keep the level rule,
  and an unequal pair is graded by level instead of stopping the run.
- The VZV rerun on the fixed code (14:31Z) recorded ([run](../runs/vzv-2026-11-17.md)): coverage
  complete, the same figures, the window now 2023-2026 (75 records collected, Incomplete).
- Code identity for GUI runs and other laboratories (user: "build both"): `scripts/build_gui.sh`
  builds the GUI image with the commit (Docker build arguments), so GUI records name it; and
  `qpcr-assay-check fingerprint` prints the installed code's fingerprint, which each release
  entry in CHANGELOG.md will list from v2.2.0 on, so another laboratory can confirm it runs a
  release unchanged. The image build itself was not tested here (no Docker daemon).
- Release v2.2.0 prepared (user: "Make the release V2.2.0"): version 2.2.0, the Unreleased
  CHANGELOG entries merged into one 2.2.0 entry (Added, Changed, Fixed) with a summary and the
  code fingerprint `b68fa8fe...e44455`, the same as the NAS image built from commit 6085892. The
  user sets and pushes the annotated tag.
- 2026-11-18: the HSV-1 rerun on v2.2.0 recorded ([run](../runs/hsv1-2026-11-17.md)). At the
  user's request the HSV-1 assay file sets `inclusivity.status_axis: release` (it overrides the
  NAS configuration's collection axis), and the report's sentence on predicted products names
  the graded rule instead of "at least warning level".
- 2026-11-18, licence: the user asked to have the options explained (free for science, paid for
  commercial use: PolyForm Noncommercial, a custom academic licence, AGPL plus a commercial
  licence; versions already published stay Apache-2.0; primer3-py is GPL-2.0-or-later, which
  conflicts with a noncommercial licence for a distributed image) and then decided to keep
  Apache-2.0. CLAUDE.md and the open item updated.
- 2026-11-18: the influenza A rerun on v2.2.0 ([run](../runs/influenza-a-2026-11-18.md)) showed
  the first No-flags inclusivity for that assay, and uncovered a blind spot the P3 change had
  left: a partial BLAST hit that could only stay "minor" by the mismatch counts was never
  fetched and re-aligned, so it never got a class and could not prime. On the influenza B record
  ON845595.1 (forward primer perfect, `infa_rev` one mismatch at -3, tolerated under R1) that hid
  a plausible product. `worth_realigning` (renamed from `can_reach_warning`) now rules a hit out
  only by the mismatch bound when the classes decide; the validation script and its tests follow.
