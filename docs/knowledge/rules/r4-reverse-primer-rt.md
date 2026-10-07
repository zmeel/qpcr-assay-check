---
type: Grading Rule
title: R4 - reverse primer in a one-step RT-PCR (not encoded)
description: Stadhouders found reverse-primer mismatches mattered little with Taq + MMLV and more with rTth; a caveat, not a class.
tags: [grading, primer, R4, RNA]
status: stable
verified: { by: human:zmeel, at: 2026-10-07T08:39:00Z }
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: stadhouders
    resource: ../sources/stadhouders-2010.md
    title: Stadhouders et al. 2010
  - id: christopherson
    resource: ../sources/christopherson-1997.md
    title: Christopherson et al. 1997
  - id: d-classes
    resource: ../decisions/2026-09-25-graded-classes-without-mix-setting.md
    title: Decision to grade sites without a mix setting
---

# Rule

Not encoded. With Taq + MMLV all 24 tested reverse-primer mismatches cost < 0.7 Ct, "most
likely caused by" the mismatch acting only in the RT step; with rTth the reverse primer was the
more sensitive one.[^stadhouders] Without a mix setting[^d-classes] the report prints a caveat
instead. For assays with `template_type: RNA` the report also prints the RNA note
(Christopherson 1997: 2-4 internal mismatches without significant effect on HIV-1 RNA, 5 and 6
cutting yield about 22- and 100-fold).[^christopherson]

[^stadhouders]: Stadhouders et al. 2010
[^christopherson]: Christopherson et al. 1997
[^d-classes]: Decision to grade sites without a mix setting
