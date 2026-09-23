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

---

## 1. Respiratory pathogen panel

| Pathogen | Type | Notes |
|---|---|---|
| Influenza A virus | Virus | Often subtyped (H1, H3, H1pdm09) |
| Influenza B virus | Virus | |
| Respiratory syncytial virus (RSV) A/B | Virus | |
| Human parainfluenza virus 1–4 | Virus | |
| Human metapneumovirus | Virus | |
| Human rhinovirus / enterovirus | Virus | Often reported as one combined target (overlapping primer regions) |
| Adenovirus | Virus | |
| Human coronavirus 229E, NL63, OC43, HKU1 | Virus | Endemic seasonal coronaviruses |
| SARS-CoV-2 | Virus | Now routinely combined with influenza/RSV (see §11) |
| Human bocavirus | Virus | Extended panels only |
| *Bordetella pertussis* | Bacterium | |
| *Bordetella parapertussis* | Bacterium | |
| *Mycoplasma pneumoniae* | Bacterium | See naming note above |
| *Chlamydia pneumoniae* | Bacterium | See naming note above |
| *Legionella pneumophila* | Bacterium | |
| *Streptococcus pneumoniae* | Bacterium | Semi-quantitative in lower-respiratory (pneumonia) panels |
| *Haemophilus influenzae* | Bacterium | |
| *Moraxella catarrhalis* | Bacterium | |
| *Staphylococcus aureus* | Bacterium | Often with *mecA*/*mecC* resistance markers |
| *Klebsiella pneumoniae*, *K. oxytoca*, *K. aerogenes* | Bacterium | Lower-respiratory (pneumonia) panels |
| *Escherichia coli* | Bacterium | Lower-respiratory (pneumonia) panels |
| *Enterobacter cloacae* complex | Bacterium | Lower-respiratory (pneumonia) panels |
| *Serratia marcescens* | Bacterium | Lower-respiratory (pneumonia) panels |
| *Proteus* spp. | Bacterium | Lower-respiratory (pneumonia) panels |
| *Pseudomonas aeruginosa* | Bacterium | Lower-respiratory (pneumonia) panels |
| *Acinetobacter calcoaceticus–baumannii* complex | Bacterium | Lower-respiratory (pneumonia) panels |

Resistance genes commonly co-reported on lower-respiratory panels: *mecA*/*mecC*, *CTX-M*, *KPC*,
*NDM*, OXA-48-like, *VIM*, *IMP*.

## 2. Gastrointestinal (GI) panel

