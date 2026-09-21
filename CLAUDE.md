# qpcr-assay-check — project rules

Full specification: docs/SPEC.md (authoritative). Progress log: docs/PROGRESS.md.
Read both at the start of every session. Update PROGRESS.md before ending a session.

## Hard rules
- NEVER invent primer/probe sequences, NCBI parameters, limits or API behaviour.
  If unverified, check current NCBI docs and state what you found, or use a clearly
  labelled placeholder and tell me.
- All example-assay sequences must be verified against the source publication.
- Remote NCBI only: no local BLAST database. No form scraping.
- NCBI email/API key come only from env vars (NCBI_EMAIL, NCBI_API_KEY). Never commit
  secrets; keep .env gitignored.
- Respect NCBI etiquette: tool/email params, throttling, backoff, polite polling.
- Never present a sample as the full population. Never fabricate results.
- Reports must state that in silico analysis does not replace experimental validation
  and that the lab must verify the software within its own quality system.

## Engineering
- Python 3.11+, pyproject.toml, typer, type hints, docstrings, logging (no bare prints).
- Tests: pytest with mocked BLAST XML/Entrez. Live-network tests are marked
  @pytest.mark.live and are never run in CI.
- Before every commit: `ruff check .` and `pytest -m "not live"` must pass.

## Git
- Conventional Commits. Annotated tags per phase (v0.1.0 ... v1.0.0).
- Never force-push. Never push without asking me first.
- Update CHANGELOG.md at the end of each phase.

## Workflow
- Work phase by phase as defined in docs/SPEC.md. Do not start the next phase
  without my go-ahead.
- I run live NCBI checks locally (scripts/smoke_test.py) and paste back the output
  you specify.

## Open items
- LICENSE not yet chosen: ask me before adding one.
