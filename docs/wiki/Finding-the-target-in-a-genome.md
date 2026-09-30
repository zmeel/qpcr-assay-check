# Finding the target in a genome

Before any primer or probe can be judged, the tool has to find **every copy of the assay's
region** in every genome of the target. This sounds easy and is not. Real genomes differ from
the reference in ways that break simple approaches:

- **Divergence.** Related species or lineages carry the region with many substitutions
  (a *Legionella* genus assay spans species whose 23S–5S spacer differs by tens of bases).
- **Insertions and deletions.** A copy can be tens of bases longer or shorter than the reference.
  In the *Legionella* measurement 191 of 283 copies differed in length by more than 20 bases.
- **Several copies per genome.** The *N. gonorrhoeae* opa genes occur about 10 times per genome,
  rRNA operons 3 to 7 times, and the copies can differ.
- **Draft assemblies.** Most genomes are assembled from short reads into many *contigs*.
  Repeated regions break those assemblies, so a copy may be cut by a contig end or collapsed.
- **Unknown bases.** Low sequencing coverage leaves runs of `N`, sometimes over the whole
  region.

The locator described here (the *chain locator*) was designed for these cases and measured on
real genomes before it was built (see [Limits and validation](Limits-and-validation)).

## The reference

For each region (*locus*) the laboratory gives one or more **reference fragments**: the sequence
the assay amplifies, from the 5′ end of the forward primer to the 5′ end of the reverse primer
on the other strand. Optionally a **context accession** is named: a complete genome in which the
fragment occurs. The tool finds the fragment's best copy there and takes up to **1,000 bases on
either side** of it, the *context* or *flanks*. The reference the genomes are searched with is
then

```
   left flank (≤1000 nt)          fragment (e.g. 260 nt)          right flank (≤1000 nt)
 ─────────────────────────────┬──────────────────────────────┬─────────────────────────────
                               F►                       ◄R
```

Why flanks help: the sequence next to the assay region is often more conserved than the region
itself (for *Legionella* the 23S rRNA before and the 5S rRNA after the variable spacer). A copy
whose fragment has diverged beyond recognition can still be placed exactly between its
conserved flanks, and a fragment that reads `N` from end to end can be placed by the flanks
around it.

## Step 1: exact seeds

The reference is cut into overlapping words of **16 bases** (*k-mers*, *seeds*): one starting
at every 2nd base of the fragment, and every 8th base in the flanks. Each seed is looked up
exactly in the genome, on both strands. A seed that occurs more than 50 times in a genome is
ignored (a repeat says nothing about where the copy is).

Searching thousands of flank seeds across a 4-million-base genome would be slow, so the flanks
are searched in **two passes**: first a coarse set of seeds (every 32nd base) over the whole
genome, then the fine seeds only near where the coarse ones hit.

Why 16 bases and every 2nd position: a random 16-mer occurs by chance about once in 4.3 billion
bases (4¹⁶), so a hit in a bacterial genome is rarely chance; stepping by 2 finds any stretch of
17 or more identical bases in the fragment. Measured on *N. gonorrhoeae*, step 2 found
everything step 1 found, while step 4 missed divergent opa copies.

## Step 2: blocks

Seed hits that lie on the same *diagonal* (the same offset between reference and genome) and
overlap are merged into **blocks**: maximal stretches where reference and genome agree exactly.

```
 reference   ····[=====A=====]······[===B===]········[======C======]····
 genome      ····[=====A=====]··x···[===B===]··ins··········[======C======]····
                                 └ substitution          └ insertion shifts the diagonal
```

## Step 3: chains

Blocks that lie **in the same order** on the reference and on the genome, on the same strand,
are linked into a **chain**. Between two blocks the genome may carry substitutions, and the
diagonal may shift by up to **150 bases** (an insertion or deletion). The chain with the most
reference bases is taken first, then the best chain of what is left, and so on. Each chain is
one **candidate copy**.

For each candidate the tool records:

| Evidence | Meaning |
|---|---|
| anchored bases (M) | fragment bases covered by exact blocks |
| context left / right | flank bases covered by exact blocks on each side |
| start, end | where the fragment lies on the copy's own strand, **signed**: a copy cut by the start of a contig starts below 0, one cut by its end ends beyond the contig |
| anchors | the blocks themselves (fragment position, genome position, length) |
| identity | a banded alignment of the region with the fragment: matching bases / fragment bases covered |
| N inside / next to it | unknown bases in the fragment, and N-runs directly beside it |
| region | the fragment with 50 bases either side (plus room for its length difference) |
| molecule | chromosome or plasmid, from NCBI's sequence report or the FASTA description |

Coordinates are never clamped: a copy cut by a contig end keeps its true, partly off-contig
position, so the oligo sites that *are* on the contig are still placed correctly.

## Step 4: the copy rule

