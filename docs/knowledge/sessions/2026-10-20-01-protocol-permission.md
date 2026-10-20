---
type: Session
title: "Permission for the protocol's oligos, and four days of a held-back commit"
description: "Session log of 2026-10-20."
tags: [session]
session_date: 2026-10-20
session_label: "2026-10-20"
generated: { by: claude-code/agent, at: 2026-10-20T07:00:00Z }
---

# 2026-10-20: the permission

- The commit of 2026-10-16 holding `infa_rev2` and the Erasmus MC provenance had stayed local
  since it was written: the protocol prohibits distribution outside the Dutch network and
  publication in any form without its authors' permission, and this repository is public. Every
  attempt to push it was refused on those grounds.
- A permission rule was considered and dropped. It would have addressed the wrong thing: the
  refusal was a judgement about what the commit publishes, not about whether `git push` may run,
  so the rule would not have cleared it and granting oneself the permission one was just refused
  defeats the refusal. Recorded here because the first suggestion in the session was that rule,
  and it was wrong.
- The state was written down instead, as the open item
  [Permission to publish the Erasmus MC influenza oligos](../open/influenza-protocol-permission.md):
  what the protocol says, what each answer would mean for the public example file, and the
  separate question of the four oligos already in the public history since 2026-10-07. The three
  changed files were handed to the user as well, since this container is ephemeral and the
  commits would have died with it.
- **The user obtained the permission**: R. Molenkamp gave it, reported 2026-10-20. Both commits
  were pushed on that basis. The assay file and the assay concept record it, and the open item is
  closed. What is published is the five oligos, their names and the reaction conditions; the
  protocol itself is not redistributed. The wording and form of the permission are held by the
  laboratory - this project holds the user's report of it, and says so.
- The four oligos in the public history since 2026-10-07 are among the five the permission
  covers, so no history rewrite and no force-push are needed.
- Aside: `python scripts/build_knowledge.py` failed on the user's machine with
  `ModuleNotFoundError: No module named 'yaml'`. PyYAML is a declared dependency, so that was an
  environment the project is not installed into; the script imports nothing else third-party and
  nothing from the package.

# Next

- A rerun of the influenza assay with both reverse primers: the next run.
- Giardia: still waiting on confirmation of the oligos against Verweij 2004, on `status_axis`,
  and on what the predicted detection of *G. microti* and *G. psittaci* means.
