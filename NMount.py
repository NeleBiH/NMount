#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NMount - simple ISO mounter with tray, DnD, installer, autostart, i18n, themes,
one-click polkit 'Fix permissions', desktop shortcut, Help/License popups,
'last mounted' persistence/restore, Ubuntu isohybrid mount fix,
failsafe unmount on uninstall, and graceful self-termination on uninstall.

Default UI language: English. Live language & theme switching.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
import getpass
import signal
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QLineEdit, QMessageBox, QFrame,
    QCheckBox, QGroupBox, QComboBox, QToolButton, QStyle, QSizePolicy
)

# ---------------- App identity & paths ----------------
APP_NAME = "NMount"

HOME = Path.home()
BIN_DIR = HOME / ".local" / "bin"
APP_BIN = BIN_DIR / "nmount"
APPS_DIR = HOME / ".local" / "share" / "applications"
APP_LAUNCHER = APPS_DIR / "nmount.desktop"

# Desktop shortcut (KDE/GNOME, etc.)
USER_DESKTOP_DIR = HOME / "Desktop"
DESKTOP_SHORTCUT = USER_DESKTOP_DIR / "NMount.desktop"

CONF_DIR = HOME / ".config" / "nmount"
CONF_FILE = CONF_DIR / "config.json"

AUTOSTART_DIR = HOME / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "nmount.desktop"

CACHE_DIR = HOME / ".cache" / "nmount"
FALLBACK_ICON = CACHE_DIR / "icon.svg"

DEFAULT_MOUNT_BASE = HOME / "mnt" / "nmount"

# Polkit rule we manage
POLKIT_RULE_DST = Path("/etc/polkit-1/rules.d/90-nmount.rules")
POLKIT_RULE_MARK = "# Managed by NMount"

# Tools
PKEXEC = shutil.which("pkexec")
UDISKSCTL = shutil.which("udisksctl")
LOSETUP = shutil.which("losetup")

# License (auto-chosen for this code)
LICENSE_NAME = "MIT License"
LICENSE_URL = "https://opensource.org/license/mit/"
PY_SIDE_LICENSE_URL = "https://doc.qt.io/qtforpython/licenses.html"
UDISKS_LICENSE_URL = "https://gitlab.freedesktop.org/udisks/udisks/-/blob/master/COPYING"
POLKIT_LICENSE_URL = "https://gitlab.freedesktop.org/polkit/polkit/-/blob/master/COPYING"

# ---------------- Utilities ----------------
def run(cmd, capture=True):
    """Run command, return (rc, stdout, stderr)."""
    try:
        if capture:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            return p.returncode, p.stdout.strip(), p.stderr.strip()
        else:
            p = subprocess.run(cmd)
            return p.returncode, "", ""
    except Exception as e:
        return 1, "", str(e)

def open_url(url: str):
    try:
        QDesktopServices.openUrl(QUrl(url))
    except Exception:
        pass

