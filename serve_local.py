"""
Cursiv Local Server — substrate-level hosting.

No registrar. No DNS. No cloud. Raw TCP on your machine.

Layers:
  /substrate/*   — RUW layer, attractor network, reservoir (beneath)
  /api/*         — board, auth, blast (at)
  /              — health + static (above)

Access:
  http://cursiv.local      (after install_local.py adds hosts entry)
  http://127.0.0.1:1969    (always works, no setup)
  http://<your-LAN-IP>:1969 (any device on your network)

Run:
  python serve_local.py
  python serve_local.py --port 80     (port 80 = no port number in URL, needs admin)
  python serve_local.py --host 0.0.0.0 --port 1969
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

# ── resolve project root ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── default port: 1969 (year ARPANET first came alive) ───────────────────────
DEFAULT_PORT = 1969
DEFAULT_HOST = "0.0.0.0"   # all interfaces — LAN + localhost


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Cursiv local substrate server")
    parser.add_argument("--host",  default=DEFAULT_HOST)
    parser.add_argument("--port",  type=int, default=DEFAULT_PORT)
    parser.add_argument("--reload", action="store_true", help="hot reload (dev)")
    args = parser.parse_args()

    lan_ip   = _local_ip()
    hostname = "cursiv.local"

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║          CURSIV — SUBSTRATE LOCAL SERVER             ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  Local:      http://127.0.0.1:{args.port:<6}                ║")
    print(f"  ║  LAN:        http://{lan_ip:<16}:{args.port:<6}         ║")
    print(f"  ║  Hostname:   http://{hostname}:{args.port:<6}              ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print("  ║  /substrate/status    RUW layer state                ║")
    print("  ║  /substrate/weave?q=  resonance query                ║")
    print("  ║  /substrate/activate  feed synthesis to substrate    ║")
    print("  ║  /api/posts           public board feed              ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print("  No registrar. No DNS. No cloud. Raw substrate hosting.")
    print()

    try:
        import uvicorn
        from cursiv_v215.web.app import app
        uvicorn.run(
            app,
            host    = args.host,
            port    = args.port,
            reload  = args.reload,
            log_level = "info",
        )
    except ImportError as e:
        print(f"  Missing dependency: {e}")
        print("  Run: pip install fastapi uvicorn[standard]")
        sys.exit(1)


if __name__ == "__main__":
    main()
