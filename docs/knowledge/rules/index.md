# Rules

How a primer or probe site is graded and how a genome counts, rule by rule.

* [Site classes](classes.md) - The five classes every primer or probe site on the target gets, and which of them count as detectable.
* [Copy rule (a, b, c)](copy-rule.md) - When a located region counts as a copy of the locus - 32 anchored bases, 32 context bases, or identity 0.75 with 16 anchored.
* [Genome outcome](genome-outcome.md) - How one genome counts - detected, not detected (escape), undetermined, possibly unassembled, or with its region cut, hidden or not found.
* [Inclusivity status](inclusivity-status.md) - The whole-fragment status over the last 3 complete years plus the current one - 95% review, 80% exceeds limit, Incomplete above 25% undetermined.
* [LAB - laboratory evidence](lab-evidence.md) - An evidence entry in the assay file replaces the in silico class of one exact variant with the laboratory's result.
* [R1 - one mismatch in the last 5 nt of a primer](r1-last-five.md) - Class by mismatch type, position and Stadhouders Table 1 (Taq on DNA); terminal G2 at risk since 2026-10-02.
* [R2 - one mismatch beyond the last 5 nt of a primer](r2-single-beyond-five.md) - Tolerated; moderate at -6 to -8 and almost negligible from -9 on, after Lefever 2013.
* [R3 - several mismatches in one primer](r3-several-mismatches.md) - Counts within the 3'-most 16 nt decide; R3b grades mismatches beyond -16 from Otwell 2025.
* [R4 - reverse primer in a one-step RT-PCR (not encoded)](r4-reverse-primer-rt.md) - Stadhouders found reverse-primer mismatches mattered little with Taq + MMLV and more with rTth; a caveat, not a class.
* [R5 - gaps (bulges)](r5-gaps.md) - A gap is indeterminate unless the site's mismatches already give at risk or likely failure; an unpaired end base is a mismatch.
* [R5b - homopolymer length differences in a primer site](r5b-homopolymer-length.md) - One extra or missing base in a run of 3+ is at risk with the run outside the last 3 nt, otherwise likely failure; our class, no PCR study.
* [R5c - deletions in a probe site](r5c-probe-deletions.md) - 1-5 deleted bases at risk, 6 or more likely failure, from Otwell 2025; the notes now say where that study's data stop (25-28 nt linear probes, 55 C, 50 cycles).
* [R6 - ambiguity codes in the genome](r6-ambiguity-codes.md) - A code is graded both ways in the last 5 nt; only when it decides between detectable and not is the site undetermined.
* [R7 - degenerate primers](r7-degenerate-primers.md) - The best-matching variant of a degenerate oligo is graded; no source for partially matching pools.
* [R8 - the primer pair](r8-primer-pair.md) - 3 mismatches in one primer with 2+ in the other, or 4 with 1+, is likely failure for the pair (Lefever 2013).
* [R9 - probe mismatches](r9-probes.md) - MGB probe - 1 mismatch under the MGB likely failure, further 5' undetermined, 2+ likely failure; unmodified probe - 1 outside the last 5 tolerated, 2 at risk, 3+ likely failure.
* [Specificity findings](specificity-findings.md) - Off-target sites as critical or warning by mismatches, gaps and clean 3' bases; products paired from facing primer sites; severities per finding.
