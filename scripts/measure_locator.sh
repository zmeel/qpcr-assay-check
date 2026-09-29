#!/bin/sh
# Run scripts/measure_locator.py in the Docker image, in the background (no Python needed).
# Run from the folder that contains work/ and scripts/:
#     sh scripts/measure_locator.sh NAME [measure_locator.py options]
# NAME is the output folder under work/measure_out; the log is work/measure_out/NAME.log.
# NCBI_EMAIL / NCBI_API_KEY: exported in the shell, or in .env in this folder (gitignored;
# lines NCBI_EMAIL=you@example.org, without quotes).
set -e
[ $# -ge 1 ] || { echo "usage: sh scripts/measure_locator.sh NAME [options]" >&2; exit 2; }
name=$1
shift
mkdir -p work/measure_out
opts=""
[ -f .env ] && opts="--env-file .env"
[ -n "${NCBI_EMAIL:-}" ] && opts="$opts -e NCBI_EMAIL=$NCBI_EMAIL"
[ -n "${NCBI_API_KEY:-}" ] && opts="$opts -e NCBI_API_KEY=$NCBI_API_KEY"
# shellcheck disable=SC2086
nohup docker run --rm --user "$(id -u):$(id -g)" $opts -v "$PWD/work:/work" \
    -v "$PWD/scripts:/scripts:ro" --entrypoint python qpcr-assay-check \
    /scripts/measure_locator.py --outdir "measure_out/$name" "$@" \
    > "work/measure_out/$name.log" 2>&1 &
echo "started; follow it with: tail -f work/measure_out/$name.log"
