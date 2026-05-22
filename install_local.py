"""
Cursiv Local Installer

Does three things:
  1. Writes `cursiv.local` → 127.0.0.1 into your hosts file
     (C:\Windows\System32\drivers\etc\hosts)
  2. Creates a Windows Task Scheduler task that starts Cursiv server on login
  3. Prints the LAN IP so you can reach it from other devices

Must be run as Administrator (right-click → Run as administrator) for
the hosts file write and Task Scheduler registration.

Run:
  python install_local.py
  python install_local.py --uninstall
  python install_local.py --port 1969
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT        = Path(__file__).resolve().parent
HOSTS_FILE  = Path(r"C:\Windows\System32\drivers\etc\hosts")
HOSTS_ENTRY = "127.0.0.1  cursiv.local"
TASK_NAME   = "CursivLocalServer"


def _is_admin() -> bool:
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def install_hosts() -> bool:
    """Add cursiv.local to hosts file if not already present."""
    try:
        text = HOSTS_FILE.read_text(encoding="utf-8")
        if "cursiv.local" in text:
            print("  ✓  cursiv.local already in hosts file")
            return True
        with HOSTS_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n{HOSTS_ENTRY}  # Cursiv substrate local server\n")
        print("  ✓  Added cursiv.local → 127.0.0.1 to hosts file")
        return True
    except PermissionError:
        print("  ✗  Hosts file write failed — run as Administrator")
        return False
    except Exception as e:
        print(f"  ✗  Hosts file error: {e}")
        return False


def remove_hosts() -> None:
    try:
        lines  = HOSTS_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
        kept   = [l for l in lines if "cursiv.local" not in l]
        HOSTS_FILE.write_text("".join(kept), encoding="utf-8")
        print("  ✓  Removed cursiv.local from hosts file")
    except Exception as e:
        print(f"  ✗  {e}")


def install_task(port: int) -> bool:
    """Register Windows Task Scheduler task to start server on login."""
    python  = sys.executable
    script  = str(ROOT / "serve_local.py")
    cmd = (
        f'schtasks /Create /F /TN "{TASK_NAME}" '
        f'/TR "\\"{python}\\" \\"{script}\\" --port {port}" '
        f'/SC ONLOGON /DELAY 0000:30 /RL HIGHEST'
    )
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓  Task '{TASK_NAME}' registered — starts at login on port {port}")
            return True
        else:
            print(f"  ✗  Task Scheduler: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  ✗  {e}")
        return False


def remove_task() -> None:
    try:
        subprocess.run(
            f'schtasks /Delete /F /TN "{TASK_NAME}"',
            shell=True, capture_output=True,
        )
        print(f"  ✓  Task '{TASK_NAME}' removed")
    except Exception as e:
        print(f"  ✗  {e}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--port", type=int, default=1969)
    parser.add_argument("--no-task", action="store_true", help="skip Task Scheduler")
    args = parser.parse_args()

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║        CURSIV LOCAL INSTALLER                        ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    if args.uninstall:
        remove_hosts()
        remove_task()
        print("\n  Cursiv local server uninstalled.\n")
        return

    if not _is_admin():
        print("  ⚠  Not running as Administrator.")
        print("  Hosts file write and Task Scheduler require elevated privileges.")
        print("  Right-click install_local.py → Run as administrator")
        print()
        print("  Continuing anyway (hosts + task may fail)...")
        print()

    ok_hosts = install_hosts()
    ok_task  = install_task(args.port) if not args.no_task else True

    lan_ip = _local_ip()
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║  ACCESS POINTS (no internet required)                ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  http://cursiv.local:{args.port:<5}  (this machine)         ║")
    print(f"  ║  http://127.0.0.1:{args.port:<5}     (this machine)         ║")
    print(f"  ║  http://{lan_ip}:{args.port:<5}  (any LAN device)      ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print("  ║  To start now:  python serve_local.py                ║")
    print("  ║  Auto-starts at login (Task Scheduler)               ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print("  No registrar. No DNS. No Google. Raw substrate hosting.")
    print()

    if not ok_hosts:
        print("  Manual hosts entry:")
        print(f"    Add this line to {HOSTS_FILE}")
        print(f"    {HOSTS_ENTRY}")
        print()


if __name__ == "__main__":
    main()
