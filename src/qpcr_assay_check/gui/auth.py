"""The GUI's single password, its session secret and the brake on repeated failed logins.

Only a salted scrypt hash of the password is stored (Python's standard library), with the key
that signs session cookies, in ``<work>/gui/auth.json`` (mode 0600). Setting a new password also
makes a new signing key, so every open session ends.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 10
# scrypt cost: n=2**15, r=8 takes about 32 MiB and a few tenths of a second per check
_N, _R, _P, _DKLEN = 2**15, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    """``scrypt$n$r$p$salt$hash`` with a fresh 16-byte salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN, maxmem=_MAXMEM
    )
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of ``password`` against a :func:`hash_password` value."""
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r),
            p=int(p), dklen=len(base64.b64decode(expected)), maxmem=_MAXMEM,
        )  # fmt: skip
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, base64.b64decode(expected))


def check_new_password(password: str) -> str | None:
    """Why a new password is refused, or None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"use at least {MIN_PASSWORD_LENGTH} characters"
    if password.strip() != password:
        return "leading or trailing spaces are not allowed"
    return None


class AuthStore:
    """``<work>/gui/auth.json``: the password hash and the session signing key."""

    def __init__(self, work_dir: Path) -> None:
        self.path = Path(work_dir) / "gui" / "auth.json"

    def _read(self) -> dict[str, str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        return data if isinstance(data, dict) else {}

    @property
    def is_set(self) -> bool:
        data = self._read()
        return bool(data.get("password") and data.get("secret_key"))

    @property
    def secret_key(self) -> str:
        return self._read()["secret_key"]

    def verify(self, password: str) -> bool:
        encoded = self._read().get("password")
        return bool(encoded) and verify_password(password, encoded)

    def set_password(self, password: str) -> None:
        """Store a new password and a new signing key (ends every session)."""
        problem = check_new_password(password)
        if problem:
            raise ValueError(problem)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "password": hash_password(password),
            "secret_key": secrets.token_urlsafe(32),
            "set_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, self.path)
        log.info("GUI password set (%s)", self.path)


@dataclass
class LoginThrottle:
    """After ``free`` failed attempts from one client, each further attempt must wait
    2, 4, 8, ... seconds (at most ``max_wait``) after the last failure. Kept in memory: a
    restart clears it."""

    free: int = 3
    max_wait: float = 300.0
    _failures: dict[str, tuple[int, float]] = field(default_factory=dict)

    def wait(self, client: str, now: float) -> float:
        """Seconds the client must still wait before trying again (0 = may try now)."""
        n, last = self._failures.get(client, (0, 0.0))
        if n < self.free:
            return 0.0
        return max(0.0, last + min(2.0 ** (n - self.free + 1), self.max_wait) - now)

    def failed(self, client: str, now: float) -> None:
        n, _ = self._failures.get(client, (0, 0.0))
        self._failures[client] = (n + 1, now)
        log.warning("GUI: failed login from %s (%d in a row)", client, n + 1)

    def succeeded(self, client: str) -> None:
        self._failures.pop(client, None)
