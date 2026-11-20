---
type: Component
title: "Off-target search tiers"
description: "The five search tiers (target, near neighbours, out of scope, background, exclusivity): where each one's taxa come from, how they are checked against the target and each other, how each tier is searched and judged, and what an unsearched or waived tier does to the status."
tags: [component, specificity]
status: draft
generated: { by: claude-code/agent, at: 2026-11-20T15:00:00Z }
sources:
  - id: planner
    resource: ../../../src/qpcr_assay_check/search/planner.py
    title: "src/qpcr_assay_check/search/planner.py (which tiers are planned, chunking, batching)"
  - id: models
    resource: ../../../src/qpcr_assay_check/models.py
    title: "src/qpcr_assay_check/models.py (near_neighbour_taxids, exclusion_taxids, target.taxa roles)"
  - id: organisms
    resource: ../../../src/qpcr_assay_check/taxonomy/organisms.py
    title: "src/qpcr_assay_check/taxonomy/organisms.py (which exclusivity list is used)"
  - id: assess
    resource: ../../../src/qpcr_assay_check/specificity/assess.py
    title: "src/qpcr_assay_check/specificity/assess.py (only configured tiers are assessed)"
  - id: findings
    resource: ../../../src/qpcr_assay_check/specificity/findings.py
    title: "src/qpcr_assay_check/specificity/findings.py (severities; out of scope is information)"
  - id: pipeline
    resource: ../../../src/qpcr_assay_check/pipeline.py
    title: "src/qpcr_assay_check/pipeline.py (a configured tier that was not searched)"
  - id: grouping
    resource: ../../../src/qpcr_assay_check/report/grouping.py
    title: "src/qpcr_assay_check/report/grouping.py (tier order and rows in the report)"
  - id: config
    resource: ../../../src/qpcr_assay_check/data/default_config.yaml
    title: "Packaged default configuration (search, specificity, organisms)"
  - id: spec
    resource: ../../SPEC.md
    title: "docs/SPEC.md (tiered, taxon-restricted searches instead of one unrestricted search)"
  - id: rules
    resource: ../rules/specificity-findings.md
    title: Specificity findings (site levels, products, severities)
  - id: tiers
    resource: ../../../src/qpcr_assay_check/search/tiers.py
    title: "src/qpcr_assay_check/search/tiers.py (tier taxa against the target and each other)"
  - id: hsv2b
    resource: ../runs/hsv2-2026-11-19b.md
    title: The HSV-2 run with near neighbours (2026-11-19 10:45Z)
  - id: review
    resource: ../../reviews/2026-11-20-tiers-advisor.md
    title: Advisor review of the search tiers (2026-11-20)
  - id: hsv2run
    resource: ../runs/hsv2-2026-11-19.md
    title: The first HSV-2 run (2026-11-19)
---

# Why tiers

