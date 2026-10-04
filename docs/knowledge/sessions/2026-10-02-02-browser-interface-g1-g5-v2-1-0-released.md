---
type: Session
title: "Browser interface G1-G5; v2.1.0 released"
description: "Session log of 2026-10-02."
tags: [session]
session_date: 2026-10-02
session_label: "2026-10-02"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-10-02: Browser interface G1-G5; v2.1.0 released

- Neisseria escapes checked with the user (2026-10-02): GCF_001025995.1 (first escape example)
  has 3 assembled copies of the region (2 whole on the reverse strand with A8 and A9 at NG-R's
  poly-A 7, 1 cut at the end of contig 275 with T9 = A9); no copy with A7. The tool found every
  copy; the escape comes from the strict homopolymer rule (best copy A8, at risk, R5b), not
  the contig end. Not "possibly unassembled" (3 copies vs median 9) because complete genomes
  fail with the same three sites. Most of the 1,889 escapes are this kind (933 reverse A8 only,
  713 with a tolerated forward mismatch as well); 92.8% if bulges were tolerated. Whether NG-R
  primes over T8/T9 is a wet-lab question.
- Added (user: "Add escape reason per genome"): escape_reason() in variants/exhaustive.py,
  CopyCoverage.escape_reasons / escape_rows, the report's escape row by kind, workbook sheet
  "Escapes", run_summary includes escape_reasons. Tests in test_genome_outcome.py and
  test_multi_copy.py. No change to who counts as an escape.

- v2.0.0 tag pushed by the user (verified: annotated, on c5ef505, the merge of PR #56).
- GUI decisions (user, 2026-10-02): one user with a password, LAN/VPN only, 8 hours idle
  sign-out, mockup first (approved: https://claude.ai/artifact/S8iW1kmSFw65wYQJuDULmx).
  Phases G1-G5 in SPEC (amendment 2026-10-02).
- G1 built: `qpcr_assay_check/gui/` (auth.py: scrypt hash, LoginThrottle; records.py: record
  index cached by mtime; app.py: sessions, form tokens, CSP, login/logout/dashboard; templates
  and static with vendored IBM Plex 5.3.0 from @fontsource, OFL texts beside them), CLI
  `gui set-password` / `gui serve`, extra `gui`, Dockerfile installs it, docker-compose.yml,
  `work/` gitignored, CI installs `.[dev,gui]`. tests/test_gui.py (17 tests). Checked in
  Chromium (light, dark, 390 px wide) against two sample records.
- First try on the NAS (user): `UID` is read-only in the Synology shell, so compose ran as uid
  1000 and could not write work/gui. Fixed in PR #58 (QAC_UID/QAC_GID in .env; clear error).
  The user confirmed the GUI works on the NAS.
- G2 built (user go-ahead "Start next step"): gui/assays.py (AssayFiles: list, create, save
  with .history, delete to .deleted; validate_text = the CLI's model + load_config + QC-only
  oligo QC, about 20 ms), gui/form.py (ruamel.yaml round trip, byte-identical on every example
  and template file; form edits change only their lines; oligo renames follow into loci,
  channels, evidence), gui/assay_routes.py (list, new, editor, live validate, QC-only record,
  delete; names checked against a strict pattern and resolved inside the folder), templates and
  CSS, app.js live validation (debounced, ignores a redirect to the login page) and an
  unsaved-changes guard. Decision: YAML stays the source of truth; the form covers the common
  fields, loci/channels/references/settings are edited as YAML (comments with provenance must
  survive). tests/test_gui_assays.py (20 tests). Checked in Chromium.
- NAS: port 8080 taken; the user edited the compose file, which blocked `git pull`. Fixed in
  PR #60 (QAC_PORT in .env).
- G3 built (user: "Start G3"): gui/runs.py (Job, JobStore in work/gui/jobs/<id>/ with the
  confirmed assay copy, Runner: one subprocess at a time running the CLI itself with --yes,
  own process group; cancel sends SIGINT, SIGTERM after 30 s, SIGKILL after 60 s; exit codes
  0/10/20/30 done, 64/70 failed with a message; jobs left running at start-up marked
  interrupted; progress read from the log's INFO lines), gui/run_routes.py (new, plan via
  plan_searches as --dry-run, confirm with a SHA-256 of the planned file, list, detail,
  status JSON polled every 2 s, cancel, again), templates, CSS, JS polling. Decision: the GUI
  confirms the dry-run plan (the exclusivity tier resolves at run time, as on the command
  line); the per-run genome budget stays a config/assay setting (an override would be beaten
  by an assay's own settings). tests/test_gui_runs.py (10 tests, one a real QC-only run through
  the queue). Checked in Chromium.
- G4 built (user: "Start G4"): gui/results_routes.py (/results, /results/<slug>,
  /results/<slug>/<run>, /records/<slug>/<run>/<file> for four allowed file names; report
  served with CSP default-src 'none', style-src 'unsafe-inline', frame-ancestors 'self',
  X-Frame-Options SAMEORIGIN, a <base target="_blank"> added in the response only; iframe
  sandbox allow-popups), RecordIndex.record_dir/get/of_assay (segments checked and resolved
  inside results/), coverage and inclusivity status per record, links from dashboard and run
  page; the global middleware now lets a route set its own CSP and frame option.
  tests/test_gui_results.py (10 tests, on a real QC-only record). Checked in Chromium: the
  report renders in the frame.
- G5 built (user: "Start G5"): gui/settings_routes.py (password change with the login
  brake; config editor checked by load_config on a temporary copy, history in work/gui/history;
  NCBI env set/not set; storage measured on request with a 5 s limit), session generation
  (sha256 of the signing key) checked on every request, so a new password, also from the CLI,
  ends other sessions without a restart; wiki page Browser-interface.md, README section,
  USER_GUIDE section. tests/test_gui_settings.py (6 tests).
- PRs merged by the user: #57 (G1), #58 (QAC_UID/QAC_GID), #59 (G2), #60 (QAC_PORT), #61 (G3),
  #62 (G4), #63 (G5 + release).
- v2.1.0 released: version 2.1.0, CHANGELOG [2.1.0]; annotated tag v2.1.0 pushed by the user on
  5a4db38 (the merge of PR #63), verified on the remote. This session cannot push tags (403):
  the user pushes them. Docker on the NAS: `git checkout v2.1.0`, `docker compose build`,
  `docker compose up -d`; the GUI container runs the image's code, so every update needs a
  rebuild (run_assay.sh mounts src/ and does not).
- NAS setup as used: `.env` holds NCBI_EMAIL, NCBI_API_KEY, QAC_UID, QAC_GID and QAC_PORT=8880
  (8080 is taken on the NAS); `docker-compose.yml` needs no local edits.
- Not done yet:
  - live check of the GUI on the NAS: a full run with NCBI started from the browser (only
    QC-only runs went through the queue here; this session cannot reach NCBI);
  - Neisseria: about 29,600 of 51,583 genomes left (two runs at 20,000), now possible from the
    browser;
  - Legionella with the v2 code;
  - publishing docs/wiki/ (the new Browser-interface page included) to the GitHub wiki (user);
  - theory-review items deferred to the user: position-aware MGB rule, a third source for
    terminal mismatch types, a deduplicated inclusivity figure, collection date as the status
    axis, scanning every locus, one rule set for off-target sites, independent validation.

# Related

* [Browser interface - one user, LAN or VPN, YAML stays the source](../decisions/2026-10-02-gui-one-user.md)
* [Neisseria gonorrhoeae, 2026-10-02 21:13Z](../runs/neisseria-2026-10-02.md)
