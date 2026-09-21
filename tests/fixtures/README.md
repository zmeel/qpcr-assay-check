# Test fixtures

- `real_hit_*.json`: **real NCBI output** captured on 2026-09-21 by `scripts/smoke_test.py`
  (BLASTN 2.17.0+, database core_nt). Hit objects are verbatim; the report around them is reduced
  to the fields the parser reads. They prove the parser works on what NCBI really returns.
- Everything produced by `tests/fake_ncbi.py` is **constructed by hand** from the documented format
  and is used only to exercise control flow (retries, resume, planning), not to prove format
  compatibility.