| Pathogen | Type | Notes |
|---|---|---|
| *Campylobacter jejuni* / *C. coli* | Bacterium | |
| *Salmonella* spp. | Bacterium | |
| *Shigella* spp. / enteroinvasive *E. coli* (EIEC) | Bacterium | Often one combined target |
| *Yersinia enterocolitica* | Bacterium | |
| *Vibrio cholerae*, *V. parahaemolyticus*, *V. vulnificus* | Bacterium | |
| *Plesiomonas shigelloides* | Bacterium | |
| *Clostridioides difficile* (toxin A/B genes) | Bacterium | |
| Enterotoxigenic *E. coli* (ETEC) | Bacterium | |
| Enteropathogenic *E. coli* (EPEC) | Bacterium | |
| Enteroaggregative *E. coli* (EAEC) | Bacterium | |
| Shiga toxin-producing *E. coli* (STEC/EHEC), incl. *E. coli* O157 | Bacterium | *stx1*/*stx2*, *eae* targets |
| Norovirus GI/GII | Virus | |
| Rotavirus A | Virus | |
| Adenovirus F40/41 | Virus | |
| Astrovirus | Virus | |
| Sapovirus | Virus | |
| *Giardia duodenalis* (*lamblia*) | Parasite | |
| *Cryptosporidium* spp. | Parasite | |
| *Entamoeba histolytica* | Parasite | |
| *Cyclospora cayetanensis* | Parasite | |

## 3. Meningitis / encephalitis panel

| Pathogen | Type | Notes |
|---|---|---|
| *Streptococcus pneumoniae* | Bacterium | |
| *Neisseria meningitidis* | Bacterium | |
| *Haemophilus influenzae* | Bacterium | |
| *Listeria monocytogenes* | Bacterium | |
| *Streptococcus agalactiae* (Group B strep) | Bacterium | Neonatal meningitis |
| *Escherichia coli* K1 | Bacterium | Neonatal meningitis |
| Cytomegalovirus (CMV) | Virus | |
| Enterovirus | Virus | |
| Herpes simplex virus 1 & 2 | Virus | |
| Human herpesvirus 6 | Virus | |
| Human parechovirus | Virus | |
| Varicella zoster virus | Virus | |
| *Cryptococcus neoformans* / *C. gattii* | Fungus | |

## 4. Bloodstream infection / blood culture identification panel

| Pathogen | Type | Notes |
|---|---|---|
| *Staphylococcus aureus* | Bacterium (Gram+) | + *mecA*/*mecC* |
| Coagulase-negative staphylococci (e.g. *S. epidermidis*) | Bacterium (Gram+) | |
| *Streptococcus pyogenes*, *S. agalactiae*, *S. pneumoniae*, *S. anginosus* group | Bacterium (Gram+) | |
| *Enterococcus faecalis*, *E. faecium* | Bacterium (Gram+) | + *vanA*/*vanB* |
| *Listeria monocytogenes* | Bacterium (Gram+) | |
| *Escherichia coli* | Bacterium (Gram−) | |
| *Klebsiella pneumoniae*, *K. oxytoca* | Bacterium (Gram−) | |
| *Enterobacter cloacae* complex | Bacterium (Gram−) | |
| *Proteus* spp. | Bacterium (Gram−) | |
| *Serratia marcescens* | Bacterium (Gram−) | |
| *Acinetobacter baumannii* complex | Bacterium (Gram−) | |
| *Pseudomonas aeruginosa* | Bacterium (Gram−) | |
| *Haemophilus influenzae* | Bacterium (Gram−) | |
| *Neisseria meningitidis* | Bacterium (Gram−) | |
| *Candida albicans* | Fungus | |
| *Candida glabrata* | Fungus | current name *Nakaseomyces glabratus* |
| *Candida parapsilosis*, *C. tropicalis* | Fungus | |
| *Candida krusei* | Fungus | current name *Pichia kudriavzevii* |
| *Candida auris* | Fungus | |

Resistance markers commonly co-reported: *mecA*/*mecC*, *vanA*/*vanB*, *KPC*, *NDM*, OXA-48-like,
*VIM*, *IMP*, *CTX-M*.

## 5. Sexually transmitted infection (STI) panel

| Pathogen | Type | Notes |
|---|---|---|
| *Chlamydia trachomatis* | Bacterium | |
| *Neisseria gonorrhoeae* | Bacterium | |
| *Trichomonas vaginalis* | Parasite | |
| *Mycoplasma genitalium* | Bacterium | Some assays add macrolide-resistance mutation targets |
| *Mycoplasma hominis* | Bacterium | |
| *Ureaplasma urealyticum* | Bacterium | |
| *Ureaplasma parvum* | Bacterium | |
| *Treponema pallidum* | Bacterium | Syphilis |
| Herpes simplex virus 1 & 2 | Virus | |
| *Haemophilus ducreyi* | Bacterium | Chancroid; extended assays only |

## 6. Vaginitis / vaginosis panel

| Pathogen | Type | Notes |
|---|---|---|
| *Candida albicans* / *C. glabrata* group / other *Candida* spp. | Fungus | |
| *Trichomonas vaginalis* | Parasite | |
| *Gardnerella vaginalis* | Bacterium | Bacterial vaginosis marker |
| *Atopobium vaginae* | Bacterium | current name *Fannyhessea vaginae* |
| BVAB-2 | Bacterium | Bacterial vaginosis-associated bacterium |
| *Megasphaera* type 1/2 | Bacterium | Bacterial vaginosis marker |
| *Lactobacillus* spp. | Bacterium | Normal-flora marker, not a pathogen |
| *Mobiluncus* spp. | Bacterium | |

## 7. Tick-borne pathogen panel

| Pathogen | Type | Notes |
|---|---|---|
| *Borrelia burgdorferi* sensu lato | Bacterium | Lyme disease |
| *Borrelia miyamotoi* | Bacterium | |
| *Anaplasma phagocytophilum* | Bacterium | |
| *Ehrlichia chaffeensis*, *E. ewingii* | Bacterium | |
| *Babesia microti*, *B. duncani* | Parasite | |
| *Rickettsia* spp. (spotted fever group) | Bacterium | |

## 8. Congenital / perinatal infection panel

| Pathogen | Type | Notes |
|---|---|---|
| *Toxoplasma gondii* | Parasite | |
| Cytomegalovirus (CMV) | Virus | |
| Herpes simplex virus 1 & 2 | Virus | |
| Parvovirus B19 | Virus | |
| *Treponema pallidum* | Bacterium | Congenital syphilis |
| Zika virus | Virus | |
| Rubella virus | Virus | |
| *Streptococcus agalactiae* (Group B strep) | Bacterium | Intrapartum screening, not the congenital panel proper |

## 9. Mycobacterial / tuberculosis panel

| Pathogen | Type | Notes |
|---|---|---|
| *Mycobacterium tuberculosis* complex | Bacterium | Often with *rpoB* (rifampin resistance), *inhA*/*katG* (isoniazid resistance) in extended assays |
| *Mycobacterium avium* complex | Bacterium | Non-tuberculous |
| *Mycobacterium abscessus* complex | Bacterium | Non-tuberculous |
| *Mycobacterium chelonae* | Bacterium | Non-tuberculous |
| *Mycobacterium kansasii* | Bacterium | Non-tuberculous |
| *Mycobacterium fortuitum* | Bacterium | Non-tuberculous |

