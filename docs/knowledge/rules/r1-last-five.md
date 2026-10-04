---
type: Grading Rule
title: R1 - one mismatch in the last 5 nt of a primer
description: Class by mismatch type, position and Stadhouders Table 1 (Taq on DNA); terminal G2 at risk since 2026-10-02.
tags: [grading, primer, R1]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: stadhouders
    resource: ../sources/stadhouders-2010.md
    title: Stadhouders et al. 2010
  - id: lefever
    resource: ../sources/lefever-2013.md
    title: Lefever et al. 2013
  - id: kwok
    resource: ../sources/kwok-1990.md
    title: Kwok et al. 1990
  - id: huang
    resource: ../sources/huang-1992.md
    title: Huang et al. 1992
  - id: d-g2
    resource: ../decisions/2026-10-02-terminal-g2-at-risk.md
    title: Decision on terminal G2
  - id: mismatch-classes
    resource: ../../MISMATCH_CLASSES.md
    title: docs/MISMATCH_CLASSES.md, R1 and section 10
---

# Rule

Positions count from the 3' end (-1 is the terminal base); the type is written primer-template.

- Type groups: **G1** A-A, A-G, G-A, G-G, C-C; **G2** T-T, T-C, C-T; **G3** C-A, A-C, G-T, T-G.
- Position groups: terminal (-1), penultimate (-2), -3 to -5.
- Stadhouders Table 1, Taq on DNA, gives "acceptable" (generally < 2.0 Ct) or "avoid" per group
  and position.[^stadhouders] Encoding (ours): "avoid" is `likely_failure` at -1 and
  `at_risk` at -2 to -5; "acceptable" is `tolerated`.
- Position -4 was not tested (only 1, 2, 3 and 5); applying the -3 to -5 group to it is an
  interpolation, printed as such.[^stadhouders]
- Where Stadhouders and Lefever disagree, the worse is taken,[^lefever] except:
- **Terminal G2 is `at_risk`** (since 2026-10-02).[^d-g2] Stadhouders measured 3.77-4.75 Ct (a
  delay, not a block); Kwok found PCR yield 1.0 for T-T, T-C and C-T;[^kwok] Huang measured C-T as
  the most easily extended mispair (2x10^-2), T-C and T-T 10^-4 to 10^-5.[^huang]
- Terminal G1 stays `likely_failure` (all sources agree); terminal G3 stays `tolerated`
  (Stadhouders 0.99-1.91 Ct, Kwok 1.0); Huang's kinetic values for G3 are printed in the note
  only.[^mismatch-classes]

# Code

`_single_in_last5` in `oligo/grade.py`; the encoded Table 1 cells are in the same file. That
the encoding matches the printed table is still unchecked: see
[open item](../open/stadhouders-table-check.md).

[^stadhouders]: Stadhouders et al. 2010
[^lefever]: Lefever et al. 2013
[^kwok]: Kwok et al. 1990
[^huang]: Huang et al. 1992
[^d-g2]: Decision on terminal G2
[^mismatch-classes]: docs/MISMATCH_CLASSES.md, R1 and section 10
