---
type: Decision
title: "Plain words: amplicon, the opposite primer, and gaps that say what is unknown"
description: "The report says amplicon instead of product and \"check for the opposite primer\" instead of partner scan, and each gap names what stopped, at which setting, and what that leaves unknown; \"not bounded\" is gone. Setting names and results.json fields stay."
tags: [decision, report, specificity]
status: draft
decided_on: 2026-11-25
generated: { by: claude-code/agent, at: 2026-11-25T15:00:00Z }
sources:
  - id: condensed
    resource: 2026-11-25-findings-condensed.md
    title: "Findings condensed: no repeated list, specificity as a table per tier"
---

# Decision

- **Amplicon, not product.** "Amplicon" is the usual qPCR term, and the setting
  `max_amplicons` already uses it. The report, the findings, the workbook (sheet "Predicted
  amplicons", column "Predicted amplicon"), the GUI and the user documentation now say amplicon.
- **"Check for the opposite primer", not "partner scan".** The check works like this: next to an
  off-target primer site that BLAST reported without a facing primer, the tool fetches the
  sequence and looks for the opposite primer within amplicon distance, because BLAST can miss that
  site.
- **Every gap says three things:** what stopped, at which setting, and what that leaves unknown.
  The HSV-1 lines read:
  - near neighbours: "Amplicon list stopped at 500 (max_amplicons); amplicons beyond it are not
    checked and cannot be ruled out as detected";
  - all tiers: "485 off-target primer sites not checked for the opposite primer binding nearby
    (partner_scan_max_windows); an amplicon formed there could be missing";
  - background: "Only the 2,000 strongest alignments checked for HSV-1-gG1-FP_v8 and
    HSV-1-gG1-P (max_sites_per_query); weaker ones not assessed".

  Other gaps are reworded in the same style: a full BLAST hit list, and an amplicon in which the
  probe was not checked.
- **Each gap's full note is written in plain language.** For example, the note on an amplicon
  list that stopped at the limit explains why the unlisted amplicons cannot be ruled out, and
  how to close the gap: raise `specificity.max_amplicons` above the number of amplicons.
- **"Bounded" and "not bounded" are gone.** "Not detected (bounded)" reads "Not detected
  (proven)". Where the proof fails, the note says it "cannot be ruled out", with the reason.
- **What stays as it was:** the setting names (`max_amplicons`, `partner_scan_max_windows`,
  `probe_scan_max_products`), the results.json fields and the log lines. Renaming those would
  break existing assay files, older records and the GUI's progress reading. Records made before
  this change keep their old wording.

# Who and why

User, 2026-11-25. Asked what "Near neighbours: product list cut at max_amplicons, not bounded"
means, the user wanted it rephrased. On option A ("Product list stopped at 500 (max_amplicons);
products beyond it are not checked and cannot be ruled out as detected") the user asked: "Is it
not better to use the word amplicon in stead of product? And you mention partner primer. Thats
also not common terminology." The proposal was "amplicon" and "the opposite primer" throughout
the report, the three gap lines reworded, a plain-language note for each gap, and the workbook
sheet renamed. The user's answer: "Yes build as you propose".

[^condensed]: "Findings condensed: no repeated list, specificity as a table per tier"
