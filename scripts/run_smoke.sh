#!/bin/sh
# scripts/smoke_test.py in the Docker image, in the background (no Python needed).
# Run from the folder that contains work/ and scripts/:
#     sh scripts/run_smoke.sh [smoke_test.py options]      e.g. --quick --expect-sweep
# The report is work/smoke_out/smoke_report.json (paste that back); the log work/smoke_out/run.log.
# NCBI_EMAIL / NCBI_API_KEY: exported in the shell, or in .env in this folder (gitignored).
# The checkout's src/ is mounted over the image's installed package, so 'git pull' is enough.
set -e
mkdir -p work/smoke_out
opts=""
[ -f .env ] && opts="--env-file .env"
[ -n "${NCBI_EMAIL:-}" ] && opts="$opts -e NCBI_EMAIL=$NCBI_EMAIL"
[ -n "${NCBI_API_KEY:-}" ] && opts="$opts -e NCBI_API_KEY=$NCBI_API_KEY"
# shellcheck disable=SC2086
nohup docker run --rm --user "$(id -u):$(id -g)" $opts -v "$PWD/work:/work" \
    -v "$PWD/scripts:/scripts:ro" -v "$PWD/src:/src:ro" -e PYTHONPATH=/src \
    --entrypoint python qpcr-assay-check /scripts/smoke_test.py --out /work/smoke_out "$@" \
    > work/smoke_out/run.log 2>&1 &
echo "started; follow it with: tail -f work/smoke_out/run.log"
echo "when it ends, paste back: work/smoke_out/smoke_report.json"
