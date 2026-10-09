---
type: Assay
title: Giardia lamblia, SSU rRNA (Verweij 2004 multiplex)
description: One primer pair and a linear FAM/BHQ1 probe in the 18S rRNA gene, 63 bp; the supplied reference sequence was the three oligos concatenated, so the real amplicon was taken from NCBI instead.
resource: ../../examples/giardia_lamblia_ssu.yaml
tags: [assay, example, DNA, parasite]
status: draft
generated: { by: claude-code/agent, at: 2026-10-09T09:00:00Z }
sources:
  - id: assay-file
    resource: ../../examples/giardia_lamblia_ssu.yaml
    title: docs/examples/giardia_lamblia_ssu.yaml (provenance and checks in its header)
  - id: verweij
    resource: "Verweij JJ, Blange RA, Templeton K et al. J Clin Microbiol 2004; 42: 1220-1223"
    title: Verweij et al. 2004, the faecal multiplex the oligos come from
  - id: ncbi
    resource: "live ESearch and EFetch against NCBI Taxonomy and Nucleotide, 2026-10-09"
    title: Taxonomy, record counts and the real amplicon, measured live
  - id: r9
    resource: ../rules/r9-probes.md
    title: R9 - probe mismatches
  - id: session
    resource: ../sessions/2026-10-09-01-giardia-assay.md
    title: "Session 2026-10-09: Giardia assay file"
stale_after: 2027-04-09T00:00:00Z
---

# Provenance

Oligos supplied by the user on 2026-10-09 together with the publication they come from, Verweij
et al. 2004, the faecal multiplex that detects *Entamoeba histolytica*, *Giardia lamblia* and
*Cryptosporidium parvum* in one reaction.[^verweij] The sequences are in the file exactly as the
user wrote them; they were not read out of the paper, so whether they match it is unchecked. The
names are the user's with the spaces replaced by hyphens, which the format requires. The
exclusivity panel was suggested in this session and is the user's to edit.[^assay-file]

# Design

| Role | Oligo | Position in the 63-nt amplicon |
|---|---|---|
| forward | RealT-G.lamblia-F (20 nt, R at 14) | 1-20, exact |
| probe | RealT-G.lamblia-P (20 nt, FAM, BHQ1) | 27-46, same strand, exact |
| reverse | RealT-G.lamblia-R (16 nt) | binds 48-63, exact |

Product 63 bp, GC 73%. The three oligos tile the region almost end to end: a 6-nt spacer between
the forward primer and the probe, one base between the probe and the reverse site. The probe is
linear, so the unmodified-probe ladder of [R9](../rules/r9-probes.md) applies.[^r9] Target
*Giardia duodenalis* (5741); template DNA. Nothing inside the target is excluded: assemblages A
and B both infect humans and a pan-Giardia assay should detect both.

# The supplied reference sequence was not a real amplicon

The user gave a 56-nt "reference sequence" that is the three oligos concatenated with nothing
between them. No such sequence exists in Giardia: the real template carries a 6-nt spacer
(`GCACCC`) between the forward primer and the probe and one `C` between the probe and the reverse
site, so the product is 63 bp. Of 60 *G. duodenalis* SSU rRNA records sampled live, 55 carry the
probe and **41 carry the whole 63-nt amplicon exactly** (37 with G at the primer's degenerate R,
4 with A), and none carries the 56-nt form.[^ncbi]

So the file takes the real amplicon in both of its forms as its references, each named after a
record that holds it exactly, and the header records what was supplied and why it was not used.
A stitched reference would have been worse than useless: the region is located by exact 16-base
seeds, and every seed crossing one of its two junctions matches nothing.

# Taxonomy and the variant source

NCBI's scientific name is **Giardia duodenalis** (5741); "Giardia lamblia" and "Giardia
intestinalis" resolve to the same taxon only through the `[All Names]` synonym fallback, so the
file gives the number.[^ncbi] The gene is SSU (18S) rRNA: the probe and the reverse site sit in
rRNA records (LC947396.1, PZ685973.1), not in the beta-giardin, gdh or tpi genes that most other
Giardia records cover.

`blast_partitioned`, narrowed to rRNA titles: the rRNA genes are multi-copy and almost every
Giardia record is a single gene, so there is no assembly to walk. Measured live on 2026-10-09:
54,162 Nucleotide records for 5741, of which **2,791** match the query - one run at a 3,000
budget, much like [E. histolytica](entamoeba-histolytica-ssu.md).

One caveat for reading a run: many of those records are short deposits of 107-120 nt, i.e. PCR
products of about this region. Records that exist *because* an assay of this region worked are
not independent evidence that it works.

# Exclusivity panel

Suggested here, in four groups: the co-targets of the same reaction and their near neighbours
(*E. histolytica*, *E. dispar*, *C. parvum*, *C. hominis*), the rest of the genus (*G. muris*,
*microti*, *ardeae*, *psittaci*, *agilis*, *cricetidarum*, *peramelis*), the nearest intestinal
flagellates outside it (*Spironucleus*, *Hexamita*, *Chilomastix mesnili*, *Retortamonas
intestinalis*, *Enteromonas hominis*, *Pentatrichomonas hominis*, *Trichomonas vaginalis*) and
the rest of the faecal differential (*Dientamoeba fragilis*, *Blastocystis*, *Cyclospora
cayetanensis*, *Cystoisospora belli*, *Enterocytozoon bieneusi*). Every name resolves to exactly
one taxon by scientific name.[^ncbi] Gut bacteria are deliberately in the background tier
instead (`search.background_taxids: [9606, 562, 816]`), because the oligos sit in 18S rRNA while
the bacterial flora is the largest mass of DNA in a stool.

# Oligo QC (`run --qc-only`, no network)

**Review**: 0 outside the limit, 8 outside the preferred range, all of them the design itself -
a GC-rich rRNA target and a deliberately short, hot amplicon. The forward primer is 65% GC with a
Tm of 67.3-69.2 C, the reverse primer is 16 nt at 68.8% GC with 4 G/C in its last 5 nt, the
primers are 4.0 C apart in Tm, and the amplicon is 71-73% GC. The three sites are exact and the
product is the whole reference, with no flanking bases.

# Runs

None yet.

[^assay-file]: docs/examples/giardia_lamblia_ssu.yaml (provenance and checks in its header)
[^verweij]: Verweij et al. 2004, the faecal multiplex the oligos come from
[^ncbi]: Taxonomy, record counts and the real amplicon, measured live
[^r9]: R9 - probe mismatches
[^session]: "Session 2026-10-09: Giardia assay file"
