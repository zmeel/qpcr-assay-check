---
type: Session
title: "Added a reference doc: pathogens by syndromic real-time PCR panel"
description: "Session log of 2026-09-23."
tags: [session]
session_date: 2026-09-23
session_label: "2026-09-23"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-23: Added a reference doc: pathogens by syndromic real-time PCR panel

The user asked for a compiled list of human pathogens typically detected by real-time PCR, grouped
into syndromic panels, as a doc in the repo. Added `docs/clinical_pathogen_panels.md`: twelve
panels (respiratory, GI, meningitis/encephalitis, bloodstream infection/BCID, STI, vaginitis,
tick-borne, congenital/perinatal, mycobacterial/TB, skin and soft tissue, the now-standard
SARS-CoV-2/flu/RSV combo, and group A strep), each a table of pathogen/type/notes, compiled from
general public knowledge of how commercial syndromic multiplex panels (BioFire FilmArray, Cepheid
Xpert, GenMark ePlex, Seegene Allplex, QIAstat-Dx, and similar) are organised -- without claiming to
reproduce any single product's exact validated target list.

Labelled explicitly as reference material, not verified against NCBI Taxonomy or any package
insert the way this project's own primer/probe sequences must be (`CLAUDE.md`'s "never invent"
rule is about oligo sequences and NCBI parameters specifically, not general pathogen-panel
knowledge) -- distinct in kind from `data/clinical_organisms.yaml`, which is small, deliberately
non-authoritative, and directly wired into the exclusivity search. This new doc is not wired into
the tool at all; it is a broader planning aid for curating that list, linked from README's
Exclusivity section. No code changed.
