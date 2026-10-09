---
type: NCBI Fact
title: BLAST URL API - what the code relies on
description: Documented parameters, word size 7 minimum, JSON2_S, core_nt, ENTREZ_QUERY outside the documented surface, and the search statistics behind the score floor.
tags: [ncbi, blast]
status: draft
stale_after: 2027-04-01T00:00:00Z
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: urlapi
    resource: ../sources/ncbi-blast-urlapi.md
    title: NCBI BLAST Common URL API
  - id: arch
    resource: ../../ARCHITECTURE.md
    title: docs/ARCHITECTURE.md, NCBI facts and live runs
  - id: ye
    resource: ../sources/ye-2012.md
    title: Ye et al. 2012
---

# Documented (read 2026-09-20 and 2026-09-30)

- Parameters not in the API table are unsupported. Listed: `WORD_SIZE`, `NUCL_REWARD`,
  `NUCL_PENALTY`, `EXPECT`, `FILTER`, `HITLIST_SIZE`, `SHORT_QUERY_ADJUST`; no `ENTREZ_QUERY`
  or taxid list.[^urlapi]
- blastn word sizes 7, 11 and 15 only, so the remote search cannot go below 7.
- Report formats include `JSON2_S`; legacy `XML` is not listed. `nt` requests go to `core_nt`.

# Measured live

- Taxon restriction through `ENTREZ_QUERY` (`txid<ID>[ORGN]` joined by `OR`, and `NOT`) works
  but is not airtight: an accession list of 100 returned all 100 plus 43 others, so partitioned
  searches filter hits back to their list (2026-09-23).[^arch]
- Short-oligo settings in use: word size 7, E-value 1000, `FILTER=F`, reward 1 / penalty -3,
  gap costs 5/2 (accepted by the server; validity for this scoring is assumed).
- Score floor `ceil(ln(K * eff_space / EXPECT) / lambda)`: predicted 10/8/7 for EXPECT
  1e3/1e4/1e5 and reported minimum 10/8/7 (NG-F vs N. meningitidis, lambda 1.374, K 0.711,
  2026-09-30). For each query of a multi-query search NCBI reports `eff_space` 0; the space is
  then derived from the reported alignments.
- A human-restricted `core_nt` search takes about an hour (one took 61 min).
- **A RID can be READY and still have no report.** On 2026-10-09 a taxon-restricted exclusivity
  search (RID CHAN7C89016) polled READY and the `FORMAT_TYPE=JSON2_S` request answered with an
  HTML page: "SYSTEM CAN'T PROCESS YOUR REQUEST, PLEASE CONTACT blasthelp.RID: CHAN7C89016 INFO:
  CHAN7C89016-ALIGNMENT-JSON2_S". So READY is not a promise that the formatter will deliver, and
  a fetched body has to be checked before it is treated, or stored, as a result. Whether the
  cause was the RID, the format or the load was not established; the retry and the resubmission
  in `ncbi/runner.py` assume it is transient.

# Consequence

A site whose matches are all in runs shorter than 7 is never reported: about 0.5% of 2-mismatch
sites of a 20-mer;[^ye] up to 7.4% of 2-mismatch and 15-33% of 3-mismatch placements for the
project's 17-19-nt oligos (measured 2026-09-30). The report says so.

[^urlapi]: NCBI BLAST Common URL API
[^arch]: docs/ARCHITECTURE.md, NCBI facts and live runs
[^ye]: Ye et al. 2012
