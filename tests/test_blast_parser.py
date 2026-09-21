import json

import pytest

from qpcr_assay_check.ncbi import blast
from qpcr_assay_check.ncbi.http import NcbiError
from qpcr_assay_check.ncbi.parser import ParseError, parse_blast_json

from .fake_ncbi import blast_json, put_text, status_text

LABELS = ["forward", "reverse", "probe"]


def test_put_parameters_follow_the_configured_short_oligo_settings(cfg):
    fasta = blast.build_query_fasta({"forward": "ACGT", "probe": "GGCC"})
    assert fasta == ">forward\nACGT\n>probe\nGGCC\n"
    p = blast.build_put_params(cfg, fasta, "txid9606[ORGN]")
    assert p["CMD"] == "Put" and p["PROGRAM"] == "blastn" and p["DATABASE"] == "core_nt"
    assert (p["WORD_SIZE"], p["EXPECT"], p["FILTER"]) == ("7", "1000", "F")
    assert (p["NUCL_REWARD"], p["NUCL_PENALTY"], p["GAPCOSTS"]) == ("1", "-3", "5 2")
    assert p["ENTREZ_QUERY"] == "txid9606[ORGN]" and p["HITLIST_SIZE"] == "5000"
    assert "ENTREZ_QUERY" not in blast.build_put_params(cfg, fasta, None)


def test_entrez_query_for_one_or_many_taxa():
    assert blast.build_entrez_query([]) is None
    assert blast.build_entrez_query([9606]) == "txid9606[ORGN]"
    assert blast.build_entrez_query([9606, 562]) == "(txid9606[ORGN] OR txid562[ORGN])"


def test_request_key_changes_with_every_parameter(cfg):
    base = blast.build_put_params(cfg, ">a\nACGT\n", "txid9606[ORGN]")
    keys = {blast.request_key(base)}
    for change in (
        {"QUERY": ">a\nACGA\n"},
        {"ENTREZ_QUERY": "txid562[ORGN]"},
        {"WORD_SIZE": "11"},
        {"DATABASE": "nt"},
    ):
        keys.add(blast.request_key({**base, **change}))
    assert len(keys) == 5
    assert blast.request_key(base) == blast.request_key(dict(reversed(base.items())))


def test_parse_put_and_status_responses():
    assert blast.parse_put_response(put_text("ABC123", 42)) == ("ABC123", 42)
    with pytest.raises(NcbiError, match="request ID"):
        blast.parse_put_response("<html>Error: something</html>")
    assert blast.parse_status_response(status_text("READY", "yes")) == ("READY", True)
    assert blast.parse_status_response(status_text("WAITING", "no")) == ("WAITING", False)
    assert blast.parse_status_response("nonsense") == ("UNKNOWN", None)
    assert blast.parse_status_response("Status=SOMETHING_NEW")[0] == "UNKNOWN"


def hit(**kw):
    return {"acc": "MN908947", "taxid": 2697049, "sciname": "SARS-CoV-2", "identity": 24, **kw}


def test_parse_maps_queries_by_title_and_reads_hit_details():
    text = blast_json(
        {"forward": [hit(merged=["OK000001"])], "reverse": [], "probe": [hit(identity=15)]}
    )
    parsed = parse_blast_json(text, LABELS)
    assert parsed.program == "blastn" and parsed.database == "core_nt"
    assert set(parsed.queries) == set(LABELS)
    h = parsed.queries["forward"].hits[0]
    assert len(h.descriptions) == 2 and h.descriptions[0].accession_version == "MN908947.1"
    assert h.descriptions[0].taxid == 2697049 and h.best_identity == 24
    assert h.hsps[0].hit_strand == "Plus" and h.hsps[0].qseq
    assert parsed.queries["reverse"].hits == []
    assert parsed.queries["probe"].hits[0].best_identity == 15


def test_parse_falls_back_to_query_number_when_titles_are_missing():
    text = blast_json({"a": [hit()], "b": [hit()], "c": [hit()]}, by_title=False)
    parsed = parse_blast_json(text, LABELS)
    assert parsed.queries["reverse"].query_id == "Query_2"


def test_parse_accepts_a_single_report_object():
    parsed = parse_blast_json(blast_json({"forward": [hit()]}, single_dict=True), ["forward"])
    assert len(parsed.queries["forward"].hits) == 1


def test_minus_strand_is_normalised():
    text = blast_json({"forward": [hit(strand="Minus")]})
    assert (
        parse_blast_json(text, ["forward"]).queries["forward"].hits[0].hsps[0].hit_strand == "Minus"
    )


@pytest.mark.parametrize(
    "text, message",
    [
        ("<html>Server error</html>", "not JSON"),
        ("{not json", "not valid JSON"),
        ('{"other": 1}', "BlastOutput2"),
        ('{"BlastOutput2": [{"nope": 1}]}', "report"),
    ],
)
def test_parse_fails_loudly_instead_of_guessing(text, message):
    with pytest.raises(ParseError, match=message):
        parse_blast_json(text, LABELS)


def test_parse_rejects_missing_hsp_fields():
    doc = json.loads(blast_json({"forward": [hit()]}))
    del doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["identity"]
    with pytest.raises(ParseError, match="identity"):
        parse_blast_json(json.dumps(doc), ["forward"])


def test_parse_reports_missing_queries_and_unmatched_labels():
    with pytest.raises(ParseError, match="no section for query"):
        parse_blast_json(blast_json({"forward": [hit()]}), ["forward", "reverse"])
    with pytest.raises(ParseError, match="Cannot match"):
        parse_blast_json(blast_json({"weird": [hit()]}, by_title=True), ["forward"])
