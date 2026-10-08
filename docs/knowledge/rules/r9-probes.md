---
type: Grading Rule
title: R9 - probe mismatches
description: MGB probe - 1 mismatch under the MGB likely failure, further 5' undetermined, 2+ likely failure; unmodified probe - 1 outside the last 5 tolerated, 2 at risk, 3+ likely failure.
tags: [grading, probe, MGB, R9]
status: stable
verified: { by: human:zmeel, at: 2026-10-08T07:37:00Z }
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
  - id: d-ceiling
    resource: ../decisions/2026-10-07-probe-rule-ceiling-and-r5c-scope.md
    title: "Probe mismatch ceiling, and the scope of the deletion data"
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
| unmodified | 1 in the last 5 nt, or 2 anywhere | `at_risk`[^klungthong] |
| unmodified | 3 or more | `likely_failure` (expert judgement)[^d-ceiling] |

Kutyavin: the MGB folds into the minor groove of the terminal 5-6 bp and can slide 1-2 bp toward
the 5' end; a mismatch there is far more destabilising (T/G under the MGB dTm 15 vs 6 C), and a
12-mer with a mismatch 5 nt from the 3' end gave no meaningful signal on the mismatched template
in real-time PCR. At 11 nt from the 3' end the MGB added nothing.[^kutyavin]

Klungthong's probe is unmodified, not MGB. Every sample was still detected with two probe
mismatches, but the mean Ct gap to the reference target widened from 5.58 to 9.28, which is the
measurement behind the 2-mismatch step.[^klungthong] Süss 2009 (single mismatches in unmodified
probes) could not be obtained.[^suss]

The **ceiling at 3 mismatches** was added on 2026-10-07 after the user read a Legionella row in
which the unmodified 35-nt LEGpneu probe, with 11 mismatches and 2 gaps, was graded `at_risk`
while the 19-nt MGB LEGgenus probe with 7 mismatches on the same genome was `likely_failure`.
Until then the unmodified branch had no count-based escalation at all.[^d-ceiling] It is expert
judgement with no source, the same standing as the MGB 2+ rule.

Deletions in a probe site: [R5c](r5c-probe-deletions.md). Both theory reviews ranked the probe
rules the weakest part.

[^kutyavin]: Kutyavin et al. 2000
[^klungthong]: Klungthong et al. 2010
[^suss]: Süss et al. 2009
[^d-ceiling]: Probe mismatch ceiling, and the scope of the deletion data
[^d-mgb7]: Decision on the MGB region
[^d-mgb2]: Decisions on MGB probe mismatches
