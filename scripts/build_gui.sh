#!/bin/sh
# Build the GUI image with the commit it comes from, so every record names it, then restart the
# GUI. Run from the checkout (the folder with docker-compose.yml), after `git pull`:
#     sh scripts/build_gui.sh
# Without git, or outside a checkout, the commit is "unknown"; the code fingerprint in each
# record still names the code exactly. Options after the script name go to `docker compose up`.
set -e
commit=$(git rev-parse HEAD 2>/dev/null || echo unknown)
dirty=unknown
if [ "$commit" != unknown ]; then
    if [ -n "$(git status --porcelain --untracked-files=no -- src 2>/dev/null)" ]; then
        dirty=yes
    else
        dirty=no
    fi
fi
echo "building the GUI image from commit $commit (local changes in src/: $dirty)"
QAC_GIT_COMMIT=$commit QAC_GIT_DIRTY=$dirty docker compose build
docker compose up -d "$@"
docker compose run --rm --no-deps gui fingerprint
