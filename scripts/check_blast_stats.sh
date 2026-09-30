#!/bin/sh
# Show whether the cached BLAST results carry NCBI's search statistics (read-only, no network).
# Run from the folder that contains work/ and scripts/:  sh scripts/check_blast_stats.sh
# Optional: a cache folder as the container sees it (default /work/cache) and a count (6).
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/work:/work:ro" \
    -v "$PWD/scripts:/scripts:ro" --entrypoint python qpcr-assay-check \
    /scripts/check_blast_stats.py "${1:-/work/cache}" "${2:-6}"
