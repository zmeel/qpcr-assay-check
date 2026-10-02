"""scripts/export_amplicons.py: distinct amplicons with their outcomes, store left untouched."""

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

from .test_variants_exhaustive import AMP, run, setup

SCRIPT = Path(__file__).parents[1] / "scripts" / "export_amplicons.py"


def _module():
    spec = importlib.util.spec_from_file_location("export_amplicons", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_amplicons_are_grouped_with_outcomes_and_the_store_is_untouched(tmp_path, monkeypatch):
    cfg, fake, client, assay = setup(tmp_path)
    run(tmp_path, cfg, client, assay)
    (store,) = (tmp_path / "cache" / "genomes").glob("*.jsonl")
    before, files = store.read_bytes(), sorted(p.name for p in store.parent.iterdir())
    ex = _module()
    monkeypatch.setattr(ex, "build_assay", lambda path, overrides: assay)
    monkeypatch.setattr(ex, "load_config", lambda path, settings: cfg)
    monkeypatch.setattr(sys, "argv", ["export_amplicons.py", "assay.yaml", str(store)])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        ex.main()
    d = json.loads(out.getvalue())
    assert (d["genomes_in_store"], d["found"], d["cut"]) == (5, 4, 1)
    assert d["judged_on_a_whole_copy"] == 3 and d["distinct_amplicons"] == 2
    ref, variant = d["amplicons"]
    # GCF_1 and GCF_2 (the reverse strand, read in the fragment's sense) carry the reference
    assert ref["seq"] == AMP and ref["n"] == 2 and ref["outcomes"] == {"detected": 2}
    assert variant["outcomes"] == {"not detected": 1} and variant["example"] == "GCA_000000003.1"
    assert store.read_bytes() == before  # read-only: nothing appended, nothing set aside
    assert sorted(p.name for p in store.parent.iterdir()) == files