One BLAST search against all of core_nt would fill its hit list with the closest hits wherever
they are, and miss the organisms that matter. The specification therefore asks for tiered,
taxon-restricted searches instead.[^spec] Each tier is a list of taxonomy IDs; the planner turns
it into remote BLAST searches restricted by ENTREZ_QUERY to those taxa (with their descendants;
ENTREZ_QUERY is not in NCBI's documented URL-API parameter table, so the behaviour rests on the
project's own checks, see `ncbi/blast.py`), at most `search.max_taxids_per_search` (20) taxa per
search, split into searches of balanced size (23 taxa: 12 + 11, since 2026-11-20; 20 + 3
before), and query batches of at most 1,000 bases.[^planner] The restriction is effective but not
airtight. What handles a leak is the assessment: a hit whose organism lies outside its tier's
taxa by NCBI lineage, or is the target itself, is set aside, not assessed under that tier, and
the findings say so; the report's "taxon restriction check" counts the relevant hits that way
(inside, set aside, not checkable) since 2026-11-20 (exact IDs before, which read "0 of 1,649"
for HSV-1 filed under a node below its species).[^assess][^hsv2b] A tier's reporting floor is that
of its least sensitive search, and the report gives each search's floor as well.[^review]

# Tier taxa against the target and each other

Before a real search, `search/tiers.py` checks every tier's taxa against the target's NCBI
lineage and against each other (since 2026-11-20, review F2):[^tiers]

- the target itself, or a taxon inside it that is not in `target.taxa`: refused, with what to do
  (put it in `target.taxa` with its role, or remove it);
- a taxon that contains the target (a genus around a species target): searched with NOT the
  target, and the plan says so;
- a taxon listed in two tiers: searched once, in the more specific tier (near neighbours, out of
  scope, background, organism list); the packaged starter list names *Homo sapiens*, which the
  background tier searches, so human is no longer searched twice;
- a taxon whose descendants a more specific tier searches: searched without them.

Exact duplicates are removed even in a dry run (no network); the lineage rules need NCBI
Taxonomy, and if that lookup fails the run goes on with a warning in the plan.

# The five tiers

| Tier | Taxa come from | Planned when | Judged |
|---|---|---|---|
| **target** | `target.taxid`, minus every taxon in `target.taxa` | `search.target_tier: true` (default false) | no: a positive control |
| **near_neighbours** | the assay file: `near_neighbour_taxids`, `exclusion_taxids` and `target.taxa` with role `must_not_detect` | that list is not empty | yes, cautiously |
| **out_of_scope** | `target.taxa` with role `out_of_scope` | that list is not empty | no: information ("also detects") |
| **background** | the configuration: `search.background_taxids` (default `[9606]`, human) | the list is not empty | yes |
| **exclusivity** | the clinical organism list, by name, resolved to taxonomy IDs at run time | at least one name resolves | yes |

[^planner][^models][^config]

- **Target.** Off by default since the exhaustive variant analysis assesses every record of the
  target itself; for a large target it was the slowest search of a run (user decision
  2026-10-23, recorded in the planner).[^planner]
- **Near neighbours.** The target's closest relatives, and the taxa *inside* the target taxon
  that the assay must not detect (the rhinoviruses inside the genus Enterovirus, for the
  enterovirus assay). Taxa in `target.taxa` are left out of the target's own search,
  inclusivity and the variant analysis either way.[^models] In the report this tier comes first,
  and its rows are always listed, flagged or not.[^grouping] It is a cautious tier
  (`specificity.cautious_tiers`): a site graded at risk or indeterminate primes or binds at
  warning level, a gapped probe site included, whatever `probe_binds_if` says.[^review]
- **Out of scope.** Taxa inside the target taxon that are not the intended target but no
  problem either (animal enteroviruses for a human diagnostic assay): searched and reported,
  every finding INFO, never counted as unsearched.[^findings][^pipeline]
- **Background.** Human by default; the planner warns if 9606 is missing, and the report then
  says that binding to human DNA was not evaluated. For RNA assays, a product on an organism
  whose NCBI lineage holds a taxon of `specificity.eukaryote_taxids` (default 9606 and 2759,
  Eukaryota, since 2026-11-20; matched exactly, human only, before) gets a note: on a genomic
  record it matters only if the specimen holds genomic DNA and no intron separates the primer
  sites.[^planner][^config]
- **Exclusivity.** The assay's own `exclusivity_organisms` when it has them
  (`organisms.source: assay`, the default), otherwise the global list (`organisms.list_file`,
  or the packaged starter list); `organisms.source: global` always uses the global list.[^organisms]
  A name that resolves to no taxon or to more than one is left out, never guessed, and the plan
  and report say so; it makes exclusivity Incomplete unless that tier exceeds a limit. A row
  with exactly the assay's target taxid is marked and not searched. In the per-organism table a
  hit belongs to the most specific row among its organism's NCBI ancestors (a genus row such as
  "Parechovirus" collects its species' hits); a row searched once in another tier (human, in
  the background tier) says so and shows that tier's evidence.

# Judged the same way

Every judged tier (near neighbours, background, exclusivity) is assessed by the same rules:
full-length re-alignment, site levels (critical, warning, minor) together with the graded
classes R1-R9 since 2.2.0, products from facing primer sites within `max_amplicon_size`, the
partner scan, and the severities in `specificity.severity` - a product the probe detects is
FAIL (Exceeds limit), a product it does not detect and a critical primer site without a product
are WARN (Review), a probe site alone is INFO.[^rules][^config] The exception is the cautious
reading of near neighbours above. `max_amplicons` (500) applies per tier, and the partner scan
skips a tier whose product list was cut.

