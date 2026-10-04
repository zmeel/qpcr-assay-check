---
type: Session
title: "v1.3.0 confirmed live and released"
description: "Session log of 2026-09-25."
tags: [session]
session_date: 2026-09-25
session_label: "2026-09-25"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-25: v1.3.0 confirmed live and released

- Live NG run with `fb7ede5` (budget 15,000, overnight): 2026 1,170, 2025 3,083 and 2024 10,747
  scanned; 12,735 of the 15,000 were the rescans of genomes stored with at most 5 copies, 2,265
  were new. No genome is left with capped copies; at most 11 copies per genome. 31 downloads
  failed (retried on the next run); ChunkedEncodingError retries recovered.
- 29,520 of 51,572 assemblies assessed (29,480 multi-copy; best copy not the first found:
  4,725). With a detectable copy: 24,870 (84.2%) strict, 28,795 (97.5%) if homopolymer bulges
  are tolerated; 4,650 escapes (strict). Coverage: NG-F 98.8% (341 none, mostly one 6-mismatch
  variant), NG-R 84.4% (4,617 none), NG-P1 96.0%, NG-P2 3.9% (all "only"), probe none 44.
  Reverse inclusivity 70/78/86% (2026/2025/2024), 91% for 2023 (58 assessed).
- Released as v1.3.0 (CHANGELOG section, version 1.3.0, README status and version table,
  FEATURE_IDEAS #8 done). About 22,000 older assemblies remain for later runs. The user merges
  and tags.
- v1.3.0 merged (PR #19) and tagged by the user (verified: annotated, on main's merge commit
  f03c5be). Next: the user picks the next feature from docs/FEATURE_IDEAS.md.
