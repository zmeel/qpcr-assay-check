# Judging primer and probe sites

Once every copy of the region is found (see
[Finding the target in a genome](Finding-the-target-in-a-genome)), each primer and probe is
judged on each copy. The result is a **graded class** per site, a judgement per copy, per
genome, per channel, and finally the inclusivity status.

## 1. Placing each oligo on the copy

The oligo's position in the reference fragment is known. On the copy it is found **through the
nearest exact block** of that copy's chain: the offset between reference and genome is taken
from the block closest to the oligo's site, not from one average for the whole copy.

This matters when a copy is longer or shorter than the reference. With one average offset, an
insertion between the forward primer and the probe shifts every site after it, and the probe is
judged at the wrong place (on the *Legionella* measurement the old single-offset method judged
518 of 1,132 oligo sites at a worse position than the correct one). With the nearest block, each
site lands where the copy actually carries it.

## 2. Aligning the oligo end to end

Around the expected site (±15 bases, to allow insertions or deletions) the oligo is aligned
**semi-globally**: the whole oligo against any part of the window, so an oligo is never scored on
only part of its length. Scoring follows BLAST's short-oligo settings (match +1, mismatch −3, gap
opening 5, gap extension 2). Degenerate oligos are expanded into all their variants and the
best-matching variant counts. When several oligos share a role (two forward primers used as
alternatives in one mix), the best-binding one counts for that copy.

The alignment gives the mismatches and their positions counted from the 3′ end (position −1 is
the terminal base), the mismatch types (primer base facing template base), gaps, and ambiguity
codes in the genome.

## 3. The graded mismatch class

Each site gets one of five classes, from published primer-mismatch studies. Every rule names its
source, and the report prints the rule (R1–R9) next to each class. The full rule set is in
`docs/MISMATCH_CLASSES.md`.

| Class | Meaning |
|---|---|
| **perfect** | no mismatch, no gap |
| **tolerated** | mismatches expected to cost little |
| **at risk** | a measurable delay is expected; relevant near the limit of detection |
| **likely failure** | amplification blocked or strongly delayed in the source data |
| **indeterminate** | no published basis (gaps, some probe mismatches, ambiguity codes) |

The main rules, in short:

- **One primer mismatch in the last 5 bases** (Stadhouders et al. 2010, Table 1, Taq on DNA):
  the class depends on the mismatch *type* (which primer base faces which template base) and
  its *position*. A terminal A–A, A–G, G–A, G–G or C–C mismatch is *likely failure*; at positions
  −3 to −5 every type is *tolerated* with Taq on DNA.
- **One primer mismatch further from the 3′ end** (Lefever et al. 2013): *tolerated*.
- **Several mismatches in one primer** (Lefever 2013), counted within the 3′-most 16 bases, the
  region Lefever tested: two are at least *at risk*; the terminal base plus another within the
  last 5 is *likely failure*; three or four are *likely failure*.
- **Mismatches beyond the 3′-most 16 bases** (Otwell et al. 2025, wet-lab data): alone, up to 4
  are *tolerated* (3–4 of them shifted Ct by at most 2.2) and 5 or more *at risk*, since no data
  cover that many; together with one within the region at least *at risk* (mostly +3 to +6 Ct).
- **The primer pair** (Lefever 2013): 3 mismatches in one primer with 2 or more in the other, or
  4 with 1 or more (within the 3′-most 16 bases), is *likely failure* for the pair, whatever each
  primer alone.
- **Homopolymer length differences** (a primer site that differs only in the length of a run of
  identical bases, e.g. seven A instead of eight): *at risk* for one base outside the last 3,
  otherwise *likely failure*. No PCR study measured these, and they are also a known sequencing
  and assembly error, so the report shows the result under both a strict and a lenient setting
  (`variants.homopolymer_bulges_detectable`).
- **Probe mismatches** (no quantitative data used yet; expert judgement, stated as such): an MGB
  probe with one mismatch is *indeterminate*, with two or more *likely failure*; an unmodified
  probe with one mismatch outside its last 5 bases is *tolerated*, otherwise *at risk*. Both
  theory reviews (`docs/reviews/`) call these the weakest rules and name data not yet used.
- **Deletions in the probe site** (Otwell et al. 2025, wet-lab data): 1–5 deleted bases *at
  risk*; 6 or more *likely failure* (6 bases was tolerated in one assay and fatal in another;
  the worse is taken); a deletion with three or more mismatches *likely failure*. Insertions
  were not tested and stay *indeterminate*.
- **Ambiguity codes in the genome** (R, Y, …): a code that could pair counts as a match beyond the
  last 5 bases; within them the site is graded both ways, and only when that decides between
  detectable and not is the site *indeterminate*.
