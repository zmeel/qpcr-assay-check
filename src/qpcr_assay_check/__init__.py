"""qpcr-assay-check: in silico re-evaluation of real-time PCR (TaqMan) assays."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("qpcr-assay-check")
except PackageNotFoundError:  # pragma: no cover - running from an uninstalled source tree
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
