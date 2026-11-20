# Review of the off-target search tiers: independent advisor (molecular diagnostics, in silico qPCR evaluation, scientific software)

Review requested by the user on 2026-11-20 ("Have the advisor look at the logic of the tiers") and
carried out by a subagent of the Claude Code session, which read the project's documentation,
code and tests read-only (no NCBI calls; the run reports themselves are not in the repository).
Scope: the logic of the off-target search tiers only, with the observations from the HSV-1 and
HSV-2 runs of 2026-11-19 as material.

This file holds that reviewer's report as delivered, unedited. It is a reviewer's opinion, not a
project decision: what was taken up is recorded in `README.md` in this folder, in CHANGELOG.md and
in the knowledge bundle's session pages. Claims are the reviewer's own; the ones acted upon are
checked against the code first.

---

# Review: the off-target search tiers (2026-11-20)

Reviewer: independent advisor (molecular diagnostics, in silico qPCR evaluation, scientific software). Scope: the tier logic only. I worked read-only. The offline suite passed (1159 passed, 5 skipped, no fastapi). Three small demonstrations ran from a scratch directory, using the test helpers in `tests/test_assess.py` and `tests/test_exclusivity.py`.

## 1. Summary verdict

The tier design is sound in its main lines:
- Searches are restricted by taxon.
- Each hit is checked against its tier by lineage after the search.
- Each tier reports the floor of its least sensitive search.
- Missing evidence never reads as No flags when nothing else is flagged.

The weak points are at the edges between tiers, not inside them:
- A searched tier can show a clean row it never assessed.
- Tier taxa are never checked against the target's lineage.
- Overlaps between tiers are not removed, and the packaged defaults create one: human is searched twice.
- Several checks compare exact taxonomy IDs where the code already has lineages.

The HSV-1 "not detected" argument does hold under the code's own rules. But the code should make that argument itself, and one rule it rests on (gapped probe sites never bind) leans the wrong way for an off-target check.

## 2. Findings, most important first

### F1. A tier dropped from `off_target_tiers` is still searched, and its row reads No flags

**What the code does**
- The planner plans the near-neighbour tier whenever the assay has taxa. It never consults `off_target_tiers` (`search/planner.py:157-162`).
- The assessment skips every tier not in that list (`specificity/assess.py:158, 177-179`).
- The report builds its tier rows from all searches (`report/html.py:128-153`, `report/grouping.py:384`). It takes the row's level only from findings that name the tier (`report/summary.py:101-106`), and an empty list reads PASS (`summary.py:43-44`).
- `off_target_tiers` is a free `list[str]` with no check of the names (`config.py:353`). `[target, near_neighbors]` is accepted.

**Verified.** I built a near-neighbour product that both primers and the probe detect:
- With the default tiers: tier row FAIL, specificity FAIL.
- With `off_target_tiers: [background]`: the row read "Near neighbours | no predicted product; 0 critical and 0 warning primer sites | PASS", and specificity read PASS.

**Why it matters.** The project's own advice invites exactly this setting. The finding at `pipeline.py:371-374` and `search-tiers.md` both say "remove the tier from off_target_tiers". A lab that removes it globally, so that assays without near neighbours stop reading Incomplete, gets a false No flags on the next HSV-1 run. The HSV-2 search would still be sent but silently ignored.

**Change**
- Assess every searched tier except `target`.
- Let `off_target_tiers` mean only "must be present for No flags".
- Replace the removal advice with an explicit per-assay waiver that carries a reason and is printed in the report.
- Validate tier names against the known set, and reject `target`.

### F2. Tier taxa are never checked against the target's lineage; overlaps are not removed

**What the code does (Verified)**
- Only `target.taxa` is checked to lie inside the target (`search/execute.py:62-75`).
- `near_neighbour_taxids` and `exclusion_taxids` are not checked. The near-neighbour search carries no `NOT target` clause; only the target tier does (`planner.py:218`).
- The exclusivity tier drops only an exact match to the target taxid (`execute.py:85`). The "own target" row is also marked by exact ID only (`taxonomy/exclusivity.py:145`).
- No taxon is removed when it appears in two tiers. The packaged list contains "Homo sapiens" (`data/clinical_organisms.yaml:73-75`) and `background_taxids` is `[9606]`. So every assay that uses the global list searches human twice. Human then also shares a 20-taxon exclusivity chunk with 19 other organisms, and can fill that chunk's hit list.

