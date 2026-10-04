---
type: Session
title: "Docker image built and run successfully by the user"
description: "Session log of 2026-09-22."
tags: [session]
session_date: 2026-09-22
session_label: "2026-09-22"
generated: { by: claude-code/agent }
moved_from: docs/PROGRESS.md (verbatim, 2026-10-04)
---

# 2026-09-22: Docker image built and run successfully by the user

The user built the image on their Synology NAS (Docker running as root) and ran it: `--version`
and `--help` worked immediately. `init` failed on the first try with a `PermissionError` writing
into the bind-mounted `/work` directory -- the image's default user is non-root (uid 1000), which
does not own a directory created/owned by root on the host. Gave two fixes (`--user
"$(id -u):$(id -g)"` on `docker run`, or `chown` the host directory to uid 1000 first); the user
used `--user` and it worked. `run --qc-only` then produced the exact same verdict and rationale
message as the plain-virtualenv install this was first checked against in-sandbox, confirming the
image installs and runs the real package correctly end to end for the offline path.

Updated README.md (Docker section now shows `--user` in every example, explains why, and states
what's confirmed vs. not — a full NCBI network run through the container specifically hasn't been
separately exercised, only through the plain-virtualenv install), docs/ARCHITECTURE.md (moved
Docker from "still unverified" to a new "Verified for v1.0.0" section), and CHANGELOG.md (Known
limitations updated to describe the uid-1000 permission behavior rather than "not built at all").

One thing to note for next time: the first copy-pasted `docker run` command with a trailing `\`
line continuation failed with "docker: invalid reference format" in the user's terminal --
resolved by giving the same command as one line instead. Multi-line backslash-continued shell
commands are apparently not safe to assume will paste correctly into every terminal; prefer
single-line commands (or a documented heredoc, as used for the git tag commands earlier in this
session) when giving copy-paste instructions to run remotely, since round-tripping a fix through
chat is slow.
