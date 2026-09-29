#!/bin/sh
# A full run of one assay in the Docker image, in the background (overhaul step 8).
# Run from the folder that contains work/ and scripts/:
#     sh scripts/run_assay.sh NAME ASSAY [qpcr-assay-check run options]
# NAME:  a label; the log is work/runs/NAME.log, the summary to paste back
#        work/runs/NAME-summary.json (written when the run ends).
# ASSAY: the assay file as the container sees it: /work/... for a file in work/, or
#        /examples/... for one of docs/examples (mounted read-only).
# Uses work/config.yaml when it exists (e.g. ncbi: cache_dir: /work/cache). Results go to
# work/results. NCBI_EMAIL / NCBI_API_KEY: exported in the shell, or in .env in this folder
# (gitignored; lines NCBI_EMAIL=you@example.org, without quotes).
# The checkout's src/ is mounted over the image's installed package (PYTHONPATH), so a
# 'git pull' is enough: no image rebuild.
set -e
[ $# -ge 2 ] || { echo "usage: sh scripts/run_assay.sh NAME ASSAY [options]" >&2; exit 2; }
name=$1
assay=$2
shift 2
mkdir -p work/runs work/results
opts=""
[ -f .env ] && opts="--env-file .env"
[ -n "${NCBI_EMAIL:-}" ] && opts="$opts -e NCBI_EMAIL=$NCBI_EMAIL"
[ -n "${NCBI_API_KEY:-}" ] && opts="$opts -e NCBI_API_KEY=$NCBI_API_KEY"
conf=""
[ -f work/config.yaml ] && conf="-c /work/config.yaml"
docker_run="docker run --rm --user $(id -u):$(id -g) $opts -v $PWD/work:/work \
    -v $PWD/docs/examples:/examples:ro -v $PWD/scripts:/scripts:ro \
    -v $PWD/src:/src:ro -e PYTHONPATH=/src --entrypoint python qpcr-assay-check"
log="work/runs/$name.log"
# shellcheck disable=SC2086
nohup sh -c "
    $docker_run -m qpcr_assay_check run $assay $conf -o /work/results --yes -v $* > $log 2>&1
    echo \"exit code \$?\" >> $log
    dir=\$(grep 'Record written to' $log | tail -1 | sed 's/.*Record written to //')
    if [ -n \"\$dir\" ]; then
        $docker_run /scripts/run_summary.py \$dir/results.json > work/runs/$name-summary.json 2>&1
    fi
" > /dev/null 2>&1 &
echo "started; follow it with: tail -f $log"
echo "when it ends, paste back: work/runs/$name-summary.json"
