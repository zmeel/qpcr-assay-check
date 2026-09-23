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


class Assay(BaseModel):
    """One real-time PCR assay: forward primer, reverse primer, TaqMan probe, and its target."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    assay_name: str = Field(min_length=1, max_length=120)
    forward: str
    reverse: str
    probe: str
    probe_reporter: str | None = None
    probe_quencher: str | None = None
    probe_modifications: list[str] = Field(default_factory=list)
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
        description="Optional reference amplicon (sense strand); enables amplicon QC in v0.1.0.",
    )
    oligo_source: str | None = Field(default=None, description="Where the oligos come from")
    notes: str | None = None

    @field_validator("forward", "reverse", "probe", mode="before")
    @classmethod
    def _oligo(cls, v: Any, info: Any) -> str:
        return _clean_oligo(v, f"{info.field_name} sequence")

    @field_validator("reference_amplicon", mode="before")
    @classmethod
    def _amplicon(cls, v: Any) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if not isinstance(v, str):
            raise ValueError("reference_amplicon must be a text sequence")
        seq = iupac.normalise(v)
        invalid = iupac.find_invalid(seq)
        if invalid:
            raise ValueError(
                "reference_amplicon contains non-IUPAC characters: "
                f"{iupac.describe_invalid(invalid)}"
            )
        if len(seq) < MIN_AMPLICON_LENGTH:
            raise ValueError(f"reference_amplicon is only {len(seq)} nt")
        return seq

    @field_validator("probe_modifications", mode="before")
    @classmethod
    def _mods(cls, v: Any) -> list[str]:
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
    def oligos(self) -> dict[str, str]:
        """The three oligos keyed by role, in report order."""
        return {"forward": self.forward, "reverse": self.reverse, "probe": self.probe}

    @property
    def slug(self) -> str:
        """Filesystem-safe identifier derived from the assay name."""
        return re.sub(r"[^A-Za-z0-9._-]+", "-", self.assay_name).strip("-.").lower() or "assay"

    def declared_modifications(self, unreliable_tokens: Iterable[str]) -> list[str]:
        """Modifications that make nearest-neighbour Tm unreliable.

        Every user-declared modification counts, plus known tokens (MGB, LNA, ZEN, ...) found
        in the reporter or quencher name.
        """
        found: dict[str, None] = dict.fromkeys(self.probe_modifications)
        labels = f"{self.probe_reporter or ''} {self.probe_quencher or ''}".upper()
        for token in unreliable_tokens:
            if token in labels:
                found[token] = None
        return list(found)
