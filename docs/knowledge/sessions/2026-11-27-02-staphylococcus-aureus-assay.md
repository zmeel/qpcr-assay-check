---
type: Session
title: "S. aureus assay file (realT Martineau)"
description: "Session log of 2026-11-27."
tags: [session]
session_date: 2026-11-27
session_label: "2026-11-27 (2)"
generated: { by: claude-code/agent, at: 2026-11-27T11:10:00Z }
---

# 2026-11-27: S. aureus assay file (realT Martineau)

- **The request.** The user supplied the primers, two FAM/TAMRA probes and a 112-nt reference of
  the laboratory's "realT Martineau" S. aureus PCR, and asked for an assay file with tier groups.
- **Built:** `docs/examples/staphylococcus_aureus_martineau.yaml`
  ([assay](../assays/staphylococcus-aureus-martineau.md)).
  - **Against the reference:** forward primer 1-26, reverse primer site 81-112, probe Martineau
    28-58, all exact; Martineau2 on the same site with 2 mismatches. The two probes are
    alternatives in one FAM channel.
  - **Against the paper** (Martineau et al. 1998, PMID 9508283; the user supplied the PDF):
    the primers are shifted and shortened versions of Sa442-1 and Sa442-2; the probes are
    not in the paper.
  - **Tier groups:** near neighbours *S. argenteus* and *S. schweitzeri*; then coagulase-negative
    staphylococci, other coagulase-positive staphylococci, other Gram-positive organisms, and
    Gram-negatives and yeast.
  - **Annealing:** 60 C (the user).
  - **Checked:** `qpcr-assay-check validate` passes; ruff, ruff format and `pytest -m "not live"` pass.
- **Open:**
  - a live run, which also resolves the near-neighbour taxids, not yet checked against NCBI;
  - the user's decision whether *S. argenteus* and *S. schweitzeri* should be detected or not.

# Related

- [S. aureus, realT Martineau](../assays/staphylococcus-aureus-martineau.md)
- [Current status](../status.md)
