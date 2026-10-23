---
type: Assay
title: Influenza A, matrix gene (Erasmus MC Viroscience protocol)
description: "One forward primer, two reverse primers and two linear FAM/BHQ1 probes in segment 7; the second reverse primer covers the 3'-terminal escape the runs found."
resource: ../../examples/influenza_a_matrix.yaml
tags: [assay, example, RNA, virus]
status: stable
verified: { by: human:zmeel, at: 2026-10-07T08:00:00Z }
generated: { by: claude-code/agent, at: 2026-10-08T07:26:00Z }
sources:
  - id: assay-file
    resource: ../../examples/influenza_a_matrix.yaml
    title: docs/examples/influenza_a_matrix.yaml (provenance and checks in its header)
  - id: session
    resource: ../sessions/2026-10-07-02-influenza-a-assay.md
    title: "Session 2026-10-07: Influenza A assay file"
  - id: run
    resource: ../runs/influenza-a-2026-10-07.md
    title: "Influenza A (matrix), 2026-10-07 (13:08Z)"
  - id: complete
    resource: ../runs/influenza-a-2026-10-07-complete.md
    title: "Influenza A (matrix), 2026-10-07 (17:35Z, complete)"
  - id: protocol
    resource: "Protocol for Influenza RT-PCR, Viroscience Erasmus MC (R. Molenkamp), last update 02-02-2026 (supplied by the user 2026-10-16; distribution restricted)"
    title: Erasmus MC Viroscience influenza RT-PCR protocol
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: taxonomy
    resource: "live ESearch and EFetch against NCBI Taxonomy and Nucleotide, 2026-10-07"
    title: NCBI counts and taxonomy IDs measured live, 2026-10-07
stale_after: 2027-04-07T00:00:00Z
---

# Provenance

The five oligos are those of the Erasmus MC Viroscience influenza RT-PCR protocol (R. Molenkamp,
last update 02-02-2026), which the user supplied on 2026-10-16, with its own names, dyes
(FAM-BHQ1 on both probes) and cycling (60 C, 45 cycles).[^protocol] It confirms every sequence
the file already held and adds one.

**That protocol restricts distribution**: it may be used by microbiological and virological
laboratories in the Netherlands, and distribution outside that network or publication in any
form needs the author's permission. So the author was asked, and on 2026-10-20 the user reported
that R. Molenkamp gave permission; the sequences went into the public repository on that basis
and not before, and the file records the same.[^assay-file] What is published is the five oligos,
their names and the reaction conditions - not the protocol itself. The wording and the form of
the permission are held by the laboratory; this is the user's report of it.

How it got here: on 2026-10-07 the user passed on four of the oligos from another laboratory, as
`FfluA` / `RfluA` / `PfluA1-tq-NED` / `PfluA2-tq-NED`, with the reverse primer two bases short.
That was found from the data and replaced by the user's own 24-mer; the protocol now confirms it,
so the 22-mer was a transcription error.

# Design

