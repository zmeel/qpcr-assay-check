"""Assay files for the GUI (phase G2): listing, saving with history, validation and live QC.

Assay files live in ``<work>/assays/`` as plain YAML, the same files the command line runs.
Every save first copies the previous version to ``<work>/assays/.history/<stem>/``; deleting
moves the file to ``<work>/assays/.deleted/``. Nothing is lost silently.

Validation is the command line's: the same assay model, the same configuration merge
(``<work>/config.yaml`` when present, then the assay's own ``settings:``), and the oligo QC of a
QC-only run, which takes milliseconds.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ..config import Config, format_validation_error, load_config
from ..errors import QpcrAssayCheckError
from ..models import Assay
from ..results import QCReport

log = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.ya?ml$")
MAX_BYTES = 1_000_000  # an assay file is a few kB; refuse anything absurd


class AssayFileError(ValueError):
    """A file name or file content the GUI refuses."""


def check_name(name: str) -> str:
    """A safe file name (letters, digits, '.', '_', '-'; ending .yaml or .yml)."""
    if not NAME_RE.match(name or ""):
        raise AssayFileError(
            "use a file name of letters, digits, '.', '_' or '-' ending in .yaml (no folders)"
        )
    return name


@dataclass
class AssayEntry:
    """One assay file as the list shows it."""

    name: str
    assay_name: str
    modified: str
    valid: bool
    problem: str = ""


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _summary(path: Path) -> AssayEntry:
    modified = datetime.fromtimestamp(path.stat().st_mtime, UTC).strftime("%Y-%m-%d %H:%M")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        name = str((data or {}).get("assay_name") or "") if isinstance(data, dict) else ""
        Assay.model_validate(data)
        return AssayEntry(path.name, name or path.stem, modified, True)
    except (OSError, yaml.YAMLError, ValidationError, TypeError, AttributeError) as exc:
        problem = "not valid YAML" if isinstance(exc, yaml.YAMLError) else "needs attention"
        return AssayEntry(path.name, locals().get("name") or path.stem, modified, False, problem)


class AssayFiles:
    """``<work>/assays`` (editable) and an optional read-only examples folder."""

    def __init__(self, assays_dir: Path, examples_dir: Path | None = None) -> None:
        self.dir = Path(assays_dir)
        self.examples_dir = Path(examples_dir) if examples_dir else None

    def _in(self, folder: Path, name: str) -> Path:
        path = (folder / check_name(name)).resolve()
        if path.parent != folder.resolve():
            raise AssayFileError("the file must be directly in the assays folder")
        return path

    def path(self, name: str) -> Path:
        return self._in(self.dir, name)

    def exists(self, name: str) -> bool:
        return self.path(name).is_file()

    def list(self) -> list[AssayEntry]:
        if not self.dir.is_dir():
            return []
        files = [p for p in self.dir.iterdir() if p.is_file() and NAME_RE.match(p.name)]
        return sorted((_summary(p) for p in files), key=lambda e: e.assay_name.lower())

    def examples(self) -> list[AssayEntry]:
        if not self.examples_dir or not self.examples_dir.is_dir():
            return []
        files = [p for p in self.examples_dir.iterdir() if p.is_file() and NAME_RE.match(p.name)]
        return sorted((_summary(p) for p in files), key=lambda e: e.assay_name.lower())

    def example_text(self, name: str) -> str:
        if not self.examples_dir:
            raise AssayFileError("no examples folder is configured")
        return self._in(self.examples_dir, name).read_text(encoding="utf-8")

    def read(self, name: str) -> str:
        path = self.path(name)
        if not path.is_file():
            raise FileNotFoundError(name)
        return path.read_text(encoding="utf-8")

    def _write(self, path: Path, text: str) -> None:
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise AssayFileError("the file is larger than 1 MB")
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def create(self, name: str, text: str) -> None:
        path = self.path(name)
        if path.exists():
            raise AssayFileError(f"{name} already exists")
        self._write(path, text)
        log.info("GUI: assay file %s created", name)

    def save(self, name: str, text: str) -> None:
        """Overwrite, after copying the previous version to ``.history/<stem>/``."""
        path = self.path(name)
        if path.is_file():
            if path.read_text(encoding="utf-8") == text:
                return
            keep = self.dir / ".history" / path.stem
            keep.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, keep / f"{_stamp()}-{path.name}")
        self._write(path, text)
        log.info("GUI: assay file %s saved", name)

    def delete(self, name: str) -> None:
        """Move to ``.deleted/`` (never removed)."""
        path = self.path(name)
        if not path.is_file():
            raise FileNotFoundError(name)
        gone = self.dir / ".deleted"
        gone.mkdir(parents=True, exist_ok=True)
        os.replace(path, gone / f"{_stamp()}-{path.name}")
        log.info("GUI: assay file %s moved to %s", name, gone)


def parse_mapping(text: str) -> dict[str, Any]:
    """The YAML text as a mapping; :class:`AssayFileError` with the parser's message if not."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AssayFileError(f"not valid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise AssayFileError("the file must be a YAML mapping (key: value lines)")
    return data


@dataclass
class Validation:
    """What the editor shows beside the file."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    assay: Assay | None = None
    cfg: Config | None = None
    qc: QCReport | None = None


def validate_text(text: str, config_path: Path | None) -> Validation:
    """The assay model, the merged configuration and the oligo QC, as a QC-only run has them."""
    try:
        data = parse_mapping(text)
    except AssayFileError as exc:
        return Validation(False, [str(exc)])
    try:
        assay = Assay.model_validate(data)
    except ValidationError as exc:
        return Validation(False, format_validation_error(exc).splitlines())
    try:
        cfg = load_config(config_path, assay.settings)
    except QpcrAssayCheckError as exc:
        return Validation(False, str(exc).splitlines(), assay=assay)
    from ..pipeline import evaluate

    try:
        qc = evaluate(assay, cfg, qc_only=True).oligo_qc
    except (QpcrAssayCheckError, ValueError) as exc:
        return Validation(False, [f"oligo QC failed: {exc}"], assay=assay, cfg=cfg)
    return Validation(True, assay=assay, cfg=cfg, qc=qc)
