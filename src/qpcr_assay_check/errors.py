"""Exception types for expected, user-facing failures."""


class QpcrAssayCheckError(Exception):
    """Base class for all errors that are reported to the user without a traceback."""


class InputError(QpcrAssayCheckError):
    """The assay definition (or a CLI argument) is invalid."""


class ConfigError(InputError):
    """The configuration file is invalid."""
