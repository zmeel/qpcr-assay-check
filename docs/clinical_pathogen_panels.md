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

**NCBI Taxonomy IDs are not filled in below yet.** This development sandbox cannot reach NCBI (see
`CLAUDE.md`), and per this project's own "never guess a taxonomy ID" rule
(`taxonomy/resolve.py`: "never picks a UID out of an ambiguous result: that would be guessing"),
they are not typed in from memory either. `scripts/resolve_pathogen_panel_taxids.py` resolves every
name below through the exact same live Entrez Taxonomy lookup this tool already uses for its own
exclusivity organism list — run it locally (`export NCBI_EMAIL=...` then
`python scripts/resolve_pathogen_panel_taxids.py`) and paste back `pathogen_taxid_report.json` to
get the IDs filled in, with any ambiguous or unresolved name reported rather than guessed.

---

## 1. Respiratory pathogen panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| Influenza A virus | pending | Virus | Often subtyped (H1, H3, H1pdm09) |
| Influenza B virus | pending | Virus | |
| Respiratory syncytial virus (RSV) A/B | pending | Virus | |
| Human parainfluenza virus 1–4 | pending | Virus | |
| Human metapneumovirus | pending | Virus | |
| Human rhinovirus / enterovirus | pending | Virus | Often reported as one combined target (overlapping primer regions) |
| Adenovirus | pending | Virus | |
| Human coronavirus 229E, NL63, OC43, HKU1 | pending | Virus | Endemic seasonal coronaviruses |
| SARS-CoV-2 | pending | Virus | Now routinely combined with influenza/RSV (see §11) |
| Human bocavirus | pending | Virus | Extended panels only |
| *Bordetella pertussis* | pending | Bacterium | |
| *Bordetella parapertussis* | pending | Bacterium | |
| *Mycoplasma pneumoniae* | pending | Bacterium | See naming note above |
| *Chlamydia pneumoniae* | pending | Bacterium | See naming note above |
| *Legionella pneumophila* | pending | Bacterium | |
| *Streptococcus pneumoniae* | pending | Bacterium | Semi-quantitative in lower-respiratory (pneumonia) panels |
| *Haemophilus influenzae* | pending | Bacterium | |
| *Moraxella catarrhalis* | pending | Bacterium | |
| *Staphylococcus aureus* | pending | Bacterium | Often with *mecA*/*mecC* resistance markers |
| *Klebsiella pneumoniae*, *K. oxytoca*, *K. aerogenes* | pending | Bacterium | Lower-respiratory (pneumonia) panels |
| *Escherichia coli* | pending | Bacterium | Lower-respiratory (pneumonia) panels |
| *Enterobacter cloacae* complex | pending | Bacterium | Lower-respiratory (pneumonia) panels |
| *Serratia marcescens* | pending | Bacterium | Lower-respiratory (pneumonia) panels |
| *Proteus* spp. | pending | Bacterium | Lower-respiratory (pneumonia) panels |
| *Pseudomonas aeruginosa* | pending | Bacterium | Lower-respiratory (pneumonia) panels |
| *Acinetobacter calcoaceticus–baumannii* complex | pending | Bacterium | Lower-respiratory (pneumonia) panels |

Resistance genes commonly co-reported on lower-respiratory panels: *mecA*/*mecC*, *CTX-M*, *KPC*,
*NDM*, OXA-48-like, *VIM*, *IMP*.

