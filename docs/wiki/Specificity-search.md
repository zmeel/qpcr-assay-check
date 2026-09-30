# Specificity search

Inclusivity asks whether the assay still detects its target; specificity asks whether it detects
anything else. The tool searches every oligo against NCBI's nucleotide database with **remote
BLAST**, restricted by taxon, re-aligns every relevant hit over the full oligo length, and
predicts which primer sites could form a PCR product.

## Tiers

The search is split into **tiers**, each restricted to a set of taxa with BLAST's
`ENTREZ_QUERY` (at most 20 taxa per search):

| Tier | Taxa | Role in the verdict |
|---|---|---|
| **target** | the assay's own target | not used for specificity; a check that the oligos still match the target (perfect full-length hits per oligo) |
| **near neighbours** | taxa inside the target that must not be detected (e.g. rhinoviruses for an enterovirus assay) and exclusion taxa | off-target |
| **out of scope** | taxa inside the target that the assay may detect but that are not its purpose (e.g. animal enteroviruses) | information only ("also detects") |
| **exclusivity** | the clinical organism list, resolved to taxonomy IDs | off-target |
| **background** | human (taxid 9606) by default | off-target (genomic DNA in the specimen) |

The taxa excluded from the target (near neighbours) are left out of the target tier's search,
and when the organism list names the assay's own target (a respiratory panel listing
SARS-CoV-2, for a SARS-CoV-2 assay) the target is left out of the exclusivity tier, so the
assay's own target is never counted as off-target.

## Search settings

BLAST is used with settings for short oligos: blastn against `core_nt`, word size 7, E-value
1000, match +1 / mismatch −3, gap opening 5 / extension 2, no low-complexity filter, and up to
5,000 hits per query. Degenerate oligos are expanded into all their variants, each searched as its
own query. Searches are submitted through NCBI's BLAST URL API with the tool's own client, so a
search ID (RID) can be stored and a run that was interrupted resumes the same search instead of
submitting it again.

**What a search can miss.** BLAST reports an alignment only when its expected number of chance
hits (E-value) is at most 1,000. The E-value grows with the size of the search, so the smallest
reportable score does too. NCBI reports the statistics of every search (the effective search
space, λ and K), and from them the tool computes, per tier and oligo, the smallest score the
search could report, E = K · search space · e<sup>−λS</sup> ≤ 1000, and how many mismatches a
full-length site may carry and still always be reported. Measured with the 17-nt *N. gonorrhoeae*
primer against *N. meningitidis* (search space 8.1 × 10⁸): the formula gives scores 10, 8 and 7
for E-values of 1,000, 10,000 and 100,000, and the lowest scores NCBI actually reported were 10,
8 and 7. A site with one internal mismatch (score 13) is reported there; one with two (score 9)
can be missing. A search space 1,000 times larger raises the floor by 5 points. Raising the
E-value is no remedy: at 100,000 the same small search nearly filled its 5,000-hit list. The
report shows the floor per tier and oligo ("Reported down to"); the partner scan below closes
the gap where it matters most.

**A full hit list is only a problem when it is still relevant.** When a query returns the maximum
number of hits and even its weakest hit has at least 14 identical bases, relevant hits may have
been cut off: the tier is marked *saturated* and the result *Incomplete*, with the advice to
search fewer taxa at a time.

## Full-length re-alignment

BLAST reports local alignments: it often stops before the end of the oligo, especially at the
3′ end where a mismatch matters most. Every relevant hit is therefore turned into a **full-length
site**, from most to least certain:

1. **BLAST covers the whole oligo**: its alignment is used as is.
2. **Partial hit, re-aligned**: the subject sequence around the hit (±10 bases) is fetched from
   NCBI and the whole oligo is aligned semi-globally.
3. **Partial hit, worst case**: a hit that provably cannot reach a reportable level is not
   fetched. With match +1 and mismatch −3, an alignment that stops early implies at least one
   mismatch per four unaligned bases (extending would otherwise have raised the score); the
   unaligned bases are assumed to match as well as that allows, the risk-conservative assumption.

Each site is graded **critical**, **warning** or **minor** by configurable limits. By default a
primer site is critical with at most 3 mismatches, no gap and at least 5 matching bases at the
3′ end; warning with at most 5 mismatches, 1 gap and 3 matching 3′ bases.

## Predicted products

A product is predicted when a forward-type and a reverse-type primer site, both at least
*warning*, **face each other on the same record within 2,000 bases**. A probe site at
*critical* level inside the product makes it **likely detected**; otherwise the product is
amplified but not detected by the probe. Products are listed per tier and species, with the
channels whose probes bind inside them. For an RNA assay, a product on a genomic record of a
eukaryote (human by default) carries a note: it matters only if the specimen contains genomic
DNA and no intron separates the primer sites.

**Partner scan.** A product needs two primer sites, but BLAST need not report both: the second
may score below the search's floor. So for every off-target primer site of at least *warning*
level that forms no product from the reported sites, the sequence a product could span (2,000
bases in the direction the primer extends) is fetched, and every primer of the partner role is
aligned in it end to end. A partner site of at least *warning* level that faces the first one is
added (marked "scanned" and "not reported by BLAST"), in the same search tier as the first. Likewise,
inside every product without a reported probe site, each probe is re-aligned end to end; a probe
site of at least *warning* level is added, so a probe site hidden from BLAST still counts. At most
`specificity.partner_scan_max_windows` (1,000) fetches are made per run, partner windows first
(strongest primer sites first), then products; beyond that the result is *Incomplete*. A tier
whose product list was cut at `max_amplicons` is not scanned. Windows are cached. The scan cannot
find a product of which BLAST reported neither primer site.

A primer site that forms no product (no facing partner in range, also after the scan) is
reported as off-target priming, a lower concern than a product.

## Status

- a product the probe would detect, in an off-target tier: **Exceeds limit**;
- a product without probe signal, or critical primer sites without a product: **Review**;
- a saturated search, sites cut by the per-query cap, or failed fetches: **Incomplete**;
- a tier that was configured but not searched: **Not assessed**.

These are configurable (`specificity.severity`). The report's specificity summary states per tier
whether any product is predicted, which primer carries the discrimination, and its closest
off-target site.
