---
type: Session
title: "Pathogen-panel taxonomy IDs resolved live and merged into the doc"
description: "Session log of 2026-09-23."
tags: [session]
session_date: 2026-09-23
session_label: "2026-09-23"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-23: Pathogen-panel taxonomy IDs resolved live and merged into the doc

The user ran `scripts/resolve_pathogen_panel_taxids.py` locally and pasted back its console
output (137 names). Merged the results into `docs/clinical_pathogen_panels.md`'s "Taxonomy ID"
column, replacing every `pending` placeholder (131 table rows) with the resolved value(s) for that
row's pathogen name(s), via a small positional-replacement script rather than manual editing —
which caught a real bug in the process: a first draft of the replacement list was silently missing
one entry (*Serratia marcescens*, section 1), which a per-section length assertion (26/20/13/19/
10/8/6/8/6/10/4/1) caught before it could quietly shift every later cell in the document by one row.
That mismatch happened to also produce a confusing red herring while debugging it: an intermediate
`grep`/Python count of `"| pending |"` occurrences flip-flopped between 130 and 131 across separate
tool calls on an apparently-unchanged file (confirmed unchanged by a stable md5sum) -- eventually
traced to misreading which assertion actually failed (`len(replacements) == 131`, not the file's
own pending-count), not a real file-race; the fix was to build and validate the replacement list
per-section rather than as one flat, hand-counted list.

Five results came back genuinely unresolved or ambiguous (*Mycoplasma hominis*, *Borrelia
burgdorferi*, *Candida parapsilosis* unresolved -- surprising for such common species and flagged
as worth a follow-up live check, distinct from *Mycoplasma pneumoniae* and *Mycobacterium
chelonae*, whose non-resolution was already expected/documented from prior work; bare genus
*Proteus* ambiguous), plus three cases where two names intended as synonyms (RSV, adenovirus,
parvovirus B19) resolved to two *different* taxonomy IDs -- none of these five situations were
guessed past: the doc's new "Notes on this resolution pass" section records exactly what is and
is not settled, and the table cells themselves say `unresolved`/`ambiguous`/`not queried` rather
than a number wherever that is the honest state, per this project's own "never guess a taxonomy
ID" rule.
