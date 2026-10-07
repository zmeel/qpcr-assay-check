# Graded mismatch classes (FEATURE_IDEAS #9)

Status: **built (unreleased)**, as described here, with the user's changes of 2026-09-25: no
lab-specific setting for the reaction mix, and the classes replace the old rule directly. Written 2026-09-25 at the user's request from the two papers
the user supplied (Stadhouders et al. 2010; Lefever et al. 2013; citations and study designs in
FEATURE_IDEAS #9), and checked against both PDFs by the advisor subagent the same day (its
corrections are applied). Every rule below names its source; where
no source exists the rule says so and the tool must not pretend otherwise. No thresholds of our
own invention; no predicted Cq values. In silico classes do not replace experimental validation.

## 1. Why

Today a site is "detectable" with at most 1 mismatch, no gap and no mismatch in the last 5 nt of
the 3' end, the same for every oligo and every chemistry. Both papers show that the effect of a
primer mismatch depends on its **position**, its **type** (which primer base faces which template
base), the **number** of mismatches in one primer and across the pair, and the **reaction setup**
(polymerase / one-step RT-PCR). The binary rule is too strict for mild mismatches (e.g. the
EV-D68 C-A at -3 in the enterovirus reverse primer, 816 of 5,130 records in our live run of 2026-09-25, scored as an escape) and
says nothing about how bad a failing site is.

## 2. Classes (per primer site, and per primer pair)

| Class | Meaning in the report |
|---|---|
| `perfect` | no mismatch, no gap |
| `tolerated` | mismatches expected to cost little under the lab's setup |
| `at_risk` | a measurable delay is expected; relevant near the limit of detection |
| `likely_failure` | amplification blocked or strongly delayed in the source data |
| `indeterminate` | no published basis (gap/bulge, ambiguity code in the genome, probe mismatch rules, ...) |

Classes, not numbers: the papers' absolute delays differ by master mix and detection chemistry
(Lefever: terminal mismatch 5-7 dCq depending on the mix; Stadhouders: overall impact up to
sevenfold different between mixes, and the two one-step RT-PCR kits "showed entirely opposing
phenomena", pp. 109, 116). The report shows the class, the rule that gave it and the source.

## 3. One basis for every lab (no mix setting)

The user decided against a setting for the reaction mix (e.g. Taq on DNA vs one-step RT-PCR
kits): the tool is meant for many laboratories, and such a setting is too specific. R1 therefore
uses one column of Stadhouders' Table 1, **Taq polymerase on DNA** ("standard"), which applies to
both primers, and the report prints a fixed caveat: the size of a mismatch effect differs between
master mixes, and in one-step RT-PCR a mismatch in the reverse (RT) primer can matter less or more
than on DNA (Stadhouders: with Taq + MMLV all 24 reverse-primer mismatches cost < 0.7 Ct; with rTth
the reverse primer was the more sensitive one). The other columns stay documented in section 10
for the laboratory's own interpretation.

## 4. Rules for one primer site

Positions are counted from the 3' end: -1 is the terminal base (Stadhouders nt 1, Lefever
distance 0). Mismatch type is written primer-template (Stadhouders' convention): the primer base,
then the base on the template strand facing it. A degenerate position that still matches is not a
mismatch and takes no class, but it is named (`-9 Y=T`) and drawn as a grey letter rather than a
dot, because two site variants can differ in nothing else; the duplex Tm of such a site is
computed for the member of the mix the template takes, not for the degenerate code.

**R1. Last 5 nt, a single mismatch** (Stadhouders Table 1, p. 116): classes by type group, position
and setup.

- Type groups: *G1* A-A, A-G, G-A, G-G, C-C; *G2* T-T, T-C, C-T; *G3* C-A, A-C, G-T, T-G.
- Position groups: terminal (-1), penultimate (-2), -3 to -5.
- Table 1 gives "avoid" or "acceptable" per group x position x setup, separately for forward and
  reverse primers in the one-step setups (full lookup in section 10). "Acceptable (for general
  applications)" means the effect was "generally <2,0 Ct" (Table 1 footnote); "avoid" is not
  defined numerically. Single non-terminal mismatches occasionally cost up to 5.96 Ct (Taq on
  DNA, p. 111), so "acceptable" is not a guarantee.
