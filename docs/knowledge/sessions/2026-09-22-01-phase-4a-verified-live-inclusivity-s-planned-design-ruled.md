---
type: Session
title: "Phase 4a verified live; inclusivity's planned design ruled out"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: Phase 4a verified live; inclusivity's planned design ruled out

The user ran `scripts/smoke_test.py` and pasted back `smoke_report.json` (all steps `ok: true`).
Updated README.md, `docs/ARCHITECTURE.md`, `CHANGELOG.md` and `data/clinical_organisms.yaml` to
reflect the real results rather than leave them marked "unverified." Also clarified for the user
that no pull request exists (none was requested) and re-verified branch/tag/version sync between
local and `origin/claude/brave-dirac-1vppye` before this.

Key results:
- **Taxonomy lineage parsing works**: 5/5 sampled lineages (Homo sapiens, Mus musculus, SARS-CoV-2,
  E. coli, S. aureus) came back with a populated genus and family through the real `resolve.py`
  code, not ad-hoc smoke-test code. One real subtlety worth remembering: SARS-CoV-2's own Taxonomy
  `Rank` is `"no rank"`, not `"species"` -- its species comes from its `LineageEx` ancestor
  (`Betacoronavirus pandemicum`). `Lineage.species` handles this correctly already.
- **The organism-list resolution path works**: 38/40 packaged names resolved through the real
  `resolve_organism_list` function (not a mock). Unresolved: "Mycoplasma pneumoniae" and
  "Mycobacterium chelonae".
- **A hypothesis from the previous session was wrong, and worth remembering as a lesson**: I
  assumed (docs/ARCHITECTURE.md, `taxonomy/resolve.py`'s docstring) that the `[All Names]` synonym
  fallback would catch "Mycoplasma pneumoniae"'s 2018 genus rename to *Mycoplasmoides*. It does
  not -- both terms returned zero hits. Fixed by renaming the organism-list entry to
  "Mycoplasmoides pneumoniae" directly (itself not yet confirmed live) rather than relying on the
  fallback. Updated the docstring and ARCHITECTURE.md to stop claiming the fallback would catch
  this, and to note synonym resolution is not as complete as assumed.
- **Significant, unprompted finding from a pre-existing smoke-test check (step 08, not written this
  session): combining `ENTREZ_QUERY` taxon restriction with a `[PDAT]` date filter in one BLAST call
  does not reliably restrict by date** (`blast_date_window_restriction_honoured: false` -- 4 of 20
  checked hit accessions fell outside the requested window). This directly rules out the inclusivity
  design SPEC.md step 7 describes and this project had assumed for phase 4b ("BLAST the reference
  amplicon against nt restricted to the target taxid, stratified into time windows via `ENTREZ_QUERY`
  date filters"). ESearch's own `[PDAT]` filtering is independently confirmed reliable, so phase 4b
  must get each window's accession list from ESearch and work from that list directly, not lean on
  BLAST for the date filtering. This is a design-level finding that must be read before starting 4b.
- Also newly confirmed: Entrez queries with 11/40/100 taxids are all accepted by the BLAST URL API
  (true upper limit still unknown, but 100 is now a safe planning number).
- Did not bump `pyproject.toml` or tag anything: phase 4a's *code* was already committed and pushed
  in the previous session; this session only updated documentation to match the live results, plus
  one data fix (the organism-list rename). Committed and pushed (user asked directly both times).

Left for the user / next session:
- **"Mycoplasmoides pneumoniae" and "Mycobacterium chelonae" still need a live re-check** (a
  smaller, targeted smoke-test run, or just watch the next full run's `exclusivity.unresolved`).
- **Phase 4b (inclusivity) needs a redesign before implementation starts**, per the `[PDAT]`+BLAST
  finding above -- do not start coding phase 4b against the old SPEC.md step 7 description without
  first working out the ESearch-based alternative.
- `--human`/`--probe-databases` smoke-test options still not run; alternative database timing for
  the human background tier remains unmeasured beyond the original 61-minute `core_nt` figure.
