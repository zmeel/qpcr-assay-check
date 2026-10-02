"""The editor's form: the common fields of an assay file, changed in place.

The file is read and written with ruamel.yaml's round-trip mode, so comments (provenance, what
was checked), key order and flow style stay as they are; only the values the form changes are
replaced. Loci, channels, references, taxa and settings other than the annealing temperature
are edited in the YAML tab.
"""

from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .assays import AssayFileError

ROLES = ("forward", "reverse", "probe")
TEMPLATE_TYPES = ("DNA", "RNA")


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def load(text: str) -> CommentedMap:
    try:
        data = _yaml().load(text)
    except Exception as exc:  # ruamel raises several unrelated error types
        raise AssayFileError(f"not valid YAML: {exc}") from exc
    if data is None:
        return CommentedMap()
    if not isinstance(data, CommentedMap):
        raise AssayFileError("the file must be a YAML mapping (key: value lines)")
    return data


def dump(data: CommentedMap) -> str:
    out = io.StringIO()
    _yaml().dump(data, out)
    return out.getvalue()


@dataclass
class OligoRow:
    """One oligo as the form shows it; ``original`` is its name in the file ('' = new)."""

    role: str
    name: str
    sequence: str
    reporter: str = ""
    quencher: str = ""
    modifications: str = ""
    original: str = ""
    remove: bool = False


@dataclass
class FormValues:
    """The fields the form edits."""

    assay_name: str = ""
    template_type: str = "DNA"
    taxid: str = ""
    annealing: str = ""
    exclusivity: str = ""  # one organism per line
    oligos: list[OligoRow] = field(default_factory=list)


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _items(node: Any) -> list[Any]:
    if node is None:
        return []
    return list(node) if isinstance(node, list) else [node]


def _mods(v: Any) -> str:
    if v is None:
        return ""
    return ", ".join(str(m) for m in v) if isinstance(v, list) else str(v)


def values_of(text: str) -> FormValues:
    """The form's fields from a file (the raw values, before defaults are applied)."""
    data = load(text)
    target = data.get("target") if isinstance(data.get("target"), Mapping) else {}
    reaction = ((data.get("settings") or {}).get("reaction") or {}) if isinstance(
        data.get("settings"), Mapping
    ) else {}  # fmt: skip
    rows: list[OligoRow] = []
    for role in ROLES:
        items = _items(data.get(role))
        for item in items:
            if isinstance(item, Mapping):
                name = _s(item.get("name")) or role
                rows.append(OligoRow(
                    role, name, _s(item.get("sequence")), _s(item.get("reporter")),
                    _s(item.get("quencher")), _mods(item.get("modifications")), original=name,
                ))  # fmt: skip
            else:
                rows.append(OligoRow(role, role, _s(item), original=role))
    organisms = data.get("exclusivity_organisms") or []
    return FormValues(
        assay_name=_s(data.get("assay_name")),
        template_type=_s(data.get("template_type")) or "DNA",
        taxid=_s(target.get("taxid")),
        annealing=_s(reaction.get("annealing_temp_C") if isinstance(reaction, Mapping) else ""),
        exclusivity="\n".join(str(o) for o in organisms if o is not None),
        oligos=rows,
    )


def _number(label: str, raw: str, kind: type) -> Any:
    try:
        return kind(raw)
    except ValueError as exc:
        raise AssayFileError(f"{label}: '{raw}' is not a number") from exc


def _flow_map(**values: Any) -> CommentedMap:
    m = CommentedMap((k, v) for k, v in values.items() if v not in (None, "", []))
    m.fa.set_flow_style()
    return m


def _flow_seq(values: list[Any]) -> CommentedSeq:
    s = CommentedSeq(values)
    s.fa.set_flow_style()
    return s


def _set_or_drop(m: CommentedMap, key: str, value: Any) -> None:
    if value in (None, "", []):
        if key in m:
            del m[key]
    elif m.get(key) != value:
        m[key] = value