- Encoding (ours): "avoid" -> `likely_failure` at -1, `at_risk` at -2 to -5; "acceptable" ->
  `tolerated`. Mapping "avoid" to two classes by position is our presentation choice, not the
  paper's; the terminal G1 mismatches cost 8.29-9.09 Ct, G2 3.77-4.75 Ct, G3 0.99-1.91 Ct with Taq
  on DNA (pp. 111-113).
- Only positions 1, 2, 3 and 5 were mutated (p. 110); Table 1 groups "positions 3-5". Applying it
  to -4 is our interpolation: print "interpolated".
- Where Stadhouders and Lefever disagree (terminal C-T/T-C: intermediate in Stadhouders, among the
  smallest in Lefever), take the worse, except terminal G2 below.
- **Terminal G2 (T-T, T-C, C-T) is `at_risk`, not `likely_failure`** (user decision 2026-10-02,
  after reading two more sources the theory reviews named):
  - Stadhouders: "avoid", 3.77-4.75 Ct with Taq on DNA (pp. 111-113): a delay, not a block.
  - Kwok S, Kellogg DE, McKinney N, Spasic D, Goda L, Levenson C, Sninsky JJ (1990). Nucleic
    Acids Res 18(4):999-1005, doi:10.1093/nar/18.4.999. Table III (p. 1001), PCR yield relative
    to a perfect match at 800 uM dNTPs, 30 cycles: T-T, T-C, C-T all 1.0.
  - Huang MM, Arnheim N, Goodman MF (1992). Nucleic Acids Res 20(17):4567-4573,
    doi:10.1093/nar/20.17.4567. Single-step extension efficiency by Taq (enzyme kinetics, not
    PCR yield): C-T 2x10^-2, the most easily extended mispair (p. 4570); T-C and T-T 10^-4 to
    10^-5 (p. 4567).
  - Lefever: terminal C-T/T-C among the smallest effects.
- **Terminal G1 and G3 are unchanged.** G1: all three agree (Kwok: A-G, G-A, C-C yield <0.01,
  A-A 0.05, G-G 1.0 at 800 uM but poor at 50 uM dNTPs; Huang <10^-6, A-A about 2x10^-6). G3:
  Stadhouders "acceptable" (0.99-1.91 Ct) and Kwok 1.0 agree; Huang measured 10^-3 to 10^-4 by
  kinetics, printed in the note only. The molecular-biologist review's claim that terminal G3
  "contradicts two foundational datasets" does not hold for Kwok 1990; Huang himself notes that
  in Kwok's PCR only 4 of the 12 terminal mismatches were extended inefficiently (p. 4572).
- Kwok (p. 1003, "data not shown"): a terminal mismatch other than T plus another in the last 4
  bases cut yield at least 100-fold (supports R3); with a T at the terminus, an extra penultimate
  mismatch cut it only 5-10-fold and two Ts 2-5-fold. Not encoded (no data shown).

**R2. Single mismatch beyond the last 5 nt**: `tolerated`, with the note "moderate effect, can be
tolerated" for -6 to -8 (Lefever abstract, p. 1470) and "almost negligible" from -9 on (Lefever
p. 1477: "almost negligible for position 8 and higher"; Lefever counts positions from 0 at the
3' terminus, so their position 8 is -9 here). Both rest on one experiment (440 assays, one mix,
SsoAdvanced SYBR, supplementary Fig. 7, not checked): print that. Keeping -6 to -8 at
`tolerated` also keeps the classes monotonic (R1 gives `tolerated` at -3 to -5 for every group
with Taq on DNA). Lefever tested the 3'-most 16 nt of 20-mers (p. 1472); farther positions are
untested.

