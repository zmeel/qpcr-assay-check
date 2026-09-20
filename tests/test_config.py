import pytest

from qpcr_assay_check.config import Band, deep_merge, load_config
from qpcr_assay_check.errors import ConfigError
from qpcr_assay_check.models import Status


def test_defaults_load_and_match_documented_values(cfg):
    assert cfg.reaction.na_mM == 50.0
    assert cfg.reaction.mg_mM == 3.0
    assert cfg.reaction.primer_nM == 400.0
    assert cfg.reaction.probe_nM == 200.0
    assert cfg.structure_fail_tm_c == cfg.reaction.annealing_temp_C


def test_user_file_overrides_only_given_keys(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "reaction:\n  annealing_temp_C: 55\nthresholds:\n  structures:\n    warn_tm_c: 40\n"
    )
    c = load_config(p)
    assert c.reaction.annealing_temp_C == 55
    assert c.reaction.mg_mM == 3.0  # untouched default
    assert c.thresholds.structures.warn_tm_c == 40
    assert c.structure_fail_tm_c == 55


def test_unknown_key_is_rejected_not_ignored(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "thresholds:\n  primer:\n    tm_cc: {pass_range: [58, 62], fail_range: [55, 65]}\n"
    )
    with pytest.raises(ConfigError, match="tm_cc"):
        load_config(p)


def test_inconsistent_band_is_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("thresholds:\n  primer:\n    tm_c: {pass_range: [58, 66], fail_range: [60, 70]}\n")
    with pytest.raises(ConfigError, match="fail_range must enclose"):
        load_config(p)


def test_band_grading():
    b = Band(pass_range=(58, 66), fail_range=(54, 70))
    assert b.grade(60) is Status.PASS
    assert b.grade(56) is Status.WARN
    assert b.grade(66.0) is Status.PASS
    assert b.grade(53.9) is Status.FAIL
    assert b.grade(70.1) is Status.FAIL


def test_deep_merge_does_not_mutate_inputs():
    base = {"a": {"b": 1, "c": 2}}
    merged = deep_merge(base, {"a": {"b": 9}})
    assert merged == {"a": {"b": 9, "c": 2}}
    assert base == {"a": {"b": 1, "c": 2}}


def test_missing_config_file_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="Cannot read"):
        load_config(tmp_path / "nope.yaml")
