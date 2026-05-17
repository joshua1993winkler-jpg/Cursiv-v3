"""
Temple Guardian package — Cursiv v2.1.5 defense layers.

Modules:
  temple_guardian  — centralized Robot Language Filter + pi-squared firewall
  obfuscation      — session-local adaptive label shuffling (transparent to user)
  decoys           — isolated honeytrap agents activated on detected probing
"""
from .temple_guardian import scan, scan_cli, receive_fragment, get_session_threat_level, unlock_owner_session, is_owner_session
from .obfuscation import session_fingerprint, get_route_label
from .decoys import get_decoy_response

__all__ = [
    "scan",
    "scan_cli",
    "receive_fragment",
    "get_session_threat_level",
    "unlock_owner_session",
    "is_owner_session",
    "session_fingerprint",
    "get_route_label",
    "get_decoy_response",
]