## 2. Gastrointestinal (GI) panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Campylobacter jejuni* / *C. coli* | pending | Bacterium | |
| *Salmonella* spp. | pending | Bacterium | |
| *Shigella* spp. / enteroinvasive *E. coli* (EIEC) | pending | Bacterium | Often one combined target |
| *Yersinia enterocolitica* | pending | Bacterium | |
| *Vibrio cholerae*, *V. parahaemolyticus*, *V. vulnificus* | pending | Bacterium | |
| *Plesiomonas shigelloides* | pending | Bacterium | |
| *Clostridioides difficile* (toxin A/B genes) | pending | Bacterium | |
| Enterotoxigenic *E. coli* (ETEC) | pending | Bacterium | |
| Enteropathogenic *E. coli* (EPEC) | pending | Bacterium | |
| Enteroaggregative *E. coli* (EAEC) | pending | Bacterium | |
| Shiga toxin-producing *E. coli* (STEC/EHEC), incl. *E. coli* O157 | pending | Bacterium | *stx1*/*stx2*, *eae* targets |
| Norovirus GI/GII | pending | Virus | |
| Rotavirus A | pending | Virus | |
| Adenovirus F40/41 | pending | Virus | |
| Astrovirus | pending | Virus | |
| Sapovirus | pending | Virus | |
| *Giardia duodenalis* (*lamblia*) | pending | Parasite | |
| *Cryptosporidium* spp. | pending | Parasite | |
| *Entamoeba histolytica* | pending | Parasite | |
| *Cyclospora cayetanensis* | pending | Parasite | |

## 3. Meningitis / encephalitis panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Streptococcus pneumoniae* | pending | Bacterium | |
| *Neisseria meningitidis* | pending | Bacterium | |
| *Haemophilus influenzae* | pending | Bacterium | |
| *Listeria monocytogenes* | pending | Bacterium | |
| *Streptococcus agalactiae* (Group B strep) | pending | Bacterium | Neonatal meningitis |
| *Escherichia coli* K1 | pending | Bacterium | Neonatal meningitis |
| Cytomegalovirus (CMV) | pending | Virus | |
| Enterovirus | pending | Virus | |
| Herpes simplex virus 1 & 2 | pending | Virus | |
| Human herpesvirus 6 | pending | Virus | |
| Human parechovirus | pending | Virus | |
| Varicella zoster virus | pending | Virus | |
| *Cryptococcus neoformans* / *C. gattii* | pending | Fungus | |

## 4. Bloodstream infection / blood culture identification panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Staphylococcus aureus* | pending | Bacterium (Gram+) | + *mecA*/*mecC* |
| Coagulase-negative staphylococci (e.g. *S. epidermidis*) | pending | Bacterium (Gram+) | |
| *Streptococcus pyogenes*, *S. agalactiae*, *S. pneumoniae*, *S. anginosus* group | pending | Bacterium (Gram+) | |
| *Enterococcus faecalis*, *E. faecium* | pending | Bacterium (Gram+) | + *vanA*/*vanB* |
| *Listeria monocytogenes* | pending | Bacterium (Gram+) | |
| *Escherichia coli* | pending | Bacterium (Gram−) | |
| *Klebsiella pneumoniae*, *K. oxytoca* | pending | Bacterium (Gram−) | |
| *Enterobacter cloacae* complex | pending | Bacterium (Gram−) | |
| *Proteus* spp. | pending | Bacterium (Gram−) | |
| *Serratia marcescens* | pending | Bacterium (Gram−) | |
| *Acinetobacter baumannii* complex | pending | Bacterium (Gram−) | |
| *Pseudomonas aeruginosa* | pending | Bacterium (Gram−) | |
| *Haemophilus influenzae* | pending | Bacterium (Gram−) | |
| *Neisseria meningitidis* | pending | Bacterium (Gram−) | |
| *Candida albicans* | pending | Fungus | |
| *Candida glabrata* | pending | Fungus | current name *Nakaseomyces glabratus* |
| *Candida parapsilosis*, *C. tropicalis* | pending | Fungus | |
| *Candida krusei* | pending | Fungus | current name *Pichia kudriavzevii* |
| *Candida auris* | pending | Fungus | |

Resistance markers commonly co-reported: *mecA*/*mecC*, *vanA*/*vanB*, *KPC*, *NDM*, OXA-48-like,
*VIM*, *IMP*, *CTX-M*.

## 5. Sexually transmitted infection (STI) panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Chlamydia trachomatis* | pending | Bacterium | |
| *Neisseria gonorrhoeae* | pending | Bacterium | |
| *Trichomonas vaginalis* | pending | Parasite | |
| *Mycoplasma genitalium* | pending | Bacterium | Some assays add macrolide-resistance mutation targets |
| *Mycoplasma hominis* | pending | Bacterium | |
| *Ureaplasma urealyticum* | pending | Bacterium | |
| *Ureaplasma parvum* | pending | Bacterium | |
| *Treponema pallidum* | pending | Bacterium | Syphilis |
| Herpes simplex virus 1 & 2 | pending | Virus | |
| *Haemophilus ducreyi* | pending | Bacterium | Chancroid; extended assays only |

## 6. Vaginitis / vaginosis panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Candida albicans* / *C. glabrata* group / other *Candida* spp. | pending | Fungus | |
| *Trichomonas vaginalis* | pending | Parasite | |
| *Gardnerella vaginalis* | pending | Bacterium | Bacterial vaginosis marker |
| *Atopobium vaginae* | pending | Bacterium | current name *Fannyhessea vaginae* |
| BVAB-2 | pending | Bacterium | Bacterial vaginosis-associated bacterium |
| *Megasphaera* type 1/2 | pending | Bacterium | Bacterial vaginosis marker |
| *Lactobacillus* spp. | pending | Bacterium | Normal-flora marker, not a pathogen |
| *Mobiluncus* spp. | pending | Bacterium | |

## 7. Tick-borne pathogen panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Borrelia burgdorferi* sensu lato | pending | Bacterium | Lyme disease |
| *Borrelia miyamotoi* | pending | Bacterium | |
| *Anaplasma phagocytophilum* | pending | Bacterium | |
| *Ehrlichia chaffeensis*, *E. ewingii* | pending | Bacterium | |
| *Babesia microti*, *B. duncani* | pending | Parasite | |
| *Rickettsia* spp. (spotted fever group) | pending | Bacterium | |

## 8. Congenital / perinatal infection panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Toxoplasma gondii* | pending | Parasite | |
| Cytomegalovirus (CMV) | pending | Virus | |
| Herpes simplex virus 1 & 2 | pending | Virus | |
| Parvovirus B19 | pending | Virus | |
| *Treponema pallidum* | pending | Bacterium | Congenital syphilis |
| Zika virus | pending | Virus | |
| Rubella virus | pending | Virus | |
| *Streptococcus agalactiae* (Group B strep) | pending | Bacterium | Intrapartum screening, not the congenital panel proper |

## 9. Mycobacterial / tuberculosis panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Mycobacterium tuberculosis* complex | pending | Bacterium | Often with *rpoB* (rifampin resistance), *inhA*/*katG* (isoniazid resistance) in extended assays |
| *Mycobacterium avium* complex | pending | Bacterium | Non-tuberculous |
| *Mycobacterium abscessus* complex | pending | Bacterium | Non-tuberculous |
| *Mycobacterium chelonae* | pending | Bacterium | Non-tuberculous |
| *Mycobacterium kansasii* | pending | Bacterium | Non-tuberculous |
| *Mycobacterium fortuitum* | pending | Bacterium | Non-tuberculous |

