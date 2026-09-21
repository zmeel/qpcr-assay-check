"""Loading the clinical organism list."""

from __future__ import annotations

import pytest

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import ConfigError
from qpcr_assay_check.taxonomy.organisms import load_organism_list


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
