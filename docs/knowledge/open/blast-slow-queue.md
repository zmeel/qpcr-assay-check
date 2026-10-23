---
type: Open Item
title: BLAST searches held for a day by a change at NCBI (closed)
description: "From 2026-10-20 the user's BLAST URL API searches stayed WAITING for hours. NCBI answered (case CAS-1714885-G5R3Z2): a change of theirs, rolled back. Searches of 2026-10-23 took 1-2 minutes again. Closed."
tags: [open, question, answered, ncbi, blast, etiquette, influenza, closed]
status: draft
generated: { by: claude-code/agent, at: 2026-10-21T08:30:00Z }
sources:
  - id: devinfo
    resource: ../sources/ncbi-blast-developer-info.md
    title: NCBI BLAST developer information and usage guidelines
  - id: etiquette
    resource: ../ncbi/etiquette.md
    title: NCBI etiquette and limits
  - id: assay
    resource: ../assays/influenza-a-matrix.md
    title: "Influenza A (matrix gene)"
  - id: session
    resource: ../sessions/2026-10-21-01-blast-slow-queue.md
    title: "Session 2026-10-21: the BLAST slow queue"
---

# What happened

The rerun of the influenza A (matrix) assay with both reverse primers did not get past its
first BLAST search.[^assay] The log only ever said `WAITING`: no error, no failure.[^session]

- **2026-10-20.** The target-tier search (`ENTREZ_QUERY=txid11320[ORGN]`, all 8 resolved
  oligo sequences in one query) stayed WAITING. The run was restarted four times, about 90
  minutes apart. A restart more than `resubmit_after_minutes` (default 90) after submission
  submits the search anew, so the restarts added submissions and threw the queued RID away.
- **2026-10-20, the control.** From the NAS, a deliberately small search - one 23-nt primer
  (`infa_fwd`), `HITLIST_SIZE=100`, `ENTREZ_QUERY` limited to the 10,334 influenza A records
  published 2026-10-01 to 2026-10-20 - was still WAITING after 12 minutes (RID `DES788WX014`,
  submitted 12:39:05Z). The user ran the same primer through the BLAST web page at the same
  time: it returned almost at once.
- **2026-10-21, 07:20Z.** Rerun with `resubmit_after_minutes: 2000` and `max_wait_minutes:
  2000` in `work/config.yaml`. It resumed the target RID `DEPS5BKC014` instead of replacing it,
  and found it READY after 1147 minutes, about 19 hours. The first fetch of the JSON2_S report
  got HTTP 502 and then NCBI's "SYSTEM CAN'T PROCESS YOUR REQUEST, PLEASE CONTACT blasthelp"
  page; a retry a minute later worked (success is not logged, but nothing was resubmitted and the
  run moved on). The human background search `DGU51Z2N014` was then submitted; its outcome was
  not known when this was written.

A search that small cannot be slow on its own merits, and the web page is fast because NCBI
gives "priority to interactive users".[^devinfo] So the API searches were being held. This session
then read that as NCBI's documented slower queue for more than 100 searches in 24 hours; NCBI's
answer (below) shows the hold was real but the cause was not that.

# What was ruled out

- **The size of the search.** The target tier does search a lot - 1,680,151 records for
  `txid11320[ORGN]`, against the 173,234 the assay itself cares about (both counted
  2026-10-20) - and the first diagnosis blamed that. The control showed it was not the cause:
  the one-oligo search against 10,334 records was held too. The size is still worth reducing
  (below).