## 10. Skin and soft tissue infection panel

| Pathogen | Type | Notes |
|---|---|---|
| *Staphylococcus aureus* | Bacterium | + *mecA*/*mecC*, sometimes PVL |
| *Streptococcus pyogenes* | Bacterium | |
| *Streptococcus agalactiae* | Bacterium | |
| *Enterococcus faecalis*, *E. faecium* | Bacterium | |
| *Pseudomonas aeruginosa* | Bacterium | |
| *Serratia marcescens* | Bacterium | |
| *Proteus mirabilis* | Bacterium | |
| *Bacteroides fragilis* | Bacterium | Anaerobe |
| *Clostridium perfringens* | Bacterium | Anaerobe |
| *Finegoldia magna*, *Peptoniphilus* spp. | Bacterium | Anaerobe |

## 11. Combined SARS-CoV-2 / influenza / RSV panel

The simplified triage panel widely deployed since 2020–2021.

| Pathogen | Type |
|---|---|
| SARS-CoV-2 | Virus |
| Influenza A virus (± subtyping) | Virus |
| Influenza B virus | Virus |
| RSV A/B | Virus |

## 12. Group A strep (pharyngitis)

Usually a standalone rapid single-target real-time PCR rather than part of a larger panel, but
extremely common in point-of-care testing.

| Pathogen | Type |
|---|---|
| *Streptococcus pyogenes* (Group A strep) | Bacterium |

---

## How this relates to this project

This project's own exclusivity organism list
([`src/qpcr_assay_check/data/clinical_organisms.yaml`](../src/qpcr_assay_check/data/clinical_organisms.yaml))
is a much smaller, deliberately non-authoritative starter set focused on STI, atypical pneumonia,
mycobacteria and common respiratory pathogens, with human as background — every lab must review and
edit it for its own assay. This document is broader reference material for that curation exercise;
it is not itself wired into the tool, and adding to it does not change any packaged configuration.
