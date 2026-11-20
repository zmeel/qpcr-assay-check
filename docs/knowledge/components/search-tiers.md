---
type: Component
title: "Off-target search tiers"
description: "The five search tiers (target, near neighbours, out of scope, background, exclusivity): where each one's taxa come from, how it is searched and judged, and what an unsearched tier does to the status."
tags: [component, specificity]
status: draft
generated: { by: claude-code/agent, at: 2026-11-20T10:00:00Z }
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
it into remote BLAST searches restricted by ENTREZ_QUERY to those taxa (with their
descendants; ENTREZ_QUERY is not in NCBI's documented URL-API parameter table, so the behaviour
rests on the project's own checks, see `ncbi/blast.py`), at most `search.max_taxids_per_search` (20) taxa per search and query batches of
at most 1,000 bases.[^planner] The first HSV-2 run, for example, sent 1 background search and 2
exclusivity searches (25 taxa, so two chunks).[^hsv2run] The restriction is effective but not
airtight. What handles a leak is the assessment: a hit whose organism lies outside its tier's
taxa by NCBI lineage is set aside, not assessed under that tier, and the findings say so.[^assess]
The report's "taxon restriction check" is only a count, and it compares exact IDs, so a species
whose records are filed under a node below it reads "0 of N" although every hit belongs to it
(HSV-1 as a near neighbour of HSV-2, 2026-11-19).[^hsv2b] Chunks are cut 20 taxa at a time in
taxid order, and a tier's reporting floor is that of its least sensitive search, so a small tail
chunk with few alignments can weaken the whole tier's floor (HSV-2, 2026-11-19: score 12 to 18
for the primers after two taxa moved out).[^review]

# The five tiers

| Tier | Taxa come from | Planned when | Judged |
|---|---|---|---|
| **target** | `target.taxid`, minus every taxon in `target.taxa` | `search.target_tier: true` (default false) | no: a positive control |
| **near_neighbours** | the assay file: `near_neighbour_taxids`, `exclusion_taxids` and `target.taxa` with role `must_not_detect` | that list is not empty | yes |
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
  and its rows are always listed, flagged or not.[^grouping]
- **Out of scope.** Taxa inside the target taxon that are not the intended target but no
  problem either (animal enteroviruses for a human diagnostic assay): searched and reported,
  every finding INFO, never counted as unsearched.[^findings][^pipeline]
- **Background.** Human by default; the planner warns if 9606 is missing, and the report then
  says that binding to human DNA was not evaluated. For RNA assays, a product on a taxon in
  `specificity.eukaryote_taxids` gets a note: on a genomic record it matters only if the
  specimen holds genomic DNA and no intron separates the primer sites.[^planner][^config]
- **Exclusivity.** The assay's own `exclusivity_organisms` when it has them
  (`organisms.source: assay`, the default), otherwise the global list (`organisms.list_file`,
  or the packaged starter list); `organisms.source: global` always uses the global list.[^organisms]
  A name that resolves to no taxon or to more than one is left out, never guessed, and the plan
  and report say so; it makes exclusivity Incomplete only when that tier is otherwise clean. A
  row with exactly the assay's target taxid is marked and not searched; an ancestor or
  descendant of the target is searched and judged like any other organism (no lineage check
  against the target, unlike `target.taxa`). The packaged starter list includes *Homo sapiens*,
  which the background tier searches as well. The report adds a table per organism, which
  groups hits by species name or exact ID: a row resolved to a genus collects no species-level
  hits in that table, although the status counts them.[^review]

# Judged the same way

Every judged tier (near neighbours, background, exclusivity) is assessed by the same rules:
full-length re-alignment, site levels (critical, warning, minor) together with the graded
classes R1-R9 since 2.2.0, products from facing primer sites within `max_amplicon_size`, the
partner scan, and the severities in `specificity.severity` - a product the probe detects is
FAIL (Exceeds limit), a product it does not detect and a critical primer site without a product
are WARN (Review), a probe site alone is INFO.[^rules][^config] `max_amplicons` (500) applies per
tier. The partner scan skips a tier whose product list was cut, and partner windows and the probe
re-alignment inside products share one fetch budget (`partner_scan_max_windows`), partner
windows first: in the HSV-1 run of 2026-11-19 none was left for the 500 HSV-2 products.[^review]
Moving an organism from one judged tier to another does not change the rules it is judged by,
but it can change the chunks and so the floor a tier guarantees; listing it in two tiers searches
it twice (the packaged defaults do so for human).

# Configured but not searched

`specificity.off_target_tiers` (default `[near_neighbours, background, exclusivity]`) names the
tiers a run must search before its specificity can read No flags. A configured tier that no
search covered is a "Not assessed" row and makes the summary Incomplete (since 2.2.0: missing
evidence never reads as No flags); the finding says to give the assay the taxa or remove the
tier from `off_target_tiers`.[^pipeline] The Incomplete is applied only when the run would
otherwise read No flags: next to a Review elsewhere, a missing tier shows only as its "Not
assessed" row. Removing a tier from `off_target_tiers` does not stop it being searched (the
planner plans near neighbours whenever the assay has taxa) but stops its hits being assessed,
and its row in the summary then reads No flags with no sites: do not remove a tier that an
assay fills (review of 2026-11-20, F1; open).[^assess][^review]

Until 2026-11-19 only the enterovirus assay filled the near-neighbour tier (its rhinovirus
taxa); for the others it was configured and not searched. Where another finding was worse
(Exceeds limit for influenza A, HSV-1 and VZV) that did not show; for HSV-2, with nothing worse,
it kept the first run Incomplete.[^hsv2run] Since then HSV-1, HSV-2 and VZV name their closest
relatives as near neighbours (user); the other example assays still leave the tier unsearched.

# Limits

A tier covers only its own taxa: a result says nothing about organisms outside the searched
tiers. core_nt holds no WGS draft assemblies, so for organisms known mostly from draft genomes
the evidence is their complete genomes and other core_nt records. Primer-BLAST remains a useful
manual cross-check.

[^planner]: src/qpcr_assay_check/search/planner.py (which tiers are planned, chunking, batching)
[^models]: src/qpcr_assay_check/models.py (near_neighbour_taxids, exclusion_taxids, target.taxa roles)
[^organisms]: src/qpcr_assay_check/taxonomy/organisms.py (which exclusivity list is used)
[^assess]: src/qpcr_assay_check/specificity/assess.py (only configured tiers are assessed)
[^findings]: src/qpcr_assay_check/specificity/findings.py (severities; out of scope is information)
[^pipeline]: src/qpcr_assay_check/pipeline.py (a configured tier that was not searched)
[^grouping]: src/qpcr_assay_check/report/grouping.py (tier order and rows in the report)
[^config]: Packaged default configuration (search, specificity, organisms)
[^spec]: docs/SPEC.md (tiered, taxon-restricted searches instead of one unrestricted search)
[^rules]: Specificity findings (site levels, products, severities)
[^hsv2run]: The first HSV-2 run (2026-11-19)
[^review]: Advisor review of the search tiers (2026-11-20)
[^hsv2b]: The HSV-2 run with near neighbours (2026-11-19 10:45Z)