- **An NCBI outage.** None was reported, and the web page worked.
- **The usage guidelines.** Checked against the code on 2026-10-21:[^etiquette]

  | Guideline | Code |
  |---|---|
  | At most one contact every 10 s | `blast_min_interval_s: 10`, before every BLAST request, retries included |
  | One poll per RID per minute | `poll_interval_s: 60`; the config refuses less |
  | `email` and `tool` | on every BLAST request (submit, status, fetch); `NCBI_EMAIL` is required |
  | Off-peak above 50 searches | an influenza run submits 3 (target, background, exclusivity): its ~1,000 nt segment 7 records are scanned directly, without BLAST |
  | Merge short queries up to 1,000 bases | `MAX_BATCH_BASES = 1000`; all 8 sequences in one search per tier |

  The user ran only a few runs in the week before, so well under 100 searches in 24 hours.

One gap was found: the 10-second limiter is per process. Two runs at the same time keep separate
clocks, so together they can contact NCBI more often than allowed and their searches add up.
`scripts/run_assay.sh` starts runs in the background, so a run that was never stopped keeps going.

# NCBI's answer

**Asked** on 2026-10-21, through blasthelp@ncbi.nlm.nih.gov: case **CAS-1714885-G5R3Z2**, created
2026-10-21T07:54:07Z. The questions: is the address being limited, what triggered it, how is a
user identified, how long does it last, and is a search like `DEPS5BKC014` a problem in itself.

**Answered** by the NCBI BLAST Support Team (pasted by the user on 2026-10-22), in full:

> "The developers made a change recently that could account for the slowness (long WAITING
> times) you observed. This change is being rolled back sometime today. Before submitting new
> searches we suggest that you wait for any currently running searches to complete."

So the cause was on NCBI's side, not the user's volume and not the size of the searches. The
user had said as much on 2026-10-20 ("I think there is something else going on at NCBI").
The answer does not say what the change was, why it affected API searches and not the web page,
or address the other questions (how a user is identified; whether `DEPS5BKC014` is a problem in
itself). Those stay unknown.

**Checked, closed 2026-10-23:** the HSV-1 run of that day took 1 minute for its human
background search and 1-2 minutes for every other search
([run](../runs/hsv1-2026-10-23.md)). Searches are back to normal.

Before that: **still to check** was that searches are back to normal. The influenza run was left to finish, as
NCBI advised ([run](../runs/influenza-a-2026-10-21.md)): its human background search, submitted
on the morning of 2026-10-21, took 481 minutes (about 60 before), and its exclusivity search,
submitted that afternoon, 2 minutes. That fits a rollback during that day but does not show it.
The HSV-1 run of 2026-10-23, with its own human background search, is the clean test; this item
closes when a run shows normal times.

# What still matters

This episode was not caused by heavy use, but the worry behind the original question stands: the
tool searches only at NCBI (a local BLAST database is excluded by the project rules), so its
throughput is whatever a shared public service allows, and NCBI says the servers are "not intended
for projects that involve a large number of BLAST searches".[^devinfo] And whatever holds a search
- a change at NCBI as here, or a real slower queue - nothing tells the user: a held search looks
exactly like a slow one.

What would make the tool sturdier against that - none of it decided, and less urgent now that the
cause is known:

- **Fewer searches per run.** The target tier is redundant for an assay whose records are all
  scanned directly (as here), and it is the largest search. Skipping it in that case, or
  narrowing it to the assay's own `nucleotide_query`, was proposed on 2026-10-20 and not built.
- **No restarts that resubmit.** The default `resubmit_after_minutes: 90` turns every late restart
  into a new submission. A higher default, or resubmitting only on NCBI's `UNKNOWN`, would stop
  that.
- **One run at a time**, enforced or at least warned about, so the per-process limiter holds.
- **Telling the user.** A search WAITING far beyond its estimate could say that NCBI may be holding
  it, and point to `scripts/blast_queue_check.py` (added 2026-10-20), which tells a held queue from
  an oversized search with one small control search.
- **A local BLAST.** Against the project rule, so the user's call alone.


[^devinfo]: NCBI BLAST developer information and usage guidelines
[^etiquette]: NCBI etiquette and limits
[^assay]: Influenza A (matrix gene)
[^session]: "Session 2026-10-21: the BLAST slow queue"
