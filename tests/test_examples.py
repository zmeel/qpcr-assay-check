from importlib import resources
from pathlib import Path

import pytest

from qpcr_assay_check.cli import build_assay
from qpcr_assay_check.config import load_config

from .conftest import CDC_N1_F, CDC_N1_P, CDC_N1_R

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["cdc_2019-nCoV_N1.yaml", "config_annealing_55C.yaml"]


@pytest.mark.parametrize("name", NAMES)
def test_repo_examples_match_the_packaged_copies(name):
    packaged = (resources.files("qpcr_assay_check") / "data" / "examples" / name).read_text()
    assert (ROOT / "examples" / name).read_text() == packaged


def test_example_assay_is_valid_and_matches_the_verified_sequences():
    a = build_assay(ROOT / "examples" / "cdc_2019-nCoV_N1.yaml", {})
    assert (a.forward, a.reverse, a.probe) == (CDC_N1_F, CDC_N1_R, CDC_N1_P)
    assert a.target.taxid == 2697049
    assert a.reference_amplicon is None  # deliberately not shipped unverified


def test_example_config_loads():
    assert (
        load_config(ROOT / "examples" / "config_annealing_55C.yaml").reaction.annealing_temp_C
        == 55.0
    )
