---
type: Grading Rule
title: R9 - probe mismatches
description: MGB probe - 1 mismatch in the 3'-most 7 nt likely failure, further 5' undetermined, 2+ likely failure; unmodified probe - 1 outside the last 5 tolerated.
tags: [grading, probe, MGB, R9]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: kutyavin
    resource: ../sources/kutyavin-2000.md
    title: Kutyavin et al. 2000
  - id: klungthong
    resource: ../sources/klungthong-2010.md
    title: Klungthong et al. 2010
  - id: suss
    resource: ../sources/suss-2009.md
    title: Süss et al. 2009
  - id: d-mgb7
    resource: ../decisions/2026-10-02-mgb-region-likely-failure.md
    title: Decision on the MGB region
  - id: d-mgb2
    resource: ../decisions/2026-09-25-mgb-probe-mismatches.md
    title: Decisions on MGB probe mismatches
---

# Rule

Neither Stadhouders nor Lefever tested probes.

| Probe | Mismatches | Class |
|---|---|---|
| MGB | 1 in the 3'-most 7 nt (`MGB_REGION = 7`) | `likely_failure`[^kutyavin][^d-mgb7] |
| MGB | 1 further toward the 5' end | `indeterminate`, genome undetermined |
| MGB | 2 or more | `likely_failure`, position-free (expert judgement)[^d-mgb2] |
| unmodified | 1 outside the last 5 nt | `tolerated` (expert judgement) |
| unmodified | otherwise | `at_risk` |

Kutyavin: the MGB folds into the minor groove of the terminal 5-6 bp and can slide 1-2 bp toward
the 5' end; a mismatch there is far more destabilising (T/G under the MGB dTm 15 vs 6 C), and a
12-mer with a mismatch 5 nt from the 3' end gave no meaningful signal on the mismatched template
in real-time PCR. At 11 nt from the 3' end the MGB added nothing.[^kutyavin]

Klungthong's probe is unmodified, not MGB, and every sample was detected; it is consistent with
the unmodified-probe rule.[^klungthong] Süss 2009 (single mismatches in unmodified probes) could
not be obtained, so the unmodified rule stays expert judgement.[^suss] Deletions in a probe site:
[R5c](r5c-probe-deletions.md). Both theory reviews ranked the probe rules the weakest part.

[^kutyavin]: Kutyavin et al. 2000
[^klungthong]: Klungthong et al. 2010
[^suss]: Süss et al. 2009
[^d-mgb7]: Decision on the MGB region
[^d-mgb2]: Decisions on MGB probe mismatches
