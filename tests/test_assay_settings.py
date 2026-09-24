"""Assay-specific settings in the assay file (settings:), applied over the lab-wide config."""

from __future__ import annotations

from pathlib import Path

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


def test_a_key_in_the_wrong_section_says_where_it_belongs():
    """Live: an uncommented background_taxids line ended up under variants:."""
    assay = make_assay(settings={"variants": {"source": "datasets", "background_taxids": []}})
    with pytest.raises(ConfigError, match="'background_taxids' belongs under 'search:'"):
        load_config(None, assay.settings)


# ------------------------------------------------------------------ the full template
TEMPLATE = Path(__file__).parents[1] / "examples" / "assay_template.yaml"


def _filled(text: str) -> dict:
    """The template with its required fields filled (SYNTHETIC test values, not an assay)."""
    data = yaml.safe_load(text)
    data.update(assay_name="template test", forward="ACGTACGTACGTACGTAC",
                reverse="TTGCATTGCAAGCTTGCA", probe="CCATGGCATTACGGACTTGA",
                target={"taxid": 485})  # fmt: skip
    return data


def test_the_full_template_is_valid_as_shipped():
    from qpcr_assay_check.models import Assay

    assay = Assay.model_validate(_filled(TEMPLATE.read_text()))
    assert load_config(None, assay.settings) == load_config()  # nothing active: all defaults


def test_every_option_in_the_template_shows_its_true_default():
    """Uncommenting every option must reproduce the built-in defaults exactly (and be valid)."""
    import re

    from qpcr_assay_check.models import Assay

    text = re.sub(r"^(\s+)# ([A-Za-z_0-9]+:)", r"\1\2", TEMPLATE.read_text(), flags=re.M)
    assay = Assay.model_validate(_filled(text))
    assert assay.settings["variants"]["source"] == "datasets"  # options really were uncommented
    assert load_config(None, assay.settings) == load_config()


def test_the_template_lists_every_option_an_assay_may_set():
    import re

    from qpcr_assay_check.models import ASSAY_SETTING_SECTIONS

    text = re.sub(r"^(\s+)# ([A-Za-z_0-9]+:)", r"\1\2", TEMPLATE.read_text(), flags=re.M)
    shown = yaml.safe_load(text)["settings"]
    defaults = load_config().model_dump()
    leaf = {"pass_range", "warn_at", "min", "warn_above", "max_mismatches", "match"}

    def missing(have: dict, want: dict, path: str) -> list[str]:
        out = []
        for key, value in want.items():
            if key not in have:
                out.append(path + key)
            elif isinstance(value, dict) and not (leaf & set(value)):
                out += missing(have[key] or {}, value, f"{path}{key}.")
        return out

    gaps = [
        m for s in ASSAY_SETTING_SECTIONS for m in missing(shown[s] or {}, defaults[s], s + ".")
    ]
    assert gaps == []


def test_init_writes_the_same_full_template(tmp_path):
    r = CliRunner().invoke(app, ["init", str(tmp_path)])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "assay.yaml").read_text() == TEMPLATE.read_text()
