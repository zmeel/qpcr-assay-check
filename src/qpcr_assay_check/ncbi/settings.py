"""NCBI credentials. Read from environment variables only, never from files."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote, quote_plus

from ..errors import InputError

ENV_EMAIL = "NCBI_EMAIL"
ENV_API_KEY = "NCBI_API_KEY"


_SECRET_PARAM = re.compile(r"(?i)\b(email|api_key)=[^&\s'\")]+")


def scrub(text: str) -> str:
    """Mask ``email=`` and ``api_key=`` query parameters wherever they appear in text.

    Exception messages from the HTTP library contain the full request URL, in which the address
    is URL-encoded (``%40``). Masking the parameters works whatever the encoding.
    """
    return _SECRET_PARAM.sub(lambda m: f"{m.group(1)}=<redacted>", text)


@dataclass(frozen=True)
class Credentials:
    """Identification NCBI asks every API user to provide."""

    email: str
    api_key: str | None = None

    def redact(self, text: str) -> str:
        """Remove the API key and e-mail address, in any URL encoding, from text to be logged."""
        out = scrub(text)
        for secret, mask in ((self.api_key, "***"), (self.email, "<email>")):
            if not secret:
                continue
            for variant in {
                secret,
                quote(secret, safe=""),
                quote_plus(secret),
                quote(secret, safe="").lower(),
            }:
                out = out.replace(variant, mask)
        return out


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
