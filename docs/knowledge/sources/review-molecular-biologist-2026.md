---
type: Reference
title: Theory review by a molecular biologist (2026-10-01)
description: Independent review of the tool's theoretical basis by a senior theoretical molecular biologist and bioinformatician, kept verbatim.
resource: ../../reviews/2026-10-01-theory-review-molecular-biologist.md
tags: [review]
status: draft
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: review
    resource: ../../reviews/2026-10-01-theory-review-molecular-biologist.md
    title: The review, verbatim
  - id: comparison
    resource: ../../reviews/README.md
    title: docs/reviews/README.md (comparison and what was taken up)
---

# What it is

A reviewer's opinion, not a project decision, written by a subagent in the role of a senior
theoretical molecular biologist from the project documents, the code and the
literature.[^review] It was written independently of the [advisor's review](review-advisor-2026.md).

# Main points

- The method is sound; the probe rules are the weakest part; terminal mismatch types rest on one
  source; duplex Tm should be computed on the mismatched duplex; database redundancy inflates
  percentages; RNA assays are graded on DNA evidence.
- Only this review: the classes concern detection, not quantification
  ([Bru 2008](bru-2008.md)); the 3'-most-16-nt window is an artefact of Lefever's 20-mers.

# Checked afterwards

Two claims do not hold against the papers: Klungthong 2010 reports reduced sensitivity, not
clinical false negatives, with an unmodified probe; Kwok 1990 does not contradict terminal G3
being tolerated.[^comparison] What was taken up is listed in the comparison and in
[decisions](../decisions/index.md).

[^review]: The review, verbatim
[^comparison]: docs/reviews/README.md (comparison and what was taken up)