A chain is not automatically a copy: a single chance 16-mer somewhere in the genome also makes a
chain. A candidate counts as a **copy** when at least one of three conditions holds:

| Rule | Condition | What it catches |
|---|---|---|
| **(a)** | at least **32** fragment bases in exact blocks | ordinary copies |
| **(b)** | at least **32** flank bases in exact blocks on one side, **and** the fragment has a block, or both sides are anchored, or the copy is cut by a contig end | divergent copies between conserved flanks, copies cut by a contig end |
| **(c)** | identity to the fragment **≥ 0.75** with at least **16** anchored bases | divergent members of a multi-copy family without shared flanks (e.g. opa copies at identity 0.79–0.80) |

The thresholds come from measurements, not assumptions: chains built from random
(shuffled) reference sequences reached **at most 18** anchored bases, so 32 leaves a wide margin;
in *Legionella*, regions that merely resemble the fragment had identity 0.60–0.66 and no
matching flank bases, while real divergent copies had 40 to 792 matching flank bases.

The rule is applied **when the genomes are assessed, not when they are scanned**. Every
candidate is stored with its evidence, so the thresholds
(`variants.min_anchored_bases`, `min_context_bases`, `min_copy_identity`,
`min_identity_anchored_bases`) can be changed without downloading anything again.

Candidates that do not meet the rule are never judged; genomes in which *only* such candidates
were found are reported as "related regions, not the target".

## Step 5: regions hidden by N

When no candidate reaches 32 anchored bases and the genome contains `N`, a second search runs
with **N-tolerant seeds**: a seed may match a genome word containing `N`, as long as at least
half of its bases are real, and at least two seeds must agree on the same place. A copy found
this way is reported as **hidden by N**. It is never judged: an `N` is neither a match nor a
variant. Where exact and N-tolerant candidates overlap, an exact copy wins; an N-tolerant copy
is kept only where no exact *copy* lies.

## Step 6: a second search for divergent copies

Some real copies share no stretch of 16 identical bases with the fragment at all. In the
enterovirus run, EV-C105 and EV-C117 records carry the region at 78–82% identity, but their
longest exact stretches in common with the fragment are 12–13 bases, so steps 1–5 find nothing.

When a genome has no copy under the copy rule, it is searched again with **12-base seeds**. A
candidate from this search counts as a copy only when it has **at least two separate exact
blocks in the fragment**, at least 16 anchored bases and identity **≥ 0.75**; rules (a) and (b),
measured with 16-base blocks, do not apply to it. Only candidates that pass are stored. Measured
on shuffled decoy fragments (about 73,500 virus-sized and 40 bacterial scans): chance chains
with two blocks reached identity 0.64 at most, real divergent copies 0.78 and more; a single
chance block can reach 0.77, which is why two blocks are required. The search for regions hidden
by N keeps 16-base seeds (at 12 bases a single `N` produced false "hidden by N" copies). The
report counts the genomes whose copies were found only this way.

A limitation remains: the second search only runs where no copy was found, so a divergent second
copy in a genome that already has a copy is not searched for. For a known divergent clade, a
second reference fragment from that clade in the assay file is the better fix.

## Records where the region is there but cannot be located

A genome without a copy is split in two: when the sequence on one side of the region (the flank)
was found, the region is there but the fragment could not be located (**present, not
locatable**; possibly an escape); otherwise the region is absent from the record, for example a
record of the coding sequence only. The inclusivity rationale says what the detectable
percentage would be if every "present, not locatable" genome were an escape, so these genomes do
not silently leave the denominator.

## Several references, one place

A locus may have several reference fragments (e.g. one per probe variant or lineage). Each is
searched; where several find the same place on the genome, the candidate with the most anchored
bases, then the highest identity, is kept, and it remembers which reference it matched.

## Where the genomes come from

| Source | Used for | How |
|---|---|---|
| **NCBI Datasets** (`datasets`) | bacteria and other organisms with genome assemblies | every current assembly of the target taxon (atypical ones excluded, one copy per GenBank/RefSeq pair) is listed by release year and downloaded in batches of 20; a failed batch is retried in halves; for assemblies with several sequences the sequence report is fetched to tell chromosomes from plasmids |
| **NCBI Nucleotide** (`blast_partitioned`) | viruses and targets without assemblies | every Nucleotide record of the taxon (optionally narrowed, e.g. `6500:8500[SLEN]` for near-complete enterovirus genomes) is listed with ESearch; records up to 200,000 bases are fetched whole and scanned exactly like assemblies; longer ones are found by BLASTing the reference fragment against lists of 100 accessions at a time, so no search can fill its hit list |

In both cases the newest release year comes first, a run processes at most a set number of new
genomes, and the next run continues. **Only the located regions are kept, never the genomes**
(see [Data storage and cache](Data-storage-and-cache)).