## 10. Skin and soft tissue infection panel

| Pathogen | Taxonomy ID | Type | Notes |
|---|---|---|---|
| *Staphylococcus aureus* | pending | Bacterium | + *mecA*/*mecC*, sometimes PVL |
| *Streptococcus pyogenes* | pending | Bacterium | |
| *Streptococcus agalactiae* | pending | Bacterium | |
| *Enterococcus faecalis*, *E. faecium* | pending | Bacterium | |
| *Pseudomonas aeruginosa* | pending | Bacterium | |
| *Serratia marcescens* | pending | Bacterium | |
| *Proteus mirabilis* | pending | Bacterium | |
| *Bacteroides fragilis* | pending | Bacterium | Anaerobe |
| *Clostridium perfringens* | pending | Bacterium | Anaerobe |
| *Finegoldia magna*, *Peptoniphilus* spp. | pending | Bacterium | Anaerobe |

## 11. Combined SARS-CoV-2 / influenza / RSV panel

The simplified triage panel widely deployed since 2020–2021.

| Pathogen | Taxonomy ID | Type |
|---|---|---|
| SARS-CoV-2 | pending | Virus |
| Influenza A virus (± subtyping) | pending | Virus |
| Influenza B virus | pending | Virus |
| RSV A/B | pending | Virus |

## 12. Group A strep (pharyngitis)

Usually a standalone rapid single-target real-time PCR rather than part of a larger panel, but
extremely common in point-of-care testing.

| Pathogen | Taxonomy ID | Type |
|---|---|---|
| *Streptococcus pyogenes* (Group A strep) | pending | Bacterium |

---

## How this relates to this project

This project's own exclusivity organism list
([`src/qpcr_assay_check/data/clinical_organisms.yaml`](../src/qpcr_assay_check/data/clinical_organisms.yaml))
is a much smaller, deliberately non-authoritative starter set focused on STI, atypical pneumonia,
mycobacteria and common respiratory pathogens, with human as background — every lab must review and
edit it for its own assay. This document is broader reference material for that curation exercise;
it is not itself wired into the tool, and adding to it does not change any packaged configuration.
