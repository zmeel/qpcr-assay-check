---
type: Session
title: "v0.3.0: specificity assessment integrated"
description: "Session log of 2026-09-21."
tags: [session]
session_date: 2026-09-21
session_label: "2026-09-21"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-21: v0.3.0: specificity assessment integrated

Picked up a work-in-progress snapshot (`qpcr-assay-check-v0.3.0-WIP-snapshot.zip`, built in a
separate sandbox without NCBI access) that implemented phase 3 of the roadmap: full-length
re-alignment (`align/realign.py`), amplicon pairing and site classification (`specificity/`), and
wired them into `run`. State at handoff: 249/250 tests passing, one ruff E501.

What this session did:
- Diffed the snapshot against the repo, scanned it for anything suspicious (network calls, eval/exec,
  unexpected URLs) before integrating — clean — then copied it in file by file.
- Fixed the one failing test. Root cause: `tests/world.py`'s "realistic BLAST hit" guard only checked
  that the first base beyond a partial alignment mismatched. That is too weak — with match +1 /
  mismatch -3 scoring, BLAST's alignment is locally maximal, so *no prefix* of the unaligned flank
  (read outward from the alignment boundary) may sum to a positive score, or BLAST would have
  extended over it. Rewrote the guard to check every prefix, and fixed the handful of test scenarios
  (`f=[10,16]`+`trim3=5`, `r=[7,23]`+`trim5=7`, and two `human_world()` cases) that had relied on the
  weaker check — each needed one more mismatch placed adjacent to the alignment boundary to stay
  realistic. Confirmed the fix by re-deriving each affected assertion (n_mismatch, defect_positions,
  clean_3prime_nt, level) from `specificity/sites.py`'s actual classification rules rather than
  guessing.
- Fixed the ruff E501 (a docstring line in `tests/test_validation_script.py`).
- `ruff check .` and `pytest -m "not live"` are both clean: 250 passed.
- Updated README.md (status banner, privacy note — `run` now sends oligos and hit accessions to
  NCBI, not just `search`; new Specificity assessment and live-validation sections; limitations;
  roadmap), `docs/ARCHITECTURE.md` (status, v0.3.0 design decisions, moved the now-verified
  minus-strand coordinate fact out of "still unverified", added the v0.3.0 unverified-pruning-bounds
  note), and `CHANGELOG.md` (0.3.0 entry).
- Did not run `scripts/smoke_test.py` or `scripts/validate_assessment.py` live — this sandbox has no
  NCBI access, per CLAUDE.md. Both need to be run locally and their output pasted back (see below).
- Applied the user's go-ahead on the license question: proceeded with the already-committed
  Apache-2.0 (`LICENSE`, `pyproject.toml`) rather than treating it as still open.

Left for the user / next session:
- **Run `scripts/validate_assessment.py` live** (needs `NCBI_EMAIL`; background tier can take about
  an hour, cached 7 days after). Paste back `validation_out/validation_report.json`. If it reports a
  contradicted rule, the pruning in `specificity/sites.py` (`can_reach_warning` / `Candidate.lower_bound`)
  needs fixing before the specificity verdict can be trusted — do not treat the "world" as necessarily
  wrong this time; the script tests the rule, not just the constructed data.
- `scripts/smoke_test.py` is unchanged (wire protocol only) but has not been re-run since 0.2.1.
- Local commit created on `claude/brave-dirac-1vppye`; not pushed. CLAUDE.md requires asking before
  any push — waiting for that go-ahead.
- Still open from the previous session: no git tags exist locally even though CHANGELOG documents
  0.1.0–0.2.1 as released — worth reconciling before the next tag is cut.
- No annotated tag has been cut for 0.3.0 yet.
