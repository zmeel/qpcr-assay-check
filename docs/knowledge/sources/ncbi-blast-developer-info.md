---
type: Reference
title: NCBI BLAST developer information and usage guidelines
description: NCBI's page for BLAST API users - the usage guidelines, the slower queue for more than 100 searches in 24 hours, and the advice against large search projects.
resource: https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html
tags: [ncbi, blast, documentation, etiquette]
status: draft
generated: { by: claude-code/agent, at: 2026-10-21T08:30:00Z }
sources:
  - id: devinfo
    resource: https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html
    title: NCBI BLAST developer information
    author: team:ncbi
---

# What it says (read 2026-10-20)

The usage guidelines, quoted:[^devinfo]

- "The NCBI BLAST servers are a shared resource. We give priority to interactive users."
- "We will move searches of users who submit more than 100 searches in a 24 hour period to a
  slower queue, or, in extreme cases, will block the requests."
- "Do not contact the server more often than once every 10 seconds."
- "Do not poll for any single RID more often than once a minute."
- "Use the URL parameter email and tool, so that the NCBI can contact you if there is a problem."
- "Run scripts weekends or between 9 pm and 5 am Eastern time on weekdays if more than 50
  searches will be submitted."
- Short queries (less than a few hundred bases) are best merged "into one search of up to 1,000
  bases".
- "The NCBI servers are a shared resource and not intended for projects that involve a large
  number of BLAST searches."

What the page does **not** say: how a "user" is identified (IP address, `email`, `tool`), what
else can put searches in the slower queue, how long that lasts, and how a search held there
shows to the client. The episode that raised these questions is
[the slow queue open item](../open/blast-slow-queue.md).

[^devinfo]: NCBI BLAST developer information
