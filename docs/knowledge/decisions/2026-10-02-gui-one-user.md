---
type: Decision
title: "Browser interface - one user, LAN or VPN, YAML stays the source"
description: "A password-protected GUI for one user on a LAN or VPN, 8 hours idle sign-out; YAML stays the source of truth; the GUI confirms the dry-run plan."
tags: [decision]
status: draft
decided_on: 2026-10-02
generated: { by: claude-code/agent, at: 2026-10-04T04:30:00Z }
sources:
  - id: progress
    resource: ../sessions/2026-10-02-02-browser-interface-g1-g5-v2-1-0-released.md
    title: "Session 2026-10-02: Browser interface G1-G5; v2.1.0 released"
  - id: spec
    resource: ../../SPEC.md
    title: "docs/SPEC.md (amendments)"
---

# Decision

One user with a password, LAN/VPN only, sign-out after 8 hours idle, mock-up first. The assay YAML stays the source of truth (the form covers common fields; loci, channels, references and settings are edited as YAML so provenance comments survive). The GUI confirms the dry-run plan; the per-run genome budget stays a config/assay setting.[^progress][^spec]

# Who and why

User decisions (2026-10-02), after an approved mock-up.

# What followed

Phases G1-G5 built and released as v2.1.0 ([GUI](../components/gui.md)).

[^progress]: Session 2026-10-02: Browser interface G1-G5; v2.1.0 released
[^spec]: docs/SPEC.md (amendments)
