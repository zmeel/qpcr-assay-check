"""The summary table at the top of the report (user decision 2026-09-27; code review): its rows
must always show the overall review status, and the comparison must survive older records."""

from datetime import UTC, datetime

from qpcr_assay_check.config import load_config
from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.summary import summary_rows
from qpcr_assay_check.specificity.models import Finding
from qpcr_assay_check.verdict import Verdict

from .conftest import make_assay
from .test_report_exclusivity import _specificity_with_exclusivity

NOW = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)
_RANK = {Verdict.PASS: 0, Verdict.WARN: 1, Verdict.INCOMPLETE: 2, Verdict.FAIL: 3}


def _worst_row(rows) -> Verdict:
    levels = [Verdict(r.css) for r in rows if r.css in Verdict.__members__]
    return max(levels, key=_RANK.__getitem__)


def _untiered_spec():
    """Only a finding that belongs to no search tier: a window that could not be fetched."""
    return _specificity_with_exclusivity().model_copy(
        update={
            "verdict": Verdict.INCOMPLETE,
            "verdict_sites": Verdict.INCOMPLETE,
            "verdict_amplicons": Verdict.PASS,
            "sites": [],
            "amplicons": [],
            "findings": [
                Finding(
                    severity="INCOMPLETE",
                    message="3 sequence window(s) could not be fetched; those hits were not "
                    "assessed.",
                )
            ],
        }
    )


def test_the_rows_always_show_the_overall_status():
    cfg = load_config()
    cfg.specificity.off_target_tiers = []  # no tier row to carry the finding
    assay = make_assay()
    for kwargs in ({"qc_only": True}, {"specificity": _untiered_spec()}):
        result = evaluate(assay, cfg, now=NOW, **kwargs)
        rows = summary_rows(result, cfg, [])
        assert _worst_row(rows) is result.overall.verdict, kwargs
    rows = summary_rows(evaluate(assay, cfg, now=NOW, specificity=_untiered_spec()), cfg, [])
    search = [r for r in rows if r.check == "Off-target search"]
    assert len(search) == 1 and "could not be fetched" in search[0].result
    # the organism list was not searched: its own row says so
    (excl,) = [r for r in rows if r.check.startswith("Exclusivity")]
    assert excl.css == "INCOMPLETE" and "not searched" in excl.result
