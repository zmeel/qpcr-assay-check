"""Loading the clinical organism list."""

from __future__ import annotations

import pytest

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import ConfigError
from qpcr_assay_check.taxonomy.organisms import load_organism_list, organism_list_source

from .conftest import make_assay


def test_the_packaged_starter_list_loads_and_covers_the_spec_categories():
    ol = load_organism_list(load_config())
    names = {c.name for c in ol.categories}
    assert "Background" in names
    assert "Homo sapiens" in ol.names
    assert len(ol.names) == len(set(ol.names))  # already deduplicated


def test_a_custom_list_file_overrides_the_packaged_one(tmp_path):
    custom = tmp_path / "mine.yaml"
    custom.write_text(
        "categories:\n  - name: Test\n    organisms: [Chlamydia trachomatis, Homo sapiens]\n"
    )
    cfg = load_config()
    cfg.organisms.list_file = str(custom)
    ol = load_organism_list(cfg)
    assert ol.names == ["Chlamydia trachomatis", "Homo sapiens"]


def test_duplicate_names_across_categories_are_deduplicated_keeping_first_order(tmp_path):
    custom = tmp_path / "dup.yaml"
    custom.write_text(
        "categories:\n"
        "  - name: A\n    organisms: [Chlamydia trachomatis]\n"
        "  - name: B\n    organisms: [Chlamydia trachomatis, Homo sapiens]\n"
    )
    cfg = load_config()
    cfg.organisms.list_file = str(custom)
    ol = load_organism_list(cfg)
    assert ol.names == ["Chlamydia trachomatis", "Homo sapiens"]


def test_a_missing_list_file_is_a_clear_config_error(tmp_path):
    cfg = load_config()
    cfg.organisms.list_file = str(tmp_path / "does-not-exist.yaml")
    with pytest.raises(ConfigError, match="Cannot read organism list file"):
        load_organism_list(cfg)


def test_an_empty_category_is_rejected(tmp_path):
    custom = tmp_path / "empty.yaml"
    custom.write_text("categories:\n  - name: Empty\n    organisms: []\n")
    cfg = load_config()
    cfg.organisms.list_file = str(custom)
    with pytest.raises(ConfigError, match="Invalid organism list"):
        load_organism_list(cfg)


def test_unknown_keys_are_rejected(tmp_path):
    custom = tmp_path / "typo.yaml"
    custom.write_text("categories:\n  - name: A\n    organism: [Homo sapiens]\n")  # typo'd key
    cfg = load_config()
    cfg.organisms.list_file = str(custom)
    with pytest.raises(ConfigError, match="Invalid organism list"):
        load_organism_list(cfg)


# ---------------------------------------------------- per-assay exclusivity list (organisms.source)


def test_source_defaults_to_the_assay_s_own_list_when_it_has_one():
    cfg = load_config()
    assert cfg.organisms.source == "assay"
    assay = make_assay(exclusivity_organisms=["Chlamydia trachomatis", "Neisseria gonorrhoeae"])
    assert organism_list_source(cfg, assay) == "assay"
    ol = load_organism_list(cfg, assay)
    assert ol.names == ["Chlamydia trachomatis", "Neisseria gonorrhoeae"]
    assert [c.name for c in ol.categories] == ["Assay-specific exclusivity list"]


def test_an_assay_with_no_list_of_its_own_falls_back_to_the_global_list():
    cfg = load_config()  # organisms.source: assay (default)
    assay = make_assay()  # exclusivity_organisms defaults to []
    assert organism_list_source(cfg, assay) == "global"
    assert load_organism_list(cfg, assay).names == load_organism_list(cfg).names


def test_no_assay_at_all_falls_back_to_the_global_list():
    cfg = load_config()
    assert organism_list_source(cfg, None) == "global"
    assert load_organism_list(cfg, None).names == load_organism_list(cfg).names


def test_source_global_ignores_the_assay_s_own_list_even_when_it_has_one():
    cfg = load_config()
    cfg.organisms.source = "global"
    assay = make_assay(exclusivity_organisms=["Chlamydia trachomatis"])
    assert organism_list_source(cfg, assay) == "global"
    assert load_organism_list(cfg, assay).names == load_organism_list(cfg).names
