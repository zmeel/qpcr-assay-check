"""Global configuration: reaction conditions, thresholds, and report settings.

The packaged ``data/default_config.yaml`` is the single source of defaults. A user file passed
with ``--config`` is deep-merged over it, then validated; unknown keys are rejected so that a
typo in a threshold name can never silently fall back to a default.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from .errors import ConfigError
from .models import Status


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _fmt(x: float) -> str:
    return f"{x:g}"


class Band(_Strict):
    """PASS inside ``pass_range``, FAIL outside ``fail_range``, WARN in between."""

    pass_range: tuple[float, float]
    fail_range: tuple[float, float]

    @model_validator(mode="after")
    def _nested(self) -> Band:
        p, f = self.pass_range, self.fail_range
        if not (p[0] <= p[1] and f[0] <= p[0] and p[1] <= f[1]):
            raise ValueError("fail_range must enclose pass_range, and each range must be ordered")
        return self

    def grade(self, value: float) -> Status:
        """Grade one value."""
        if self.pass_range[0] <= value <= self.pass_range[1]:
            return Status.PASS
        if self.fail_range[0] <= value <= self.fail_range[1]:
            return Status.WARN
        return Status.FAIL

    def describe(self, unit: str = "") -> str:
        """Human-readable rule."""
        u = f" {unit}" if unit else ""
        p, f = self.pass_range, self.fail_range
        return f"PASS {_fmt(p[0])}–{_fmt(p[1])}{u}; FAIL outside {_fmt(f[0])}–{_fmt(f[1])}{u}"


class RunLimit(_Strict):
    """WARN at ``warn_at`` and FAIL at ``fail_at`` or more (e.g. homopolymer run length)."""

    warn_at: int
    fail_at: int

    @model_validator(mode="after")
    def _ordered(self) -> RunLimit:
        if self.fail_at < self.warn_at:
            raise ValueError("fail_at must be >= warn_at")
        return self

    def grade(self, value: float) -> Status:
        """Grade one value."""
        if value >= self.fail_at:
            return Status.FAIL
        if value >= self.warn_at:
            return Status.WARN
        return Status.PASS

    def describe(self, unit: str = "") -> str:
        """Human-readable rule."""
        u = f" {unit}" if unit else ""
        return f"WARN at {self.warn_at}{u} or more; FAIL at {self.fail_at}{u} or more"


class UpperLimit(_Strict):
    """WARN above ``warn_above`` and FAIL above ``fail_above``."""

    warn_above: float
    fail_above: float

    @model_validator(mode="after")
    def _ordered(self) -> UpperLimit:
        if self.fail_above < self.warn_above:
            raise ValueError("fail_above must be >= warn_above")
        return self

    def grade(self, value: float) -> Status:
        """Grade one value."""
        if value > self.fail_above:
            return Status.FAIL
        if value > self.warn_above:
            return Status.WARN
        return Status.PASS

    def describe(self, unit: str = "") -> str:
        """Human-readable rule."""
        u = f" {unit}" if unit else ""
        return f"WARN above {_fmt(self.warn_above)}{u}; FAIL above {_fmt(self.fail_above)}{u}"


class CountRange(_Strict):
    """PASS when a count lies within [min, max] (inclusive); otherwise WARN."""

    min: int
    max: int

    @model_validator(mode="after")
    def _ordered(self) -> CountRange:
        if self.max < self.min:
            raise ValueError("max must be >= min")
        return self

    def grade(self, value: float) -> Status:
        """Grade one value."""
        return Status.PASS if self.min <= value <= self.max else Status.WARN

    def describe(self, unit: str = "") -> str:
        """Human-readable rule."""
        u = f" {unit}" if unit else ""
        return f"PASS {self.min}–{self.max}{u}; otherwise WARN"


class ReactionConditions(_Strict):
    """Reaction conditions used in all thermodynamic calculations."""

    na_mM: float
    mg_mM: float
    dntp_mM: float
    primer_nM: float
    probe_nM: float
    annealing_temp_C: float
    tm_method: Literal["santalucia", "breslauer"]
    salt_correction: Literal["santalucia", "owczarzy", "schildkraut"]

    @model_validator(mode="after")
    def _positive(self) -> ReactionConditions:
        for name in ("na_mM", "mg_mM", "dntp_mM", "primer_nM", "probe_nM"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must not be negative")
        if self.primer_nM <= 0 or self.probe_nM <= 0:
            raise ValueError("primer_nM and probe_nM must be greater than zero")
        return self


class OligoSettings(_Strict):
    """Handling of degenerate oligos."""

    max_degenerate_expansions: int
    max_pair_combinations: int


class PrimerThresholds(_Strict):
    """Thresholds applied to each primer."""

    length_nt: Band
    gc_percent: Band
    tm_c: Band
    gc_in_last5: CountRange
    max_run: RunLimit
    max_g_run: RunLimit


class ProbeThresholds(_Strict):
    """Thresholds applied to the probe."""

    length_nt: Band
    gc_percent: Band
    tm_minus_mean_primer_c: Band
    max_run: RunLimit
    max_g_run: RunLimit
    warn_if_more_g_than_c: bool
    g_sensitive_reporters: list[str]


class PairThresholds(_Strict):
    """Thresholds comparing the two primers."""

    primer_tm_diff_c: UpperLimit


class StructureThresholds(_Strict):
    """Melting temperature limits for hairpins and dimers."""

    warn_tm_c: float
    fail_tm_c: float | None


class AmpliconThresholds(_Strict):
    """Thresholds for the amplicon (needs a reference amplicon in v0.1.0)."""

    length_bp: Band
    gc_percent: Band
    allow_probe_primer_overlap: bool
    max_site_mismatches: int


class Thresholds(_Strict):
    """All QC thresholds."""

    primer: PrimerThresholds
    probe: ProbeThresholds
    pair: PairThresholds
    structures: StructureThresholds
    amplicon: AmpliconThresholds


class NcbiSettings(_Strict):
    """Network behaviour towards NCBI. Credentials come from the environment, never from here."""

    tool: str
    blast_url: str
    eutils_url: str
    request_timeout_s: float
    max_retries: int
    backoff_base_s: float
    blast_min_interval_s: float
    poll_interval_s: float
    max_wait_minutes: float
    rid_lifetime_hours: float
    blast_cache_ttl_days: float
    taxonomy_cache_ttl_days: float
    cache_dir: str | None

    @model_validator(mode="after")
    def _etiquette(self) -> NcbiSettings:
        if self.blast_min_interval_s < 10:
            raise ValueError("blast_min_interval_s must be at least 10 (NCBI usage guideline)")
        if self.poll_interval_s < 60:
            raise ValueError("poll_interval_s must be at least 60 (NCBI usage guideline)")
        if self.max_retries < 0 or self.backoff_base_s <= 0:
            raise ValueError("max_retries must be >= 0 and backoff_base_s > 0")
        return self


class RelevanceSettings(_Strict):
    """When is a hit relevant enough that missing it would matter?"""

    min_identical_bases: int


class SearchSettings(_Strict):
    """BLAST parameters and search planning."""

    program: Literal["blastn"]
    database: str
    word_size: Literal[7, 11, 15]
    expect: float
    filter: str
    reward: int
    penalty: int
    gap_open: int
    gap_extend: int
    hitlist_size: int
    result_format: Literal["JSON2_S", "JSON2", "XML2_S", "XML2"]
    max_taxids_per_search: int
    max_searches_warn: int
    background_taxids: list[int]
    relevance: RelevanceSettings

    @model_validator(mode="after")
    def _sane(self) -> SearchSettings:
        if self.hitlist_size < 1 or self.max_taxids_per_search < 1:
            raise ValueError("hitlist_size and max_taxids_per_search must be >= 1")
        if self.reward <= 0 or self.penalty >= 0:
            raise ValueError("reward must be positive and penalty negative")
        if any(t <= 0 for t in self.background_taxids):
            raise ValueError("background_taxids must be positive integers")
        return self


class AlignScores(_Strict):
    """Scores for re-alignment (a gap of length k costs gap_open + k * gap_extend)."""

    match: int
    mismatch: int
    gap_open: int
    gap_extend: int

    @model_validator(mode="after")
    def _signs(self) -> AlignScores:
        if self.match <= 0 or self.mismatch >= 0 or self.gap_open < 0 or self.gap_extend <= 0:
            raise ValueError("match > 0, mismatch < 0, gap_open >= 0 and gap_extend > 0 required")
        return self


class SiteCriteria(_Strict):
    """Limits a binding site must respect to reach a level."""

    max_mismatches: int
    max_gaps: int
    min_clean_3prime_nt: int


class SiteRules(_Strict):
    """Critical and warning limits for one kind of oligo."""

    critical: SiteCriteria
    warning: SiteCriteria

    @model_validator(mode="after")
    def _warning_is_looser(self) -> SiteRules:
        c, w = self.critical, self.warning
        if (
            w.max_mismatches < c.max_mismatches
            or w.max_gaps < c.max_gaps
            or w.min_clean_3prime_nt > c.min_clean_3prime_nt
        ):
            raise ValueError("warning limits must be at least as permissive as critical limits")
        return self


Severity = Literal["FAIL", "WARN", "INFO"]


class SeverityMap(_Strict):
    """How each finding contributes to the specificity verdict."""

    primer_site_critical: Severity
    primer_site_warning: Severity
    probe_site_critical: Severity
    amplicon_likely_detected: Severity
    amplicon_not_detected: Severity


class SpecificitySettings(_Strict):
    """Assessment of BLAST hits."""

    off_target_tiers: list[str]
    max_sites_per_query: int
    window_padding_nt: int
    max_amplicon_size: int
    max_amplicons: int
    report_top_sites: int
    alignment: AlignScores
    primer_site: SiteRules
    probe_site: SiteRules
    probe_binds_if: Literal["critical", "warning"]
    severity: SeverityMap
    eukaryote_taxids: list[int]

    @model_validator(mode="after")
    def _positive(self) -> SpecificitySettings:
        if min(self.max_sites_per_query, self.max_amplicon_size, self.max_amplicons) < 1:
            raise ValueError(
                "max_sites_per_query, max_amplicon_size and max_amplicons must be >= 1"
            )
        if self.window_padding_nt < 0:
            raise ValueError("window_padding_nt must be >= 0")
        return self


class OrganismsSettings(_Strict):
    """The clinical organism list used for the exclusivity tier (data/clinical_organisms.yaml)."""

    list_file: str | None
    resolve_synonyms: bool


class InclusivitySettings(_Strict):
    """Time-windowed inclusivity: how well the oligos still match the intended target, over time.

    Built from the same "target" tier search every run already makes (taxon-restricted only, no
    date filter -- combining ENTREZ_QUERY taxon restriction with a [PDAT] date filter in one BLAST
    call was checked live and found unreliable, see docs/ARCHITECTURE.md), bucketed into years
    afterwards using each hit's own submission date (ESummary).
    """

    lookback_years: int
    sample_per_window: int
    warn_below_percent: float
    fail_below_percent: float

    @model_validator(mode="after")
    def _sane(self) -> InclusivitySettings:
        if self.lookback_years < 1 or self.sample_per_window < 1:
            raise ValueError("lookback_years and sample_per_window must be >= 1")
        if not (0 <= self.fail_below_percent <= self.warn_below_percent <= 100):
            raise ValueError("require 0 <= fail_below_percent <= warn_below_percent <= 100")
        return self


class ReportSettings(_Strict):
    """Report rendering options."""

    include_charts: bool


class Config(_Strict):
    """Effective configuration for one run."""

    schema_version: Literal[1]
    reaction: ReactionConditions
    oligo: OligoSettings
    thresholds: Thresholds
    ncbi: NcbiSettings
    search: SearchSettings
    specificity: SpecificitySettings
    organisms: OrganismsSettings
    inclusivity: InclusivitySettings
    report: ReportSettings

    @property
    def structure_fail_tm_c(self) -> float:
        """Tm at or above which a hairpin/dimer is a FAIL (annealing temperature by default)."""
        fail = self.thresholds.structures.fail_tm_c
        return self.reaction.annealing_temp_C if fail is None else fail


def default_config_text() -> str:
    """The packaged default configuration as text (used by ``init``)."""
    return (resources.files("qpcr_assay_check") / "data" / "default_config.yaml").read_text(
        encoding="utf-8"
    )


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base`` (override wins)."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def format_validation_error(exc: ValidationError) -> str:
    """Turn a pydantic error into one readable line per problem."""
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(root)"
        msg = str(err["msg"]).removeprefix("Value error, ")
        lines.append(f"  {loc}: {msg}")
    return "\n".join(lines)


def load_config(path: Path | None = None) -> Config:
    """Load the defaults, merge an optional user file over them, and validate."""
    data: dict[str, Any] = yaml.safe_load(default_config_text())
    if path is not None:
        try:
            user = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"Cannot read configuration file {path}: {exc}") from exc
        if not isinstance(user, dict):
            raise ConfigError(f"Configuration file {path} must contain a YAML mapping")
        data = deep_merge(data, user)
    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        where = f" in {path}" if path else ""
        raise ConfigError(f"Invalid configuration{where}:\n{format_validation_error(exc)}") from exc
