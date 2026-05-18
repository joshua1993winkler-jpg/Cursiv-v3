"""
Cursiv Access Gate — bcrypt credential system.
Phase slot: Structure / Security & Access

Storage:
  .cursiv/runtime/auth.hash   — bcrypt hash of the password (64 bytes, safe to store)
  .cursiv/runtime/auth.meta   — SHA-256 of username (no password info)
  .cursiv/runtime/auth.ini    — setup marker

Security model:
  bcrypt is a one-way function. The original password cannot be recovered from the
  stored hash under any circumstances. An attacker who steals auth.hash gains nothing
  actionable — they still cannot log in or recover the password without brute-forcing
  every possible input at ~250ms per attempt (enforced by rounds=12).

  This is strictly stronger than any fragmentation/distribution scheme, which only
  delays recovery rather than preventing it.
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

try:
    import bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False

_RUNTIME   = Path(__file__).parent.parent.parent / ".cursiv" / "runtime"
_HASH_FILE = _RUNTIME / "auth.hash"    # bcrypt hash (64 bytes)
_META_FILE = _RUNTIME / "auth.meta"    # SHA-256 of username (hex string)
_FLAG_FILE = _RUNTIME / "auth.ini"     # setup marker


def _ensure() -> None:
    _RUNTIME.mkdir(parents=True, exist_ok=True)


def _check_bcrypt() -> None:
    if not _BCRYPT_OK:
        raise RuntimeError(
            "bcrypt is not installed. Run:  pip install bcrypt"
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def setup_credentials(username: str, password: str) -> None:
    """
    First-run setup. Hashes the password with bcrypt (rounds=12, ~250ms) and
    stores the hash. The original password is never written anywhere.
    Call once; overwrites any existing credentials.
    """
    _check_bcrypt()
    _ensure()

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()

    _HASH_FILE.write_bytes(hashed)
    _META_FILE.write_text(username_hash, encoding="utf-8")
    _FLAG_FILE.write_text(username_hash, encoding="utf-8")


def verify_credentials(username: str, password: str) -> bool:
    """
    Login verification. Hashes the provided password and compares against the
    stored hash using bcrypt's constant-time comparison. Returns True on success.
    The original password is never stored or reconstructed anywhere.
    """
    _check_bcrypt()

    if not _META_FILE.exists() or not _HASH_FILE.exists():
        return False

    # Verify username first (constant-time)
    stored_user_hash = _META_FILE.read_text(encoding="utf-8").strip()
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(username_hash, stored_user_hash):
        return False

    # Verify password via bcrypt
    stored_hash = _HASH_FILE.read_bytes()
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
    except Exception:
        return False


def is_setup_complete() -> bool:
    """True if credentials have been configured."""
    return _FLAG_FILE.exists()


def fragment_status() -> dict[str, bool]:
    """Diagnostic: which credential files are present. No password data exposed."""
    return {
        "hash_file":  _HASH_FILE.exists(),
        "meta_file":  _META_FILE.exists(),
        "setup_flag": _FLAG_FILE.exists(),
        "bcrypt_ok":  _BCRYPT_OK,
    }
