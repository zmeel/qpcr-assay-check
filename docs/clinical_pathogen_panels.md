# Human pathogens typically detected by real-time PCR, grouped by syndromic panel

**Status: reference material, not shipped code.** This document is a general reference compiled
from public knowledge of how clinical microbiology laboratories organise multiplex real-time PCR
testing into syndromic panels (the grouping mirrors the shape of widely used FDA/CE-marked
platforms — BioFire FilmArray, Cepheid Xpert, GenMark ePlex, Seegene Allplex, QIAstat-Dx, bioMérieux
BIOFIRE, Luminex ARIES/ NxTAG, and similar systems — without claiming to reproduce any single
product's exact, validated target list).

**It is NOT an authoritative or exhaustive list, and it is NOT independently verified against NCBI
Taxonomy or any specific assay's package insert**, unlike the primer/probe sequences this project
evaluates, which `CLAUDE.md` requires to be verified against a source publication. Every
laboratory's own validated menu — not this document — is authoritative for what it actually tests.
Names here are common/working names as generally used in clinical microbiology; several have
current NCBI Taxonomy synonyms (e.g. *Chlamydia pneumoniae* / *Chlamydophila pneumoniae*,
*Mycoplasma pneumoniae* / *Mycoplasmoides pneumoniae*, *Candida glabrata* /
*Nakaseomyces glabratus*, *Candida krusei* / *Pichia kudriavzevii*) — see
[`docs/ARCHITECTURE.md`](ARCHITECTURE.md) and
[`src/qpcr_assay_check/data/clinical_organisms.yaml`](../src/qpcr_assay_check/data/clinical_organisms.yaml)
for this project's own name-resolution approach (resolved via Entrez Taxonomy at run time, never
guessed).

This document is a planning/reference aid — e.g. for deciding what to add to a lab's own
`organisms.list_file` for the exclusivity tier of a specific assay. It does not itself change any
packaged configuration.

**Taxonomy IDs below were resolved live on 2026-09-23** via
`scripts/resolve_pathogen_panel_taxids.py` (the user ran it locally, since this development
sandbox cannot reach NCBI), using the exact same Entrez Taxonomy lookup this tool already uses for
its own exclusivity organism list (`[Scientific Name]` first, then `[All Names]` for synonyms) —
never typed in from memory. A `·`-separated cell lists one ID per organism named in that row, in
the same order. Several rows resolve to `unresolved`, `ambiguous`, or `not queried`/`not a formally
named NCBI taxon` rather than a number: **see "Notes on this resolution pass" at the end of this
document before treating any of those as settled.**

---

## 1. Respiratory pathogen panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| Influenza A virus | 11320 | Virus | Often subtyped (H1, H3, H1pdm09) |
| Influenza B virus | 11520 | Virus | |
| Respiratory syncytial virus (RSV) A/B | 11250 | Virus | |
| Human parainfluenza virus 1–4 | 12730 · 2560525 · 11216 · 2560526 | Virus | |
| Human metapneumovirus | 162145 | Virus | |
| Human rhinovirus / enterovirus | 169066 · 12059 | Virus | Often reported as one combined target (overlapping primer regions) |
| Adenovirus | 3567875 | Virus | |
| Human coronavirus 229E, NL63, OC43, HKU1 | 11137 · 277944 · 31631 · 290028 | Virus | Endemic seasonal coronaviruses |
| SARS-CoV-2 | 2697049 | Virus | Now routinely combined with influenza/RSV (see §11) |
| Human bocavirus | 329641 | Virus | Extended panels only |
| *Bordetella pertussis* | 520 | Bacterium | |
| *Bordetella parapertussis* | 519 | Bacterium | |
| *Mycoplasma pneumoniae* | 2104 | Bacterium | See naming note above |
| *Chlamydia pneumoniae* | 83558 | Bacterium | See naming note above |
| *Chlamydia psittaci* | 83554 | Bacterium | See naming note above |
| *Legionella pneumophila* | 446 | Bacterium | |
| *Streptococcus pneumoniae* | 1313 | Bacterium | Semi-quantitative in lower-respiratory (pneumonia) panels |
| *Haemophilus influenzae* | 727 | Bacterium | |
| *Moraxella catarrhalis* | 480 | Bacterium | |
| *Staphylococcus aureus* | 1280 | Bacterium | Often with *mecA*/*mecC* resistance markers |
| *Klebsiella pneumoniae*, *K. oxytoca*, *K. aerogenes* | 573 · 571 · 548 | Bacterium | Lower-respiratory (pneumonia) panels |
| *Escherichia coli* | 562 | Bacterium | Lower-respiratory (pneumonia) panels |
| *Enterobacter cloacae* complex | 550 | Bacterium | Lower-respiratory (pneumonia) panels |
| *Serratia marcescens* | 615 | Bacterium | Lower-respiratory (pneumonia) panels |
| *Proteus* spp. | ambiguous | Bacterium | Lower-respiratory (pneumonia) panels |
| *Pseudomonas aeruginosa* | 287 | Bacterium | Lower-respiratory (pneumonia) panels |
| *Acinetobacter calcoaceticus–baumannii* complex | 470 | Bacterium | Lower-respiratory (pneumonia) panels |

Resistance genes commonly co-reported on lower-respiratory panels: *mecA*/*mecC*, *CTX-M*, *KPC*,
*NDM*, OXA-48-like, *VIM*, *IMP*.

