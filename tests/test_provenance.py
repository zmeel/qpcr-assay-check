"""Which code made a record (whole-project review 2026-11-17, P1)."""

from __future__ import annotations

import shutil

from qpcr_assay_check import provenance


def _fresh(monkeypatch, package_dir=None):
    if package_dir is not None:
        monkeypatch.setattr(provenance, "PACKAGE_DIR", package_dir)
    provenance.code_fingerprint.cache_clear()
    provenance.git_revision.cache_clear()


def test_the_fingerprint_changes_with_any_file_of_the_package(tmp_path, monkeypatch):
    copy = tmp_path / "pkg"
    shutil.copytree(provenance.PACKAGE_DIR, copy,
                    ignore=shutil.ignore_patterns("__pycache__"))  # fmt: skip
    _fresh(monkeypatch, copy)
    first = provenance.code_fingerprint()
    _fresh(monkeypatch)
    assert provenance.code_fingerprint() == first  # same files, same fingerprint
    (copy / "__pycache__").mkdir(exist_ok=True)
    (copy / "__pycache__" / "x.pyc").write_bytes(b"compiled")  # caches do not count
    _fresh(monkeypatch)
    assert provenance.code_fingerprint() == first
    limits = copy / "data" / "default_config.yaml"
    limits.write_text(limits.read_text() + "\n# changed\n")  # a rule limit is part of the code
    _fresh(monkeypatch)
    assert provenance.code_fingerprint() != first


def test_the_commit_comes_from_the_environment_when_given(monkeypatch):
    monkeypatch.setenv("QAC_GIT_COMMIT", "abc123")
    monkeypatch.setenv("QAC_GIT_DIRTY", "yes")
    _fresh(monkeypatch)
    info = provenance.tool_info()
    assert (info["git_commit"], info["git_dirty"]) == ("abc123", "yes")
    assert len(info["code_fingerprint"]) == 64 and info["version"]
    monkeypatch.delenv("QAC_GIT_COMMIT")
    monkeypatch.delenv("QAC_GIT_DIRTY")
    _fresh(monkeypatch)


def test_no_git_reads_as_unknown(tmp_path, monkeypatch):
    monkeypatch.delenv("QAC_GIT_COMMIT", raising=False)
    _fresh(monkeypatch, tmp_path)  # not a checkout
    assert provenance.git_revision() == ("unknown", "unknown")


def teardown_function():
    provenance.code_fingerprint.cache_clear()
    provenance.git_revision.cache_clear()


def test_the_record_and_its_report_name_the_code(tmp_path):
    from qpcr_assay_check.config import load_config
    from qpcr_assay_check.pipeline import evaluate, write_outputs
    from qpcr_assay_check.report.html import render_report

    from .conftest import make_assay

    cfg = load_config()
    result = evaluate(make_assay(), cfg, qc_only=True)
    fp = provenance.code_fingerprint()
    assert result.tool["code_fingerprint"] == fp
    assert {"git_commit", "git_dirty"} <= set(result.tool)
    html = render_report(result, cfg)
    assert "code <code" in html and fp[:12] in html
    write_outputs(result, tmp_path, cfg)  # the workbook writes the same fields


def test_an_old_record_without_a_fingerprint_still_renders():
    from qpcr_assay_check.config import load_config
    from qpcr_assay_check.pipeline import evaluate
    from qpcr_assay_check.report.html import render_report

    from .conftest import make_assay

    cfg = load_config()
    result = evaluate(make_assay(), cfg, qc_only=True)
    old = result.model_copy(update={"tool": {"name": "qpcr-assay-check", "version": "2.1.0"}})
    assert "code fingerprint not recorded" in render_report(old, cfg)