Partner windows (`partner_scan_max_windows`) and products whose probe is re-aligned
(`probe_scan_max_products`) have separate budgets since 2026-11-20 (one shared budget, partner
windows first, left none for the 500 HSV-2 products of the HSV-1 run of 2026-11-19). Where
products remain without a re-aligned probe, or a tier's product list was cut, the code checks
whether "not detected" is bounded: every probe site that could bind (up to 2 mismatches, 1 for an
MGB probe, no gap) is always reported by the tier's searches, no list was cut, the probe is long
enough to pass the relevance filter with those mismatches, and a gapped probe site cannot bind
in the tier; for a cut list also that no binding probe site lies on a record beyond the cut. Then
the finding is information ("bounded"), otherwise Incomplete with the reason. In a cautious tier
a gapped probe site can bind, so there the bound does not hold. Product findings also count
distinct product patterns by the sequences under the oligos.[^review]

Moving an organism from one judged tier to another does not change the rules it is judged by
(except the cautious reading), but it can change the searches and so the floor a tier
guarantees.

# Configured, searched, waived

Every tier that is searched is assessed (before 2026-11-20 only the tiers in
`specificity.off_target_tiers`: a tier left out there was still searched, not assessed, and its
row read No flags, review F1). `off_target_tiers` (default `[near_neighbours, background,
exclusivity]`, names checked) now only names the tiers a run must search before its specificity
can read No flags. A configured tier that no search covered is a "Not assessed" row and Incomplete
evidence, which outranks Review and yields only to Exceeds limit (before 2026-11-20 it only kept
No flags away, review F7).[^pipeline] To do without a tier deliberately, waive it with a reason
in `specificity.tier_waivers` (e.g. in the assay's settings); the report prints the reason and
the tier does not make the run Incomplete.[^config]

Until 2026-11-19 only the enterovirus assay filled the near-neighbour tier (its rhinovirus
taxa); for the others it was configured and not searched. Since then HSV-1, HSV-2 and VZV name
their closest relatives as near neighbours (user); the other example assays still leave the
tier unsearched.[^hsv2run]

# Limits

A tier covers only its own taxa: a result says nothing about organisms outside the searched
tiers. core_nt holds no WGS draft assemblies, so for organisms known mostly from draft genomes
the evidence is their complete genomes and other core_nt records. Primer-BLAST remains a useful
manual cross-check. Not built (review F4, F9): an exhaustive analysis over a near neighbour's
own records (a denominator, "0 of N genomes give signal"), specimen panels to choose organisms
from, and near-neighbour suggestions taken from the taxonomy.

[^planner]: src/qpcr_assay_check/search/planner.py (which tiers are planned, chunking, batching)
[^models]: src/qpcr_assay_check/models.py (near_neighbour_taxids, exclusion_taxids, target.taxa roles)
[^organisms]: src/qpcr_assay_check/taxonomy/organisms.py (which exclusivity list is used)
[^assess]: src/qpcr_assay_check/specificity/assess.py (every searched tier but the target is assessed)
[^findings]: src/qpcr_assay_check/specificity/findings.py (severities; out of scope is information)
[^pipeline]: src/qpcr_assay_check/pipeline.py (a configured tier that was not searched)
[^grouping]: src/qpcr_assay_check/report/grouping.py (tier order and rows in the report)
[^config]: Packaged default configuration (search, specificity, organisms)
[^spec]: docs/SPEC.md (tiered, taxon-restricted searches instead of one unrestricted search)
[^rules]: Specificity findings (site levels, products, severities)
[^hsv2run]: The first HSV-2 run (2026-11-19)
[^review]: Advisor review of the search tiers (2026-11-20)
[^tiers]: src/qpcr_assay_check/search/tiers.py (tier taxa against the target and each other)
[^hsv2b]: The HSV-2 run with near neighbours (2026-11-19 10:45Z)