def _rename_references(data: CommentedMap, renames: dict[str, str]) -> None:
    """A renamed oligo keeps its place in loci, channels and lab evidence."""
    if not renames:
        return
    for section, keys in (("loci", ("primers", "probes")), ("channels", ("probes",))):
        for entry in _items(data.get(section)):
            if not isinstance(entry, Mapping):
                continue
            for key in keys:
                names = entry.get(key)
                if isinstance(names, list):
                    for i, n in enumerate(names):
                        if n in renames:
                            names[i] = renames[n]
    for ev in _items(data.get("evidence")):
        if isinstance(ev, Mapping) and ev.get("oligo") in renames:
            ev["oligo"] = renames[ev["oligo"]]


def _apply_oligos(data: CommentedMap, rows: list[OligoRow]) -> None:
    renames: dict[str, str] = {}
    for role in ROLES:
        mine = [r for r in rows if r.role == role]
        if not mine:
            continue
        node = data.get(role)
        existing = _items(node)
        by_name: dict[str, tuple[int, Any]] = {}
        for i, item in enumerate(existing):
            name = _s(item.get("name")) or role if isinstance(item, Mapping) else role
            by_name[name] = (i, item)
        kept: list[Any] = []
        for r in mine:
            if r.remove:
                continue
            seq = r.sequence.strip()
            name = r.name.strip() or role
            if r.original and r.original != name:
                renames[r.original] = name
            probe_fields = {}
            if role == "probe":
                mods = [m.strip() for m in r.modifications.split(",") if m.strip()]
                probe_fields = {"reporter": r.reporter.strip(), "quencher": r.quencher.strip(),
                                "modifications": mods}  # fmt: skip
            old = by_name.get(r.original)[1] if r.original in by_name else None
            if isinstance(old, CommentedMap):
                _set_or_drop(old, "name", name)
                old["sequence"] = seq
                for key, value in probe_fields.items():
                    if key == "modifications" and key in old and not value:
                        old[key] = _flow_seq([])  # keep an explicit 'no modifications'
                    elif key == "modifications" and value:
                        if list(old.get(key) or []) != value:
                            old[key] = _flow_seq(value)
                    else:
                        _set_or_drop(old, key, value)
                kept.append(old)
            elif old is not None and name == role and not any(probe_fields.values()):
                kept.append(seq)  # a bare sequence stays a bare sequence
            else:
                kept.append(_flow_map(name=name, sequence=seq, **probe_fields))
        if not kept:
            raise AssayFileError(f"{role}: keep at least one oligo")
        if len(kept) == 1 and not isinstance(node, list):
            data[role] = kept[0]
        elif isinstance(node, CommentedSeq):
            node[:] = kept
        else:
            data[role] = CommentedSeq(kept)
    _rename_references(data, renames)


def apply(text: str, v: FormValues) -> str:
    """The file with the form's values put in; everything else unchanged."""
    data = load(text)
    if not v.assay_name.strip():
        raise AssayFileError("give the assay a name")
    data["assay_name"] = v.assay_name.strip()
    if v.template_type not in TEMPLATE_TYPES:
        raise AssayFileError("template type: DNA or RNA")
    data["template_type"] = v.template_type
    target = data.get("target")
    if not isinstance(target, CommentedMap):
        target = CommentedMap()
        data["target"] = target
    taxid = v.taxid.strip()
    _set_or_drop(target, "taxid", _number("target taxon", taxid, int) if taxid else None)
    annealing = v.annealing.strip()
    settings = data.get("settings")
    if annealing:
        value = _number("annealing temperature", annealing, float)
        value = int(value) if value.is_integer() else value
        if not isinstance(settings, CommentedMap):
            settings = CommentedMap()
            data["settings"] = settings
        reaction = settings.get("reaction")
        if not isinstance(reaction, CommentedMap):
            reaction = CommentedMap()
            settings["reaction"] = reaction
        if reaction.get("annealing_temp_C") != value:
            reaction["annealing_temp_C"] = value
    elif isinstance(settings, CommentedMap) and isinstance(settings.get("reaction"), Mapping):
        _set_or_drop(settings["reaction"], "annealing_temp_C", None)
    organisms = [line.strip() for line in v.exclusivity.splitlines() if line.strip()]
    current = data.get("exclusivity_organisms")
    if isinstance(current, CommentedSeq):
        if list(current) != organisms:
            current[:] = organisms
    elif organisms or "exclusivity_organisms" in data:
        data["exclusivity_organisms"] = organisms
    _apply_oligos(data, v.oligos)
    return dump(data)
