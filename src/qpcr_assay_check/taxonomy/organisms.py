"""Load the clinical organism list: names grouped by category, from a YAML file or an assay.

Ships as ``data/clinical_organisms.yaml`` (a starting point, see that file's own header); a
laboratory's own list is a drop-in replacement with the same structure, set via
``organisms.list_file`` in the configuration. An assay can also carry its own exclusivity panel
(``Assay.exclusivity_organisms``), preferred over the global list when ``organisms.source`` is
``"assay"`` (the default) -- see ``organism_list_source``.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..config import Config, format_validation_error
from ..errors import ConfigError
from ..models import Assay


class OrganismCategory(BaseModel):
    """One named group of organisms (grouping is for readability only)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    organisms: list[str] = Field(min_length=1)


class OrganismList(BaseModel):
    """The clinical organism list: every category and its organism names."""

    model_config = ConfigDict(extra="forbid")

    categories: list[OrganismCategory] = Field(min_length=1)

    @property
    def names(self) -> list[str]:
        """Every organism name, file order, duplicates removed (first occurrence kept)."""
        seen: dict[str, None] = {}
        for category in self.categories:
            for name in category.organisms:
                seen.setdefault(name, None)
        return list(seen)

    def category_of(self, name: str) -> str | None:
        """The first category listing ``name``, or None."""
        for category in self.categories:
            if name in category.organisms:
                return category.name
        return None


def default_organism_list_text() -> str:
    """The packaged starter organism list, as text."""
    return (resources.files("qpcr_assay_check") / "data" / "clinical_organisms.yaml").read_text(
        encoding="utf-8"
    )


def organism_list_source(cfg: Config, assay: Assay | None) -> Literal["assay", "global"]:
    """Which exclusivity list a run actually uses: the assay's own, or the global one.

    ``"assay"`` only when ``organisms.source`` is ``"assay"`` *and* the assay defines a non-empty
    ``exclusivity_organisms``; every other combination falls back to ``"global"`` (including an
    assay-preferring config with an assay that leaves its own list empty, so existing assays keep
    working unchanged until they opt in).
    """
    if cfg.organisms.source == "assay" and assay is not None and assay.exclusivity_organisms:
        return "assay"
    return "global"


def load_organism_list(cfg: Config, assay: Assay | None = None) -> OrganismList:
    """Load the exclusivity organism list per ``organism_list_source(cfg, assay)``.

    ``"assay"``: the assay's own ``exclusivity_organisms``, as a single category so it renders and
    resolves exactly like the global list. ``"global"``: ``organisms.list_file``, or the packaged
    starter list when that is unset.
    """
    if organism_list_source(cfg, assay) == "assay":
        assert assay is not None  # organism_list_source only returns "assay" when this holds
        return OrganismList(
            categories=[
                OrganismCategory(
                    name="Assay-specific exclusivity list", organisms=assay.exclusivity_organisms
                )
            ]
        )
    path = cfg.organisms.list_file
    source = path or "the packaged starter list"
    if path:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"Cannot read organism list file {path}: {exc}") from exc
    else:
        text = default_organism_list_text()
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Cannot parse organism list ({source}): {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Organism list ({source}) must contain a YAML mapping")
    try:
        return OrganismList.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(
            f"Invalid organism list ({source}):\n{format_validation_error(exc)}"
        ) from exc
