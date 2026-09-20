import pytest

from qpcr_assay_check.errors import InputError
from qpcr_assay_check.oligo import iupac


def test_normalise_strips_whitespace_and_uppercases():
    assert iupac.normalise(" gac ccc\naaa ") == "GACCCCAAA"


def test_reverse_complement_plain_and_iupac():
    assert iupac.reverse_complement("AACG") == "CGTT"
    # R (A/G) <-> Y (C/T); reversed
    assert iupac.reverse_complement("ARN") == "NYT"


def test_complement_is_an_involution_for_all_codes():
    for code in iupac.IUPAC_CODES:
        assert iupac.complement(iupac.complement(code)) == code


def test_expand_degenerate_is_sorted_and_complete():
    assert iupac.expand("ARY", cap=64) == ["AAC", "AAT", "AGC", "AGT"]
    assert iupac.combinations("NNN") == 64


def test_expand_respects_cap():
    with pytest.raises(InputError, match="above the configured cap"):
        iupac.expand("NNNN", cap=64)


def test_find_invalid_reports_positions():
    assert iupac.find_invalid("ACUG-") == [(3, "U"), (5, "-")]


def test_gc_and_runs():
    assert iupac.gc_percent("GGCCAATT") == 50.0
    assert iupac.longest_run("AAGGGGCT") == 4
    assert iupac.longest_run("AAGGGGCT", "A") == 2
    assert iupac.longest_run("AAGGGGCT", "T") == 1


def test_mismatch_counting_uses_iupac_compatibility():
    assert iupac.count_mismatches("ACGT", "ACGT") == 0
    assert iupac.count_mismatches("ACGT", "ACGA") == 1
    assert iupac.count_mismatches("ACRT", "ACGT") == 0  # R matches G
    assert iupac.count_mismatches("ACRT", "ACCT") == 1  # R does not match C
    with pytest.raises(ValueError):
        iupac.count_mismatches("ACG", "ACGT")
