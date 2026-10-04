---
type: Session
title: "Taxonomy IDs for the pathogen-panel doc: a script, not typed-in numbers"
description: "Session log of 2026-09-23."
tags: [session]
session_date: 2026-09-23
session_label: "2026-09-23"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-23: Taxonomy IDs for the pathogen-panel doc: a script, not typed-in numbers

The user asked to add NCBI taxonomy IDs to `docs/clinical_pathogen_panels.md`. Confirmed this
sandbox still cannot reach NCBI (`curl` to `eutils.ncbi.nlm.nih.gov` through the proxy returns
HTTP 403, same as every prior session), so taxids could only come from memory -- which this
project's own rules treat the same way as a primer/probe sequence or an NCBI parameter: never
typed in unverified (`CLAUDE.md`: "NEVER invent... NCBI parameters... never guessed";
`taxonomy/resolve.py`: "never picks a UID out of an ambiguous result: that would be guessing").
A wrong digit in a taxonomy ID is exactly the kind of silent, hard-to-catch error that rule exists
to prevent.

Instead of guessing, added `scripts/resolve_pathogen_panel_taxids.py`: resolves all 137 unique
pathogen names from the doc (some listed under two names -- a current name and a still-common
synonym, e.g. the *Mycoplasma*/*Mycoplasmoides pneumoniae* rename already found live not to
resolve via the `[All Names]` fallback -- so both get tried) through the exact same live Entrez
Taxonomy lookup (`taxonomy/resolve.py`'s `resolve_name`, `[Scientific Name]` then `[All Names]`)
this project already uses for its own exclusivity organism list, using the same
`NcbiHttp`/`Eutils`/`Cache` construction as `scripts/smoke_test.py`. Confirmed the script fails
fast and cleanly without `NCBI_EMAIL` set, before any network call. Added a "Taxonomy ID" column
to every table in the doc, currently `pending` for all 131 rows, and a note at the top explaining
why and how to fill it in (run the script locally, paste back `pathogen_taxid_report.json`).

Not yet done: the script has not been run live, so no taxid in the doc is filled in yet -- waiting
on the user to run it and paste back the report.
