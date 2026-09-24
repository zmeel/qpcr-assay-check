"""Assay-specific settings in the assay file (settings:), applied over the lab-wide config."""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from qpcr_assay_check.cli import app
from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import ConfigError
from qpcr_assay_check.pipeline import evaluate, inputs_hash
from qpcr_assay_check.report.html import render_report

from .conftest import make_assay


def test_assay_settings_override_the_defaults_and_the_config_file(tmp_path):
    lab = tmp_path / "lab.yaml"
    lab.write_text("reaction: {annealing_temp_C: 58}\nsearch: {background_taxids: [9606, 10090]}\n")
    assay = make_assay(settings={"search": {"background_taxids": []},
                                 "variants": {"source": "blast_partitioned"}})  # fmt: skip
    cfg = load_config(lab, assay.settings)
    assert cfg.reaction.annealing_temp_C == 58  # from the lab file, untouched by the assay
    assert cfg.search.background_taxids == []  # the assay wins
    assert cfg.variants.source == "blast_partitioned"
    assert load_config(lab).search.background_taxids == [9606, 10090]


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"ncbi": {"cache_dir": "/x"}}, "lab-wide"),
        ({"report": {"include_charts": False}}, "lab-wide"),
        ({"variant": {"source": "datasets"}}, "not a configuration section"),
        ({"search": "none"}, "must be a mapping"),
    ],
)
def test_misplaced_settings_are_rejected_in_the_assay_file(settings, message):
    with pytest.raises(ValidationError, match=message):
        make_assay(settings=settings)


def test_an_unknown_or_invalid_key_names_the_assay_settings():
    assay = make_assay(settings={"variants": {"sourse": "datasets"}})
    with pytest.raises(ConfigError, match="the assay file's settings") as err:
        load_config(None, assay.settings)
    assert "sourse" in str(err.value)


def test_the_report_shows_the_assay_s_own_settings():
    assay = make_assay(settings={"search": {"background_taxids": []}})
    cfg = load_config(None, assay.settings)
    html = render_report(evaluate(assay, cfg, qc_only=True), cfg)
    assert "Settings from the assay file" in html and "background_taxids: []" in html


def test_a_run_budget_in_the_assay_does_not_count_as_a_change():
    a = make_assay(settings={"variants": {"max_assemblies_per_run": 100}})
    b = make_assay(settings={"variants": {"max_assemblies_per_run": 5000}})
    assert inputs_hash(a, load_config(None, a.settings)) == inputs_hash(
        b, load_config(None, b.settings)
    )
    c = make_assay(settings={"variants": {"source": "blast_partitioned"}})
    assert inputs_hash(c, load_config(None, c.settings)) != inputs_hash(
        a, load_config(None, a.settings)
    )


def test_validate_uses_the_assay_file_s_settings(tmp_path):
    data = yaml.safe_load(make_assay().model_dump_json(exclude={"reference_amplicons"}))
    data["settings"] = {"reaction": {"annealing_temp_C": 62}}
    path = tmp_path / "assay.yaml"
    path.write_text(yaml.safe_dump(data))
    r = CliRunner().invoke(app, ["validate", str(path)])
    assert r.exit_code == 0, r.output
    assert "annealing 62 °C" in r.output and "settings from the assay file: reaction" in r.output