## 2. Gastrointestinal (GI) panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Campylobacter jejuni* / *C. coli* | 197 · 195 | Bacterium | |
| *Salmonella* spp. | 28901 | Bacterium | |
| *Shigella* spp. / enteroinvasive *E. coli* (EIEC) | 620 · 562 | Bacterium | Often one combined target |
| *Yersinia enterocolitica* | 630 | Bacterium | |
| *Vibrio cholerae*, *V. parahaemolyticus*, *V. vulnificus* | 666 · 670 · 672 | Bacterium | |
| *Plesiomonas shigelloides* | 703 | Bacterium | |
| *Clostridioides difficile* (toxin A/B genes) | 1496 | Bacterium | |
| Enterotoxigenic *E. coli* (ETEC) | 562 | Bacterium | |
| Enteropathogenic *E. coli* (EPEC) | 562 | Bacterium | |
| Enteroaggregative *E. coli* (EAEC) | 562 | Bacterium | |
| Shiga toxin-producing *E. coli* (STEC/EHEC), incl. *E. coli* O157 | 562 | Bacterium | *stx1*/*stx2*, *eae* targets |
| Norovirus GI/GII | 142786 | Virus | |
| Rotavirus A | 28875 | Virus | |
| Adenovirus F40/41 | 130309 | Virus | |
| Astrovirus | 1868658 | Virus | |
| Sapovirus | 95341 | Virus | |
| *Giardia duodenalis* (*lamblia*) | 5741 | Parasite | |
| *Cryptosporidium* spp. | 5807 · 237895 | Parasite | |
| *Entamoeba histolytica* | 5759 | Parasite | |
| *Cyclospora cayetanensis* | 88456 | Parasite | |

## 3. Meningitis / encephalitis panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Streptococcus pneumoniae* | 1313 | Bacterium | |
| *Neisseria meningitidis* | 487 | Bacterium | |
| *Haemophilus influenzae* | 727 | Bacterium | |
| *Listeria monocytogenes* | 1639 | Bacterium | |
| *Streptococcus agalactiae* (Group B strep) | 1311 | Bacterium | Neonatal meningitis |
| *Escherichia coli* K1 | 562 | Bacterium | Neonatal meningitis |
| Cytomegalovirus (CMV) | 10359 | Virus | |
| Enterovirus | 12059 | Virus | |
| Herpes simplex virus 1 & 2 | 10298 · 10310 | Virus | |
| Human herpesvirus 6 | 10368 | Virus | |
| Human parechovirus | 1803956 | Virus | |
| Varicella zoster virus | 10335 | Virus | |
| *Cryptococcus neoformans* / *C. gattii* | 5207 · 37769 | Fungus | |

## 4. Bloodstream infection / blood culture identification panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Staphylococcus aureus* | 1280 | Bacterium (Gram+) | + *mecA*/*mecC* |
| Coagulase-negative staphylococci (e.g. *S. epidermidis*) | not queried | Bacterium (Gram+) | |
| *Streptococcus pyogenes*, *S. agalactiae*, *S. pneumoniae*, *S. anginosus* group | 1314 · 1311 · 1313 · not queried | Bacterium (Gram+) | |
| *Enterococcus faecalis*, *E. faecium* | 1351 · 1352 | Bacterium (Gram+) | + *vanA*/*vanB* |
| *Listeria monocytogenes* | 1639 | Bacterium (Gram+) | |
| *Escherichia coli* | 562 | Bacterium (Gram−) | |
| *Klebsiella pneumoniae*, *K. oxytoca* | 573 · 571 | Bacterium (Gram−) | |
| *Enterobacter cloacae* complex | 550 | Bacterium (Gram−) | |
| *Proteus* spp. | ambiguous | Bacterium (Gram−) | |
| *Serratia marcescens* | 615 | Bacterium (Gram−) | |
| *Acinetobacter baumannii* complex | 470 | Bacterium (Gram−) | |
| *Pseudomonas aeruginosa* | 287 | Bacterium (Gram−) | |
| *Haemophilus influenzae* | 727 | Bacterium (Gram−) | |
| *Neisseria meningitidis* | 487 | Bacterium (Gram−) | |
| *Candida albicans* | 5476 | Fungus | |
| *Candida glabrata* | 5478 | Fungus | current name *Nakaseomyces glabratus* |
| *Candida parapsilosis*, *C. tropicalis* | unresolved · 5482 | Fungus | |
| *Candida krusei* | 4909 | Fungus | current name *Pichia kudriavzevii* |
| *Candida auris* | 498019 | Fungus | |

Resistance markers commonly co-reported: *mecA*/*mecC*, *vanA*/*vanB*, *KPC*, *NDM*, OXA-48-like,
*VIM*, *IMP*, *CTX-M*.

## 5. Sexually transmitted infection (STI) panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Chlamydia trachomatis* | 813 | Bacterium | |
| *Neisseria gonorrhoeae* | 485 | Bacterium | |
| *Trichomonas vaginalis* | 5722 | Parasite | |
| *Mycoplasma genitalium* | 2097 | Bacterium | Some assays add macrolide-resistance mutation targets |
| *Mycoplasma hominis* | unresolved | Bacterium | |
| *Ureaplasma urealyticum* | 2130 | Bacterium | |
| *Ureaplasma parvum* | 134821 | Bacterium | |
| *Treponema pallidum* | 160 | Bacterium | Syphilis |
| Herpes simplex virus 1 & 2 | 10298 · 10310 | Virus | |
| *Haemophilus ducreyi* | 730 | Bacterium | Chancroid; extended assays only |

## 6. Vaginitis / vaginosis panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Candida albicans* / *C. glabrata* group / other *Candida* spp. | 5476 · 5478 | Fungus | |
| *Trichomonas vaginalis* | 5722 | Parasite | |
| *Gardnerella vaginalis* | 2702 | Bacterium | Bacterial vaginosis marker |
| *Atopobium vaginae* | 82135 | Bacterium | current name *Fannyhessea vaginae* |
| BVAB-2 | not a formally named NCBI taxon | Bacterium | Bacterial vaginosis-associated bacterium |
| *Megasphaera* type 1/2 | 906 | Bacterium | Bacterial vaginosis marker |
| *Lactobacillus* spp. | 1578 | Bacterium | Normal-flora marker, not a pathogen |
| *Mobiluncus* spp. | 2050 | Bacterium | |

## 7. Tick-borne pathogen panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Borrelia burgdorferi* sensu lato | unresolved | Bacterium | Lyme disease |
| *Borrelia miyamotoi* | 47466 | Bacterium | |
| *Anaplasma phagocytophilum* | 948 | Bacterium | |
| *Ehrlichia chaffeensis*, *E. ewingii* | 945 · 947 | Bacterium | |
| *Babesia microti*, *B. duncani* | 5868 · 323732 | Parasite | |
| *Rickettsia* spp. (spotted fever group) | 780 | Bacterium | |

## 8. Congenital / perinatal infection panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Toxoplasma gondii* | 5811 | Parasite | |
| Cytomegalovirus (CMV) | 10359 | Virus | |
| Herpes simplex virus 1 & 2 | 10298 · 10310 | Virus | |
| Parvovirus B19 | 10798 | Virus | |
| *Treponema pallidum* | 160 | Bacterium | Congenital syphilis |
| Zika virus | 64320 | Virus | |
| Rubella virus | 11041 | Virus | |
| *Streptococcus agalactiae* (Group B strep) | 1311 | Bacterium | Intrapartum screening, not the congenital panel proper |

## 9. Mycobacterial / tuberculosis panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Mycobacterium tuberculosis* complex | 77643 | Bacterium | Often with *rpoB* (rifampin resistance), *inhA*/*katG* (isoniazid resistance) in extended assays |
| *Mycobacterium avium* complex | 37162 | Bacterium | Non-tuberculous |
| *Mycobacterium abscessus* complex | 36809 | Bacterium | Non-tuberculous |
| *Mycobacterium chelonae* | unresolved | Bacterium | Non-tuberculous |
| *Mycobacterium kansasii* | 1768 | Bacterium | Non-tuberculous |
| *Mycobacterium fortuitum* | 1766 | Bacterium | Non-tuberculous |