**R3. Several mismatches in one primer** (Lefever pp. 1472, 1476-1479; Stadhouders pp. 113-115).
The effect of 2 or more mismatches grows at low input (Lefever p. 1478: the input independence was
lost at 20 molecules for 2 mismatches and at 20-2,000 for 3), so these classes carry the note
"worse near the limit of detection".

- the terminal base plus any other within the last 5 nt: `likely_failure` (Lefever: mean dCq
  7.93-12.15, 244- to 4545-fold, p. 1472; Stadhouders: several mismatches within the last 3 nt
  including the terminal one gave no amplification in the two Taq setups, pp. 113-114, while rTth
  still amplified at 6.65-7.64 Ct, p. 114). Both papers' multiple-mismatch data always include
  the terminal base; two in the last 5 without it fall under the next bullet;
- 2 within the 3'-most 16 nt: at least `at_risk` (Lefever p. 1477: 2-mismatch combinations gave
  "more pronounced inhibition ... even when they were located near the 5' end"; Fig. 6, median
  about 7.7 dCq, read from the figure);
- **Counted within the 3'-most 16 nt** (since 2026-09-30, user decision after section 11): the
  region Lefever tested (p. 1472). The counts below and R8 use only mismatches within it.
  Mismatches beyond -16 (**R3b**): alone, up to 4 `tolerated` (Otwell 2025: 3-4 of them shifted
  Ct by at most 2.2) and 5 or more `at_risk` (beyond the measured data; code review and user
  decision 2026-09-30, no Otwell outcome changes); together with at least one within the region,
  at least `at_risk` (Otwell 2025: one within plus 3 at -20..-22, mostly +3 to +6 Ct, never
  undetected at 50 copies);
- 3: `likely_failure` (since 2026-09-30; before, `at_risk` without one in the last 5 nt: Lefever
  "less pronounced and depended on the mismatch position", p. 1479, but Fig. 6 median about 15
  dCq, read from the figure; Otwell 2025: 3 within the region, none in the last 5, +6 to +7 Ct,
  2 of 3 undetected at 50 copies);