- **Laboratory evidence**: an `evidence:` entry in the assay file (an oligo variant the laboratory
  tested) replaces the in silico class for every site with exactly that variant.

A site is **detectable** when its class is *perfect* or *tolerated*. Classes present published
data; they are not predicted Ct values.

**Detection, not quantification.** The classes say whether a site is expected to be detected,
not whether a quantity measured through it is right. A single internal mismatch the classes
call *tolerated* can still distort a copy number considerably (Bru et al. 2008 measured up to
1000-fold underestimation). For an assay used to quantify, such as a viral load, a *tolerated*
variant is a reason to check the quantification in the laboratory.

**ΔTm next to the class** (information only). Each site variant in the report also shows the
estimated change in duplex melting temperature against the perfect match (ΔTm, with Tm and ΔG on
hover and in the workbook), from primer3's nearest-neighbour model under the configured reaction
conditions. It helps where the class says little, such as an MGB probe with one mismatch
(*indeterminate*): a mismatch that costs 1 °C and one that costs 8 °C are not the same risk. The
model is for unmodified DNA: MGB, LNA and other modifications are not modelled, and a mismatch at
the 3′-terminal base barely changes Tm although it usually blocks extension. The class remains
the judgement; ΔTm never changes it.

**Calibrated against wet-lab data, not yet validated.** The classes were compared with 132
synthetic templates of 16 SARS-CoV-2 assays measured by Otwell et al. (2025) under one
permissive set of conditions: no template graded *detectable* was delayed by 3 Ct or more, and
every template graded *likely failure* was delayed by at least 3 Ct or not detected. Most delays
of 3–6 Ct are *at risk*. Because rules were adjusted after seeing these outcomes, this is a
calibration, an in-sample fit; independent data are still needed. Details and limits:
`docs/MISMATCH_CLASSES.md`, section 11.

## 4. From sites to a copy, and from copies to a genome

- A **copy is detectable** when every role (forward, probe, reverse) is detectable on it.
- A **genome is judged by its best copy**: the PCR needs only one copy it can amplify. The best
  copy is the one with the best classes, not the one found first. In the *N. gonorrhoeae* run
  the best copy differed from the most confidently found one in 10,474 of 19,970 genomes.

Every genome ends in exactly one **outcome**, decided in one place in this order:

| Outcome | When |
|---|---|
| **detectable from parts** | every copy is cut by a contig end, but every role has a detectable site on some cut copy; the sites may come from different copies, so by default this is *not* counted as detected (`variants.judge_from_parts`) |
| **detected** | at least one detectable copy |
| **undetermined** | no detectable copy, and the only problem has no published basis (a single MGB probe mismatch, a deciding ambiguity code) |
| **possibly unassembled** | a draft genome whose best copy fails but that carries fewer than half the copies typical of the complete genomes in the run: near-identical repeats are often left unassembled, so the copy judged may not be the one the PCR would amplify |
| **not detected** (an escape) | the region is there, no copy is detectable |

Genomes without a judgeable copy are counted apart: **region not found**, **hidden by N**,
**cut by a contig end** and **related regions only**. The report shows each number, so the gap
between "genomes listed" and "genomes judged" is always explained.

## 5. Channels

Each fluorescence channel is judged separately on its own **target taxon**, using each genome's
NCBI taxonomy lineage:

- For a genome **inside the channel's target**: detected, not detected, undetermined, or no
  locus. A **complete genome without the region counts as not detected** (a possible deletion);
  a draft without it is listed apart, since assembly gaps are common.
- For a genome of the scan **outside the channel's target**: *signal* (the channel would light
  up) or *silent*. For the *L. pneumophila* channel in a *Legionella* genus assay, a signal in
  another *Legionella* species is a specificity problem of that channel.
- Taxa marked **out of scope** in the assay file are counted for information only.

A channel detects a genome when one copy carries both primers and one of the channel's probes,
all detectable.

## 6. Inclusivity status

The status uses the **whole fragment** (forward, probe and reverse together on one copy) pooled
over the **last three complete release years plus the current one**, so that it reflects the
strains circulating now rather than historical collections:

- below **95%** detectable: *Review*; below **80%**: *Exceeds limit* (both configurable);
- fewer than **100** judged genomes in the window: *Incomplete*;
- a single year in the window with at least 30 genomes below 80%: *Review*, even when the pooled
  figure has no flags;
- the percentage leaves out the undetermined, possibly-unassembled and from-parts genomes, and
  says how many they are.

Each channel gets its own status by the same limits, and a signal outside its target makes a
channel *Review*. The inclusivity status is the worst of the whole-fragment status and every
channel's status, never better.
