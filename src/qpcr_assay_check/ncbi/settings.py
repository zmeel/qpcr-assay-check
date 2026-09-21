"""NCBI credentials. Read from environment variables only, never from files."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from ..errors import InputError

ENV_EMAIL = "NCBI_EMAIL"
ENV_API_KEY = "NCBI_API_KEY"


@dataclass(frozen=True)
class Credentials:
    """Identification NCBI asks every API user to provide."""

    email: str
    api_key: str | None = None

    def redact(self, text: str) -> str:
        """Remove the API key (and e-mail) from text that may be logged or shown."""
        out = text
        if self.api_key:
            out = out.replace(self.api_key, "***")
        return out.replace(self.email, "<email>")


def credentials_from_env(env: Mapping[str, str] | None = None) -> Credentials:
    """Load credentials from ``NCBI_EMAIL`` (required) and ``NCBI_API_KEY`` (optional)."""
    env = os.environ if env is None else env
    email = (env.get(ENV_EMAIL) or "").strip()
    if not email or "@" not in email:
        raise InputError(
            f"Set the {ENV_EMAIL} environment variable to an address that reaches you or your "
            "laboratory. NCBI requires it so they can contact you if your usage causes problems. "
            f'Example: export {ENV_EMAIL}="your.name@example.org"'
        )
    key = (env.get(ENV_API_KEY) or "").strip() or None
    return Credentials(email=email, api_key=key)
