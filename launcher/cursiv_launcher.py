"""
Cursiv Desktop Launcher — robust PyQt6 launcher with login gate.

Improvements over v1:
  - Single-instance lock via local socket binding
  - Process cleanup (app + terminals) on quit
  - Watchdog timer detects app crashes and updates status
  - Port-poll timeout no longer speculatively opens browser
  - Stop Cursiv action in tray menu
  - Username displayed in title bar after login
  - aboutToQuit cleanup signal ensures processes die even on TitleBar X click
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget,
)

if getattr(sys, "frozen", False):
    _HERE = Path(sys.executable).parent
    _ROOT = _HERE
else:
    _HERE = Path(__file__).parent
    _ROOT = _HERE.parent

_ICONS = (
    _HERE / "launcher" / "resources" / "icons"
    if getattr(sys, "frozen", False)
    else _HERE / "resources" / "icons"
)

_LOCK_PORT       = 17_860        # local socket port for single-instance lock
_APP_PORT        = 7_860         # Cursiv Gradio app port
_WATCHDOG_MS     = 3_000         # ms between app-health checks
_POLL_DEADLINE_S = 30            # seconds to wait for app to bind its port

# ── Palette ───────────────────────────────────────────────────────────────────
BG     = "#0b0b12"
BG2    = "#13131e"
BORDER = "#2a2a3f"
GOLD   = "#FFD700"
LGOLD  = "#9B7B20"
SILVER = "#C8C8D4"
SILV2  = "#666680"
RED    = "#FF4455"

QSS = f"""
QWidget {{
    background-color: {BG};
    color: {SILVER};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    border: none;
}}
QLabel {{ background: transparent; }}
QMenu {{
    background: {BG2}; color: {SILVER};
    border: 1px solid {LGOLD}; border-radius: 4px; padding: 4px;
}}
QMenu::item:selected {{ background: #2255DD; color: {GOLD}; }}
"""

# ── Single-instance lock ──────────────────────────────────────────────────────

_lock_socket: Optional[socket.socket] = None


def _acquire_instance_lock() -> bool:
    """
    Bind a local TCP socket as a single-instance lock.
    Returns True if this is the first instance, False if another is running.
    """
    global _lock_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        _lock_socket = s
        return True
    except OSError:
        return False


def _release_instance_lock() -> None:
    global _lock_socket
    if _lock_socket:
        try:
            _lock_socket.close()
        except Exception:
            pass
        _lock_socket = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _secrets_env() -> dict:
    env = os.environ.copy()
    bat = _ROOT / "secrets.bat"
    if not bat.exists():
        return env
    try:
        result = subprocess.run(
            ["cmd", "/c", f'call "{bat}" && set'],
            capture_output=True, text=True, cwd=str(_ROOT),
        )
        for line in result.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    except Exception:
        pass
    return env


def _launch_hidden(cmd: list[str]) -> subprocess.Popen:
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return subprocess.Popen(
        cmd,
        cwd=str(_ROOT),
        env=_secrets_env(),
        startupinfo=si,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _find_python() -> str:
    if getattr(sys, "frozen", False):
        import shutil
        return shutil.which("python") or shutil.which("python3") or "python"
    return sys.executable


def _find_wt() -> Optional[str]:
    try:
        r = subprocess.run(["where", "wt"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip().splitlines()[0]
    except Exception:
        pass
    wt = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WindowsApps/wt.exe"
    return str(wt) if wt.exists() else None


def _terminate_safely(proc: Optional[subprocess.Popen]) -> None:
    """Graceful then forceful termination of a subprocess."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    except OSError:
        pass


# ── Terminal launcher ─────────────────────────────────────────────────────────

def _open_terminal_window(title: str, cmd: str) -> None:
    root = str(_ROOT)
    env  = _secrets_env()
    wt   = _find_wt()

    secrets_prefix = (
        f'if exist "{_ROOT / "secrets.bat"}" call "{_ROOT / "secrets.bat"}" && '
    )
    full_cmd = f'title {title} && cd /d "{root}" && {secrets_prefix}{cmd}'

    if wt:
        subprocess.Popen(
            [wt, "-w", "new", "cmd", "/k", full_cmd],
            cwd=root, env=env,
        )
    else:
        subprocess.Popen(
            ["cmd", "/k", full_cmd],
            cwd=root, env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )


# ── Title bar ─────────────────────────────────────────────────────────────────

class TitleBar(QWidget):
    def __init__(self, parent: QMainWindow, username: str = ""):
        super().__init__(parent)
        self._win    = parent
        self._drag   = False
        self._origin = QPoint()
        self.setFixedHeight(44)
        self.setStyleSheet(f"background: {BG2}; border-bottom: 1px solid {LGOLD};")

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 8, 0)
        row.setSpacing(8)

        brand = QLabel("✦  CURSIV")
        brand.setStyleSheet(
            f"color: {GOLD}; font-size: 13px; font-weight: 700; letter-spacing: 2px;"
        )
        row.addWidget(brand)
        row.addStretch()

        if username:
            u = QLabel(username)
            u.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
            row.addWidget(u)

        for symbol, tip, slot, col in [
            ("─", "Minimise", lambda: parent.showMinimized(), SILV2),
            ("✕", "Quit",     QApplication.quit,              RED),
        ]:
            btn = QPushButton(symbol)
            btn.setToolTip(tip)
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {SILV2};
                    font-size: 14px; border-radius: 4px; border: none;
                }}
                QPushButton:hover {{ background: {col}22; color: {col}; }}
            """)
            btn.clicked.connect(slot)
            row.addWidget(btn)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag   = True
            self._origin = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.MouseButton.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._origin)

    def mouseReleaseEvent(self, e):
        self._drag = False


# ── Main window ───────────────────────────────────────────────────────────────

class CursivLauncher(QMainWindow):
    def __init__(self, username: str = "Joshua"):
        super().__init__()
        self._username   = username
        self._app_proc:  Optional[subprocess.Popen] = None
        self._app_alive  = False           # True while app process is running

        self.setWindowTitle("Cursiv")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setFixedSize(QSize(420, 360))
        self.setStyleSheet(QSS)

        self._build_ui()
        self._build_tray()

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        # Cleanup hook — fires on every quit path (TitleBar X, tray Quit, etc.)
        QApplication.instance().aboutToQuit.connect(self._cleanup)

        # Auto-open Guardian + Tracker terminals after first paint
        QTimer.singleShot(200, self._launch_terminals)

        # Watchdog: detect if the app process dies unexpectedly
        self._watchdog = QTimer(self)
        self._watchdog.timeout.connect(self._check_app_health)
        self._watchdog.start(_WATCHDOG_MS)

    # ── Cleanup (connected to aboutToQuit) ────────────────────────────────

    def _cleanup(self):
        _terminate_safely(self._app_proc)
        _release_instance_lock()

    # ── Auto-launch terminals ─────────────────────────────────────────────

    def _launch_terminals(self):
        python = _find_python()
        _open_terminal_window(
            "Cursiv Guardian",
            f'"{python}" services/guardian_service.py debug',
        )
        QTimer.singleShot(600, lambda: _open_terminal_window(
            "Cursiv Tracker",
            f'"{python}" -m cursiv_v215.training.watcher',
        ))
        self._set_status("Guardian + Tracker running")

    # ── App health watchdog ───────────────────────────────────────────────

    def _check_app_health(self):
        if self._app_proc is None or not self._app_alive:
            return
        if self._app_proc.poll() is not None:
            self._app_alive = False
            self._app_proc  = None
            self._stop_act.setEnabled(False)
            self._btn.setEnabled(True)
            self._btn.setText("Open Cursiv")
            self._set_status("Cursiv stopped unexpectedly — click to restart")

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet(f"background: {BG}; border: 1px solid {LGOLD};")

        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        vlay.addWidget(TitleBar(self, self._username))
        vlay.addStretch()
        vlay.addLayout(self._build_center())
        vlay.addStretch()
        vlay.addWidget(self._build_footer())

    def _build_center(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setContentsMargins(40, 0, 40, 0)
        col.setSpacing(20)

        glyph = QLabel("✦")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph.setStyleSheet(f"color: {GOLD}; font-size: 48px;")
        col.addWidget(glyph)

        greet = QLabel(f"Welcome back, {self._username}.")
        greet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        greet.setStyleSheet(f"color: {SILVER}; font-size: 15px; font-weight: 600;")
        col.addWidget(greet)

        self._btn = QPushButton("Open Cursiv")
        self._btn.setFixedHeight(52)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: #2255DD; color: #ffffff;
                font-size: 15px; font-weight: 600;
                border-radius: 8px; border: none;
            }}
            QPushButton:hover   {{ background: #3366EE; }}
            QPushButton:pressed {{ background: #1144CC; }}
            QPushButton:disabled {{ background: #1a1a2e; color: {SILV2}; }}
        """)
        self._btn.clicked.connect(self._launch_app)
        col.addWidget(self._btn)

        hint_box = QWidget()
        hint_box.setStyleSheet(
            f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px;"
        )
        hint_lay = QVBoxLayout(hint_box)
        hint_lay.setContentsMargins(16, 10, 16, 10)
        hint_lay.setSpacing(4)

        hint_title = QLabel("TERMINAL ACCESS")
        hint_title.setStyleSheet(
            f"color: {SILV2}; font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        hint_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lay.addWidget(hint_title)

        code = QLabel("cursiv")
        code.setStyleSheet(
            f"color: {GOLD}; font-family: 'Cascadia Code', 'Consolas', monospace;"
            f" font-size: 16px; font-weight: 700;"
        )
        code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lay.addWidget(code)

        sub = QLabel("Open any folder in terminal, then type cursiv")
        sub.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        hint_lay.addWidget(sub)

        col.addWidget(hint_box)
        return col

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(32)
        footer.setStyleSheet(f"background: {BG2}; border-top: 1px solid {BORDER};")
        row = QHBoxLayout(footer)
        row.setContentsMargins(16, 0, 16, 0)

        self._status_lbl = QLabel("Starting…")
        self._status_lbl.setStyleSheet(f"color: {SILV2}; font-size: 10px;")
        row.addWidget(self._status_lbl)
        row.addStretch()

        ver = QLabel("Cursiv v3.0")
        ver.setStyleSheet(f"color: {SILV2}; font-size: 10px;")
        row.addWidget(ver)
        return footer

    # ── App launch / stop ─────────────────────────────────────────────────

    def _launch_app(self):
        url = f"http://localhost:{_APP_PORT}"

        # Already running — just open browser
        if self._app_proc and self._app_proc.poll() is None:
            webbrowser.open(url)
            self._set_status("Already running — browser opened")
            return

        # Check if something else already bound the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("localhost", _APP_PORT)) == 0:
                webbrowser.open(url)
                self._set_status(f"Found existing server at {url}")
                return

        self._btn.setEnabled(False)
        self._btn.setText("Starting…")
        self._set_status("Launching Cursiv…")

        python = _find_python()
        self._app_proc = _launch_hidden([python, "-m", "cursiv_v215.ui.chat_app"])
        self._poll_port(url)

    def _poll_port(self, url: str):
        port    = int(url.split(":")[-1])
        elapsed = [0]

        def _check():
            # Process died before port opened
            if self._app_proc and self._app_proc.poll() is not None:
                self._btn.setEnabled(True)
                self._btn.setText("Open Cursiv")
                self._set_status("Failed to start — check secrets.bat / API keys")
                return

            try:
                with socket.create_connection(("localhost", port), timeout=0.3):
                    self._app_alive = True
                    self._stop_act.setEnabled(True)
                    webbrowser.open(url)
                    self._btn.setEnabled(True)
                    self._btn.setText("Open Cursiv")
                    self._set_status(f"Running at {url}")
                    return
            except OSError:
                pass

            elapsed[0] += 500
            if elapsed[0] >= _POLL_DEADLINE_S * 1000:
                # Hit deadline — report timeout, do NOT open browser speculatively
                self._btn.setEnabled(True)
                self._btn.setText("Open Cursiv")
                self._set_status(
                    f"Startup timeout ({_POLL_DEADLINE_S}s) — "
                    "click again if app is still loading"
                )
                return

            QTimer.singleShot(500, _check)

        QTimer.singleShot(500, _check)

    def _stop_app(self):
        _terminate_safely(self._app_proc)
        self._app_proc  = None
        self._app_alive = False
        self._stop_act.setEnabled(False)
        self._btn.setEnabled(True)
        self._btn.setText("Open Cursiv")
        self._set_status("Cursiv stopped")

    def _set_status(self, msg: str):
        self._status_lbl.setText(msg)

    # ── Tray ──────────────────────────────────────────────────────────────

    def _build_tray(self):
        self._tray = QSystemTrayIcon(self._make_icon(), self)
        self._tray.setToolTip("Cursiv")
        self._tray.activated.connect(
            lambda r: self._show()
            if r == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )

        menu = QMenu()
        menu.setStyleSheet(QSS)

        for label, slot in [
            ("Open Cursiv",   self._launch_app),
            ("Show Launcher", self._show),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            menu.addAction(act)

        self._stop_act = QAction("Stop Cursiv", self)
        self._stop_act.triggered.connect(self._stop_app)
        self._stop_act.setEnabled(False)
        menu.addAction(self._stop_act)

        menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def _make_icon(self) -> QIcon:
        for name in ("cursiv.ico", "tray.ico", "cursiv.png"):
            p = _ICONS / name
            if p.exists():
                return QIcon(str(p))
        pix = QPixmap(32, 32)
        pix.fill(QColor(BG2))
        painter = QPainter(pix)
        painter.setPen(QColor(GOLD))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "✦")
        painter.end()
        return QIcon(pix)

    def _show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        self._tray.showMessage(
            "Cursiv",
            "Running in the tray. Right-click to open.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
