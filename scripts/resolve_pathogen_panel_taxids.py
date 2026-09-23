#!/usr/bin/env python3
"""Resolve NCBI taxonomy IDs for every pathogen in docs/clinical_pathogen_panels.md, live.

WHY THIS EXISTS
    docs/clinical_pathogen_panels.md lists human pathogens by syndromic real-time PCR panel, and
    the user asked for NCBI taxonomy IDs added to it. Per CLAUDE.md ("NEVER invent... NCBI
    parameters... never guessed") and this project's own taxonomy/resolve.py design ("never picks
    a UID out of an ambiguous result: that would be guessing"), taxonomy IDs are not typed in from
    memory: this script resolves every name through the exact same Entrez Taxonomy lookup this
    tool already uses live for its own exclusivity organism list (`[Scientific Name]` first, then
    `[All Names]` for synonyms; ambiguous or unresolved names are reported, never picked at
    random), so results here get the same live confirmation.

    This is not run automatically because this development sandbox cannot reach NCBI (see
    CLAUDE.md). Run it locally and paste back the report.

HOW TO RUN (from the repository root, after `pip install -e .`)
    export NCBI_EMAIL="your.name@example.org"
    export NCBI_API_KEY="..."            # optional, raises the rate limit from 3/s to 10/s
    python scripts/resolve_pathogen_panel_taxids.py

    The report is written to pathogen_taxid_report.json (rewritten after every name, so it is
    safe to interrupt and re-run: already-resolved names are skipped on the next run unless
    --force is given). It is also printed as a Markdown table at the end.

WHAT TO PASTE BACK
    The full contents of pathogen_taxid_report.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import QpcrAssayCheckError
from qpcr_assay_check.ncbi.cache import Cache
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiHttp
from qpcr_assay_check.ncbi.settings import credentials_from_env
from qpcr_assay_check.taxonomy.resolve import resolve_name

log = logging.getLogger(__name__)

# One entry per row (or per alternate name worth trying) in docs/clinical_pathogen_panels.md.
# A few taxa are listed under two names (a current name and a still-common synonym, e.g. the
# 2018 Mycoplasma -> Mycoplasmoides rename already found not to resolve via [All Names] in this
# project's own live testing) so both can be checked; the doc gets whichever one resolves.
NAMES: list[str] = [
    # --- Viruses ---
    "Influenza A virus",
    "Influenza B virus",
    "Human orthopneumovirus",
    "Respiratory syncytial virus",
    "Human respirovirus 1",  # parainfluenza 1 (current ICTV name)
    "Human respirovirus 3",  # parainfluenza 3
    "Human orthorubulavirus 2",  # parainfluenza 2
    "Human orthorubulavirus 4",  # parainfluenza 4
    "Human parainfluenza virus 1",
    "Human parainfluenza virus 2",
    "Human parainfluenza virus 3",
    "Human parainfluenza virus 4",
    "Human metapneumovirus",
    "Rhinovirus A",
    "Rhinovirus B",
    "Rhinovirus C",
    "Human rhinovirus",
    "Enterovirus",
    "Human mastadenovirus",
    "Human adenovirus",
    "Human coronavirus 229E",
    "Human coronavirus NL63",
    "Human coronavirus OC43",
    "Human coronavirus HKU1",
    "Severe acute respiratory syndrome coronavirus 2",
    "Human bocavirus",
    "Norovirus",
    "Norwalk virus",
    "Rotavirus A",
    "Human adenovirus F",
    "Human astrovirus",
    "Sapovirus",
    "Human betaherpesvirus 5",  # cytomegalovirus (current name)
    "Human cytomegalovirus",
    "Human alphaherpesvirus 1",  # HSV-1 (current name)
    "Herpes simplex virus 1",
    "Human alphaherpesvirus 2",  # HSV-2 (current name)
    "Herpes simplex virus 2",
    "Human betaherpesvirus 6A",
    "Human betaherpesvirus 6B",
    "Human herpesvirus 6",
    "Human parechovirus",
    "Human alphaherpesvirus 3",  # varicella zoster virus (current name)
    "Varicella zoster virus",
    "Primate erythroparvovirus 1",  # parvovirus B19 (current name)
    "Human parvovirus B19",
    "Zika virus",
    "Rubella virus",
    # --- Bacteria ---
    "Bordetella pertussis",
    "Bordetella parapertussis",
    "Mycoplasmoides pneumoniae",  # current name (see data/clinical_organisms.yaml)
    "Mycoplasma pneumoniae",
    "Chlamydia pneumoniae",
    "Legionella pneumophila",
    "Streptococcus pneumoniae",
    "Haemophilus influenzae",
    "Moraxella catarrhalis",
    "Staphylococcus aureus",
    "Klebsiella pneumoniae",
    "Klebsiella oxytoca",
    "Klebsiella aerogenes",
    "Escherichia coli",
    "Enterobacter cloacae",
    "Serratia marcescens",
    "Proteus mirabilis",
    "Proteus",
    "Pseudomonas aeruginosa",
    "Acinetobacter baumannii",
    "Campylobacter jejuni",
    "Campylobacter coli",
    "Salmonella enterica",
    "Shigella",
    "Yersinia enterocolitica",
    "Vibrio cholerae",
    "Vibrio parahaemolyticus",
    "Vibrio vulnificus",
    "Plesiomonas shigelloides",
    "Clostridioides difficile",
    "Neisseria meningitidis",
    "Listeria monocytogenes",
    "Streptococcus agalactiae",
    "Enterococcus faecalis",
    "Enterococcus faecium",
    "Chlamydia trachomatis",
    "Neisseria gonorrhoeae",
    "Mycoplasma genitalium",
    "Mycoplasma hominis",
    "Ureaplasma urealyticum",
    "Ureaplasma parvum",
    "Treponema pallidum",
    "Haemophilus ducreyi",
    "Gardnerella vaginalis",
    "Fannyhessea vaginae",  # current name
    "Atopobium vaginae",
    "Megasphaera",
    "Lactobacillus",
    "Mobiluncus",
    "Borrelia burgdorferi",
    "Borrelia miyamotoi",
    "Anaplasma phagocytophilum",
    "Ehrlichia chaffeensis",
    "Ehrlichia ewingii",
    "Rickettsia",
    "Mycobacterium tuberculosis",
    "Mycobacterium tuberculosis complex",
    "Mycobacterium avium complex",
    "Mycobacterium avium",
    "Mycobacterium abscessus",
    "Mycobacterium chelonae",
    "Mycobacterium kansasii",
    "Mycobacterium fortuitum",
    "Streptococcus pyogenes",
    "Bacteroides fragilis",
    "Clostridium perfringens",
    "Finegoldia magna",
    "Peptoniphilus",
    # --- Fungi ---
    "Cryptococcus neoformans",
    "Cryptococcus gattii",
    "Candida albicans",
    "Nakaseomyces glabratus",  # current name for Candida glabrata
    "Candida glabrata",
    "Candida parapsilosis",
    "Candida tropicalis",
    "Pichia kudriavzevii",  # current name for Candida krusei
    "Candida krusei",
    "Candida auris",
    # --- Parasites ---
    "Trichomonas vaginalis",
    "Giardia duodenalis",
    "Giardia lamblia",
    "Giardia intestinalis",
    "Cryptosporidium parvum",
    "Cryptosporidium hominis",
    "Entamoeba histolytica",
    "Cyclospora cayetanensis",
    "Babesia microti",
    "Babesia duncani",
    "Toxoplasma gondii",
]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=Path("pathogen_taxid_report.json"))
    ap.add_argument("--force", action="store_true", help="re-resolve names already in the cache")
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", stream=sys.stdout
    )

    try:
        creds = credentials_from_env()
    except QpcrAssayCheckError as exc:
        log.error("%s", exc)
        return 2

    cfg = load_config()
    http = NcbiHttp(cfg.ncbi, creds)
    eu = Eutils(http, cfg.ncbi.eutils_url)
    cache = Cache(cfg.ncbi.cache_dir)

    names = list(dict.fromkeys(NAMES))  # de-duplicate, keep order
    results: dict[str, dict] = {}
    for i, name in enumerate(names, 1):
        ttl_days = 0 if args.force else 3650  # 0 forces a fresh lookup; else reuse a warm cache
        res = resolve_name(eu, cache, name, ttl_days=ttl_days, synonyms=True)
        results[name] = res.model_dump()
        log.info(
            "[%d/%d] %-45s -> %s%s", i, len(names), name, res.status,
            f" (taxid {res.taxid})" if res.taxid else "",
        )  # fmt: skip
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    n_resolved = sum(1 for r in results.values() if r["status"] == "resolved")
    n_ambiguous = sum(1 for r in results.values() if r["status"] == "ambiguous")
    n_unresolved = sum(1 for r in results.values() if r["status"] == "unresolved")
    log.info(
        "Done: %d resolved, %d ambiguous, %d unresolved (of %d names). Report: %s",
        n_resolved, n_ambiguous, n_unresolved, len(names), args.out,
    )  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
