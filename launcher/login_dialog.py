"""
Cursiv Login / Setup Dialogs — PyQt6.
Integrates with cursiv_v215.guardian.access_gate (binary-fragment auth).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout,
)

BG    = "#0b0b12"
BG2   = "#13131e"
GOLD  = "#FFD700"
LGOLD = "#9B7B20"
SILV  = "#C8C8D4"
SILV2 = "#666680"
RED   = "#FF4455"
BLUE  = "#2255DD"

_QSS = f"""
QDialog, QWidget {{
    background: {BG}; color: {SILV};
    font-family: "Segoe UI", Arial, sans-serif; font-size: 13px;
}}
QLabel {{ background: transparent; }}
QLineEdit {{
    background: {BG2}; color: {SILV};
    border: 1px solid {LGOLD}; border-radius: 5px;
    padding: 6px 10px; font-size: 13px;
}}
QLineEdit:focus {{ border-color: {GOLD}; }}
QPushButton {{
    background: {BLUE}; color: #fff;
    border: none; border-radius: 6px;
    padding: 8px 20px; font-size: 13px; font-weight: 600;
}}
QPushButton:hover   {{ background: #3366EE; }}
QPushButton:pressed {{ background: #1144CC; }}
"""


class _BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setStyleSheet(_QSS)
        self.setFixedWidth(380)
        self._ok = False

    def _header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {GOLD}; font-size: 18px; font-weight: 700; letter-spacing: 2px;"
        )
        return lbl

    def _sub(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        return lbl

    def _field(self, placeholder: str, password: bool = False) -> QLineEdit:
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        if password:
            f.setEchoMode(QLineEdit.EchoMode.Password)
        return f

    def accepted_ok(self) -> bool:
        return self._ok


class SetupDialog(_BaseDialog):
    """First-run: create username + password credentials."""

    def __init__(self, parent=None):
        super().__init__("Cursiv — Create Account", parent)
        self._username_result = ""
        self._build()

    def _build(self):
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(32, 28, 32, 24)
        vlay.setSpacing(14)

        vlay.addWidget(self._header("✦  CURSIV"))
        vlay.addWidget(self._sub(
            "Create your access credentials.\n"
            "Stored securely across multiple locations."
        ))
        vlay.addSpacing(6)

        self._user = self._field("Username")
        self._pw   = self._field("Password", password=True)
        self._pw2  = self._field("Confirm password", password=True)
        self._err  = QLabel("")
        self._err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._err.setStyleSheet(f"color: {RED}; font-size: 11px;")
        self._err.setWordWrap(True)

        for w in (self._user, self._pw, self._pw2, self._err):
            vlay.addWidget(w)

        btn = QPushButton("Create Account")
        btn.clicked.connect(self._submit)
        self._pw2.returnPressed.connect(self._submit)
        vlay.addWidget(btn)

        self._user.setFocus()

    def _submit(self):
        username = self._user.text().strip()
        password = self._pw.text()
        confirm  = self._pw2.text()

        if not username:
            self._err.setText("Username cannot be empty.")
            return
        if len(password) < 4:
            self._err.setText("Password must be at least 4 characters.")
            return
        if password != confirm:
            self._err.setText("Passwords do not match.")
            self._pw2.clear()
            self._pw2.setFocus()
            return

        try:
            from cursiv_v215.guardian.access_gate import setup_credentials
            setup_credentials(username, password)
        except Exception as exc:
            self._err.setText(f"Setup error: {exc}")
            return

        self._username_result = username
        self._ok = True
        self.accept()

    def get_username(self) -> str:
        return self._username_result


class LoginDialog(_BaseDialog):
    """Standard login dialog — verifies existing credentials."""

    def __init__(self, parent=None):
        super().__init__("Cursiv — Login", parent)
        self._username_result = ""
        self._build()

    def _build(self):
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(32, 28, 32, 24)
        vlay.setSpacing(14)

        vlay.addWidget(self._header("✦  CURSIV"))
        vlay.addWidget(self._sub("Welcome back. Please authenticate."))
        vlay.addSpacing(6)

        self._user   = self._field("Username")
        self._pw     = self._field("Password", password=True)
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color: {RED}; font-size: 11px;")

        for w in (self._user, self._pw, self._status):
            vlay.addWidget(w)

        btn = QPushButton("Login")
        btn.clicked.connect(self._submit)
        self._pw.returnPressed.connect(self._submit)
        vlay.addWidget(btn)

        reset_lbl = QLabel('<a href="#" style="color:#666680;text-decoration:none;">Forgot password? Reset account</a>')
        reset_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reset_lbl.setOpenExternalLinks(False)
        reset_lbl.linkActivated.connect(self._reset)
        vlay.addWidget(reset_lbl)

        self._user.setFocus()

    def _reset(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Reset Account",
            "This will clear your saved credentials.\n"
            "Your conversation history and settings are not affected.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from cursiv_v215.guardian.access_gate import reset_credentials
            reset_credentials()
        except Exception as exc:
            self._status.setText(f"Reset error: {exc}")
            return

        setup = SetupDialog(self)
        if setup.exec() and setup.accepted_ok():
            self._username_result = setup.get_username()
            self._ok = True
            self.accept()

    def _submit(self):
        username = self._user.text().strip()
        password = self._pw.text()

        if not username or not password:
            self._status.setText("Please enter username and password.")
            return

        self._status.setText("Verifying…")

        try:
            from cursiv_v215.guardian.access_gate import verify_credentials
            verified = verify_credentials(username, password)
        except Exception as exc:
            self._status.setText(f"Auth error: {exc}")
            return

        if verified:
            self._username_result = username
            self._ok = True
            self.accept()
        else:
            self._status.setText("Invalid credentials. Please try again.")
            self._pw.clear()
            self._pw.setFocus()

    def get_username(self) -> str:
        return self._username_result
