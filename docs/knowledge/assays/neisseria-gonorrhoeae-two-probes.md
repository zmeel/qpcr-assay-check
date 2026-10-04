---
type: Assay
title: Neisseria gonorrhoeae, two MGB probes
description: One primer pair with two alternative FAM-MGB probes on a multi-copy opa region; sequences supplied by the user.
resource: ../../examples/neisseria_gonorrhoeae_two_probes.yaml
tags: [assay, example, DNA, bacterium, multi-copy]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: assay-file
    resource: ../../examples/neisseria_gonorrhoeae_two_probes.yaml
    title: docs/examples/neisseria_gonorrhoeae_two_probes.yaml (provenance and checks in its header)
---

# Provenance

Sequences supplied by the user on 2026-09-24; not checked against a publication or kit insert.
Oligo names are placeholders. The MGB probes' quencher was not specified and is left
empty.[^assay-file]

# Design

| Role | Oligos |
|---|---|
| forward | NG-F (17 nt) |
| reverse | NG-R (24 nt; crosses a poly-A 7 run) |
| probe | NG-P1, NG-P2 (FAM, MGB; NG-P2 for a divergent variant) |

Two reference fragments (76 and 79 nt) in one locus, one FAM channel, target N. gonorrhoeae (485),
exclusivity N. meningitidis. No context accession: the region occurs 2-7 times per genome in
different surroundings. Template DNA (not stated by the user).

# What was checked

Oligo positions against both fragments and site counts on three RefSeq complete genomes, live on
2026-09-24.[^assay-file] Known issues for the laboratory: NG-R's poly-A run
([R5b](../rules/r5b-homopolymer-length.md)) and a perfect predicted product on
N. meningitidis CP171264.1 ([open](../open/cp171264-record-check.md)). Runs:
[2026-10-02](../runs/neisseria-2026-10-02.md).

[^assay-file]: docs/examples/neisseria_gonorrhoeae_two_probes.yaml (provenance and checks in its header)
