"""Input data model: the assay definition, plus the shared PASS/WARN/FAIL status type."""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .oligo import iupac

MIN_OLIGO_LENGTH = 10
MAX_OLIGO_LENGTH = 60  # primer3's thermodynamic alignment supports sequences up to 60 nt
MIN_AMPLICON_LENGTH = 30

# RefSeq (NC_045512.2, NZ_CP012345.1) and INSDC (MN908947.3) accession formats.
_ACCESSION_RE = re.compile(r"^(?:[A-Z]{2}_)?[A-Z]{0,6}\d{5,9}(?:\.\d+)?$")


class Status(StrEnum):
    """Result of a single check. INFO carries a value but never affects a verdict."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INFO = "INFO"

    @property
    def rank(self) -> int:
        """Severity ordering used to combine statuses."""
        return {"INFO": 0, "PASS": 1, "WARN": 2, "FAIL": 3}[self.value]


def worst(statuses: Iterable[Status]) -> Status:
    """Most severe status; INFO if there are no statuses (nothing was scored)."""
    return max(statuses, key=lambda s: s.rank, default=Status.INFO)


class TemplateType(StrEnum):
    """Nucleic acid the assay detects; RNA implies a reverse-transcription step."""

    DNA = "DNA"
    RNA = "RNA"


class Target(BaseModel):
    """Intended target of the assay. At least a taxonomy ID or a reference accession is needed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    taxid: int | None = Field(default=None, gt=0, description="NCBI Taxonomy ID")
    accession: str | None = Field(default=None, description="Reference accession, e.g. NC_045512.2")
    gene: str | None = None
    exclude_taxids: list[int] = Field(
        default_factory=list,
        description="taxa inside the target taxon that the assay must NOT detect (e.g. the "
        "rhinovirus species inside the genus Enterovirus): left out of the target search, "
        "inclusivity and the variant analysis, and searched as near neighbours (off-target)",
    )

    @field_validator("accession")
    @classmethod
    def _check_accession(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if not _ACCESSION_RE.match(v):
            raise ValueError(
                f"'{v}' does not look like an NCBI accession (expected e.g. NC_045512.2 or "
                "MN908947.3)"
            )
        return v

    @model_validator(mode="after")
    def _need_taxid_or_accession(self) -> Target:
        if self.taxid is None and self.accession is None:
            raise ValueError("give at least one of 'taxid' or 'accession'")
        if self.exclude_taxids:
            if self.taxid is None:
                raise ValueError("'exclude_taxids' needs the target's 'taxid'")
            if any(t <= 0 for t in self.exclude_taxids):
                raise ValueError("'exclude_taxids' must be positive taxonomy IDs")
            if self.taxid in self.exclude_taxids:
                raise ValueError("'exclude_taxids' must not contain the target's own taxid")
            self.exclude_taxids = sorted(set(self.exclude_taxids))
        return self


def _clean_oligo(value: Any, label: str) -> str:
    """Normalise and validate an oligo sequence, with actionable error messages."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a text sequence")
    seq = iupac.normalise(value)
    if not seq:
        raise ValueError(f"{label} is empty")
    invalid = iupac.find_invalid(seq)
    if invalid:
        hints = []
        if any(c == "U" for _, c in invalid):
            hints.append("write oligos as DNA (T instead of U), also for RNA targets")
        if any(c != "U" for _, c in invalid):
            hints.append(
                "put dye/quencher/modification names in probe_reporter, probe_quencher or "
                "probe_modifications, not in the sequence"
            )
        hint = f" ({'; '.join(hints)})" if hints else ""
        raise ValueError(
            f"{label} contains characters that are not IUPAC nucleotide codes: "
            f"{iupac.describe_invalid(invalid)}{hint}"
        )
    if len(seq) < MIN_OLIGO_LENGTH:
        raise ValueError(
            f"{label} is {len(seq)} nt, too short to evaluate (minimum {MIN_OLIGO_LENGTH})"
        )
    if len(seq) > MAX_OLIGO_LENGTH:
        raise ValueError(
            f"{label} is {len(seq)} nt; structure calculations support at most "
            f"{MAX_OLIGO_LENGTH} nt"
        )
    return seq


ROLES = ("forward", "reverse", "probe")
# config.yaml sections an assay file may set for itself under 'settings:'; 'ncbi' (servers,
# throttling, cache) and 'report' stay lab-wide
ASSAY_SETTING_SECTIONS = (
    "reaction", "oligo", "thresholds", "search", "specificity", "organisms", "inclusivity",
    "variants",
)  # fmt: skip
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
_DEGENERATE_SUFFIX = re.compile(r"_v\d+$")  # reserved: labels of degenerate expansions


class Oligo(BaseModel):
    """One named oligo of the reaction mix. Several oligos can share a role (alternatives)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str
    sequence: str
    role: str = Field(default="", description="forward, reverse or probe; set by the assay")
    reporter: str | None = Field(default=None, description="probes: reporter dye (e.g. FAM)")
    quencher: str | None = Field(default=None, description="probes: quencher")
    modifications: list[str] = Field(
        default_factory=list, description="probes: modifications such as MGB, LNA, ZEN"
    )

    @field_validator("modifications", mode="before")
    @classmethod
    def _mods(cls, v: Any) -> list[str]:
        return _modification_list(v)

    def declared_modifications(self, unreliable_tokens: Iterable[str]) -> list[str]:
        """Modifications that make nearest-neighbour Tm unreliable (declared or in dye names)."""
        found: dict[str, None] = dict.fromkeys(self.modifications)
        labels = f"{self.reporter or ''} {self.quencher or ''}".upper()
        for token in unreliable_tokens:
            if token in labels:
                found[token] = None
        return list(found)


class ReferenceAmplicon(BaseModel):
    """A reference amplicon (sense strand); several when lineages differ too much for one."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str
    sequence: str

    @field_validator("sequence", mode="before")
    @classmethod
    def _seq(cls, v: Any) -> str:
        return _clean_amplicon(v)


def _modification_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        v = re.split(r"[,;]", v)
    seen: dict[str, None] = {}
    for item in v:
        token = str(item).strip().upper()
        if token:
            seen[token] = None
    return list(seen)


def _clean_amplicon(v: Any) -> str:
    if not isinstance(v, str):
        raise ValueError("a reference amplicon must be a text sequence")
    seq = iupac.normalise(v)
    invalid = iupac.find_invalid(seq)
    if invalid:
        raise ValueError(
            f"reference amplicon contains non-IUPAC characters: {iupac.describe_invalid(invalid)}"
        )
    if len(seq) < MIN_AMPLICON_LENGTH:
        raise ValueError(f"reference amplicon is only {len(seq)} nt")
    return seq


def _oligo_entries(role: str, v: Any) -> list[dict[str, Any]]:
    """A role's value as a list of oligo dicts: a sequence, one {name, sequence}, or a list."""
    items = v if isinstance(v, list) else [v]
    if not items:
        raise ValueError(f"{role}: give at least one oligo")
    out: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            item = {"sequence": item}
        if not isinstance(item, dict):
            raise ValueError(
                f"{role}: each oligo is a sequence or a mapping with name and sequence"
            )
        item = dict(item)
        if not item.get("name"):
            if len(items) > 1:
                raise ValueError(f"{role}: give every oligo a name when there are several")
            item["name"] = role
        label = f"{role} '{item['name']}'" if len(items) > 1 or item["name"] != role else role
        if "sequence" not in item:
            raise ValueError(f"{label}: 'sequence' is missing")
        item["sequence"] = _clean_oligo(item["sequence"], f"{label} sequence")
        item["role"] = role
        out.append(item)
    return out


class Assay(BaseModel):
    """One real-time PCR assay: forward primer(s), reverse primer(s), probe(s), and its target.

    Each role takes one sequence (as before), one named oligo, or a list of named oligos. Oligos
    of the same role are alternatives in the same reaction mix (e.g. a second forward primer for a
    lineage a wobble base cannot bridge). Probes with the same reporter are alternatives; probes
    with different reporters detect different regions (channels).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    assay_name: str = Field(min_length=1, max_length=120)
    forward: list[Oligo]
    reverse: list[Oligo]
    probe: list[Oligo]
    probe_reporter: str | None = Field(
        default=None, description="Default reporter for probes that do not name their own"
    )
    probe_quencher: str | None = Field(
        default=None, description="Default quencher for probes that do not name their own"
    )
    probe_modifications: list[str] = Field(
        default_factory=list, description="Default modifications for probes without their own"
    )
    template_type: TemplateType = TemplateType.DNA
    target: Target
    near_neighbour_taxids: list[int] = Field(default_factory=list)
    exclusion_taxids: list[int] = Field(default_factory=list)
    exclusivity_organisms: list[str] = Field(
        default_factory=list,
        description="This assay's own exclusivity panel (organism names, resolved to taxonomy "
        "IDs the same way as the global list). Used for the exclusivity tier when "
        "'organisms.source' is 'assay' (the default) and this list is non-empty; see "
        "config.yaml's 'organisms' section.",
    )
    reference_amplicon: str | None = Field(
        default=None,
        description="Optional reference amplicon (sense strand); the first of "
        "reference_amplicons when several are given.",
    )
    reference_amplicons: list[ReferenceAmplicon] = Field(
        default_factory=list,
        description="Optional named reference amplicons, one per lineage; each oligo is placed in "
        "the one it fits best.",
    )
    oligo_source: str | None = Field(default=None, description="Where the oligos come from")
    notes: str | None = None
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="This assay's own settings, in config.yaml's structure, applied over the "
        "defaults and any --config file (sections: " + ", ".join(ASSAY_SETTING_SECTIONS) + ")",
    )

    @field_validator("settings", mode="before")
    @classmethod
    def _settings(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("settings must be a mapping, in the structure of config.yaml")
        # a section whose options are all commented out (as in the full template) reads as empty
        v = {k: val for k, val in v.items() if val is not None}
        for key, value in v.items():
            if key in ("ncbi", "report"):
                raise ValueError(
                    f"settings.{key} is lab-wide (servers, throttling, cache, report layout): "
                    "set it in a --config file, not per assay"
                )
            if key not in ASSAY_SETTING_SECTIONS:
                raise ValueError(
                    f"settings.{key} is not a configuration section; use one of "
                    + ", ".join(ASSAY_SETTING_SECTIONS)
                )
            if not isinstance(value, dict):
                raise ValueError(f"settings.{key} must be a mapping")
        return v

    @field_validator("forward", "reverse", "probe", mode="before")
    @classmethod
    def _oligos(cls, v: Any, info: Any) -> list[dict[str, Any]]:
        return _oligo_entries(info.field_name, v)

    @field_validator("reference_amplicon", mode="before")
    @classmethod
    def _amplicon(cls, v: Any) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return _clean_amplicon(v)

    @field_validator("probe_modifications", mode="before")
    @classmethod
    def _mods(cls, v: Any) -> list[str]:
        return _modification_list(v)

    @model_validator(mode="after")
    def _mix(self) -> Assay:
        """Unique names; probe defaults; one reference list (reference_amplicon = the first)."""
        seen: set[str] = set()
        for o in self.oligo_list:
            if not _NAME_RE.match(o.name) or _DEGENERATE_SUFFIX.search(o.name):
                raise ValueError(
                    f"oligo name '{o.name}': use letters, digits, '.', '_' or '-' (at most 40, "
                    "no spaces), not ending in '_v' + a number (reserved for degenerate variants)"
                )
            if o.name in seen:
                raise ValueError(f"oligo name '{o.name}' is used twice; names must be unique")
            seen.add(o.name)
        for p in self.probe:
            p.reporter = p.reporter or self.probe_reporter
            p.quencher = p.quencher or self.probe_quencher
            p.modifications = p.modifications or list(self.probe_modifications)
        derived = bool(self.reference_amplicons) and (
            self.reference_amplicon == self.reference_amplicons[0].sequence
        )  # a saved assay carries both: the single field is the first of the list
        if self.reference_amplicon and self.reference_amplicons and not derived:
            raise ValueError("give either reference_amplicon or reference_amplicons, not both")
        if self.reference_amplicon and not derived:
            self.reference_amplicons = [
                ReferenceAmplicon(name="reference", sequence=self.reference_amplicon)
            ]
        elif self.reference_amplicons:
            names = [r.name for r in self.reference_amplicons]
            if len(set(names)) != len(names):
                raise ValueError("reference_amplicons names must be unique")
            self.reference_amplicon = self.reference_amplicons[0].sequence
        return self

    @field_validator("near_neighbour_taxids", "exclusion_taxids")
    @classmethod
    def _taxids(cls, v: list[int]) -> list[int]:
        if any(t <= 0 for t in v):
            raise ValueError("taxonomy IDs must be positive integers")
        return sorted(set(v))

    @field_validator("exclusivity_organisms")
    @classmethod
    def _exclusivity_organisms(cls, v: list[str]) -> list[str]:
        seen: dict[str, None] = {}
        for name in v:
            name = name.strip()
            if not name:
                raise ValueError("exclusivity_organisms entries must not be empty")
            seen.setdefault(name, None)
        return list(seen)

    @property
    def oligo_list(self) -> list[Oligo]:
        """Every oligo of the mix, forward first, then reverse, then probe."""
        return [*self.forward, *self.reverse, *self.probe]

    @property
    def oligos(self) -> dict[str, str]:
        """Sequence by oligo name, in report order (name = role for a single unnamed oligo)."""
        return {o.name: o.sequence for o in self.oligo_list}

    def by_role(self, role: str) -> list[Oligo]:
        return {"forward": self.forward, "reverse": self.reverse, "probe": self.probe}[role]

    def oligo(self, name: str) -> Oligo:
        return next(o for o in self.oligo_list if o.name == name)

    def role_of(self, label: str) -> str:
        """Role of an oligo name or query label (``NG-P1`` or a degenerate ``NG-P1_v2``)."""
        name = _DEGENERATE_SUFFIX.sub("", label)
        for o in self.oligo_list:
            if o.name in (label, name):
                return o.role
        raise KeyError(f"no oligo named '{label}' in the assay")

    @property
    def multi_oligo(self) -> bool:
        """More than one oligo for some role."""
        return any(len(self.by_role(r)) > 1 for r in ROLES)

    @property
    def slug(self) -> str:
        """Filesystem-safe identifier derived from the assay name."""
        return re.sub(r"[^A-Za-z0-9._-]+", "-", self.assay_name).strip("-.").lower() or "assay"

    def declared_modifications(self, unreliable_tokens: Iterable[str]) -> list[str]:
        """Modifications that make nearest-neighbour Tm unreliable, over every probe."""
        found: dict[str, None] = {}
        for p in self.probe:
            found.update(dict.fromkeys(p.declared_modifications(unreliable_tokens)))
        return list(found)
