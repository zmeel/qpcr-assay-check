---
type: Assay
title: Staphylococcus aureus, realT Martineau (Sa442), two probes
description: The laboratory's real-time adaptation of the Sa442 PCR of Martineau 1998 - primers shifted and shortened from the paper's, two alternative FAM/TAMRA probes not in the paper, 112 bp; primers checked against the paper's PDF, no live run yet.
resource: ../../examples/staphylococcus_aureus_martineau.yaml
tags: [assay, example, DNA, bacterium]
status: draft
generated: { by: claude-code/agent, at: 2026-11-27T11:10:00Z }
sources:
  - id: assay-file
    resource: ../../examples/staphylococcus_aureus_martineau.yaml
    title: docs/examples/staphylococcus_aureus_martineau.yaml (provenance and checks in its header)
  - id: martineau
    resource: "Martineau F, Picard FJ, Roy PH, Ouellette M, Bergeron MG. J Clin Microbiol 1998; 36: 618-623, PMID 9508283"
    title: Martineau et al. 1998, species-specific and ubiquitous-DNA-based assays for S. aureus
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: session
    resource: ../sessions/2026-11-27-02-staphylococcus-aureus-assay.md
    title: "Session 2026-11-27: S. aureus assay file"
---

# Provenance

Oligos and a 112-nt reference supplied by the user on 2026-11-27, with the publication the PCR
is based on, Martineau et al. 1998, and then its PDF.[^martineau] The paper's assay is a
conventional gel PCR on Sa442, a 442-bp S. aureus-specific chromosomal fragment: primers
Sa442-1 (positions 5-34) and Sa442-2 (83-112), a 108-bp product, annealing at 55 C, no
probe.[^assay-file]

The laboratory's oligos are a real-time adaptation, not the paper's:

- **Forward** realT-Martineau-F: one extra base (C) at the 5' end and 4 bases shorter at the
  3' end than Sa442-1.
- **Reverse** realT-Martineau-R: three extra bases (CAA) at the 5' end and one base shorter at
  the 3' end than Sa442-2. The product is 112 bp.
- **Probes** Martineau and Martineau2 (FAM/TAMRA) are not in the paper; their source is not known.

The supplied reference fits the paper's coordinates (Sa442 positions 4-115). The PDF does not
print the Sa442 sequence, so the reference was not checked base by base.

# Design

Against the reference the forward primer is at 1-26, the reverse primer site at 81-112 and the
probe Martineau at 28-58, all exact. Martineau2 binds the same site with 2 mismatches (probe
positions 13 and 26): an alternative probe in the same FAM channel, the best-binding one counting
per genome. Both probes are linear, so the unmodified-probe ladder of R9 applies.[^r9] Annealing
at 60 C, the laboratory's real-time protocol (the user, 2026-11-27), the tool's default.

# Tier groups

Suggested 2026-11-27, the user's to change:

1. **Near neighbours:** *S. argenteus* (985002) and *S. schweitzeri* (1654388), the *S. aureus*
   complex. They were described long after 1998, so the paper never tested them. They are treated
   as must-not-detect; the taxids are not yet resolved live.
2. **Coagulase-negative staphylococci:** ten species.
3. **Other coagulase-positive or coagulase-variable staphylococci:** five species, mostly zoonotic.
4. **Other Gram-positive organisms of the same specimens:** including *Mammaliicoccus sciuri* and
   *Macrococcus caseolyticus*.
5. **Gram-negatives and yeast of mixed specimens.**

Groups 2-4 overlap the paper's negative wet-lab panel (its Table 1, 25 other staphylococcal
species). Human DNA is the default background.

# Runs

None yet. Open: a live run, which also resolves the near-neighbour taxids and the organism names.

[^assay-file]: docs/examples/staphylococcus_aureus_martineau.yaml (provenance and checks in its header)
[^martineau]: Martineau et al. 1998, species-specific and ubiquitous-DNA-based assays for S. aureus
[^r9]: R9 - probe mismatches
[^session]: "Session 2026-11-27: S. aureus assay file"
