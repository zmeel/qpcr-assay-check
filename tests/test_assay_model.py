import pytest
from pydantic import ValidationError

from qpcr_assay_check.models import Status, worst

from .conftest import make_assay


def test_valid_assay_cleans_sequences():
    a = make_assay(forward="gac ccc aaa atc agc gaa at")
    assert a.forward == "GACCCCAAAATCAGCGAAAT"
    assert a.slug == "cdc-n1"


def test_uracil_gets_a_specific_hint():
    with pytest.raises(ValidationError) as e:
        make_assay(probe="ACCCCGCAUUACGTTTGGTGGACC")
    text = str(e.value)
    assert "T instead of U" in text
    assert "probe_reporter" not in text  # the dye hint must not appear for plain U


def test_dye_label_in_sequence_gets_a_specific_hint():
    with pytest.raises(ValidationError, match="probe_reporter"):
        make_assay(probe="FAM-ACCCCGCATTACGTTTGGTGGACC")


@pytest.mark.parametrize("seq", ["", "ACGT", "A" * 61])
def test_length_limits(seq):
    with pytest.raises(ValidationError):
        make_assay(forward=seq)


def test_target_needs_taxid_or_accession():
    with pytest.raises(ValidationError, match="taxid"):
        make_assay(target={"gene": "N"})


@pytest.mark.parametrize("acc", ["NC_045512.2", "MN908947.3", "NZ_CP012345.1", "AB123456"])
def test_accepts_real_accession_formats(acc):
    assert make_assay(target={"accession": acc}).target.accession == acc


def test_rejects_garbage_accession():
    with pytest.raises(ValidationError, match="accession"):
        make_assay(target={"accession": "not an accession"})


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError, match="extra"):
        make_assay(forwrad="ACGT")


def test_modifications_are_normalised():
    assert make_assay(probe_modifications="mgb, zen; MGB").probe_modifications == ["MGB", "ZEN"]


def test_declared_modifications_detects_tokens_in_labels():
    a = make_assay(probe_quencher="MGB-NFQ", probe_modifications=["LNA"])
    assert set(a.declared_modifications(("MGB", "LNA", "ZEN"))) == {"MGB", "LNA"}


def test_taxid_lists_are_deduplicated_and_sorted():
    a = make_assay(exclusion_taxids=[9606, 562, 9606])
    assert a.exclusion_taxids == [562, 9606]


def test_worst_status():
    assert worst([Status.PASS, Status.WARN, Status.INFO]) is Status.WARN
    assert worst([Status.PASS, Status.FAIL, Status.WARN]) is Status.FAIL
    assert worst([Status.INFO]) is Status.INFO
    assert worst([]) is Status.INFO
