"""Shared fixtures. Live-network tests are opt-in (``--run-live``) and never run in CI."""

from __future__ import annotations

import pytest

from qpcr_assay_check.config import Config, load_config
from qpcr_assay_check.models import Assay
from qpcr_assay_check.oligo import iupac

# Published oligos (see examples/cdc_2019-nCoV_N1.yaml for the verification record).
CDC_N1_F = "GACCCCAAAATCAGCGAAAT"
CDC_N1_R = "TCTGGTTACTGCCAGTTGAATCTG"
CDC_N1_P = "ACCCCGCATTACGTTTGGTGGACC"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-live", action="store_true", default=False, help="run live NCBI tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-live"):
        return
    skip = pytest.mark.skip(reason="live NCBI test: use --run-live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def cfg() -> Config:
    return load_config()


def make_assay(**overrides: object) -> Assay:
    data: dict[str, object] = {
        "assay_name": "CDC N1",
        "forward": CDC_N1_F,
        "reverse": CDC_N1_R,
        "probe": CDC_N1_P,
        "probe_reporter": "FAM",
        "probe_quencher": "BHQ1",
        "template_type": "RNA",
        "target": {"taxid": 2697049, "accession": "NC_045512.2", "gene": "N"},
    }
    data.update(overrides)
    return Assay.model_validate(data)


@pytest.fixture
def n1() -> Assay:
    return make_assay()


def synthetic_amplicon(fwd: str = CDC_N1_F, probe: str = CDC_N1_P, rev: str = CDC_N1_R) -> str:
    """A SYNTHETIC amplicon built from the oligos plus filler. Not a real sequence."""
    return fwd + "TT" + probe + "AA" + iupac.reverse_complement(rev)
