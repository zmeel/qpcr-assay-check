---
type: Assay
title: VZV, ORF38
description: One primer pair and a 26-nt probe with one degenerate base in ORF38 (tegument protein UL21), 82 bp; oligos supplied without a publication. The probe's G form, matching the Oka lineage, folds into a hairpin (Tm 73.6 C).
resource: ../../examples/vzv_orf38.yaml
tags: [assay, example, DNA, virus]
status: draft
generated: { by: claude-code/agent, at: 2026-10-23T12:30:00Z }
sources:
  - id: assay-file
    resource: ../../examples/vzv_orf38.yaml
    title: docs/examples/vzv_orf38.yaml (provenance and checks in its header)
  - id: ncbi
    resource: "live ESearch, ESummary and EFetch against NCBI Taxonomy and Nucleotide, 2026-10-23: NC_001348, AB097932, AB097933"
    title: Taxonomy, record counts, and the Dumas and Oka genomes, measured live
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: session
    resource: ../sessions/2026-10-23-01-hsv1-assay.md
    title: "Session 2026-10-23: HSV-1 assay file"
stale_after: 2027-04-23T00:00:00Z
---

# Provenance

Oligos supplied by the user on 2026-10-23 without a publication, so they are in the file as given
and not checked against one. No reporter or quencher was given; none is set. The names VZV-F,
VZV-R and VZV-P were chosen here. The exclusivity panel was suggested in the session and is the
user's to edit.[^assay-file]

# Design

The reference is VZV strain Dumas exactly, NC_001348:69313-69394, in ORF38 (tegument protein
UL21).[^ncbi] The user's first reference stopped one base short of the reverse primer's 5' end;
the corrected 82-nt one is the whole product. All three oligos are exact against it.

The probe's one degenerate base, R, reads A in Dumas and G in both Oka strains (the vaccine vOka
and its parent pOka): it covers both main lineages and does not tell vaccine from wild type.

The probe is taken as linear (26 nt, no modification declared), so R9's unmodified-probe ladder
applies.[^r9]

# Oligo QC (`run --qc-only`, no network)

**Exceeds limit**, on one structure: the probe's G form folds into a hairpin (CCGCA pairs with
TGCGG around the loop ACAAC), predicted Tm 73.6 C at a 60 C annealing temperature; the A form does
not. The form that matches the Oka lineage, the vaccine strain included, is therefore the one that
may bind less well: a wet-lab check on an Oka template would settle it. Outside the preferred
range only: a 17-nt forward primer at 64.7% GC with a run of six C, the reverse primer at 37.0%
GC, and a probe only 1-3 C above the primers in Tm.

# Taxonomy and the variant source

Target: the species *Varicellovirus humanalpha3* (3050294), 2,832 Nucleotide records, 52 more than
the node "Human alphaherpesvirus 3" (10335). All of them in one run, scanned directly; most short
records hold other genes and count as not found.[^ncbi]

# Exclusivity panel

Twenty-four organisms in five groups, each name resolved live to exactly one taxon: simian
varicella virus, HSV-1, HSV-2 and B virus; the other human herpesviruses; the rash differential
(mpox, smallpox, molluscum, *S. aureus*, *S. pyogenes*, *T. pallidum*, *C. albicans*); the CSF
DNA-template differential; and adenovirus D and *Acanthamoeba* for the eye. Enteroviruses are left
out: RNA templates of a DNA assay.

# Runs

None yet.

[^assay-file]: docs/examples/vzv_orf38.yaml (provenance and checks in its header)
[^ncbi]: Taxonomy, record counts, and the Dumas and Oka genomes, measured live
[^r9]: R9 - probe mismatches
[^session]: "Session 2026-10-23: HSV-1 assay file"