# ---- Mount state helpers ----
def is_path_mounted(path: str) -> bool:
    """Quick /proc/mounts check."""
    try:
        with open("/proc/mounts","r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == path:
                    return True
    except Exception:
        pass
    return False

def list_child_partitions(loop_dev: str):
    """Return list of /dev/loopXpN partitions for given loop dev (if any)."""
    rc, out, err = run(["lsblk", "-nrpo", "TYPE,PATH", loop_dev])
    parts = []
    if rc == 0 and out.strip():
        for line in out.splitlines():
            t, path = line.strip().split()
            if t == "part":
                parts.append(path)
    return parts

def pick_mountable_block(base_loop_dev: str) -> str:
    """Pick a mountable block: prefer partition with iso9660/udf/vfat/... else base loop."""
    try:
        rc, out, err = run(["lsblk", "-nrpo", "FSTYPE,PATH", base_loop_dev])
        if rc == 0 and out.strip():
            candidates = []
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    fstype, path = parts[0], parts[1]
                    if fstype and fstype != "-":
                        candidates.append((fstype.lower(), path))
            prefer = ["iso9660", "udf", "vfat", "squashfs", "ext4", "ext3", "ext2"]
            for want in prefer:
                for fstype, path in candidates:
                    if fstype == want:
                        return path
            if candidates:
                return candidates[0][1]
    except Exception:
        pass
    return base_loop_dev

# ---------------- i18n (English default) ----------------
TR = {
    "en": {
        "browse": "Browse…",
        "drop_hint": "Drop .iso here or click “Browse…”",
        "mount": "Mount",
        "unmount": "Unmount",
        "options": "Options",
        "autostart": "Autostart on login",
        "install": "Install",
        "uninstall": "Uninstall",
        "ready": "Ready.",
        "selected_iso": "Selected ISO: {path}",
        "installed": "Installed.",
        "uninstalled": "Uninstalled.",
        "confirm_uninstall": "Are you sure you want to uninstall?",
        "no_iso": "No ISO selected.",
        "bad_path": "Path invalid or file does not exist.",
        "already_mounted": "Something is already mounted. Unmount first.",
        "loop_setup_fail": "loop-setup failed: {msg}",
        "no_loop_device": "Loop device not found in output: {out}",
        "mount_fail": "Mount failed: {msg}",
        "unmount_fail": "Unmount failed: {msg}",
        "loop_delete_fail": "Loop delete failed: {msg}",
        "losetup_fail": "losetup failed (need sudo?): {msg}",
        "losetup_delete_fail": "losetup -d failed: {msg}",
        "mounted_to": "Mounted {name} -> {mp}",
        "unmount_ok": "Unmount OK.",
        "tray_running": "Running in background (system tray).",
        "show": "Show",
        "exit": "Exit",
        "preferences": "Preferences",
        "language": "Language",
        "theme": "Theme",
        "file_filter": "ISO Files (*.iso)",
        "pick_iso_title": "Pick ISO",
        "ready_to_mount": "Ready to mount.",
        "not_ready": "Not ready: Fix permissions first.",
        "restored_mount": "Restored previous mount: {mp}",
        "fixperms": "Fix permissions",
        "fixperms_hint": "Installs a PolicyKit rule for your user so NMount can set up loop devices and mount ISOs without repeated passwords.",
        "fixperms_ok": "Permissions fixed (polkit rule installed).",
        "fixperms_exists": "Permissions already configured.",
        "fixperms_need_pkexec": "pkexec not found; run as root:\n{cmd}",
        "fixperms_failed": "Failed to install polkit rule: {err}",
        "help": "Help",
        "license": "License",
        "why": "Why?",
        "why_fix_title": "Why 'Fix permissions'?",
        "why_fix_text": (
            "NMount uses 'udisksctl' (udisks2) to set up loop devices and mount ISO files.\n"
            "By default, these actions may require authentication (root). The 'Fix permissions' button installs a "
            "small PolicyKit rule that grants your current user permission to perform only these specific udisks "
            "actions while you are logged in locally. This avoids repeated password prompts.\n\n"
            "• Location: /etc/polkit-1/rules.d/90-nmount.rules\n"
            "• Scope: current user only; local active session\n"
            "• Actions: org.freedesktop.udisks2.loop-setup, filesystem-mount*, unmount-others\n\n"
            "Uninstall removes this rule. You can also remove it manually with:\n"
            "  sudo rm /etc/polkit-1/rules.d/90-nmount.rules"
        ),
        "help_title": "NMount – Help",
        "help_text": (
            "• Browse / Drop: choose an .iso file via dialog or drag-and-drop.\n"
            "• Mount: creates a read-only loop device and mounts it via udisks.\n"
            "• Unmount: unmounts and deletes the loop device.\n"
            "• Autostart on login: create/remove an autostart entry under ~/.config/autostart.\n"
            "• Install / Uninstall: install to ~/.local/bin and application menu, also place a Desktop shortcut. "
            "Uninstall cleans up created files and will close the app.\n"
            "• Fix permissions: installs a PolicyKit rule so udisks operations don't prompt for a password.\n"
            "• Language / Theme: instant UI updates, including tray menu."
        ),
        "license_title": "License",
        "license_text": (
            f"NMount source code is released under the {LICENSE_NAME}.\n"
            f"License: {LICENSE_URL}\n\n"
            "Third-party tools/licenses:\n"
            f"• PySide6 / Qt: {PY_SIDE_LICENSE_URL}\n"
            f"• udisks2: {UDISKS_LICENSE_URL}\n"
            f"• polkit: {POLKIT_LICENSE_URL}\n"
        ),
        "uninstall_quit_title": "Uninstalling",
        "uninstall_quit_text": "The app will exit now because you removed it.",
    },
    "hr": {
        "browse": "Odaberi…",
        "drop_hint": "Dovuci .iso ovdje ili klikni „Odaberi…“",
        "mount": "Mount",
        "unmount": "Unmount",
        "options": "Opcije",
        "autostart": "Autostart pri prijavi",
        "install": "Instaliraj",
        "uninstall": "Deinstaliraj",
        "ready": "Spremno.",
        "selected_iso": "Izabran ISO: {path}",
        "installed": "Instalirano.",
        "uninstalled": "Deinstalirano.",
        "confirm_uninstall": "Sigurno želiš deinstalirati?",
        "no_iso": "Nisi izabrao ISO.",
        "bad_path": "Putanja ne valja ili fajl ne postoji.",
        "already_mounted": "Već je nešto montirano. Prvo Unmount.",
        "loop_setup_fail": "loop-setup greška: {msg}",
        "no_loop_device": "Nisam našao loop device u outputu: {out}",
        "mount_fail": "Mount greška: {msg}",
        "unmount_fail": "Unmount greška: {msg}",
        "loop_delete_fail": "Loop delete greška: {msg}",
        "losetup_fail": "losetup greška (treba sudo?): {msg}",
        "losetup_delete_fail": "losetup -d greška: {msg}",
        "mounted_to": "Mounted {name} -> {mp}",
        "unmount_ok": "Unmount OK.",
        "tray_running": "Radi u pozadini (system tray).",
        "show": "Prikaži",
        "exit": "Izlaz",
        "preferences": "Postavke",
        "language": "Jezik",
        "theme": "Tema",
        "file_filter": "ISO datoteke (*.iso)",
        "pick_iso_title": "Odaberi ISO",
        "ready_to_mount": "Spremno za mount.",
        "not_ready": "Nije spremno: prvo Sredi dozvole.",
        "restored_mount": "Vraćen prijašnji mount: {mp}",
        "fixperms": "Sredi dozvole",
        "fixperms_hint": "Instalira PolicyKit pravilo za tvog korisnika kako bi NMount mogao podešavati loop uređaje i montirati ISO bez ponovnog traženja lozinke.",
        "fixperms_ok": "Dozvole sređene (polkit pravilo instalirano).",
        "fixperms_exists": "Dozvole su već podešene.",
        "fixperms_need_pkexec": "Nema pkexec; pokreni kao root:\n{cmd}",
        "fixperms_failed": "Greška pri instalaciji polkit pravila: {err}",
        "help": "Pomoć",
        "license": "Licenca",
        "why": "Zašto?",
        "why_fix_title": "Zašto 'Sredi dozvole'?",
        "why_fix_text": (
            "NMount koristi 'udisksctl' (udisks2) za loop uređaje i montiranje ISO-a.\n"
            "Standardno za te akcije treba autentikacija (root). 'Sredi dozvole' instalira "
            "malo PolicyKit pravilo koje tvom korisniku dopušta baš te udisks akcije dok si lokalno prijavljen. "
            "Tako nema stalnog traženja lozinke.\n\n"
            "• Lokacija: /etc/polkit-1/rules.d/90-nmount.rules\n"
            "• Opseg: samo trenutni korisnik; lokalna aktivna sesija\n"
            "• Akcije: org.freedesktop.udisks2.loop-setup, filesystem-mount*, unmount-others\n\n"
            "Deinstalacija briše ovo pravilo. Možeš ga obrisati i ručno:\n"
            "  sudo rm /etc/polkit-1/rules.d/90-nmount.rules"
        ),
        "help_title": "NMount – Pomoć",
        "help_text": (
            "• Odaberi / DnD: izaberi .iso preko dijaloga ili povuci u prozor.\n"
            "• Mount: napravi read-only loop uređaj i montira ga preko udisksa.\n"
            "• Unmount: odmontira i obriše loop uređaj.\n"
            "• Autostart pri prijavi: doda/ukloni autostart u ~/.config/autostart.\n"
            "• Instaliraj / Deinstaliraj: instalira u ~/.local/bin i u izbornik aplikacija, te stavi prečac na Desktop. "
            "Deinstalacija počisti i zatvara aplikaciju.\n"
            "• Sredi dozvole: instalira PolicyKit pravilo da udisks ne traži lozinku.\n"
            "• Jezik / Tema: promjena odmah vrijedi, uključujući tray meni."
        ),
        "license_title": "Licenca",
        "license_text": (
            f"NMount izvorni kod je objavljen pod {LICENSE_NAME}.\n"
            f"Licenca: {LICENSE_URL}\n\n"
            "Vanjske komponente/licence:\n"
            f"• PySide6 / Qt: {PY_SIDE_LICENSE_URL}\n"
            f"• udisks2: {UDISKS_LICENSE_URL}\n"
            f"• polkit: {POLKIT_LICENSE_URL}\n"
        ),
        "uninstall_quit_title": "Deinstalacija",
        "uninstall_quit_text": "Aplikacija će se sada ugasiti jer ste je uklonili.",
    },
}

# ---------------- Theme CSS ----------------
THEMES = {
    "Indigo Night": """
        QWidget { background: #111827; color: #e5e7eb; }
        QGroupBox { border: 1px solid #374151; border-radius: 12px; margin-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color:#93c5fd; }
        QPushButton { border: 1px solid #4c1d95; border-radius: 10px; padding: 6px 12px; background:#1f2937; }
        QPushButton:hover { background:#312e81; }
        QPushButton:disabled { color:#9ca3af; border-color:#374151; }
        QLineEdit { border:1px solid #374151; border-radius:10px; padding:6px 8px; background:#0b1220; }
        QCheckBox, QLabel, QComboBox { background: transparent; }
        QComboBox, QMenu { border:1px solid #374151; border-radius:10px; background:#0b1220; }
        QFrame#drop { border:2px dashed #64748b; border-radius:12px; }
    """,
    "Neon Black": """
        QWidget { background: #000000; color: #e0e0e0; }
        QGroupBox { border:1px solid #222; border-radius:12px; margin-top:12px; }
        QGroupBox::title { left:10px; padding:0 6px; color:#39ff14; }
        QPushButton { border:1px solid #00ffff; border-radius:10px; padding:6px 12px; background:#111; }
        QPushButton:hover { background:#0a0f14; }
        QLineEdit, QComboBox, QMenu { border:1px solid #00ffff; border-radius:10px; background:#0a0a0a; }
        QFrame#drop { border:2px dashed #39ff14; border-radius:12px; }
    """,
    "Nord": """
        QWidget { background:#2e3440; color:#e5e9f0; }
        QGroupBox { border:1px solid #4c566a; border-radius:12px; margin-top:12px; }
        QGroupBox::title { left:10px; padding:0 6px; color:#88c0d0; }
        QPushButton { border:1px solid #5e81ac; border-radius:10px; padding:6px 12px; background:#3b4252; }
        QPushButton:hover { background:#434c5e; }
        QLineEdit, QComboBox, QMenu { border:1px solid #4c566a; border-radius:10px; background:#3b4252; }
        QFrame#drop { border:2px dashed #81a1c1; border-radius:12px; }
    """,
    "Solarized": """
        QWidget { background:#002b36; color:#eee8d5; }
        QGroupBox { border:1px solid #073642; border-radius:12px; margin-top:12px; }
        QGroupBox::title { left:10px; padding:0 6px; color:#b58900; }
        QPushButton { border:1px solid #268bd2; border-radius:10px; padding:6px 12px; background:#073642; }
        QPushButton:hover { background:#0b3a44; }
        QLineEdit, QComboBox, QMenu { border:1px solid #586e75; border-radius:10px; background:#073642; }
        QFrame#drop { border:2px dashed #93a1a1; border-radius:12px; }
    """,
    "Light Minimal": """
        QWidget { background:#ffffff; color:#111827; }
        QGroupBox { border:1px solid #e5e7eb; border-radius:12px; margin-top:12px; }
        QGroupBox::title { left:10px; padding:0 6px; color:#6b7280; }
        QPushButton { border:1px solid #d1d5db; border-radius:10px; padding:6px 12px; background:#f9fafb; }
        QPushButton:hover { background:#f3f4f6; }
        QLineEdit, QComboBox, QMenu { border:1px solid #d1d5db; border-radius:10px; background:#ffffff; }
        QFrame#drop { border:2px dashed #9ca3af; border-radius:12px; }
    """,
    "Purple Waves": """
        QWidget { background:#1a1027; color:#f3e8ff; }
        QGroupBox { border:1px solid #5b21b6; border-radius:12px; margin-top:12px; }
        QGroupBox::title { left:10px; padding:0 6px; color:#c084fc; }
        QPushButton { border:1px solid #7c3aed; border-radius:10px; padding:6px 12px; background:#2b1644; }
        QPushButton:hover { background:#3b1c5a; }
        QLineEdit, QComboBox, QMenu { border:1px solid #7c3aed; border-radius:10px; background:#2b1644; }
        QFrame#drop { border:2px dashed #c4b5fd; border-radius:12px; }
    """,
}

# ---------------- Config helpers ----------------
def read_conf():
    if CONF_FILE.exists():
        try:
            return json.loads(CONF_FILE.read_text())
        except Exception:
            pass
    return {}

def write_conf(data: dict):
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    CONF_FILE.write_text(json.dumps(data, indent=2))

def get_mount_base_from_conf_or_default(cli_mount_base: Path | None):
    if cli_mount_base:
        return cli_mount_base
    data = read_conf()
    return Path(data.get("mount_base", DEFAULT_MOUNT_BASE))

def is_installed():
    data = read_conf()
    if data.get("installed") is True:
        files = data.get("files", [])
        return all(Path(f).exists() for f in files)
    return False

# ---------------- Autostart ----------------
def set_autostart(enabled: bool, exec_path: Path):
    data = read_conf()
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Auto start {APP_NAME} on login
Exec={exec_path}
Icon=media-optical
Terminal=false
Categories=Utility;System;
X-GNOME-Autostart-enabled=true
"""
        AUTOSTART_FILE.write_text(content)
        data["autostart"] = True
        files = set(data.get("files", []))
        files.add(str(AUTOSTART_FILE))
        data["files"] = sorted(files)
        write_conf(data)
    else:
        try:
            if AUTOSTART_FILE.exists():
                AUTOSTART_FILE.unlink()
        except Exception:
            pass
        data["autostart"] = False
        files = [f for f in data.get("files", []) if f != str(AUTOSTART_FILE)]
        data["files"] = files
        write_conf(data)

# ---------------- Icons ----------------
SVG_ICON_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
<defs><radialGradient id="g" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#ddd"/><stop offset="100%" stop-color="#9aa"/></radialGradient></defs>
<circle cx="128" cy="128" r="110" fill="url(#g)" stroke="#555" stroke-width="6"/>
<circle cx="128" cy="128" r="28" fill="#f5f5f5" stroke="#666" stroke-width="4"/>
<path d="M128 18 A110 110 0 0 1 236 126" fill="none" stroke="#fff" stroke-width="10" opacity="0.35"/>
</svg>
"""

def ensure_fallback_icon():
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not FALLBACK_ICON.exists():
            FALLBACK_ICON.write_text(SVG_ICON_CONTENT)
    except Exception:
        pass

def app_icon():
    icon = QIcon.fromTheme("media-optical")
    if icon.isNull():
        icon = QIcon.fromTheme("drive-optical")
    if icon.isNull():
        ensure_fallback_icon()
        pm = QPixmap(str(FALLBACK_ICON))
        if not pm.isNull():
            icon = QIcon(pm)
    return icon if not icon.isNull() else QIcon()

# ---------------- Desktop entries ----------------
def desktop_content(exec_path: Path):
    return f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Mount/Unmount ISO images (system tray)
Exec={exec_path}
Icon=media-optical
Terminal=false
Categories=Utility;System;
StartupNotify=false
"""

def write_desktop_file(path: Path, exec_path: Path, make_executable: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop_content(exec_path))
    if make_executable:
        path.chmod(0o755)  # KDE trusts executable desktop files
    return path

def refresh_desktop_databases():
    cmds = [
        ["update-desktop-database", str(APPS_DIR)],
        ["xdg-desktop-menu", "forceupdate"],
        ["kbuildsycoca6"],
        ["kbuildsycoca5"],
    ]
    for cmd in cmds:
        exe = shutil.which(cmd[0])
        if exe:
            run(cmd, capture=False)

# ---------------- Failsafe unmount (for uninstall) ----------------
def best_effort_unmount_if_needed():
    """Try to unmount and delete loop if last_mount shows active mount. Swallow errors."""
    data = read_conf()
    lm = data.get("last_mount") or {}
    mp = lm.get("mount_point")
    loop_dev = lm.get("loop_device")
    mdev = lm.get("mount_device") or loop_dev

    if not mp and not loop_dev:
        return

    # Is it mounted?
    if mp and not is_path_mounted(mp):
        # maybe already unmounted; still try to remove loop
        if loop_dev and UDISKSCTL:
            run([UDISKSCTL, "loop-delete", "-b", loop_dev], capture=False)
        elif loop_dev and LOSETUP:
            run([LOSETUP, "-d", loop_dev], capture=False)
        return

    # Unmount
    if mdev and UDISKSCTL:
        rc, _, _ = run([UDISKSCTL, "unmount", "-b", mdev], capture=False)
        if rc != 0 and mp:
            run(["umount", mp], capture=False)
    elif mp:
        run(["umount", mp], capture=False)

    # Delete loop
    if loop_dev and UDISKSCTL:
        run([UDISKSCTL, "loop-delete", "-b", loop_dev], capture=False)
    elif loop_dev and LOSETUP:
        run([LOSETUP, "-d", loop_dev], capture=False)

# ---------------- Installer ----------------
def install_self(mount_base: Path, keep_autostart: bool):
    """Copy self to ~/.local/bin/nmount, create launcher + Desktop shortcut, persist paths."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).resolve()
    dst = APP_BIN
    shutil.copy2(src, dst)
    dst.chmod(0o755)

    app_launcher = write_desktop_file(APP_LAUNCHER, dst, make_executable=False)
    try:
        USER_DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    desktop_shortcut = write_desktop_file(DESKTOP_SHORTCUT, dst, make_executable=True)

    data = read_conf()
    data.update({
        "installed": True,
        "mount_base": str(mount_base),
        "files": sorted({str(dst), str(app_launcher), str(desktop_shortcut)} | set(data.get("files", [])))
    })
    data.setdefault("language", data.get("language", "en"))
    data.setdefault("theme", data.get("theme", "Light Minimal"))
    write_conf(data)

    set_autostart(keep_autostart, dst)
    refresh_desktop_databases()
    return True

def uninstall_self():
    """Failsafe: unmount if mounted, then remove everything we created."""
    data = read_conf()
    files = data.get("files", [])

    # 0) Try to unmount if user zaboravio (before we nuke polkit rule)
    best_effort_unmount_if_needed()

    # 1) remove autostart
    try:
        if AUTOSTART_FILE.exists():
            AUTOSTART_FILE.unlink()
    except Exception:
        pass

    # 2) remove polkit rule we added (best-effort). Avoid stat on /etc to prevent PermissionError on some setups.
    if PKEXEC:
        run([PKEXEC, "rm", "-f", str(POLKIT_RULE_DST)], capture=False)
    else:
        try:
            if POLKIT_RULE_DST.exists():
                POLKIT_RULE_DST.unlink()
        except Exception:
            pass

    # 3) remove installed files
    for f in files:
        try:
            p = Path(f)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    # 4) try clean empty dirs
    for d in (APPS_DIR, BIN_DIR):
        try:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass

    # 5) reset config
    new_conf = {
        "installed": False,
        "mount_base": data.get("mount_base", str(DEFAULT_MOUNT_BASE)),
        "autostart": False,
        "files": [],
        "language": data.get("language", "en"),
        "theme": data.get("theme", "Light Minimal"),
        "polkit_rule": False,
        "last_mount": {},
    }
    write_conf(new_conf)
    refresh_desktop_databases()
    return True

# ---------------- Polkit rule helpers ----------------
def polkit_rule_present() -> bool:
    try:
        return POLKIT_RULE_DST.exists()
    except Exception:
        return False

def polkit_rule_text_for_user(user: str) -> str:
    return f"""// {POLKIT_RULE_MARK}
polkit.addRule(function(action, subject) {{
  function allow() {{
    return (subject.user == "{user}" && subject.active) ? polkit.Result.YES : polkit.Result.NO;
  }}
  if (action.id.indexOf("org.freedesktop.udisks2.filesystem-mount") === 0) {{
    return allow();
  }}
  if (action.id === "org.freedesktop.udisks2.filesystem-unmount-others") {{
    return allow();
  }}
  if (action.id === "org.freedesktop.udisks2.loop-setup" ||
      action.id === "org.freedesktop.udisks2.loop-delete-others" ||
      action.id === "org.freedesktop.udisks2.loop-modify-others") {{
    return allow();
  }}
}});
"""

def install_polkit_rule():
    if polkit_rule_present():
        return True, ""
    user = getpass.getuser()
    rule = polkit_rule_text_for_user(user)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_DIR / "90-nmount.rules"
    tmp.write_text(rule)
    if not PKEXEC:
        cmd = f"sudo install -m 0644 {tmp} {POLKIT_RULE_DST}"
        return False, cmd
    rc, _, err = run([PKEXEC, "install", "-m", "0644", str(tmp), str(POLKIT_RULE_DST)])
    if rc != 0:
        return False, err or "pkexec install failed"
    return True, ""

# ---------------- Drag & Drop frame ----------------
class DropFrame(QFrame):
    fileDropped = Signal(str)
    def __init__(self):
        super().__init__()
        self.setObjectName("drop")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAcceptDrops(True)
        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("padding: 16px;")
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(".iso"):
                e.acceptProposedAction()
    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(".iso"):
                self.fileDropped.emit(path)

# ---------------- Main window ----------------
class MainWindow(QWidget):
    def __init__(self, mount_base: Path):
        super().__init__()

        # Platform sanity
        if not sys.platform.startswith("linux"):
            QMessageBox.critical(self, APP_NAME, "This app works on Linux only.")
            sys.exit(2)

        conf0 = read_conf()
        self.lang = conf0.get("language", "en")
        self.theme = conf0.get("theme", "Light Minimal")

        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(720)
        self.loop_device = None
        self.mount_device = None
        self.mount_point = None
        self.mount_base = mount_base

        # internal readiness cache (to avoid race while polkit writes the file)
        self._perms_fixed = bool(conf0.get("polkit_rule")) or polkit_rule_present()

        # ====== TOP PERMISSION BAR (FULL WIDTH) ======
        self.btn_fixperms = QPushButton()
        self.btn_fixperms.clicked.connect(self.on_fix_permissions)
        self.btn_fixperms.setEnabled(not self._perms_fixed)
        self.btn_fixperms.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lbl_fix_hint = QLabel()
        self.lbl_fix_hint.setWordWrap(False)
        self.lbl_fix_hint.setStyleSheet("color: #9ca3af; padding-left: 8px;")
        self.btn_why = QToolButton()
        self.btn_why.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        self.btn_why.setAutoRaise(True)
        self.btn_why.clicked.connect(self.show_why_fix)

        # blinking setup
        self._blink_on = False
        self._orig_fix_style = self.btn_fixperms.styleSheet()
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(600)
        self.blink_timer.timeout.connect(self._tick_blink)
        self._update_blinking()

        perm_bar = QVBoxLayout()
        perm_row_btn = QHBoxLayout()
        perm_row_btn.addWidget(self.btn_fixperms, 1)
        perm_bar.addLayout(perm_row_btn)
        perm_row_hint = QHBoxLayout()
        perm_row_hint.addStretch(1)
        perm_row_hint.addWidget(self.lbl_fix_hint, 0)
        perm_row_hint.addWidget(self.btn_why, 0)
        perm_bar.addLayout(perm_row_hint)

        # ====== MAIN CONTROLS (disabled until permissions fixed) ======
        self.path_edit = QLineEdit()
        self.btn_browse = QPushButton()
        self.btn_browse.clicked.connect(self.browse_iso)

        top = QHBoxLayout()
        top.addWidget(self.path_edit)
        top.addWidget(self.btn_browse)

        self.drop = DropFrame()
        self.drop.fileDropped.connect(self.set_iso_path)

        self.btn_mount = QPushButton()
        self.btn_unmount = QPushButton()
        self.btn_unmount.setEnabled(False)
        self.btn_mount.clicked.connect(self.do_mount)
        self.btn_unmount.clicked.connect(self.do_unmount)

        row_btns = QHBoxLayout()
        row_btns.addStretch(1)
        row_btns.addWidget(self.btn_mount)
        row_btns.addWidget(self.btn_unmount)

        # Options (autostart + help + license + install/uninstall in same row)
        self.box_opts = QGroupBox()
        self.cb_autostart = QCheckBox()
        self.cb_autostart.setChecked(bool(conf0.get("autostart", False)))

        self.btn_help = QPushButton()
        self.btn_help.clicked.connect(self.show_help)
        self.btn_license = QPushButton()
        self.btn_license.clicked.connect(self.show_license)

        self.btn_install_toggle = QPushButton()
        self.btn_install_toggle.clicked.connect(self.toggle_install)
        self.update_install_btn_text()

        row_opts_top = QHBoxLayout()
        row_opts_top.addWidget(self.cb_autostart)
        row_opts_top.addStretch(1)

        row_opts_bottom = QHBoxLayout()
        row_opts_bottom.addWidget(self.btn_help)
        row_opts_bottom.addWidget(self.btn_license)
        row_opts_bottom.addWidget(self.btn_install_toggle)  # aligned with Help/License
        row_opts_bottom.addStretch(1)

        vbox_opts = QVBoxLayout()
        vbox_opts.addLayout(row_opts_top)
        vbox_opts.addLayout(row_opts_bottom)
        self.box_opts.setLayout(vbox_opts)

        # Preferences: language + theme
        self.box_prefs = QGroupBox()
        self.lbl_lang = QLabel()
        self.lbl_theme = QLabel()
        self.dd_lang = QComboBox()
        self.dd_lang.addItems(["English", "Hrvatski"])
        self.lang_index = {"en": 0, "hr": 1}
        self.dd_lang.setCurrentIndex(self.lang_index.get(self.lang, 0))
        self.dd_theme = QComboBox()
        self.dd_theme.addItems(list(THEMES.keys()))
        if self.theme in THEMES:
            self.dd_theme.setCurrentText(self.theme)

        row_prefs = QHBoxLayout()
        row_prefs.addWidget(self.lbl_lang)
        row_prefs.addWidget(self.dd_lang)
        row_prefs.addSpacing(20)
        row_prefs.addWidget(self.lbl_theme)
        row_prefs.addWidget(self.dd_theme)
        self.box_prefs.setLayout(row_prefs)

        # Status
        self.status = QLabel()
        self.status.setStyleSheet("")

        # Main layout
        layout = QVBoxLayout(self)
        layout.addLayout(perm_bar)
        layout.addLayout(top)
        layout.addWidget(self.drop)
        layout.addLayout(row_btns)
        layout.addWidget(self.box_opts)
        layout.addWidget(self.box_prefs)
        layout.addWidget(self.status)

        # Tray
        self.tray = self.build_tray()
        self.setWindowIcon(app_icon())

        # Keep tray alive even if window closed
        QApplication.instance().setQuitOnLastWindowClosed(False)

        # Connectors
        self.cb_autostart.stateChanged.connect(self.on_autostart_changed)
        self.dd_lang.currentIndexChanged.connect(self.on_language_changed)
        self.dd_theme.currentIndexChanged.connect(self.on_theme_changed)

        # Init texts & theme and try to restore last mount
        self.apply_language()
        self.apply_theme()
        self.restore_previous_mount()

        # Lock UI until perms fixed
        self.set_main_enabled(self.has_permission_rules())
        self.update_ready_status()

        # If udisksctl missing, tell user proactively
        if not UDISKSCTL:
            self.error("udisksctl not found. Install package: udisks2")
            self.btn_mount.setEnabled(False)
            self.btn_unmount.setEnabled(False)

    # ---------- Blink logic ----------
    def _tick_blink(self):
        self._blink_on = not self._blink_on
        if self._blink_on:
            self.btn_fixperms.setStyleSheet(
                "QPushButton { border:2px solid #ef4444; background:#3b1c1c; }"
            )
        else:
            self.btn_fixperms.setStyleSheet(self._orig_fix_style)

    def _update_blinking(self):
        if self.has_permission_rules():
            self.blink_timer.stop()
            self.btn_fixperms.setStyleSheet(self._orig_fix_style)
        else:
            if not self.blink_timer.isActive():
                self._blink_on = False
                self.blink_timer.start()

    # ---------- Language & Theme ----------
    def t(self, key, **kwargs):
        msg = TR.get(self.lang, TR["en"]).get(key, key)
        return msg.format(**kwargs) if kwargs else msg

    def apply_language(self):
        self.btn_fixperms.setText(self.t("fixperms"))
        self.lbl_fix_hint.setText(self.t("fixperms_hint"))
        self.btn_why.setToolTip(self.t("why_fix_title"))

        self.path_edit.setPlaceholderText(self.t("pick_iso_title"))
        self.btn_browse.setText(self.t("browse"))
        self.drop.label.setText(self.t("drop_hint"))
        self.btn_mount.setText(self.t("mount"))
        self.btn_unmount.setText(self.t("unmount"))

        self.box_opts.setTitle(self.t("options"))
        self.box_prefs.setTitle(self.t("preferences"))

        self.cb_autostart.setText(self.t("autostart"))
        self.btn_help.setText(self.t("help"))
        self.btn_license.setText(self.t("license"))
        self.update_install_btn_text()
        self.lbl_lang.setText(self.t("language"))
        self.lbl_theme.setText(self.t("theme"))

        if hasattr(self, "act_show") and hasattr(self, "act_exit"):
            self.act_show.setText(self.t("show"))
            self.act_exit.setText(self.t("exit"))
        if self.tray:
            self.tray.setToolTip(APP_NAME)

        data = read_conf()
        data["language"] = self.lang
        write_conf(data)

        self.update_ready_status()

    def apply_theme(self):
        self.theme = self.dd_theme.currentText()
        qss = THEMES.get(self.theme, "")
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)

        data = read_conf()
        data["theme"] = self.theme
        write_conf(data)

    def restore_previous_mount(self):
        data = read_conf()
        lm = data.get("last_mount") or {}
        mp = lm.get("mount_point")
        if mp and is_path_mounted(mp):
            self.loop_device = lm.get("loop_device")
            self.mount_device = lm.get("mount_device") or self.loop_device
            self.mount_point = mp
            if lm.get("iso_path"):
                self.path_edit.setText(lm.get("iso_path"))
            self.btn_mount.setEnabled(False)
            self.btn_unmount.setEnabled(True)
            self.info(self.t("restored_mount", mp=mp))

    # ---------- Readiness & locking ----------
    def has_permission_rules(self):
        if getattr(self, "_perms_fixed", False):
            return True
        try:
            if polkit_rule_present():
                return True
        except Exception:
            pass
        conf = read_conf()
        return bool(conf.get("polkit_rule"))

    def set_main_enabled(self, enabled: bool):
        for w in [self.path_edit, self.btn_browse, self.drop,
                  self.btn_mount, self.btn_unmount, self.box_opts, self.box_prefs]:
            w.setEnabled(enabled)
        if not enabled and (self.loop_device and self.mount_point):
            self.btn_unmount.setEnabled(True)

    def update_ready_status(self):
        if self.has_permission_rules():
            self.status.setText(self.t("ready_to_mount"))
        else:
            self.status.setText(self.t("not_ready"))
        self._update_blinking()

    # ---------- Common helpers ----------
    def update_install_btn_text(self):
        self.btn_install_toggle.setText(self.t("uninstall") if is_installed() else self.t("install"))

    def set_iso_path(self, path):
        self.path_edit.setText(path)
        self.status.setText(self.t("selected_iso", path=path))

    def browse_iso(self):
        fn, _ = QFileDialog.getOpenFileName(self, self.t("pick_iso_title"), str(Path.home()), self.t("file_filter"))
        if fn:
            self.set_iso_path(fn)

    def info(self, msg):
        self.status.setText(msg)
        if self.tray:
            self.tray.showMessage(APP_NAME, msg, QSystemTrayIcon.MessageIcon.Information, 2500)

    def error(self, msg):
        self.status.setText(msg)
        if self.tray:
            self.tray.showMessage(APP_NAME, msg, QSystemTrayIcon.MessageIcon.Critical, 3500)

    # ---------- Tray ----------
    def build_tray(self):
        tray = QSystemTrayIcon(app_icon(), self)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        self.act_show = QAction(self.t("show"), self)
        self.act_exit = QAction(self.t("exit"), self)
        menu.addAction(self.act_show)
        menu.addAction(self.act_exit)
        self.act_show.triggered.connect(self.show_from_tray)
        self.act_exit.triggered.connect(QApplication.instance().quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self.on_tray_activated)
        tray.show()
        return tray

    def show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_from_tray()

    # ---------- Help / License / Why ----------
    def show_why_fix(self):
        QMessageBox.information(self, self.t("why_fix_title"), self.t("why_fix_text"))

    def show_help(self):
        mb = QMessageBox(self)
        mb.setIcon(QMessageBox.Icon.Information)
        mb.setWindowTitle(self.t("help_title"))
        mb.setText(self.t("help_text"))
        mb.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        mb.exec()

    def show_license(self):
        mb = QMessageBox(self)
        mb.setIcon(QMessageBox.Icon.Information)
        mb.setWindowTitle(self.t("license_title"))
        mb.setText(self.t("license_text"))
        btn_open = mb.addButton("Open license", QMessageBox.ButtonRole.AcceptRole)
        mb.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        mb.exec()
        if mb.clickedButton() == btn_open:
            open_url(LICENSE_URL)

    # ---------- Install/Uninstall ----------
    def toggle_install(self):
        installed = is_installed()
        if installed:
            if not self.confirm(self.t("confirm_uninstall")):
                return
            QMessageBox.information(self, self.t("uninstall_quit_title"), self.t("uninstall_quit_text"))
            ok = uninstall_self()
            self.update_install_btn_text()
            if ok:
                self.info(self.t("uninstalled"))
            QTimer.singleShot(400, lambda: os.kill(os.getpid(), signal.SIGTERM))
        else:
            keep_autostart = self.cb_autostart.isChecked()
            ok = install_self(Path(self.mount_base), keep_autostart)
            if ok:
                self.info(self.t("installed"))
            self.update_install_btn_text()

    def confirm(self, text):
        return QMessageBox.question(
            self, APP_NAME, text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

    def on_autostart_changed(self, state):
        enabled = state == Qt.Checked
        exec_path = APP_BIN if is_installed() else Path(__file__).resolve()
        set_autostart(enabled, exec_path)

    # ---------- Fix permissions ----------
    def on_fix_permissions(self):
        if self.has_permission_rules():
            self.info(self.t("fixperms_exists"))
            self.btn_fixperms.setEnabled(False)
            self.set_main_enabled(True)
            self._perms_fixed = True
            self.update_ready_status()
            return

        ok, err_or_cmd = install_polkit_rule()
        if ok:
            self.info(self.t("fixperms_ok"))
            data = read_conf()
            data["polkit_rule"] = True
            write_conf(data)
            self._perms_fixed = True
            self.btn_fixperms.setEnabled(False)
            QTimer.singleShot(300, self.update_ready_status)
            self.set_main_enabled(True)
            self.update_ready_status()
        else:
            if "install -m 0644" in err_or_cmd:
                self.error(self.t("fixperms_need_pkexec", cmd=err_or_cmd))
            else:
                self.error(self.t("fixperms_failed", err=err_or_cmd))

    # ---------- Mount/Unmount ----------
    def do_mount(self):
        if not self.has_permission_rules():
            self.error(self.t("not_ready"))
            return
        iso = self.path_edit.text().strip()
        if not iso:
            self.error(self.t("no_iso"))
            return
        if not Path(iso).is_file():
            self.error(self.t("bad_path"))
            return
        if self.loop_device or self.mount_point:
            self.error(self.t("already_mounted"))
            return

        if not UDISKSCTL:
            self.error("udisksctl not found. Install udisks2.")
            return

        # Setup loop (read-only)
        rc, out, err = run([UDISKSCTL, "loop-setup", "-r", "-f", iso])
        if rc != 0:
            self.error(self.t("loop_setup_fail", msg=(err or out)))
            return

        dev = next((t.rstrip(".") for t in out.split() if t.startswith("/dev/loop")), None)
        if not dev:
            self.error(self.t("no_loop_device", out=out))
            return

        # Ensure kernel noticed partitions for isohybrid images
        for cmd in (["udevadm","settle"], ["partprobe", dev], ["blockdev","--rereadpt", dev]):
            if shutil.which(cmd[0]):
                run(cmd, capture=False)

        # Choose mountable device (prefer partition if present)
        mount_dev = pick_mountable_block(dev)

        # Mount via udisksctl
        rc2, out2, err2 = run([UDISKSCTL, "mount", "-b", mount_dev, "--options", "ro"])
        if rc2 != 0:
            # Try partitions explicitly
            parts = list_child_partitions(dev)
            mounted = False
            for part in parts:
                rc_try, out_try, err_try = run([UDISKSCTL, "mount", "-b", part, "--options", "ro"])
                if rc_try == 0:
                    mount_dev = part
                    out2, err2 = out_try, err_try
                    mounted = True
                    break
            if not mounted:
                run([UDISKSCTL, "loop-delete", "-b", dev])
                self.error(self.t("mount_fail", msg=(err2 or out2)))
                return

        # Parse "Mounted /dev/loopX at /run/media/$USER/XXXX."
        mp_auto = None
        parts = out2.split()
        if "at" in parts:
            idx = parts.index("at")
            if idx + 1 < len(parts):
                mp_auto = parts[idx + 1].rstrip(".")
        self.loop_device = dev
        self.mount_device = mount_dev
        self.mount_point = mp_auto or "(unknown)"
        self.info(self.t("mounted_to", name=Path(iso).name, mp=self.mount_point))

        # Persist last mount info
        data = read_conf()
        data["last_mount"] = {
            "iso_path": iso,
            "loop_device": dev,
            "mount_device": mount_dev,
            "mount_point": self.mount_point,
        }
        write_conf(data)

        self.btn_mount.setEnabled(False)
        self.btn_unmount.setEnabled(True)

        # Best-effort refresh for Dolphin/KDE
        for cmd in (["kioclient5","refresh","/"], ["kioclient6","refresh","/"]):
            if shutil.which(cmd[0]):
                run(cmd, capture=False)

    def do_unmount(self):
        if not (self.mount_point and self.loop_device):
            self.error(self.t("unmount_fail", msg="nothing mounted"))
            return
        dev, mp = self.loop_device, self.mount_point
        mdev = getattr(self, "mount_device", dev)

        if not UDISKSCTL:
            self.error("udisksctl not found. Install udisks2.")
            return

        rc1, _, err1 = run([UDISKSCTL, "unmount", "-b", mdev])
        if rc1 != 0:
            self.error(self.t("unmount_fail", msg=err1))
            return
        rc2, _, err2 = run([UDISKSCTL, "loop-delete", "-b", dev])
        if rc2 != 0:
            self.error(self.t("loop_delete_fail", msg=err2))
            return

        self.loop_device = None
        self.mount_device = None
        self.mount_point = None
        self.btn_unmount.setEnabled(False)
        self.btn_mount.setEnabled(True)
        self.info(self.t("unmount_ok"))

        data = read_conf()
        if data.get("last_mount"):
            data["last_mount"] = {}
            write_conf(data)

    # ---------- Window -> Tray ----------
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(APP_NAME, self.t("tray_running"), QSystemTrayIcon.MessageIcon.Information, 1800)

    # ---------- Handlers ----------
    def on_language_changed(self, idx):
        self.lang = "en" if idx == 0 else "hr"
        self.apply_language()

    def on_theme_changed(self, idx):
        self.apply_theme()

# ---------------- Entry points ----------------
def run_gui(mount_base: Path):
    app = QApplication(sys.argv)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME, "System tray not available in this session.")
        sys.exit(1)
    w = MainWindow(mount_base)
    w.setWindowIcon(app_icon())
    w.show()
    sys.exit(app.exec())

def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} – GUI ISO mounter")
    parser.add_argument("--install", action="store_true", help="Install for current user")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall what the installer created (failsafe unmount)")
    parser.add_argument("--mount-base", type=str, default=None, help="Base directory for mount points (not used by udisks)")
    args = parser.parse_args()

    mount_base = get_mount_base_from_conf_or_default(Path(args.mount_base) if args.mount_base else None)

    if args.install and args.uninstall:
        print("Choose either --install or --uninstall, not both.")
        sys.exit(2)

    if args.install:
        install_self(mount_base, keep_autostart=read_conf().get("autostart", False))
        print(f"Installed to {APP_BIN}\nMenu launcher: {APP_LAUNCHER}\nDesktop shortcut: {DESKTOP_SHORTCUT}\nConfig: {CONF_FILE}")
        sys.exit(0)

    if args.uninstall:
        uninstall_self()
        print("Uninstalled.")
        sys.exit(0)

    run_gui(mount_base)

if __name__ == "__main__":
    main()
