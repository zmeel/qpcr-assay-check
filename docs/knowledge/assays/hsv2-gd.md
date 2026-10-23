---
type: Assay
title: HSV-2 detection, glycoprotein D
description: The laboratory's HSV-2 PCR, companion of its HSV-1 assay - one primer pair and a FAM/TAMRA probe in gD (US6), 71 bp; source unknown. All three oligos are type-specific (5, 4 and 3 mismatches against HSV-1). Oligo QC without a single flag.
resource: ../../examples/hsv2_gd.yaml
tags: [assay, example, DNA, virus]
status: draft
generated: { by: claude-code/agent, at: 2026-10-23T13:10:00Z }
sources:
  - id: assay-file
    resource: ../../examples/hsv2_gd.yaml
    title: docs/examples/hsv2_gd.yaml (provenance and checks in its header)
  - id: ncbi
    resource: "live EFetch and ESearch against NCBI Nucleotide, 2026-10-23: NC_001798 (HSV-2 HG52), NC_001806 (HSV-1 strain 17)"
    title: The HSV-2 and HSV-1 reference genomes and record counts, measured live
  - id: hsv1
    resource: hsv1-gg-typing.md
    title: HSV-1 detection, glycoprotein G (Ryncarz 1999 typing oligos)
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: session
    resource: ../sessions/2026-10-23-01-hsv1-assay.md
    title: "Session 2026-10-23: HSV-1 assay file"
stale_after: 2027-04-23T00:00:00Z
---

# Provenance

The laboratory's HSV-2 PCR, supplied by the user on 2026-10-23 with FAM-TAMRA and annealing at
60 C (the ABI 7500's default program); the source of the oligos is not known, so they are not
checked against a publication. The names HSV-2-F, -R and -P were chosen here. The exclusivity
panel was suggested in the session and is the user's to edit.[^assay-file]

# Design

There was no reference sequence: the 71-nt product was taken from HSV-2 strain HG52,
NC_001798:141087-141157, inside US6 (glycoprotein D), where all three oligos are exact.[^ncbi]

It is the companion of the laboratory's HSV-1 assay, which detects HSV-1 only, and the two
differ in kind:[^hsv1] the HSV-1 assay's primers amplify both types and its probe decides, while
here every oligo is type-specific - against HSV-1 strain 17 the forward primer has 5
mismatches, the reverse 4 and the probe 3 - so HSV-1 should not be amplified at all. Together
the two PCRs cover both types.

The probe is linear (FAM/TAMRA), so R9's unmodified-probe ladder applies.[^r9]

# Oligo QC (`run --qc-only`, no network)

**No flags**: not one of the checks is outside the preferred range. Primers 63.3 and 63.2 C, the
probe 68.8 C, about 5.5 C above them, as a hydrolysis probe should be.

# Taxonomy and the variant source

Target: the species *Simplexvirus humanalpha2* (3050293), 8,955 Nucleotide records, the same as
the node "Human alphaherpesvirus 2" (10310). The variant analysis takes the 577 genome-sized
records (100-200 kb) in one run, scanned directly.

# Exclusivity panel

Twenty-five organisms in five groups, HSV-1 first, then the macaque B virus, the other human
herpesviruses, the mucocutaneous and genital lesion differential, the CSF DNA-template
differential, and adenovirus D and *Acanthamoeba* for the eye. Enteroviruses are left out: RNA
templates of a DNA assay.

# Runs

None yet.

[^assay-file]: docs/examples/hsv2_gd.yaml (provenance and checks in its header)
[^ncbi]: The HSV-2 and HSV-1 reference genomes and record counts, measured live
[^hsv1]: HSV-1 detection, glycoprotein G (Ryncarz 1999 typing oligos)
[^r9]: R9 - probe mismatches
[^session]: "Session 2026-10-23: HSV-1 assay file"