## 10. Skin and soft tissue infection panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Staphylococcus aureus* | 1280 | Bacterium | + *mecA*/*mecC*, sometimes PVL |
| *Streptococcus pyogenes* | 1314 | Bacterium | |
| *Streptococcus agalactiae* | 1311 | Bacterium | |
| *Enterococcus faecalis*, *E. faecium* | 1351 · 1352 | Bacterium | |
| *Pseudomonas aeruginosa* | 287 | Bacterium | |
| *Serratia marcescens* | 615 | Bacterium | |
| *Proteus mirabilis* | 584 | Bacterium | |
| *Bacteroides fragilis* | 817 | Bacterium | Anaerobe |
| *Clostridium perfringens* | 1502 | Bacterium | Anaerobe |
| *Finegoldia magna*, *Peptoniphilus* spp. | 1260 · 162289 | Bacterium | Anaerobe |

## 11. Combined SARS-CoV-2 / influenza / RSV panel

The simplified triage panel widely deployed since 2020–2021.

| Pathogen | Taxonomy ID | Type |
|---|---|---|
| SARS-CoV-2 | 2697049 | Virus |
| Influenza A virus (± subtyping) | 11320 | Virus |
| Influenza B virus | 11520 | Virus |
| RSV A/B | 11250 | Virus |