**Scenarios**
- *Ancestor of the target.* An assay for an influenza A subtype taxid runs with a list holding "Influenza A virus", or a type-specific adenovirus assay with "Human adenovirus". Either way, the target's own records are judged off-target, giving a false Exceeds limit. The same happens with an ancestor as near neighbour.
- *Descendant of the target.* A genus-level enterovirus assay without `target.taxa` runs on the global list, which holds "Human rhinovirus A". The same rhinovirus genomes then count as detected targets in inclusivity and as off-target products in exclusivity. *Verified* from the code paths; the run itself is *Judgement*.

**Change**
- Run the existing `outside_target` / `ancestors` lookup on near-neighbour and exclusivity taxa before planning.
- An ancestor of the target: search it with `NOT txid<target>` and say so in the plan.
- A descendant of the target: refuse, and ask for it in `target.taxa` with a role.
- A taxon listed in two tiers: search it once, in the more specific tier, and record that in the plan.

### F3. Probe re-alignment is starved by the shared budget, and the "not detected" argument should be in the code

**What the code does (Verified)**
- Partner windows and product fetches share one budget, and partner windows go first (`specificity/scan.py:163-165, 182-184, 233-236`).
- Anchors from a tier whose product list was cut are excluded (`assess.py:279-286`). So in the HSV-1 run the 1,000 fetches went to exclusivity and human primer sites, and none were left for the 500 HSV-2 products.
- The budget counts windows served from the cache too, so a rerun hits the same wall.

**Checking the argument for HSV-1 (Verified)**
- With floor 12, `always_reported(25, 12, 1, -3, 7)` gives 2: probe sites with up to 2 mismatches are always reported.
- Under R9 a linear probe site binds up to 2 mismatches: two mismatches is at risk at critical level, which binds (`pairing.py:136-149`). Three or more is likely failure.
- The near-neighbour tier was a single, complete search. The floor is the maximum over a tier's searches (`reach.py:52-95`).
- The probe is not degenerate. Degenerate oligos are expanded fully or rejected (`oligo/iupac.py:56-67`), and each variant has its own floor.

So "not detected" holds under the code's rules. It rests on two weaker points:

- **Gapped probe sites never bind, which leans the non-conservative way.**
  - A 25-nt linear probe with a 1-nt deletion in the template is graded at risk under R5c. The R5c note says that Otwell measured such deletions as detected (`oligo/grade.py:435-466`; I ran it).
  - The site's level is warning, because critical allows no gap, and `probe_binds_if: critical` makes it non-binding.
  - On the target side, at risk counts against detection; off target, at risk on a gapped site counts as harmless. For must-not-detect taxa this is the wrong direction (*Judgement*).
- **The relevance filter is not part of the floor.**
  - Hits with fewer than 14 identical bases in the local alignment are dropped before re-alignment (`assess.py:106-109, 204`). `always_reported` ignores this (`reach.py:30-46`).
  - For a 17-nt oligo with one mismatch at position 4 from either end, the full-length and trimmed alignments tie at score 13. If BLAST keeps the trimmed 13-identity alignment, the site is dropped. This concerns the enterovirus MGB probe and VZV-F. Whether BLAST keeps the shorter alignment on a tie is not verifiable here (*Judgement* on NCBI behaviour); the arithmetic is Verified.
  - The 22–26-nt HSV oligos are not affected.

**Change**
- Give product probe re-alignment its own budget, or priority. Products decide Exceeds limit against Review; partner windows on human mostly add Review lines.
- When products remain unscanned, compute the bound in code, and say "not detected (bounded)" rather than "may be detected although listed as not detected" (`assess.py:447-449`). The bound needs four conditions:
  - every probe variant's always-reported mismatch count is at least the most mismatches at which an ungapped site can still bind (linear 2, MGB 1);
  - no probe hit list is full and none was cut;
  - the oligo is long enough that the relevance filter cannot drop such a site;
  - gapped sites cannot bind under the configuration in use.
