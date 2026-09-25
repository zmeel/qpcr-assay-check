"""Panel-level escape detection: genomes that escape every target of a multi-target panel.

A panel file lists two or more assay files for the same target organism (e.g. a *C. trachomatis*
assay on the cryptic plasmid plus one on a chromosomal gene). Each assay's variant analysis has
already stored the target region of every genome it processed; here those stores are read back
(no NCBI requests, except to cut the amplicon out of a target accession for an assay without a
reference amplicon), each genome is judged per assay by its best-binding copy exactly as in the
assay's own report, and the per-assay outcomes are combined per genome. The clinical risk is a
strain that escapes every target at once (as the Swedish nvCT plasmid deletion did for
single-target assays).

Only genomes processed by every assay of the panel are combined; the others are counted.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .config import Config, format_validation_error
from .errors import InputError
from .models import Assay

log = logging.getLogger(__name__)

EXAMPLES_KEPT = 200  # genomes listed per class in the report (the workbook lists them all)


class PanelFile(BaseModel):
    """The panel definition: a name and the assay files (paths relative to the panel file)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    panel_name: str = Field(min_length=1, max_length=200)
    assays: list[str] = Field(description="two or more assay files for the same target")
    notes: str = ""

    @field_validator("assays")
    @classmethod
    def _two_or_more(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("a panel needs at least two assay files")
        if len(set(v)) != len(v):
            raise ValueError("an assay file is listed twice")
        return v


class State(StrEnum):
    """What one assay does with one genome."""

    DETECTED = "detected"  # a detectable copy (the assay's own inclusivity rule)
    ESCAPE = "escape"  # region found, but no detectable copy
    NOT_FOUND = "region not found"  # the target region is absent or too divergent to find
    UNKNOWN = "not assessable"  # hidden by N, cut by a contig/record end
    UNDETERMINED = "undetermined"  # no detectable copy, but no published basis to call it
    # an escape either (a single MGB-probe mismatch, an ambiguity code near a 3' end)


AFFECTED = (State.ESCAPE, State.NOT_FOUND)
PARTIAL_RECORD_SOURCES = ("blast_partitioned",)  # records are often single genes or partial


class PanelClass(StrEnum):
    ALL = "detected by every target"
    SOME = "detected by some targets"
    NONE = "detected by no target"  # an escape, and no target detects it: the panel misses it
    UNDETERMINED = "undetermined"  # no target detects it, and none shows an escape


class MemberSummary(BaseModel):
    """One assay of the panel, over the genomes it processed."""

    file: str
    assay_name: str
    store: str
    source: str
    homopolymer_bulges_detectable: bool
    processed: int
    states: dict[str, int]


class GenomeRow(BaseModel):
    accession: str
    release_date: str
    organism: str
    states: list[str]  # per member, in panel order
    panel_class: str


class YearRow(BaseModel):
    year: int
    genomes: int
    counts: dict[str, int]


class PanelResult(BaseModel):
    """The combined outcome; ``genomes`` holds every combined genome (for the workbook)."""

    panel_name: str
    target_taxid: int
    exclude_taxids: list[int]
    generated_at: str
    members: list[MemberSummary]
    in_all: int
    not_in_all: int
    counts: dict[str, int]
    years: list[YearRow]
    genomes: list[GenomeRow]
    notes: str = ""
    partial_records: bool = Field(
        default=False,
        description="Nucleotide records: 'region not found' counted as not assessable",
    )

    def of_class(self, cls: PanelClass) -> list[GenomeRow]:
        return [g for g in self.genomes if g.panel_class == cls.value]


# ------------------------------------------------------------------ reading the panel
def load_panel(path: Path) -> PanelFile:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise InputError(f"Cannot read panel file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"Panel file {path} must contain a YAML mapping")
    try:
        return PanelFile.model_validate(data)
    except ValidationError as exc:
        raise InputError(f"Invalid panel file {path}:\n{format_validation_error(exc)}") from exc


def _roles(assay: Assay) -> set[tuple[int, str]]:
    """The target's left-out taxa and their roles; the reason text does not matter."""
    return {(t.taxid, t.role) for t in assay.target.taxa}


def check_members(assays: list[Assay], cfgs: list[Config]) -> None:
    """Every assay must look at the same collection of genomes, or combining them is wrong."""
    first, cfg0 = assays[0], cfgs[0]
    for a, c in zip(assays[1:], cfgs[1:], strict=True):
        if a.target.taxid != first.target.taxid:
            raise InputError(
                f"'{a.assay_name}' targets taxon {a.target.taxid}, '{first.assay_name}' taxon "
                f"{first.target.taxid}: a panel combines assays for the same target."
            )
        if _roles(a) != _roles(first):
            raise InputError(
                f"'{a.assay_name}' and '{first.assay_name}' leave different taxa out of the "
                "target, or give them different roles (target.taxa), so their genome "
                "collections or their interpretation differ."
            )
        if c.variants.source != cfg0.variants.source:
            raise InputError(
                f"'{a.assay_name}' uses variants.source {c.variants.source}, "
                f"'{first.assay_name}' {cfg0.variants.source}: the genomes must come from the "
                "same source to be combined."
            )
        for key in ("nucleotide_query", "current_assemblies_only", "exclude_atypical"):
            if getattr(c.variants, key) != getattr(cfg0.variants, key):
                raise InputError(
                    f"'{a.assay_name}' and '{first.assay_name}' use a different "
                    f"variants.{key}, so their genome collections differ and cannot be combined."
                )
    if first.target.taxid is None:
        raise InputError("A panel needs the target's taxonomy ID in every assay.")
    if first.target.excluded_taxids and cfg0.variants.source == "datasets":
        raise InputError(
            "Taxa left out of the target (target.taxa / exclude_taxids) are not supported "
            "with variants.source: datasets (the NCBI Datasets genome listing has no 'NOT' "
            "filter); use blast_partitioned."
        )
    if cfg0.variants.source not in ("datasets", "blast_partitioned"):
        raise InputError(
            "A panel needs the exhaustive variant analysis (variants.source datasets or "
            "blast_partitioned); blast_hits is a sample."
        )


# ------------------------------------------------------------------ combining
def member_states(items: list[Any], calls: list[Any]) -> dict[str, tuple[State, Any]]:
    """Per accession base: the assay's state and the stored item (for date and organism)."""
    call_of = {c.accession: c for c in calls}
    out: dict[str, tuple[State, Any]] = {}
    for it in items:
        if it.status == "not_found":
            state = State.NOT_FOUND
        elif it.status == "masked" or it.accession not in call_of:
            state = State.UNKNOWN  # hidden by N, or every copy cut by a contig/record end
        elif all(call_of[it.accession].role_good.values()):
            state = State.DETECTED
        elif call_of[it.accession].undetermined:
            state = State.UNDETERMINED
        else:
            state = State.ESCAPE
        out[it.accession.partition(".")[0]] = (state, it)
    return out


def classify(states: list[State], *, partial_records: bool = False) -> PanelClass:
    """The panel outcome for one genome from its per-assay states.

    "Detected by no target" needs at least one real escape (the region is there, but no copy
    is detectable): a genome in which no target region is found at all is more often an
    incomplete assembly than a strain with every region deleted, so it is undetermined.
    ``partial_records`` (Nucleotide records): "region not found" usually means the record is
    another gene or a partial sequence, so it counts as not assessable, not as a miss.
    """
    if all(s is State.DETECTED for s in states):
        return PanelClass.ALL
    if any(s is State.DETECTED for s in states):
        return PanelClass.SOME
    missed = (State.ESCAPE,) if partial_records else AFFECTED
    if all(s in missed for s in states) and State.ESCAPE in states:
        return PanelClass.NONE
    return PanelClass.UNDETERMINED


def combine(
    panel: PanelFile,
    assays: list[Assay],
    cfgs: list[Config],
    per_member: list[tuple[list[Any], list[Any], Path]],
    *,
    now: datetime | None = None,
) -> PanelResult:
    """Combine the per-assay outcomes of the genomes every assay processed."""
    maps = [member_states(items, calls) for items, calls, _p in per_member]
    members = [
        MemberSummary(
            file=f, assay_name=a.assay_name, store=str(p), source=c.variants.source,
            homopolymer_bulges_detectable=c.variants.homopolymer_bulges_detectable,
            processed=len(m), states=dict(Counter(s.value for s, _it in m.values())),
        )
        for f, a, c, m, (_i, _c, p) in zip(panel.assays, assays, cfgs, maps, per_member,
                                           strict=True)
    ]  # fmt: skip
    keys = set.intersection(*(set(m) for m in maps))
    union = set.union(*(set(m) for m in maps))
    partial = cfgs[0].variants.source in PARTIAL_RECORD_SOURCES
    genomes: list[GenomeRow] = []
    for key in keys:
        states = [m[key][0] for m in maps]
        # the newest version any assay holds (stores may have caught different versions)
        it = max((m[key][1] for m in maps), key=lambda x: _version(x.accession))
        genomes.append(
            GenomeRow(
                accession=it.accession, release_date=it.release_date, organism=it.organism,
                states=[s.value for s in states],
                panel_class=classify(states, partial_records=partial).value,
            )
        )  # fmt: skip
    genomes.sort(key=lambda g: (g.release_date, g.accession), reverse=True)
    per_year: dict[int, Counter[str]] = defaultdict(Counter)
    for g in genomes:
        per_year[int(g.release_date[:4])][g.panel_class] += 1
    return PanelResult(
        panel_name=panel.panel_name,
        target_taxid=assays[0].target.taxid or 0,
        exclude_taxids=assays[0].target.excluded_taxids,
        generated_at=(now or datetime.now(UTC)).isoformat(timespec="seconds"),
        members=members,
        in_all=len(keys),
        not_in_all=len(union) - len(keys),
        counts={c.value: sum(g.panel_class == c.value for g in genomes) for c in PanelClass},
        years=[
            YearRow(year=y, genomes=sum(c.values()), counts=dict(c))
            for y, c in sorted(per_year.items(), reverse=True)
        ],
        genomes=genomes,
        notes=panel.notes,
        partial_records=partial,
    )


def _version(accession: str) -> int:
    tail = accession.rpartition(".")[2]
    return int(tail) if tail.isdigit() else 0


def run_panel(
    panel_path: Path,
    load_member: Callable[[Path], tuple[Assay, Config]],
    cache_root: Path,
    fetch_fasta: Callable[[str], str],
    *,
    now: datetime | None = None,
) -> PanelResult:
    """Read the panel file and every assay's region store, and combine them."""
    from .variants.exhaustive import stored_calls

    panel = load_panel(panel_path)
    assays, cfgs = [], []
    for f in panel.assays:
        path = (panel_path.parent / f).resolve()
        if not path.is_file():
            raise InputError(f"Assay file {f} of the panel was not found (looked for {path}).")
        a, c = load_member(path)
        assays.append(a)
        cfgs.append(c)
    check_members(assays, cfgs)
    per_member = []
    for a, c in zip(assays, cfgs, strict=True):
        items, calls, store = stored_calls(a, c, cache_root, fetch_fasta, c.variants.source)
        if not items:
            raise InputError(
                f"No stored genomes for '{a.assay_name}' (looked in {store}): run the assay "
                "itself first; the panel only combines what its variant analysis stored."
            )
        log.info("%s: %d genomes in its region store", a.assay_name, len(items))
        per_member.append((items, calls, store))
    return combine(panel, assays, cfgs, per_member, now=now)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "panel"
