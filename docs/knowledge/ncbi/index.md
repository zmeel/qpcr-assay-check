# Ncbi

NCBI behaviour checked against current documentation or measured live.

* [BLAST URL API - what the code relies on](blast-url-api.md) - Documented parameters, word size 7 minimum, JSON2_S, core_nt, ENTREZ_QUERY outside the documented surface, and the search statistics behind the score floor.
* [NCBI Datasets v2 - what the code relies on](datasets-v2.md) - dataset_report paging, GCA/GCF duplicates, genome downloads, hydrated fetch, and sequence_reports with roles, one assembly per request.
* [NCBI etiquette and limits](etiquette.md) - 10 s between BLAST contacts, one poll per RID per minute, tool and email, off-peak for large batches, E-utilities 3 or 10 requests per second.
* [E-utilities - what the code relies on](eutils.md) - ESearch paging past a million records, EFetch accession lists, ESummary dates, taxonomy lookups, and nuccore collection dates.