- Separately, consider letting at-risk gapped sites bind in judged tiers.

### F4. `max_amplicons` makes a clear tier Incomplete on every run

**What the code does (Verified).** Products are paired in (tier, accession) order and cut at 500 (`pairing.py:195-217`). The cut tier is Incomplete (`findings.py:352-364`). Incomplete is honest as built: a binding probe site on an accession after the cut is never paired.

**A principled stopping rule (Judgement).** A product is likely detected only if a binding probe site lies on the same record. When the cap is hit, the code can check whether any binding probe site exists in that tier on a record not yet paired.
- If none exists, and the probe bound in F3 holds, the cut can hide only more not-detected products. The tier should read Review with "at least 500 products, none detectable (bounded)".
- Otherwise it stays Incomplete.

**Also (Judgement).** Count distinct product patterns (the two primer alignments plus the probe alignment) rather than records. For must-not-detect taxa, the stronger answer is to run the exhaustive variant analysis over the near neighbour's records. That gives a denominator ("0 of N HSV-2 genomes give signal") instead of a capped sample of BLAST hits.

### F5. Exact taxonomy IDs are compared where lineages are already available

**What the code does (Verified)**
- The "taxon restriction check" counts hits whose ID is exactly one of the requested IDs (`search/assess.py:81-108`). It reads 0 of 1,649 for HSV-1, whose records are filed under a node below 3050292. As built it is not meaningful.
- The meaningful check already exists: `_in_tier` sets aside hits outside the tier by lineage and reports them (`specificity/assess.py:81-103, 464-494`).
- The exclusivity table groups hits by species name or exact ID (`taxonomy/exclusivity.py:127-129`). A row resolved to a genus therefore never collects species-level hits. I ran it with a genus row "Parechovirus" and a detected product filed under its species: tier FAIL, but the row showed 0 sites and no product. The enterovirus assay's own list is "Parechovirus". The status is right; the table is wrong.

