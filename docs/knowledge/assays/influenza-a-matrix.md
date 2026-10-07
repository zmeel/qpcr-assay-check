---
type: Assay
title: Influenza A, matrix gene (two NED probes)
description: One primer pair and two alternative linear NED/BHQ1 probes in segment 7; added as supplied, with a 2-base discrepancy between the reverse primer and the reference sequence left in place.
resource: ../../examples/influenza_a_matrix.yaml
tags: [assay, example, RNA, virus]
status: draft
generated: { by: claude-code/agent, at: 2026-10-07T14:00:00Z }
sources:
  - id: assay-file
    resource: ../../examples/influenza_a_matrix.yaml
    title: docs/examples/influenza_a_matrix.yaml (provenance and checks in its header)
  - id: session
    resource: ../sessions/2026-10-07-02-influenza-a-assay.md
    title: "Session 2026-10-07: Influenza A assay file"
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: taxonomy
    resource: "live ESearch and EFetch against NCBI Taxonomy and Nucleotide, 2026-10-07"
    title: NCBI counts and taxonomy IDs measured live, 2026-10-07
stale_after: 2027-04-07T00:00:00Z
---

# Provenance

Oligos, the 141-nt reference sequence and the exclusion (influenza B) supplied by the user on
2026-10-07; not checked against a publication or kit insert. Oligo names are the user's. The
sequences are in the file exactly as given, including the discrepancy below.[^assay-file]

# Design

| Role | Oligo | Position in the 141-nt reference |
|---|---|---|
| forward | FfluA (23 nt, R at 6) | 1-23, exact |
| probe | PfluA1-tq-NED (22 nt, NED, BHQ1) | 43-64, same strand, exact |
| probe | PfluA2-tq-NED (22 nt, NED, BHQ1) | 43-64, one mismatch 3 nt from its 3' end |
| reverse | RfluA (22 nt, Y at 14) | binds 118-139, **2 mismatches** |

Product 139 bp, GC 49.6%, with 2 nt of the reference left over at the 3' end. Both probes sit on
one NED channel; both are linear (no MGB, LNA or other Tm-raising modification), so the
unmodified-probe ladder of R9 applies to them.[^r9] Target influenza A virus (11320); template
RNA.

# The reverse primer does not fit the reference

The supplied reference reads `...CTCATGGAATGGCTAAAGACAAGA` and the reverse primer, reversed,
reads `CTCATGGAARTGGCTAAAGAAGA`: two mismatches at the primer's 5' end, and the reference runs on
for 2 more bases. The reference is in frame for M1 (`CTA AAG ACA AGA` = Leu-Lys-Thr-Arg); the
primer is 2 bases short of covering it. Inserting `GT` after the primer's leading `TCTT`
(`TCTTCTTTAGCC...` to `TCTTGTCTTTAGCC...`) makes the primer match the reference over its whole
length with no mismatch and no gap. That is arithmetic on the two supplied sequences, not a
sequence from any source, and nothing was changed: the primer stands as supplied, so a run will
report a 2-base discrepancy at the 5' end of RfluA on essentially every record. **The user has
been asked to check the primer against the laboratory's order sheet.** Until then a report of
this file says more about the transcription than about the assay.

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

Exceeds limit, from the oligos as supplied: FfluA Tm 66.4 C above the preferred range, the
primers 6.2 C apart in Tm, a run of 5 identical bases in each probe, plus the two site warnings
above. Not run against NCBI yet.

# Runs

None yet.

[^assay-file]: docs/examples/influenza_a_matrix.yaml (provenance and checks in its header)
[^session]: "Session 2026-10-07: Influenza A assay file"
[^r9]: R9 - probe mismatches
[^taxonomy]: NCBI counts and taxonomy IDs measured live, 2026-10-07
