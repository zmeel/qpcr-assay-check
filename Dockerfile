# qpcr-assay-check: in silico re-evaluation of one real-time PCR (TaqMan) assay per run.
#
# No local BLAST database is built or shipped: all NCBI searching is remote, at run time, over
# the network. Give NCBI_EMAIL (required for any network use) and NCBI_API_KEY (optional) as
# environment variables; never bake credentials into the image. Mount a host directory over
# /work/results to keep evaluation records outside the container.

FROM python:3.12-slim AS build

WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-compile .

FROM python:3.12-slim

# Match the build stage's installed site-packages and console script without repeating the build.
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/qpcr-assay-check /usr/local/bin/qpcr-assay-check
COPY LICENSE /LICENSE

RUN useradd --create-home --uid 1000 qpcr
USER qpcr
WORKDIR /work

ENTRYPOINT ["qpcr-assay-check"]
CMD ["--help"]
