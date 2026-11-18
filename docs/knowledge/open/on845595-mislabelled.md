---
type: Open Item
title: "ON845595.1: an influenza A M sequence filed as influenza B (reported to NCBI)"
description: "The record that makes the influenza A assay read Exceeds limit carries an influenza A M-gene sequence under an influenza B name and taxon. Reported to NCBI (gb-admin) on 2026-11-18; awaiting their answer."
tags: [open, ncbi, influenza, question]
status: draft
stale_after: 2027-05-18T00:00:00Z
generated: { by: claude-code/agent, at: 2026-11-18T12:00:00Z }
sources:
  - id: run
    resource: ../runs/influenza-a-2026-11-18b.md
    title: The influenza A run of 2026-11-18 08:15Z
  - id: ncbi
    resource: "EFetch of ON845595.1 (GenBank flat file), of YP_009118623.1 and YP_009118622.1 (influenza A M1/M2, A/California/07/2009) and of NC_002210.1 (influenza B segment 7, M1 NP_056664.1), all checked live on 2026-11-18"
    title: The records compared at NCBI
  - id: contact
    resource: https://www.ncbi.nlm.nih.gov/home/about/contact/
    title: "NCBI Contact Us (GenBank Help: gb-admin@ncbi.nlm.nih.gov)"
---

# What is open

`ON845595.1` is the only record that makes the influenza A matrix assay read **Exceeds limit**:
the forward primer binds it perfectly, `infa_rev` has one mismatch at -3 (tolerated under R1) and
`infa_probe1` one outside its last 5 nt, so a 141 bp product is predicted and read as
detected.[^run]

The record is titled "Influenza B virus (B/Argentina/def2/2022) segment 7 matrix protein 2 (M2)
and matrix protein 1 (M1) genes, complete cds", 982 bp, `/db_xref="taxon:11520"`, submitted
2022-06-26, released 2023-07-19. Four checks against NCBI's own data, all made live on
2026-11-18, say the sequence is influenza A:[^ncbi]

1. Its own M1 translation (`USO35510.1`, 252 aa) is **250/252 = 99.2% identical** to influenza A
   M1 (`YP_009118623.1`, A/California/07/2009(H1N1)).
2. The same translation is only **62/248 = 25.0% identical** to influenza B M1 (`NP_056664.1`,
   B/Lee/40, `NC_002210.1`).
3. Influenza A M1 is 252 aa and influenza B M1 is 248 aa; this one is 252.
4. Influenza B segment 7 encodes M1 and **BM2**, an unspliced downstream ORF. This record
   annotates a spliced **M2**, `join(1..26,715..982)`, which is the influenza A arrangement, and
   its M2 translation ends in the influenza A M2 C-terminus
   (`...SMREEYQQEQQSAVDVDDGHFVNIELE`).

At nucleotide level its best match to the assay's own 141 nt influenza A reference fragment is
134/141 = 95.0%.

So the assay's flag is a true statement about the public data, not evidence that the assay
detects influenza B. Nothing in the assay file was changed for it: an example assay is not tuned
to silence a flag.

# What it needs

NCBI's answer. Reported by the user on 2026-11-18 to `gb-admin@ncbi.nlm.nih.gov` (the address
NCBI's Contact Us page gives for comments or questions about a sequence);[^contact] only the
original submitter, or NCBI acting with them, can change a record. The draft sent:

> Subject: ON845595.1 appears to contain an influenza A M-gene sequence, annotated as influenza B
>
> Dear GenBank staff,
>
> While checking the specificity of an influenza A matrix-gene RT-PCR against public sequence
> data, our in silico analysis predicted a product on ON845595.1, which is annotated as
> "Influenza B virus (B/Argentina/def2/2022) segment 7 matrix protein 2 (M2) and matrix protein 1
> (M1) genes, complete cds" (taxon:11520, 982 bp, released 19-JUL-2023).
>
> The sequence in that record appears to be influenza A, not influenza B:
>
> - the record's own M1 translation (USO35510.1, 252 aa) is 250/252 (99.2%) identical to
>   influenza A M1 (YP_009118623.1, A/California/07/2009(H1N1));
> - the same translation is 62/248 (25.0%) identical to influenza B M1 (NP_056664.1, B/Lee/40,
>   segment 7 of NC_002210.1);
> - influenza A M1 is 252 aa and influenza B M1 248 aa; this one is 252;
> - the record annotates a spliced M2, join(1..26,715..982), as influenza A has, whereas
>   influenza B segment 7 carries an unspliced BM2; its M2 translation ends with the influenza A
>   M2 C-terminus (...SMREEYQQEQQSAVDVDDGHFVNIELE).
>
> A possible explanation is a sample or file mix-up at submission. We have no connection to the
> submitters and no further information about the isolate.
>
> We mention it because records like this one affect in silico specificity checks of diagnostic
> assays: an influenza A sequence filed under influenza B makes an influenza A assay look as
> though it cross-reacts with influenza B.
>
> Could you look into it, or pass it to the submitters?
>
> With kind regards,
> [name], [institution]

[^run]: The influenza A run of 2026-11-18 08:15Z
[^ncbi]: The records compared at NCBI
[^contact]: NCBI Contact Us (GenBank Help)