## 12. Group A strep (pharyngitis)

Usually a standalone rapid single-target real-time PCR rather than part of a larger panel, but
extremely common in point-of-care testing.

| Pathogen | Taxonomy ID | Type |
|---|---|---|
| *Streptococcus pyogenes* (Group A strep) | 1314 | Bacterium |

---

## Notes on this resolution pass (2026-09-23)

**Genuinely unresolved (zero hits for both `[Scientific Name]` and `[All Names]`), worth a closer
look rather than assumed settled:**
- *Mycoplasma hominis*, *Borrelia burgdorferi*, *Candida parapsilosis* — all three are common,
  well-established clinical species, which makes a clean zero-hit result surprising rather than
  expected. This project has one confirmed precedent for exactly this pattern (a genus-level
  rename that `[All Names]` did not catch: *Mycoplasma* → *Mycoplasmoides pneumoniae*, and see
  *Candida* → *Nakaseomyces*/*Pichia* above), so a similar rename is a reasonable hypothesis here
  (e.g. the proposed *Borrelia* → *Borreliella* split for *B. burgdorferi*) — but that is a
  hypothesis, not a checked fact, and no alternate name is substituted here without its own live
  resolution. Add candidate alternate names to `scripts/resolve_pathogen_panel_taxids.py`'s
  `NAMES` list and re-run to check.
- *Mycobacterium chelonae* — already an open, unexplained item in this project's own exclusivity
  organism list (`data/clinical_organisms.yaml`, `docs/PROGRESS.md`); consistent with that prior
  finding, not new.
- *Mycoplasma pneumoniae* — expected: this project already established (`docs/ARCHITECTURE.md`)
  that this specific name does not resolve, including via `[All Names]`, and uses the current name
  *Mycoplasmoides pneumoniae* instead (which did resolve, taxid 2104).

**Ambiguous:** the bare genus *Proteus* returned more than one taxonomy match. The clinically
dominant species, *Proteus mirabilis*, resolves cleanly on its own (taxid 584, used directly for
its own row in panels 10 and 12).

**Not queried** (informal group names or subspecies-level designations that are not themselves
single NCBI binomials, and were not in the script's `NAMES` list this pass): coagulase-negative
staphylococci as a group, the *Streptococcus anginosus* group, *Megasphaera* type 1/2 specifically
(only the genus *Megasphaera* was queried).

**Not a formally named NCBI taxon:** BVAB-2 ("Bacterial Vaginosis-Associated Bacterium 2") is an
informally designated, as-yet-uncultured/unnamed organism in the literature, not a validly
published binomial — not queried, and not expected to resolve.

**Two names intended as synonyms returned two *different* taxonomy IDs — not reconciled here,
each shown as reported rather than one silently picked:**
- RSV: *Human orthopneumovirus* (taxid 11250, the current ICTV/NCBI species name, used in the
  tables above) vs. *Respiratory syncytial virus* (taxid 12814).
- Adenovirus: *Human mastadenovirus* (taxid 3567875, the current genus name, used above) vs.
  *Human adenovirus* (taxid 1907210).
- Parvovirus B19: *Human parvovirus B19* (taxid 10798, used above) vs. *Primate erythroparvovirus
  1* (taxid 3052189, the current ICTV species name).

In each case the table above uses one of the two (noted per bullet); the other taxid is recorded
here rather than discarded, and which one is actually correct for a given NCBI database search has
not been independently checked.

**Everything else** (the great majority of rows) resolved to exactly one taxonomy ID via
`[Scientific Name]` on the first try, including every case where two differently-worded query
names for the same organism (e.g. all four parainfluenza viruses queried under both their
"orthorubulavirus"/"respirovirus" and "parainfluenza virus N" names) converged on the identical
taxid — a useful cross-check that those particular resolutions are solid.

## How this relates to this project

This project's own exclusivity organism list
([`src/qpcr_assay_check/data/clinical_organisms.yaml`](../src/qpcr_assay_check/data/clinical_organisms.yaml))
is a much smaller, deliberately non-authoritative starter set focused on STI, atypical pneumonia,
mycobacteria and common respiratory pathogens, with human as background — every lab must review and
edit it for its own assay. This document is broader reference material for that curation exercise;
it is not itself wired into the tool, and adding to it does not change any packaged configuration.