- 4: `likely_failure` (Lefever: blocked "almost completely"), except 4 internal adjacent
  mismatches, which the authors attribute to "their location near the primer's 5' end" (p. 1476,
  Fig. 5); the paper gives no size for this exception, `at_risk` is our choice. The code applies
  it to any 4 adjacent mismatches with none in the last 5 nt (e.g. -6 to -9), wider than the
  paper's example near the 5' end, and only when there are no further mismatches beyond -16
  (Otwell 2025: 4 adjacent at -13..-16 plus 3 at the 5' end, +13.6 Ct).
- These counts come from DNA assays (Lefever: intercalating dye, 20-mers, no RT step);
  Stadhouders' multi-mismatch RNA constructs were all in the forward primer (p. 114). They are
  not relaxed for the reverse primer in one-step RT-PCR (untested).

**R4. Reverse primer in a one-step RT-PCR** (Stadhouders setup ii, p. 113): with Taq + MMLV all
24 tested reverse-primer mismatches cost < 0.7 Ct, only 1 of 24 significant (p. 113), "most likely
caused by" the mismatch acting only in the RT step (p. 116; the reverse primer is the RT primer,
and the cDNA then carries the primer's own sequence). The authors also name the lower RT
temperature (48 C) and reverse transcriptases extending mismatches 100-1000-fold more
efficiently than Taq as possible factors; the lab's mix runs its RT at 50 C for 5 min. With rTth
the reverse primer was the more sensitive one. Not encoded (no mix setting, section 3): it is part
of the caveat the report prints.

**R5. Gaps (bulges)**: `indeterminate`. Neither paper tested insertions or deletions. A gap can
only make a site worse, so when the site's mismatches alone already give `at_risk` or
`likely_failure`, that class stands, noted "plus a gap" (user, 2026-09-26: a probe variant with 7
mismatches and a gap was reported indeterminate). Applies to probes and to primer gaps that are
not a homopolymer length difference (R5b), except deletions in a probe site (R5c). An oligo base at either end without a partner base in
the genome (the alignment starts or ends with a genome gap) is read as a mismatch at that
position, not as a gap: at the 5' end an overhang, at the 3' end a terminal mismatch (user,
2026-09-26).

**R5c. Deletions in a probe site** (built 2026-10-01, from the two theory reviews in
`docs/reviews/`): probe bases without a template partner, not at the probe's ends, graded from the
deletions Otwell et al. 2025 measured in probe sites. C4 ORF8 (26-nt probe site): deletions of up
to 6 nt gave Ct shifts of at most 5 and no failed detection, also at 50 copies; 7 nt gave a mean
Ct above 40 at 50 copies; 8 nt was not detected at any level. ncov_n_gene, 3 nt: about +3 Ct,
detected. Young-S, 3 nt plus three mismatches: not detected at any level. Yale 69/70 del, 6 nt: not
detected at any level. Encoded: 1-5 nt `at_risk`; 6 nt or more `likely_failure` (at 6 nt the
assays disagree and the worse is taken); a deletion with three or more mismatches
`likely_failure`; with one or two mismatches `at_risk`, noted as a combination not measured.
Insertions in the template within a probe site were not tested and stay R5.

**How far the data reach** (advisor's literature search, 2026-10-07, after the user questioned
the lenient classes). A search of PubMed and Europe PMC for a deletion in a probe binding region
returns this one study; the whole dataset is 15 templates from 4 assays, and the classes carry
these limits, which the report and the site notes now state:

- **Probe length and chemistry.** All four assays use 25-28 nt linear ZEN/IBFQ probes. No study
  measured a deletion under an MGB or other Tm-raising probe, or under a shorter probe. A site on
  a probe outside that range keeps the class but is flagged "no measured data": a 26-mer with a
  6-nt gap keeps paired arms of about 12 and 8 nt, a 19-mer keeps about 6 and 7.
- **Deletion lengths.** 1, 3, 4, 6, 7 and 8 nt were measured; **2 and 5 nt never were**, so those
  two classes are interpolated and say so.
- **Conditions.** 55 C annealing (not 60) and 50 cycles (not 40), chosen by the authors to be
  permissive, so the thresholds are upper bounds on tolerance: their 7-nt template gave a mean Ct
  of 41.0 at 50 copies, already a false negative under a 40-cycle cut-off.
- **Sequence, not length, decides.** At 6 nt the same study has two near-identical geometries
  with opposite outcomes: C4 ORF8 (arms 12 + 8) detected at +4.0 Ct, Yale 69/70 del (arms 11 + 8)
  not detected at any level in four templates. The length thresholds are a calibration
  convenience, not a mechanism.
- **The failure is of signal, not amplification.** The authors' minimum positive fluorescence
  falls from 14,000-27,000 to about 2,900 at 6 nt while the Ct moves only +4, and they recovered
  dim curves for a failing template on fluorescence-focusing plates. Which side of the threshold
  a given instrument and plate land on is therefore not predictable from sequence.
- **Real-world cases are all 6 nt** (the TaqPath S-gene dropout and the like); no clinical case of
  a 1-5 nt probe-site deletion with a measured outcome has been published.

**R5b. Homopolymer length differences in a primer site** (built 2026-09-26, advisor subagent; the
class is ours): a single gap block that only changes the length of a run of at least 3 identical
bases in the primer. One base, with the run ending outside the last 3 nt: `at_risk`; two or more
bases, or a run reaching the last 3 nt: `likely_failure`; with further mismatches, the worse of
this and their class. No PCR study measured such bulges (advisor's search). What exists: single
bulges inside a run are comparatively stable (Zhu & Wartell, Biochemistry 1999;38:15986; Tanaka
et al., Biochemistry 2004;43:7143, nearest-neighbour parameters for single bulges) and primers
are seen to slip across homopolymers (Elbrecht et al., Sci Rep 2018;8:10999); the advisor read
the abstracts. Other gaps stay R5. `homopolymer_bulges_detectable: true` still counts a labelled
run-length variant without mismatch as detectable; the report shows the count under both
settings and a breakdown of how far to trust the variants (copies that disagree, assembly level),
since run length is a known sequencing and assembly error.

**LAB. Laboratory evidence** (built 2026-09-26 on the advisor's advice; user request): an
`evidence:` entry in the assay file (oligo name, the site exactly as the report writes it,
outcome detected | not_detected, and the laboratory's reference) replaces the in silico class for
every site of that oligo with exactly that variant: detected = `tolerated`, not detected =
`likely_failure`; the in silico class stays in the note. Meant for the undetermined single MGB
probe mismatches (R9) and homopolymer bulges (R5b), where no published data exist. An entry that
matches no site is flagged in the report.

**R6. Ambiguity codes in the genome sequence** (R, Y, ... in a consensus). Built: a code that can
pair with the oligo base counts as a match when it lies beyond the last 5 nt. In the last 5 nt the
site is graded twice, with the code as a match and as a mismatch: when both give a detectable
class (or both do not), that class is kept (the worse one if both are detectable; the note says
when the code could make a failing site worse); only when the code decides between detectable
and not is the site `indeterminate` (R6). So an ambiguity code never hides a real failure. A
code that cannot pair with the oligo base is a mismatch. No source; this is a presentation of
uncertainty, not a prediction.

**R7. Degenerate primers**: the best-matching variant is used (as now). No source for the effect of
a partially matching primer pool; print that the class assumes the matching variant is present at
its share of the pool.

## 5. The primer pair

**R8** (Lefever p. 1478): 3 mismatches in one primer with >= 2 in the other, or 4 with >= 1 in the
other (counted within the 3'-most 16 nt of each primer, see R3), blocked amplification "almost
completely": `likely_failure` for the pair, whatever the
single-site classes (the figure inset also shows 5 in total blocking almost completely). A pair's
class is otherwise the worse of its two primer classes, flagged when the pair has >= 4 mismatches
in total: 2/2, 1/3 and 1/4 already have medians of about 15-16 dCq in Fig. 6 (read from the
figure), for which the paper states no rule, so the worse single class may understate.

## 6. Probes

**R9**: Stadhouders and Lefever tested no probe mismatches. The rule for a single MGB mismatch is
position-aware since 2026-10-02 (user decision, after the full text of Kutyavin IV, Afonina IA,
Mills A, Gorn VV, Lukhtanov EA, Belousov ES, Singer MJ, Walburger DK, Lokhov SG, Gall AA, Dempcy
R, Reed MW, Meyer RB, Hedgpeth J (2000). Nucleic Acids Res 28(2):655-661,
doi:10.1093/nar/28.2.655). For a probe with the MGB at its 3' end, as in Kutyavin and TaqMan
MGB probes:
- MGB probe, 1 mismatch in the 3'-most 7 nt: `likely_failure`. The MGB folds into the minor
  groove of the terminal 5-6 bp (p. 655) and can slide 1-2 bp toward the 5' end (pp. 657, 661).
  A mismatch there is far more destabilising: T/G under the MGB dTm 15 vs 6 C and ddG 5.6 vs 2.0
  kcal/mol without MGB (p. 657); 7 nt from the 3' end dTm 11 vs 6.5 C (p. 660); a 12-mer with a
  mismatch 5 nt from the 3' end gave no meaningful signal on the mismatched template from 55 to
  70 C in real-time PCR (Fig. 7, p. 659). The authors could not explain why A/C at the terminal
  base and C/A at position 6 discriminated less (p. 657): the note says so.
- MGB probe, 1 mismatch further toward the 5' end: `indeterminate` (undetermined; neither
  detected nor an escape). At 11 nt from the 3' end the MGB added nothing (dTm 8.5 C with and
  without, p. 661); how the short probe then behaves in PCR is not shown.
- MGB probe, 2 or more mismatches: `likely_failure`, position-free (a short MGB probe is not
  expected to form a stable duplex; expert judgement). Before 2026-09-25 (later) this was
  `at_risk`, which ranked milder than a single mismatch.
- Unmodified probe: 1 mismatch outside the last 5 nt `tolerated`; 1 mismatch in the last 5 nt or
  2 anywhere `at_risk`; **3 or more `likely_failure`** (user decision 2026-10-07). Until then the
  rule had no ceiling, so any number of mismatches was `at_risk`: the Legionella run of
  2026-10-02 graded an 11-mismatch, 2-gap site of the unmodified 35-nt LEGpneu probe `at_risk`
  while the 19-nt MGB LEGgenus probe with 7 mismatches on the same genome was `likely_failure`.
  The 2-mismatch step has a measurement behind it: Klungthong et al. 2010 (J Clin Virol
  48(2):91-95) found an unmodified 30-mer probe with two mismatches still detected every sample,
  with the mean Ct gap to the reference target widening from 5.58 to 9.28 (Table 3, p. 93). The
  ceiling at 3 is expert judgement with no source, the same standing as the MGB rule above.
- Deletions in the template within the probe site: R5c (section 4), the one probe rule with a
  measured basis.

Both theory reviews of 2026-10-01 (`docs/reviews/`) ranked the probe rules as the weakest part of
the classes. Read since (2026-10-02):
- Kutyavin 2000: the MGB rule above.
- Klungthong C, Chinnawirotpisan P, Hussem K, Phonpakobsin T, Manasatienkij W, Ajariyakhajorn C,
  Rungrojcharoenkit K, Gibbons RV, Jarman RG (2010). J Clin Virol 48(2):91-95,
  doi:10.1016/j.jcv.2010.03.012. The WHO swH1 probe is an unmodified 30-mer with an internal
  BHQ1 quencher, not an MGB probe (Table 1, footnote b, p. 92), and no false negatives are
  reported: every sample was detected (swH1 Ct up to 38.53, p. 92). Viruses with two probe
  mismatches (3rd base from the 5' end and the 16th) plus reverse-primer mismatches had a mean
  Ct gap to InfA of 9.28 against 5.58 with the 16th-base mismatch only; homologous oligos
  recovered 4.59 Ct (Table 3, p. 93). Consistent with the unmodified-probe rule (2 mismatches
  `at_risk`); the reviews' "clinical false negatives" overstates it.
- Süß et al. 2009 (single mismatches in unmodified probes) could not be obtained; the rule for a
  single mismatch in an unmodified probe stays expert judgement.

## 7. What changes in the reports

- Variant tables: a class column, the rule (R1-R9) and the source.
- Inclusivity per year: counts per class instead of one "0-1 mismatch, clean 3' end" percentage;
  the verdict thresholds (`warn_below_percent`, `fail_below_percent`) apply to
  `perfect + tolerated`; `at_risk` counts as not detected.
- **Undetermined** (user decision 2026-09-25): a single mismatch in an MGB probe outside its
  3'-most 7 nt (R9; since 2026-10-02 one inside them is `likely_failure`) and an
  ambiguity code in the genome in the last 5 nt that decides the class (R6) are neither detected
  nor escaped: left out of the inclusivity percentage and counted as "undetermined" genomes, not
  escapes (also in the panel check). A year in which every record is undetermined gets no
  percentage and does not count in the verdict; the rationale says so. Other
  `indeterminate` sites are not: an unexplained gap near a primer's 3' end is often how the
  aligner writes two mismatches (seen in a test), so it counts as not detected, as before the
  classes; homopolymer bulges follow `homopolymer_bulges_detectable`. An MGB probe with 2 or more
  mismatches is `likely_failure` (R9).
- Copies/escapes: a genome's best copy is chosen by the class (then as now).
- History: a class change for a known variant is a history event (not built yet; the history
  compares the per-year detectable percentages).
- No switch back to the old rule (kept simple). Records made before the classes still load: their
  inclusivity windows have no class counts and keep the old "0-1 mismatch, clean 3' end" figure,
  so the first comparison with such a record shows a change once.
- The homopolymer-bulge setting stays: with `homopolymer_bulges_detectable: true` an
  `indeterminate` bulge without mismatch counts as detectable, as before.

## 8. Worked examples (what the proposal would say)

- **EV-D68, enterovirus reverse primer, C-A at -3**: G3 at positions 3-5, Taq on DNA: Table 1
  "acceptable" -> `tolerated`. (The rTth column would say "avoid in REV"; covered by the caveat.)
  -3 C-A was not itself tested (only at -1 and -5); wet-lab check with an RNA template advised.
- **N. gonorrhoeae reverse primer, poly-A 7 -> 8/9**: the run ends at -4, so poly-A 8 (one base)
  is `at_risk` and poly-A 9 (two bases) `likely_failure` (R5b), with the count under both
  homopolymer settings. Live 2026-09-25: 68.9% detectable strict, 85.7% with bulges tolerated.
- **Enterovirus forward primer F2 on Poliovirus 2 UGA_22 records (3 mismatches, 3' end intact)**:
  R3 -> `at_risk` if none in the last 5 nt (our encoding; Lefever's 3-mismatch median is about 15
  dCq, so this may understate). The positions of the 3 mismatches within F2 still have to be
  shown from the records.

## 9. Built, and still open

Built: `oligo/grade.py` (R1-R3, R5, R5b, R6, R8, R9), grades on every target site of the variant
analysis (both sources) and of the sampled inclusivity, detectability and the primer-pair rule in the genome
judgement, class counts per year (report and workbook) with the verdict on perfect + tolerated,
the class on every variant row, tests per rule.

Still open:
1. Check Table 1 once more against the PDF (the encoded cells are in `oligo/grade.py`).
2. Kutyavin 2000 (MGB probes): done 2026-10-02 (R9 position-aware).
3. R7 (degenerate primers) is only a note; the pair flag at >= 4 mismatches in total is not shown
   yet.
4. A live rerun of the NG and enterovirus assays to see the classes on real data.

## 11. Calibration against wet-lab data (Otwell et al. 2025)

**This is a calibration set, not a validation.** The rules were changed after seeing these
outcomes (R3/R3b/R8 on 2026-09-30, R5c on 2026-10-01), so the agreement below is in-sample fit.
Independent data are still needed: e.g. Knight et al. 2025 (Sci Rep 15:16184), the 90 templates
behind GoPrime (Howson et al. 2020, Pathogens 9:303) or the laboratory's own tests (the methods
advisor's review, `docs/reviews/`).

Otwell T, Knight B, Coryell M, et al. Reality check: testing the in silico predictions of false
negative results due to mutations in SARS-CoV-2 PCR assays using templates with mismatches in
vitro. Front Cell Infect Microbiol 2025;15:1524025 (CC BY 4.0), supplementary Tables 1-2: 16
assays, synthetic DNA templates at 50-50,000 copies, one set of permissive conditions for all
(TaqPath 1-Step, annealing 55 C instead of 60, primers 900 nM, probes 250 nM ZEN/IBFQ, 50
cycles). Every DNA template was graded with this module (probes as unmodified) and compared with
its measured Ct shift at 50,000 copies against the positive control of its run, and detection at
50 and 5,000 copies. One template (France_nCoV_IP2 FN5140) is left out: the reverse primer of
supplementary Table 1 already carries 2 mismatches against that run's positive control.

| Outcome (132 templates) | no relevant shift | +1.5-3 Ct | >= +3 Ct | undetected at 50 copies | undetected at >= 5,000 |
|---|---|---|---|---|---|
| before: detectable (26) | 22 | 4 | 0 | 0 | 0 |
| before: at risk (54) | 27 | 4 | 8 | 10 | 5 |
| before: likely failure (52) | 7 | 7 | 31 | 6 | 1 |
| after: detectable (35) | 28 | 6 | 0 | 1 | 0 |
| after: at risk (88) | 28 | 9 | 36 | 10 | 5 |
| after: likely failure (9) | 0 | 0 | 3 | 5 | 1 |
| after R5c: detectable (35) | 28 | 6 | 0 | 1 | 0 |
| after R5c: at risk (81) | 28 | 9 | 34 | 10 | 0 |
| after R5c: likely failure (16) | 0 | 0 | 5 | 5 | 6 |

Read: `detectable` held in both versions (the one template undetected at 50 copies after the
change, Chan-S FN4676, has 3 mismatches only beyond -16 and a +1.1 Ct shift at high copy
numbers, next to a control at Ct 37.6 at 50 copies). Before the change all 7 `likely failure`
templates without a measurable shift had 4 primer mismatches, 3 of them at the 5' end; after it,
every `likely failure` template was delayed by at least 3 Ct or undetected. `at risk` now holds
most delays of 3-6 Ct, as its definition says (a measurable delay, relevant near the limit of
detection). Before R5c the templates undetected even at >= 5,000 copies graded `at risk` were
probe deletions and one probe site with 3 mismatches and a deletion; with R5c (2026-10-01) all six
are `likely_failure`, as are two C4 ORF8 templates delayed by 3 Ct or more. One of those, FN5446
(6 nt deleted in C4 ORF8), was detected with a delay: R5c takes the worse outcome at 6 nt because
the same deletion length failed completely in the Yale 69/70 del assay. Limits: SARS-CoV-2 assays only,
one permissive set of conditions, one assay (China_N) dominates the 4-mismatch cases; not a
validation of the software for a laboratory's own conditions.

## 10. Stadhouders Table 1 (p. 116), as the lookup to encode

Checked against the PDF by the advisor (2026-09-25). Mismatches are primer-template. `taq_dna`
("standard") applies to both primers; `taq_mmlv` is the column "Real-time RT-PCR using specific
reverse primer (Taq DNA polymerase)", `rtth` the column "rTth DNA polymerase-based real-time PCR
using specific reverse primer". Footnote as printed: "Mismatches were designated as acceptable
(for general applications) when their effect was generally <2,0 Ct."

Only the `taq_dna` column is encoded (section 3); the others are kept for reference.

| Group | Position | taq_dna (both) | taq_mmlv FWD | taq_mmlv REV | rtth FWD | rtth REV |
|---|---|---|---|---|---|---|
| G1 A-A/A-G/G-A/G-G/C-C | terminal | Avoid | Avoid | Acceptable | Acceptable | Avoid |
| G1 | penultimate | Avoid | Avoid | Acceptable | Acceptable | Avoid |
| G1 | 3-5 | Acceptable | Avoid | Acceptable | Acceptable | Avoid |
| G2 T-T/T-C/C-T | terminal | Avoid | Avoid | Acceptable | Acceptable | Avoid |
| G2 | penultimate | Acceptable | Avoid | Acceptable | Acceptable | Avoid |
| G2 | 3-5 | Acceptable | Acceptable | Acceptable | Acceptable | Avoid |
| G3 C-A/A-C/G-T/T-G | terminal | Acceptable | Avoid | Acceptable | Acceptable | Avoid |
| G3 | penultimate | Acceptable | Acceptable | Acceptable | Acceptable | Avoid |
| G3 | 3-5 | Acceptable | Acceptable | Acceptable | Acceptable | Avoid |
