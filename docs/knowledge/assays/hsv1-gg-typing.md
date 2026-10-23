---
type: Assay
title: HSV-1 detection, glycoprotein G (Ryncarz 1999 typing oligos)
description: The laboratory's HSV-1 detection assay of about 20 years, built from the paper's typing oligos - type-common primers in gG (US4) with the HSV-1-specific probe, 166 bp; checked against the paper's PDF. It detects HSV-1 only - HSV-2 gives a product without a signal. The inosine in the reverse primer is written N.
resource: ../../examples/hsv1_gg_typing.yaml
tags: [assay, example, DNA, virus]
status: draft
generated: { by: claude-code/agent, at: 2026-10-23T08:00:00Z }
sources:
  - id: assay-file
    resource: ../../examples/hsv1_gg_typing.yaml
    title: docs/examples/hsv1_gg_typing.yaml (provenance and checks in its header)
  - id: ryncarz
    resource: "Ryncarz AJ, Goddard J, Wald A, Huang ML, Roizman B, Corey L. J Clin Microbiol 1999; 37: 1941-1947, doi 10.1128/JCM.37.6.1941-1947.1999"
    title: Ryncarz et al. 1999, the HSV detection and typing assays
  - id: ncbi
    resource: "live ESearch, ESummary and EFetch against NCBI Taxonomy and Nucleotide, 2026-10-23"
    title: Taxonomy, record counts, NC_001806 and NC_001798, measured live
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: session
    resource: ../sessions/2026-10-23-01-hsv1-assay.md
    title: "Session 2026-10-23: HSV-1 assay file"
stale_after: 2027-04-23T00:00:00Z
---

# Provenance

Oligos supplied by the user on 2026-10-23 with the publication, Ryncarz et al. 1999, and then
its PDF.[^ryncarz] The sequences were checked against the paper (page 1942) and are identical to
its HSV typing set in glycoprotein G: primers HSV-1 gG1-FP and gG1-RP and the HSV-1 probe
gG1-P. Two differences, both kept on purpose: the user's laboratory labels the probe FAM where
the paper uses HEX, and the paper's deoxyinosine is written N, because the tool accepts IUPAC
codes only.[^assay-file]

In the laboratory these oligos are the **HSV-1 detection assay**, run for about 20 years. They
came from another laboratory, which took them from this paper; why it chose the paper's typing
oligos and not its type-common *detection* assay (a different one, in glycoprotein B) is not
known. The paper designed the gG primers for typing, with one probe per type in the same
reaction; used with the HSV-1 probe alone they make an HSV-1 detection assay. The "HSV-1 gG1"
names are the paper's, which gives them to the type-common primers too.

# What it detects

HSV-1 only. HSV-2 is amplified by the same primers but gives no signal, because the probe has
10 mismatches against it. So an HSV-2 infection is negative in this PCR, which is right for an
HSV-1 assay and wrong for one meant to detect HSV in general. In an HSV-1/HSV-2 co-infection the
HSV-2 product also competes for the primers.

# Design

The 166-nt reference supplied is HSV-1 strain 17 exactly (NC_001806:137281-137446), inside US4,
"envelope glycoprotein G".[^ncbi] Against it the reverse primer and the probe are exact, the probe
on the antisense strand; the forward primer has one mismatch, at its 2nd base from the 5' end.

The design shows against HSV-2 HG52 (NC_001798), where the amplicon is also 166 nt but 47
positions differ: the primers bind HSV-2 as well as HSV-1, each degenerate base sitting exactly on
a type difference, while the probe has 10 mismatches in 25 nt. So the primers are type-common and
the discrimination is the probe's alone. HSV-2 is expected to give a product without a signal,
which makes it the exclusivity organism that tests the assay.

The probe is linear (FAM/TAMRA), so the unmodified-probe ladder of R9 applies.[^r9]

# The forward primer's second base

The paper prints the forward primer as TCC..., and both reference genomes read TTC there. The
mismatch is in the published primer, 21 nt from its 3' end, so every genome is expected to grade
the forward primer "tolerated" rather than "perfect". That is the oligo, not the strains. Worth
checking against the laboratory's order sheet.

# The inosine

Written N: it matches every base, so it never counts as a mismatch, which is close to how
inosine behaves. Tm and ΔTm cost it as a full Watson-Crick pair (the best of the four bases), so
they come out somewhat optimistic for the reverse primer. The position is 18 nt from the 3' end,
outside every window the grading rules count, so the classes do not depend on it. Real inosine
in the model would be a code change; not built.

# Taxonomy and the variant source

The target is the species *Simplexvirus humanalpha1* (3050292) rather than the no-rank node
"Human alphaherpesvirus 1" (10298) below it: the species holds 10,871 Nucleotide records, 7 more
than the node. The variant analysis takes the genome-sized records (100-200 kb): 618 on
2026-10-23, one run, scanned directly without BLAST. The ~10,000 shorter records, mostly other
genes, are left out by that filter.[^ncbi]

# Exclusivity panel

Twenty-five organisms in five groups, each name resolved live to exactly one taxon:[^ncbi]
HSV-2 and the macaque B virus (amplified by the type-common primers); the other seven human
herpesviruses; the differential of mucocutaneous and genital lesions (mpox, molluscum,
*T. pallidum*, *P. ducreyi*, *C. trachomatis*, *N. gonorrhoeae*, *M. genitalium*,
*T. vaginalis*, *C. albicans*); the DNA-template differential of meningitis and encephalitis;
and adenovirus D and *Acanthamoeba* for the eye. Enteroviruses are left out on purpose: RNA
viruses cannot be templates of a DNA assay without RT, and the genus would add 149,419 records to
the search. The panel is the user's to change.

# Oligo QC (`run --qc-only`, no network)

**Exceeds limit**, on primer Tm alone: 70.2 C forward and 70.5 C reverse (68-73 C over the
degenerate forms), just above the 70 C limit. The primers are 63.6% GC, the forward one has 4 G/C
in its last 5 nt, and both form hairpins near the 58 C annealing temperature; the amplicon is
166 bp. All of it is the published 1999 design, which the paper ran at 58 C, so nothing was
changed. The forward-primer mismatch to the reference is the second base above.

# Runs

[2026-10-23 09:04Z](../runs/hsv1-2026-10-23.md), the first: HSV-2 amplified but not detected,
no other exclusivity product; 96.1% of 614 genomes detectable, 0% likely failure; inclusivity
Incomplete for want of dated recent genomes (26 collected 2023-2026).

[^assay-file]: docs/examples/hsv1_gg_typing.yaml (provenance and checks in its header)
[^ryncarz]: Ryncarz et al. 1999, the HSV detection and typing assays
[^ncbi]: Taxonomy, record counts, NC_001806 and NC_001798, measured live
[^r9]: R9 - probe mismatches
[^session]: "Session 2026-10-23: HSV-1 assay file"