| Role | Oligo | Position in the 141-nt reference |
|---|---|---|
| forward | infa_fwd (23 nt, R at 6) | 1-23, exact |
| probe | infa_probe1 (22 nt, FAM, BHQ1) | 43-64, same strand, exact |
| probe | infa_probe2 (22 nt, FAM, BHQ1) | 43-64, one mismatch at 21 of 22 (2 nt from its 3' end) |
| reverse | infa_rev (24 nt, Y at 16) | binds 118-141, exact |
| reverse | infa_rev2 (24 nt, Y at 16) | binds 118-141, one mismatch at its 3'-terminal base |

Product 141 bp (the whole reference, no flanking bases), GC 49.6%. Both probes sit on one NED
channel; both are linear (no MGB, LNA or other Tm-raising modification), so the
unmodified-probe ladder of R9 applies to them.[^r9] Target influenza A virus (11320); template
RNA.

# The second reverse primer answers the sweep

`infa_rev2` differs from `infa_rev` only in its 3'-terminal base, G to T - exactly the escape the
[complete run](../runs/influenza-a-2026-10-07-complete.md) was built around. That 3'-terminal
G-A mismatch, R1 "avoid", accounted for 7,989 of the 8,186 records in "Needs attention" (97.0%)
and 11.8% of all reverse sites, and its share rose from 0.2-0.7% of samples collected up to 2021
to 6.9% of 2022 and 40.5% of 2023.[^complete] So the protocol's extra primer is the answer to
that sweep: a template carrying the variant has a perfectly matched primer again.

A rerun should show it. A copy is judged by the best-binding oligo of each role, so the escapes
that were likely failure on `infa_rev` alone become detectable on `infa_rev2`. The figures of the
earlier runs - 69.0% detectable, 30.6% likely failure of the records collected 2023-2026 -
describe the one-primer assay and are not this one's.

# The reverse primer arrived two bases short

As received, RfluA was the 22-mer `TCTTCTTTAGCCAYTCCATGAG`. Against the supplied reference its
site read two mismatches at the primer's 5' end while the reference ran on for 2 more bases:

```
reference 118-141     CTCATGGAATGGCTAAAGACAAGA
RfluA (22 nt), rev.   CTCATGGAARTGGCTAAAGAAGA-
```

The reference is in frame for M1 there (`CTA AAG ACA AGA` = Leu-Lys-Thr-Arg), so the primer was
out of register, not the reference; inserting `GT` after its leading `TCTT` restores it. That was
arithmetic on two sequences, so nothing was changed at the time and the user was asked to check
the order sheet.

The [run of 13:08Z](../runs/influenza-a-2026-10-07.md) then showed the same thing in the data:
all 23 reverse site variants, over all 14,960 assessed records (100%), carried the 2-base
difference, so not one record in 15,000 matched the primer perfectly.[^run] Two records the user
downloaded settled it live: the 22-mer gives 3 mismatches in both, the 24-mer 1, and the one left
is strain variation at a different position in each.

The user then gave their own laboratory's primer for the same influenza A PCR -
`TCTTGTCTTTAGCCAYTCCATGAG` - and the file carries that. It is the laboratory's sequence, not an
inferred one.

# Exclusivity panel

The user asked for influenza B only and, on advice, agreed to widen it the same day. The reason
is partly mechanical: an assay's own `exclusivity_organisms` **replaces** the packaged clinical
organism list (`organisms.source: assay` falls back to the global list only for an assay that
defines none), so a one-name list would have made this tier narrower than the default. The panel
is now 17 taxa:

| Group | Taxa |
|---|---|
| Orthomyxoviridae, nearest neighbours | influenza B (11520, both lineages), C (11552), D (1511084) |
| Respiratory differential | RSV (11250), hMPV (162145), Human respirovirus 1 (12730) and 3 (11216), Human orthorubulavirus 2 (2560525), SARS-CoV-2 (2697049), HCoV 229E (11137), OC43 (31631), NL63 (277944), HKU1 (290028), Rhinovirus A (147711), Enterovirus (12059), Mastadenovirus (10509), Human bocavirus 1 (689403) |

Influenza C and D are the nearest taxa outside the target and each has its own M gene, which is
the conserved segment these primers sit in. The respiratory differential is there for what the
tier is for: showing no product in the other organisms the sample contains. Every name resolves
to exactly one taxon by scientific name (checked live, 2026-10-07); parainfluenza 1-3 and
rhinovirus A are written with their current names, because the older spellings resolve only
through the `[All Names]` synonym fallback.[^taxonomy]

Nothing **inside** influenza A is excluded: avian and swine strains sit under 11320 and detecting
them is the point of an M-gene target.

# Variant source

`blast_partitioned`, narrowed to `980:1100[SLEN] AND segment 7[TITL]`. Influenza A is segmented,
so each strain's M segment is its own Nucleotide record; there is no assembly to walk. Measured
live on 2026-10-07: 1,676,357 Nucleotide records for taxid 11320, of which 172,768 match that
query.[^taxonomy] That is far beyond one run, so the analysis works newest publication year
first in batches of `blast_max_records_per_run` (5,000 here) and is resumed by running again; a
report written before the listing is exhausted says so.

Taxonomy verified the same day: 11320 "Influenza A virus" is a no-rank node under the species
Alphainfluenzavirus influenzae (2955291), so it covers every subtype and strain below it; 11520
is "Influenza B virus".[^taxonomy]

# Oligo QC (`run --qc-only`, no network)

**Review** with the five oligos of the protocol: 0 outside the limit, 8 outside the preferred
range - `infa_fwd` Tm 66.4 C, `infa_rev2` GC 37.5%, the primers 3.9 C apart in Tm, `infa_probe2`
4.6 C above the mean primer Tm, a run of 5 identical bases in each probe, and the designed single
mismatch of `infa_rev2` and `infa_probe2` against the reference, which is the point of those two
oligos rather than a defect. Under the 22-mer this was Exceeds limit: the primers were 6.2 C
apart, over the limit, because every reverse Tm was about 5.5 C low.

# Runs

[2026-10-21 15:42Z](../runs/influenza-a-2026-10-21.md), the latest, the first with `infa_rev2`:
complete, **99.6% detectable** of the 70,606 records collected 2023-2026, likely failure 0.0%,
Review with no limit crossed; `infa_rev2` is the only working reverse primer for 23,595 records
(13.6%).
[2026-10-07 17:35Z](../runs/influenza-a-2026-10-07-complete.md), the first complete one, with
`infa_rev` alone: all 172,768 records assessed, 69.0% detectable of the 69,688 collected 2023-2026,
Exceeds limit on the whole population. One reverse-primer 3'-terminal G-A mismatch is 97.0% of
the failures, and the per-year tables date its sweep: 0.7% of 2021 collections, 6.9% of 2022,
40.5% of 2023.
[16:14Z](../runs/influenza-a-2026-10-07-16h.md) was the state at 45,000 records (76.9%).
[14:01Z](../runs/influenza-a-2026-10-07-corrected.md) was the first with the corrected primer
(83.6% of 17,058), and [13:08Z](../runs/influenza-a-2026-10-07.md) the only one with the 22-mer,
so its figures describe that primer and not this assay.

[^assay-file]: docs/examples/influenza_a_matrix.yaml (provenance and checks in its header)
[^session]: "Session 2026-10-07: Influenza A assay file"
[^r9]: R9 - probe mismatches
[^taxonomy]: NCBI counts and taxonomy IDs measured live, 2026-10-07
