"""Loci and channels in the assay model (overhaul step 1): old files load as one locus and one
channel per reporter; Legionella-type (one amplicon, two channels with different target taxa)
and true multiplexes (two loci) are written explicitly. Sequences here are SYNTHETIC (filler
plus the published CDC N1 oligos), never real Legionella or Neisseria sequences."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from qpcr_assay_check.cli import build_assay
from qpcr_assay_check.models import Assay
from qpcr_assay_check.oligo import iupac

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .world import filler

ROOT = Path(__file__).resolve().parent.parent
AMP = F + filler(30, 11) + P + filler(30, 12) + iupac.reverse_complement(R)
# a second, SYNTHETIC locus for the multiplex fixture
F2, P2, R2 = filler(20, 31), filler(22, 32), filler(20, 33)
AMP2 = F2 + filler(25, 34) + P2 + filler(25, 35) + iupac.reverse_complement(R2)


def test_an_old_file_is_one_locus_and_one_channel_per_reporter():
    a = make_assay(reference_amplicon=AMP)
    (lc,) = a.loci
    assert lc.primers == ["forward", "reverse"] and lc.probes == ["probe"]
    assert [r.sequence for r in lc.references] == [AMP]
    assert lc.scan_taxid == 2697049 and lc.context_accession == "NC_045512.2"
    (ch,) = a.channels
    assert (ch.name, ch.reporter, ch.probes, ch.target_taxid) == ("FAM", "FAM", ["probe"], 2697049)


def test_the_neisseria_example_is_one_locus_with_two_fragments_and_one_fam_channel():
    a = build_assay(ROOT / "docs" / "examples" / "neisseria_gonorrhoeae_two_probes.yaml", {})
    (lc,) = a.loci
    assert [r.name for r in lc.references] == ["NG-fragment-P1", "NG-fragment-P2"]
    assert lc.primers == ["NG-F", "NG-R"] and lc.probes == ["NG-P1", "NG-P2"]
    (ch,) = a.channels
    assert (ch.reporter, ch.probes, ch.target_taxid) == ("FAM", ["NG-P1", "NG-P2"], 485)


def legionella_like(**overrides):
    """One amplicon, a genus channel and a species channel (as the Legionella assay)."""
    data = {
        "assay_name": "genus + species (synthetic)",
        "forward": {"name": "G-F", "sequence": F},
        "reverse": {"name": "G-R", "sequence": R},
        "probe": [
            {"name": "P-genus", "sequence": P, "reporter": "VIC"},
            {"name": "P-species", "sequence": filler(22, 5), "reporter": "FAM"},
        ],
        "target": {"taxid": 444},
        "loci": [{"name": "23S-5S", "primers": ["G-F", "G-R"],
                  "probes": ["P-genus", "P-species"],
                  "references": [{"name": "Lpn", "sequence": AMP}],
                  "context_accession": "NC_002942.5"}],
        "channels": [
            {"name": "Legionella", "probes": ["P-genus"]},
            {"name": "L. pneumophila", "probes": ["P-species"], "target_taxid": 446},
        ],
    }  # fmt: skip
    data.update(overrides)
    return Assay.model_validate(data)


def test_two_channels_on_one_amplicon_carry_their_own_target_and_reporter():
    a = legionella_like()
    genus, species = a.channels
    assert (genus.reporter, genus.target_taxid) == ("VIC", 444)
    assert (species.reporter, species.target_taxid) == ("FAM", 446)
    assert a.channel_of("P-species").name == "L. pneumophila"
    (lc,) = a.loci
    assert lc.scan_taxid == 444 and lc.context_accession == "NC_002942.5"
    assert a.reference_amplicon == AMP  # the variant analysis reads the first locus


def test_a_multiplex_has_one_locus_per_region():
    a = Assay.model_validate({
        "assay_name": "duplex (synthetic)",
        "forward": [{"name": "A-F", "sequence": F}, {"name": "B-F", "sequence": F2}],
        "reverse": [{"name": "A-R", "sequence": R}, {"name": "B-R", "sequence": R2}],
        "probe": [{"name": "A-P", "sequence": P, "reporter": "FAM"},
                  {"name": "B-P", "sequence": P2, "reporter": "VIC"}],
        "target": {"taxid": 2697049},
        "loci": [
            {"name": "A", "primers": ["A-F", "A-R"], "probes": ["A-P"],
             "references": [{"name": "A-ref", "sequence": AMP}]},
            {"name": "B", "primers": ["B-F", "B-R"], "probes": ["B-P"],
             "references": [{"name": "B-ref", "sequence": AMP2}], "scan_taxid": 694009},
        ],
    })  # fmt: skip
    assert [lc.name for lc in a.loci] == ["A", "B"]
    assert [lc.scan_taxid for lc in a.loci] == [2697049, 694009]
    assert [c.reporter for c in a.channels] == ["FAM", "VIC"]  # one per reporter by default
    assert [lc.name for lc in a.locus_of("B-P")] == ["B"]
    assert a.reference_amplicons[0].name == "A-ref"


def test_a_loaded_assay_survives_a_round_trip():
    a = legionella_like()
    again = Assay.model_validate(a.model_dump())
    assert again.loci == a.loci and again.channels == a.channels


def test_the_channel_reporter_fills_probes_without_one():
    probes = [{"name": "P-genus", "sequence": P},
              {"name": "P-species", "sequence": filler(22, 5)}]  # fmt: skip
    channels = [
        {"name": "g", "reporter": "VIC", "probes": ["P-genus"]},
        {"name": "s", "reporter": "FAM", "probes": ["P-species"], "target_taxid": 446},
    ]
    a = legionella_like(probe=probes, channels=channels)
    assert [a.oligo(n).reporter for n in ("P-genus", "P-species")] == ["VIC", "FAM"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"channels": [{"name": "g", "probes": ["P-genus"]}]}, "belong to no channel"),
        (
            {
                "channels": [
                    {"name": "g", "probes": ["P-genus"], "reporter": "FAM"},
                    {"name": "s", "probes": ["P-species"]},
                ]
            },
            "reads FAM",
        ),  # fmt: skip
        ({"channels": [{"name": "g", "probes": ["P-genus", "P-species"]}]}, "one dye"),
        ({"channels": [{"name": "g", "probes": ["P-x"]}]}, "no probe named"),
        (
            {
                "channels": [
                    {"name": "g", "probes": ["P-genus"]},
                    {
                        "name": "s",
                        "probes": ["P-species"],
                        "target_taxid": 446,
                        "taxa": [{"taxid": 446}],
                    },
                ]
            },
            "its own target",
        ),  # fmt: skip
        (
            {"loci": [{"name": "x", "primers": ["G-F"], "probes": ["P-genus", "P-species"]}]},
            "one forward and one reverse",
        ),  # fmt: skip
        (
            {"loci": [{"name": "x", "primers": ["G-F", "G-R"], "probes": ["P-genus"]}]},
            "belong to no locus",
        ),  # fmt: skip
        (
            {
                "loci": [
                    {"name": "x", "primers": ["G-F", "G-R", "P-genus"], "probes": ["P-species"]}
                ]
            },
            "one forward and one reverse",
        ),  # fmt: skip
        ({"reference_amplicons": [{"name": "other", "sequence": AMP2}]}, "per locus"),
    ],
)
def test_inconsistent_loci_and_channels_are_refused(overrides, message):
    with pytest.raises(ValidationError, match=message):
        legionella_like(**overrides)
