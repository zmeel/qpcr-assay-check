"""Runs scripts/smoke_test.py end to end against a fake NCBI.

A bug in the smoke script would cost a live round trip, so it is tested like any other code.
"""

import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import pytest

from qpcr_assay_check.oligo import iupac

from .fake_ncbi import FakeNcbi, FakeResponse, blast_json

ROOT = Path(__file__).resolve().parent.parent
F, R, P = "GACCCCAAAATCAGCGAAAT", "TCTGGTTACTGCCAGTTGAATCTG", "ACCCCGCATTACGTTTGGTGGACC"
# A CONSTRUCTED "genome": filler + the published oligos. Not real SARS-CoV-2 sequence.
GENOME = "T" * 100 + F + "GC" + P + "AA" + iupac.reverse_complement(R) + "T" * 100


class SmokeFake(FakeNcbi):
    def request(self, method, url, params=None, data=None, timeout=None):
        if "esearch.fcgi" in url:
            self.calls.append(
                {"method": method, "url": url, "payload": dict(params or {}), "t": None}
            )
            return FakeResponse(200, self._esearch(params))
        if "efetch.fcgi" in url:
            self.calls.append(
                {"method": method, "url": url, "payload": dict(params or {}), "t": None}
            )
            return FakeResponse(200, self._efetch(params))
        return super().request(method, url, params, data, timeout)

    def _esearch(self, p):
        term, db = p["term"], p["db"]
        if db == "taxonomy":
            ids = [str(1000 + len(term))] * (2 if term.startswith("Escherichia") else 1)
            if "species[Rank]" in term:
                ids = [str(5000 + i) for i in range(100)]
            body = "".join(f"<Id>{i}</Id>" for i in ids)
            return (
                f"<eSearchResult><Count>{len(ids)}</Count><IdList>{body}</IdList></eSearchResult>"
            )
        if "[ACCN]" in term:
            return f"<eSearchResult><Count>{term.count('[ACCN]')}</Count></eSearchResult>"
        if int(p.get("retstart", 0)) >= 100000:
            return "<eSearchResult><ERROR>Search Backend failed</ERROR></eSearchResult>"
        return "<eSearchResult><Count>4321</Count><IdList><Id>1</Id></IdList></eSearchResult>"

    def _efetch(self, p):
        if p["db"] == "taxonomy":
            name = "Severe acute respiratory syndrome coronavirus 2"
            return (
                f"<TaxaSet><Taxon><TaxId>2697049</TaxId><ScientificName>{name}</ScientificName>"
                "</Taxon></TaxaSet>"
            )
        seq = GENOME
        if "seq_start" in p:
            seq = seq[int(p["seq_start"]) - 1 : int(p["seq_stop"])]
            if int(p.get("strand", 1)) == 2:
                seq = iupac.reverse_complement(seq)
        return f">{p['id']} constructed\n{seq}\n"


def result_for(payload):
    labels = [ln[1:] for ln in payload["QUERY"].splitlines() if ln.startswith(">")]
    seqs = dict(zip(labels, payload["QUERY"].splitlines()[1::2], strict=True))
    taxids = [
        int(t) for t in re.findall(r"txid(\d+)\[ORGN\]", payload.get("ENTREZ_QUERY", ""))
    ] or [0]
    spec = {
        label: [
            {
                "acc": f"AB{100000 + i}",
                "taxid": taxids[i % len(taxids)],
                "sciname": "Organism",
                "identity": len(seq),
            }
            for i in range(3)
        ]
        for label, seq in seqs.items()
    }
    return blast_json(spec)


def load_script():
    spec = importlib.util.spec_from_file_location(
        "smoke_test_script", ROOT / "scripts" / "smoke_test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("quick", [True, False])
def test_smoke_script_runs_end_to_end_and_writes_a_clean_report(tmp_path, monkeypatch, quick):
    fake = SmokeFake(result_for)
    monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setenv("NCBI_EMAIL", "secret.person@example.org")
    monkeypatch.setenv("NCBI_API_KEY", "SUPERSECRETKEY123")
    out = tmp_path / "smoke_out"
    argv = ["smoke_test.py", "--out", str(out), *(["--quick"] if quick else [])]
    monkeypatch.setattr(sys, "argv", argv)
    script = load_script()
    fake.clock = None

    assert script.main() == 0
    text = (out / "smoke_report.json").read_text()
    report = json.loads(text)
    assert "SUPERSECRETKEY123" not in text and "secret.person@example.org" not in text
    assert all(s["ok"] for s in report["steps"].values()), {
        k: v.get("error") for k, v in report["steps"].items() if not v["ok"]
    }
    f = report["findings"]
    assert f["blast_parameters_accepted_and_report_parsed"] is True
    assert f["cdc_n1_oligos_match_reference_exactly"] is True
    assert f["positive_control_full_length_hits"] == {
        "forward": True,
        "reverse": True,
        "probe": True,
    }
    assert f["entrez_query_restriction_honoured_for_human"] is True
    assert f["esearch_retstart_10000_works"] is True and f["esearch_retstart_100000_works"] is False
    ref = report["steps"]["04_reference_check_against_NC_045512.2"]
    assert ref["amplicon_length"] == 72 and ref["efetch_strand2_is_reverse_complement"] is True
    step6 = report["steps"]["06_blast_negative_control_human_and_formats"]
    assert set(step6["report_format_probes"]) == {"JSON2", "XML2_S", "XML2", "XML", "Text"}
    assert (out / "raw" / "t1_sars2.txt.gz").exists() and (
        out / "raw" / "t2_human.head.txt"
    ).exists()
    if quick:
        assert "07_blast_multi_taxa_lists" not in report["steps"]
        assert fake.n_put == 2
    else:
        assert f["multi_taxa_entrez_query_accepted"]
        assert f["blast_date_window_restriction_honoured"] is True
        assert fake.n_put == 6


def test_smoke_script_without_email_exits_2_and_sends_nothing(tmp_path, monkeypatch):
    fake = SmokeFake(result_for)
    monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    monkeypatch.setattr(sys, "argv", ["smoke_test.py", "--out", str(tmp_path / "o")])
    assert load_script().main() == 2
    assert fake.calls == []


def test_smoke_script_reports_failures_instead_of_crashing(tmp_path, monkeypatch):
    class Broken(SmokeFake):
        def _efetch(self, p):
            return "<html>not fasta</html>"

    fake = Broken(result_for)
    monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setenv("NCBI_EMAIL", "a@example.org")
    out = tmp_path / "o"
    monkeypatch.setattr(sys, "argv", ["smoke_test.py", "--out", str(out), "--quick"])
    assert load_script().main() == 1  # some steps failed, but a report was still written
    report = json.loads((out / "smoke_report.json").read_text())
    assert not report["steps"]["04_reference_check_against_NC_045512.2"]["ok"]
    assert report["steps"]["05_blast_positive_control_sars2"]["ok"]  # later steps still ran