**Change**
- Base both checks on lineage membership (row taxid among the hit's ancestors).
- Or drop the exact-ID count and show the set-aside count instead.

### F6. Chunking and the per-tier floor: conservative, but coarse

**What the code does (Verified)**
- Taxa are cut into chunks of 20 in taxid order (`planner.py:114-115, 214-217`).
- A tier's floor is its worst chunk (`reach.py:71-74`).
- When a query has no alignments, the search space is bounded by query length × `db_len` (`ncbi/parser.py:163-197`).

**What it means**
- Taking the worst chunk is right: a tier guarantees only what its least sensitive search guarantees.
- But a 3-taxon tail chunk with no alignments now sets the whole tier's statement. The floor went from score 12 to 18, so for the 19–20-nt primers the guarantee fell from one mismatch to perfect sites only, although the 20-taxon chunk still guaranteed one mismatch.
- How loose the bound is depends on whether `db_len` in a restricted search reflects the restriction. I cannot verify that here (NCBI behaviour). The jump suggests it is very loose. It errs on the safe side, but it misleads the reader.

**Change**
- Balance the chunks (23 taxa → 12 + 11).
- Keep large-genome taxa (human, big bacterial collections) in a search of their own.
- Report the floor per chunk with its taxa, as well as the tier minimum.
- Note that "moving organisms between tiers changes only presentation" is untrue for the floor: chunk composition changes what is guaranteed.

### F7. A missing tier or an unresolved name only upgrades No flags

**What the code does (Verified)**
- An unsearched configured tier makes the run Incomplete only when everything else is No flags (`pipeline.py:301-308`). Inside specificity it is only an INFO line (`findings.py:219-225`).
- An unresolved organism name makes exclusivity Incomplete only when it would otherwise pass (`taxonomy/exclusivity.py:177`).
- The stated order elsewhere is Exceeds limit > Incomplete > Review (`verdict.py:67-80`, `findings.py:158-168`).

**Scenario.** The near-neighbour tier is not searched, and human primer sites give Review. The overall status reads Review, not Incomplete. The missing tier shows only as a "Not assessed" row.

**Change.** Treat a missing configured tier and an unresolved name as Incomplete findings at every level, so they follow the same precedence.

### F8. One rule set for every judged tier (Judgement)

Using the same rules in every tier is right for products the probe detects (Exceeds limit) and for products it does not (Review).

Near neighbours and must-not-detect taxa differ in two ways that matter:
- **The grading is calibrated on them.** R1–R9 rest on near-identical sequences, which is exactly what near neighbours are. Their at-risk and indeterminate sites should therefore be read in the cautious direction: they bind or prime regardless of level, gapped sites included.
- **They need a population answer, not a sample** (see F4).

Distant organisms and human are better served by the level-based bound used now.

I would add per-tier overrides of `probe_binds_if` and the at-risk handling, defaulting to the stricter setting for near neighbours. Moving HSV-1 between tiers would then change the judgement where it should.

### F9. Whether the tier set is complete for a laboratory (Judgement)

- **Commensal flora.** A tier of its own is not needed, since its rules would be the same. Named specimen panels (genital, respiratory, CSF, skin) that an assay selects would make the flora choice explicit and reviewable.
- **Near neighbours.** Suggestions derived from taxonomy, such as siblings in the genus, would help as a plan note, never searched automatically. The exact NCBI Taxonomy query needs checking first.
- **Target tier off.** This is acceptable while the variant analysis runs. The code already says so when that analysis fails.
- **core_nt without WGS.** This is stated as a limitation and was raised in the earlier review. It matters most for bacterial near neighbours.
- **RNA note.** `eukaryote_taxids` holds only 9606 and is matched exactly (`pairing.py:154`). An RNA assay's product on a Candida, Trichomonas, Acanthamoeba or Cryptococcus genomic record gets no genomic-DNA note.

## 3. Things that are right and should stay

- The lineage set-aside of hits that leak through the taxon restriction. When the lineage lookup fails, hits count as inside the tier, which is the cautious choice.
- The tier floor is the least sensitive search, and its source is stated.
- The upper-bound fallback errs on the safe side.
- Missing evidence is Incomplete, never No flags (within the limits of F7).
- `target.taxa` is checked against the target's lineage; those taxa are excluded from the target search and the variant analysis, and split into must-not-detect and out-of-scope.
- The out-of-scope tier is information only, with its own product cap. It is kept out of the partner-scan budget.
- `max_amplicons` applies per tier.
- Each site and product is counted once across degenerate variants.
- Organism names are never guessed. A degenerate oligo that expands beyond the cap is rejected, never cut short.
- The target's own row in the organism list stays visible but is not searched.
- Saturation and `max_sites_per_query` cuts are reported per tier.

## 4. Errors or overstatements in `docs/knowledge/components/search-tiers.md`

1. "Removing a tier there also stops its hits from being assessed … a per-assay setting." This understates it. The tier is still searched and its row reads "no predicted product" at No flags (F1).
2. "Moving an organism from one judged tier to another changes where it is shown, not how it is judged." True of the rules, but overstated. It changes chunk composition and so the floor the tier guarantees: the HSV-2 run's primer floor went from 12 to 18 (F6).
3. The restriction paragraph presents the exact-ID count as the check. It omits the lineage set-aside that actually handles leaks (`assess.py:81-103`). The count does not show the restriction; it is only a figure in the report.
4. "Every judged tier … the partner scan." The scan skips tiers whose product list was cut (`assess.py:283`), and its budget is shared, partner windows first. Both decide the HSV-1 near-neighbour result.
5. "A row that is the assay's own target is marked." Only for the exact taxid. Ancestors and descendants of the target are searched and judged (F2).
6. "Listing it in two tiers searches it twice." It should add that the packaged defaults do this for human: "Homo sapiens" is in the starter list and 9606 is in `background_taxids`.
7. "Restricted by ENTREZ_QUERY to those taxa (with their descendants)." It should say that ENTREZ_QUERY is not in NCBI's documented URL-API parameter table (`ncbi/blast.py:3-5`). The descendant behaviour rests on the project's live check, not on documentation.
8. A "name that resolves to no taxon … the plan and report say so" is correct, but the page implies it always yields Incomplete. That happens only when exclusivity is otherwise clean (F7).
