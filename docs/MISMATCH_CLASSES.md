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
then the base on the template strand facing it.

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
  smallest in Lefever), take the worse.

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
- 3: `likely_failure` if any is in the last 5 nt, else `at_risk` (our encoding; Lefever: "less
  pronounced and depended on the mismatch position", p. 1479; Fig. 6 median about 15 dCq, read
  from the figure, so `at_risk` may understate);
- 4: `likely_failure` (Lefever: blocked "almost completely"), except 4 internal adjacent
  mismatches, which the authors attribute to "their location near the primer's 5' end" (p. 1476,
  Fig. 5); the paper gives no size for this exception, `at_risk` is our choice. The code applies
  it to any 4 adjacent mismatches with none in the last 5 nt (e.g. -6 to -9), wider than the
  paper's example near the 5' end.
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

**R5. Gaps (bulges)**: `indeterminate`. Neither paper tested insertions or deletions. Probe sites
keep this for every gap.

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
other, blocked amplification "almost completely": `likely_failure` for the pair, whatever the
single-site classes (the figure inset also shows 5 in total blocking almost completely). A pair's
class is otherwise the worse of its two primer classes, flagged when the pair has >= 4 mismatches
in total: 2/2, 1/3 and 1/4 already have medians of about 15-16 dCq in Fig. 6 (read from the
figure), for which the paper states no rule, so the worse single class may understate.

## 6. Probes

**R9**: no rule from these two papers (neither tested probe mismatches). MGB probes are known to be
more mismatch-selective (Kutyavin et al. 2000, cited by the advisor from the abstract; full text
not checked). Every probe class is expert judgement with no quantitative source (advisor
subagent, 2026-09-25; user decision the same day):
- MGB probe, 1 mismatch: `indeterminate` (undetermined; neither detected nor an escape).
- MGB probe, 2 or more mismatches: `likely_failure`, position-free (a short MGB probe is not
  expected to form a stable duplex). Before 2026-09-25 (later) this was `at_risk`, which ranked
  milder than a single mismatch.
- Unmodified probe: 1 mismatch outside the last 5 nt `tolerated`, otherwise `at_risk` (longer
  probes are less mismatch-discriminating).

## 7. What changes in the reports

- Variant tables: a class column, the rule (R1-R9) and the source.
- Inclusivity per year: counts per class instead of one "0-1 mismatch, clean 3' end" percentage;
  the verdict thresholds (`warn_below_percent`, `fail_below_percent`) apply to
  `perfect + tolerated`; `at_risk` counts as not detected.
- **Undetermined** (user decision 2026-09-25): a single mismatch in an MGB probe (R9) and an
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
2. Kutyavin 2000 (MGB probes) if probe classes are wanted; until then R9 stays as written.
3. R7 (degenerate primers) is only a note; the pair flag at >= 4 mismatches in total is not shown
   yet.
4. A live rerun of the NG and enterovirus assays to see the classes on real data.

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
