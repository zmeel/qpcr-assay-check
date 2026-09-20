import json
from pathlib import Path

from typer.testing import CliRunner

from qpcr_assay_check import __version__
from qpcr_assay_check.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "cdc_2019-nCoV_N1.yaml"
CONFIG_55 = ROOT / "examples" / "config_annealing_55C.yaml"


def test_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0 and __version__ in r.output


def test_validate_example_ok():
    r = runner.invoke(app, ["validate", str(EXAMPLE)])
    assert r.exit_code == 0, r.output
    assert "GACCCCAAAATCAGCGAAAT" in r.output


def test_validate_reports_all_problems_and_exits_64(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "assay_name: x\nforward: FAM-ACGU\nreverse: ACGTACGTACGTACGTAC\nprobe: ACGTACGTACGTACGTAC\n"
    )
    r = runner.invoke(app, ["validate", str(bad)])
    assert r.exit_code == 64
    assert "forward" in r.output and "target" in r.output


def test_run_qc_only_writes_record_and_exit_code_reflects_verdict(tmp_path):
    r = runner.invoke(
        app, ["run", str(EXAMPLE), "--qc-only", "-o", str(tmp_path), "--config", str(CONFIG_55)]
    )
    assert r.exit_code == 10, r.output  # WARN: primer Tm difference
    assert "Verdict: WARN" in r.output
    (result_json,) = tmp_path.rglob("results.json")
    data = json.loads(result_json.read_text())
    assert data["config"]["reaction"]["annealing_temp_C"] == 55.0
    assert (result_json.parent / "report.html").exists()
    assert (result_json.parent / "results.xlsx").exists()


def test_full_run_is_incomplete_in_this_version(tmp_path):
    r = runner.invoke(app, ["run", str(EXAMPLE), "-o", str(tmp_path)])
    assert r.exit_code == 30, r.output
    assert "INCOMPLETE" in r.output and "remote analyses are not yet available" in r.output


def test_run_from_command_line_arguments_only(tmp_path):
    r = runner.invoke(
        app,
        [
            "run", "--qc-only", "-o", str(tmp_path),
            "--name", "cli assay",
            "--forward", "GACCCCAAAATCAGCGAAAT",
            "--reverse", "TCTGGTTACTGCCAGTTGAATCTG",
            "--probe", "ACCCCGCATTACGTTTGGTGGACC",
            "--target-taxid", "2697049",
            "--probe-modification", "MGB",
        ],
    )  # fmt: skip
    assert r.exit_code in (10, 20), r.output
    (result_json,) = tmp_path.rglob("results.json")
    assert json.loads(result_json.read_text())["assay"]["probe_modifications"] == ["MGB"]


def test_cli_options_override_the_file(tmp_path):
    r = runner.invoke(
        app, ["run", str(EXAMPLE), "--qc-only", "-o", str(tmp_path), "--name", "renamed"]
    )
    assert r.exit_code in (10, 20)
    assert (tmp_path / "renamed").is_dir()


def test_run_without_input_is_a_usage_error():
    r = runner.invoke(app, ["run"])
    assert r.exit_code == 64
    assert "assay file" in r.output


def test_init_writes_files_and_refuses_to_overwrite(tmp_path):
    r = runner.invoke(app, ["init", str(tmp_path), "--example"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "config.yaml").exists()
    assert runner.invoke(app, ["validate", str(tmp_path / "assay.yaml")]).exit_code == 0
    again = runner.invoke(app, ["init", str(tmp_path)])
    assert again.exit_code == 1 and "already exists" in again.output


def test_blank_template_is_rejected_until_filled_in(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    r = runner.invoke(app, ["validate", str(tmp_path / "assay.yaml")])
    assert r.exit_code == 64
