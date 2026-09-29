#!/bin/sh
# Borderline candidates of the locator measurements, via the Docker image (no Python needed).
# Run from the folder that contains work/ and scripts/:
#     sh scripts/measure_borderline.sh                 # legionella2 and neisseria
#     sh scripts/measure_borderline.sh legionella2     # or name the measure_out folders
# Writes work/measure_out/borderline.txt (paste that file back).
set -e
[ $# -gt 0 ] || set -- legionella2 neisseria
reports=""
for name in "$@"; do reports="$reports measure_out/$name/measure_report.json"; done
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/work:/work" -v "$PWD/scripts:/scripts:ro" \
    --entrypoint python qpcr-assay-check /scripts/measure_borderline.py $reports \
    > work/measure_out/borderline.txt 2>&1
wc -l work/measure_out/borderline.txt
