#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NMount - A simple, secure Linux GUI tool for mounting/unmounting ISO images.

Features:
- Drag & drop or browse for ISO files
- System tray with Show/Exit
- Install/Uninstall to ~/.local/bin with desktop integration
- PolicyKit integration for passwordless mounting
- Mounted ISOs list with quick access
- Recent files history
- Open mount point in file manager
- SHA-256 checksum verification
- Auto-unmount on exit
- Live language switching (English/Croatian)
- Failsafe unmount on uninstall

License: MIT
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
import getpass
import signal
import hashlib
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QLineEdit, QMessageBox, QFrame,
    QCheckBox, QGroupBox, QComboBox, QListWidget, QListWidgetItem, QProgressDialog
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

# ---------------- Import translations ----------------
from translations import TRANSLATIONS, LICENSE_URL

# ---------------- Modern UI Stylesheet ----------------
MODERN_STYLESHEET = """
/* Global font and base styling */
QWidget {
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 13px;
    background-color: #1a202c;
    color: #e9ecef;
}

/* Modern button base style */
QPushButton {
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 32px;
}

QPushButton:hover {
    opacity: 0.9;
}

QPushButton:pressed {
    padding-top: 9px;
    padding-bottom: 7px;
}

QPushButton:disabled {
    opacity: 0.6;
}

/* Input fields */
QLineEdit {
    border: 2px solid #3d4450;
    border-radius: 6px;
    padding: 8px 12px;
    background-color: #2b3038;
    color: #e9ecef;
    selection-background-color: #007bff;
}

QLineEdit:focus {
    border-color: #007bff;
}

QLineEdit:disabled {
    background-color: #1e2228;
    color: #6c757d;
}

/* ComboBox */
QComboBox {
    border: 2px solid #3d4450;
    border-radius: 6px;
    padding: 6px 12px;
    background-color: #2b3038;
    color: #e9ecef;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #007bff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #2b3038;
    border: 1px solid #3d4450;
    selection-background-color: #007bff;
    color: #e9ecef;
}

/* GroupBox */
QGroupBox {
    border: 1px solid #3d4450;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    padding-top: 20px;
    background-color: #252930;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 4px;
    padding: 2px 8px;
    color: #adb5bd;
    font-weight: 600;
    font-size: 12px;
    background-color: #252930;
    border-radius: 4px;
}

/* CheckBox */
QCheckBox {
    color: #e9ecef;
    spacing: 8px;
    background: transparent;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #3d4450;
    background-color: #2b3038;
}

QCheckBox::indicator:checked {
    background-color: #007bff;
    border-color: #007bff;
}

QCheckBox::indicator:hover {
    border-color: #007bff;
}

/* Labels */
QLabel {
    color: #e9ecef;
    background: transparent;
}

/* Status bar label */
QLabel#status {
    color: #adb5bd;
    padding: 4px 8px;
    font-size: 12px;
    background: transparent;
}
"""

# Button color styles (to be applied individually)
BTN_STYLES = {
    'danger': "QPushButton { background-color: #dc3545; color: white; } QPushButton:hover { background-color: #c82333; }",
    'success': "QPushButton { background-color: #28a745; color: white; } QPushButton:hover { background-color: #218838; }",
    'info': "QPushButton { background-color: #17a2b8; color: white; } QPushButton:hover { background-color: #138496; }",
    'warning': "QPushButton { background-color: #fd7e14; color: white; } QPushButton:hover { background-color: #e96b02; }",
    'secondary': "QPushButton { background-color: #4a5568; color: white; } QPushButton:hover { background-color: #3d4450; }",
    'primary': "QPushButton { background-color: #007bff; color: white; } QPushButton:hover { background-color: #0069d9; }",
    'purple': "QPushButton { background-color: #6f42c1; color: white; } QPushButton:hover { background-color: #5e37a6; }",
}

# ---------------- Utilities ----------------
# Note: Group membership is NOT required when using polkit rules.
# The polkit rule grants udisks2 permissions directly to the user.

def run(cmd, capture=True, timeout=30):
    """Run command, return (rc, stdout, stderr)."""
    try:
        if capture:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             text=True, check=False, timeout=timeout, encoding='utf-8', errors='replace')
            return p.returncode, p.stdout.strip(), p.stderr.strip()
        else:
            p = subprocess.run(cmd, timeout=timeout, encoding='utf-8', errors='replace')
            return p.returncode, "", ""
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except UnicodeError as e:
        return 1, "", f"Encoding error: {e}"
    except (OSError, subprocess.SubprocessError) as e:
        return 1, "", str(e)

def open_url(url: str):
    try:
        QDesktopServices.openUrl(QUrl(url))
    except Exception:
        pass

def open_file_manager(path: str):
    """Open path in the default file manager."""
    try:
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    except Exception:
        # Fallback to xdg-open
        xdg = shutil.which("xdg-open")
        if xdg:
            subprocess.Popen([xdg, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def calculate_checksum(filepath: str, algorithm: str = "sha256", callback=None) -> str:
    """Calculate checksum of a file. callback(progress_percent) for progress updates."""
    hash_func = hashlib.new(algorithm)
    file_size = os.path.getsize(filepath)
    bytes_read = 0

    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192 * 16), b""):
            hash_func.update(chunk)
            bytes_read += len(chunk)
            if callback and file_size > 0:
                callback(int(bytes_read * 100 / file_size))

    return hash_func.hexdigest()

def get_recent_files() -> list:
    """Get list of recently mounted ISO files."""
    conf = read_conf()
    return conf.get("recent_files", [])

def add_to_recent_files(filepath: str, max_items: int = 10):
    """Add a file to recent files list."""
    conf = read_conf()
    recent = conf.get("recent_files", [])

    # Remove if already exists
    if filepath in recent:
        recent.remove(filepath)

    # Add to front
    recent.insert(0, filepath)

    # Keep only max_items
    recent = recent[:max_items]

    conf["recent_files"] = recent
    write_conf(conf)

# ---- Mount state helpers ----
def is_path_mounted(path: str) -> bool:
    """Quick /proc/mounts check."""
    try:
        with open("/proc/mounts", "r", encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == path:
                    return True
    except (FileNotFoundError, PermissionError, UnicodeError):
        pass
    return False

def list_child_partitions(loop_dev: str):
    """Return list of /dev/loopXpN partitions for given loop dev (if any)."""
    rc, out, err = run(["lsblk", "-nrpo", "TYPE,PATH", loop_dev])
    parts = []
    if rc == 0 and out.strip():
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            # Split on whitespace, but handle cases where there might be extra spaces
            parts_line = line.split()
            if len(parts_line) >= 2:
                t, path = parts_line[0], parts_line[1]
                if t == "part" and path.startswith("/dev/"):
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
    except (OSError, ValueError, IndexError):
        pass
    return base_loop_dev

# (duplicate imports removed - already imported at lines 65-66)



# ---------------- Config helpers ----------------
def read_conf():
    """Read configuration with backup recovery."""
    if CONF_FILE.exists():
        try:
            return json.loads(CONF_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeError):
            # Try to read backup
            backup_file = CONF_FILE.with_suffix('.json.bak')
            if backup_file.exists():
                try:
                    return json.loads(backup_file.read_text(encoding='utf-8'))
                except (json.JSONDecodeError, OSError, UnicodeError):
                    pass
            # If both fail, return default config
            return {}
    return {}

def write_conf(data: dict):
    """Write configuration atomically with backup."""
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create backup if main config exists
    if CONF_FILE.exists():
        backup_file = CONF_FILE.with_suffix('.json.bak')
        try:
            shutil.copy2(CONF_FILE, backup_file)
        except (OSError, shutil.Error):
            pass  # Backup failure is not critical
    
    # Write to temporary file first, then atomic move
    temp_file = CONF_FILE.with_suffix('.json.tmp')
    try:
        temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        temp_file.replace(CONF_FILE)  # Atomic operation
    except Exception as e:
        # Clean up temp file if something went wrong
        if temp_file.exists():
            temp_file.unlink()
        raise e

def get_mount_base_from_conf_or_default(cli_mount_base: Path | None):
    if cli_mount_base:
        return cli_mount_base
    data = read_conf()
    return Path(data.get("mount_base", DEFAULT_MOUNT_BASE))

def is_installed():
    data = read_conf()
    if data.get("installed") is True:
        files = data.get("files", [])
        # Check if at least the main executable exists
        if files:
            return any(Path(f).exists() for f in files if f.endswith(('.AppImage', 'nmount')))
        return False
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
        except OSError:
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
    except OSError:
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

# ---------------- AppImage detection ----------------
def get_real_executable_path() -> Path:
    """Get the real executable path, handling AppImage case."""
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path and Path(appimage_path).is_file():
        return Path(appimage_path).resolve()
    return Path(__file__).resolve()

def is_running_as_appimage() -> bool:
    """Check if we're running inside an AppImage."""
    return bool(os.environ.get("APPIMAGE"))

def get_installed_appimage_path() -> Path:
    """Return the path where we install the AppImage."""
    return HOME / ".local" / "share" / "nmount" / "NMount.AppImage"

def get_installed_script_path() -> Path:
    """Return the path where we install the Python script."""
    return HOME / ".local" / "share" / "nmount" / "NMount.py"

# ---------------- Installer ----------------
def install_self(mount_base: Path, keep_autostart: bool):
    """Copy self to ~/.local/share/nmount/, create launcher + Desktop shortcut, persist paths."""
    src = get_real_executable_path()
    installed_files = []

    # Determine destination based on whether we're an AppImage or Python script
    if is_running_as_appimage():
        # Install AppImage to ~/.local/share/nmount/
        install_dir = HOME / ".local" / "share" / "nmount"
        install_dir.mkdir(parents=True, exist_ok=True)
        dst = get_installed_appimage_path()
    else:
        # Install Python scripts to ~/.local/share/nmount/
        install_dir = HOME / ".local" / "share" / "nmount"
        install_dir.mkdir(parents=True, exist_ok=True)
        dst = install_dir / "NMount.py"

        # Also copy translations.py
        translations_src = Path(__file__).resolve().parent / "translations.py"
        if translations_src.exists():
            translations_dst = install_dir / "translations.py"
            shutil.copy2(translations_src, translations_dst)
            installed_files.append(str(translations_dst))

    # Atomic copy using temporary file
    temp_dst = dst.with_suffix('.tmp')
    try:
        shutil.copy2(src, temp_dst)
        temp_dst.chmod(0o755)
        temp_dst.replace(dst)  # Atomic operation
    except Exception as e:
        if temp_dst.exists():
            temp_dst.unlink()
        raise e

    installed_files.append(str(dst))

    app_launcher = write_desktop_file(APP_LAUNCHER, dst, make_executable=False)
    try:
        USER_DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    desktop_shortcut = write_desktop_file(DESKTOP_SHORTCUT, dst, make_executable=True)

    installed_files.extend([str(app_launcher), str(desktop_shortcut)])

    data = read_conf()
    data.update({
        "installed": True,
        "mount_base": str(mount_base),
        "files": sorted(set(installed_files) | set(data.get("files", [])))
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
    except OSError:
        pass

    # 2) remove polkit rule we added (best-effort). Avoid stat on /etc to prevent PermissionError on some setups.
    if PKEXEC:
        run([PKEXEC, "rm", "-f", str(POLKIT_RULE_DST)], capture=False)
    else:
        try:
            if POLKIT_RULE_DST.exists():
                POLKIT_RULE_DST.unlink()
        except (OSError, PermissionError):
            pass

    # 3) remove installed files
    for f in files:
        try:
            p = Path(f)
            if p.exists():
                p.unlink()
        except OSError:
            pass

    # 4) try clean empty dirs (including AppImage install dir)
    install_dir = HOME / ".local" / "share" / "nmount"
    # Also remove __pycache__ if present
    pycache_dir = install_dir / "__pycache__"
    if pycache_dir.exists():
        try:
            shutil.rmtree(pycache_dir)
        except OSError:
            pass
    for d in (APPS_DIR, BIN_DIR, install_dir):
        try:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
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
    except (OSError, PermissionError):
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
    """Install polkit rule to allow udisks2 operations without password prompts."""
    if polkit_rule_present():
        return True, ""

    # Clean up any existing broken rules first
    cleanup_old_polkit_rules()

    user = getpass.getuser()
    # Sanitize username to prevent command injection
    # Valid Linux usernames: alphanumeric, underscore, hyphen
    if not user or not all(c.isalnum() or c in '_-' for c in user):
        return False, "Invalid username format"

    # Create the polkit rule (no group membership needed - polkit handles permissions)
    rule = polkit_rule_text_for_user(user)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_DIR / "90-nmount.rules"
    tmp.write_text(rule)

    if not PKEXEC:
        # Use proper command list instead of string formatting to prevent injection
        return False, ["sudo", "install", "-m", "0644", str(tmp), str(POLKIT_RULE_DST)]

    rc, _, err = run([PKEXEC, "install", "-m", "0644", str(tmp), str(POLKIT_RULE_DST)])
    if rc != 0:
        return False, err or "pkexec install failed"

    return True, ""

def cleanup_old_polkit_rules():
    """Clean up any existing NMount polkit rules that might be broken."""
    try:
        # Only attempt cleanup if we can access the directory
        if POLKIT_RULE_DST.parent.exists():
            if POLKIT_RULE_DST.exists():
                # Check if the rule contains our marker
                content = POLKIT_RULE_DST.read_text(encoding='utf-8', errors='replace')
                if POLKIT_RULE_MARK not in content:
                    # Remove broken rule
                    if PKEXEC:
                        run([PKEXEC, "rm", "-f", str(POLKIT_RULE_DST)], capture=False)
                    else:
                        # Try direct removal, but ignore permission errors
                        try:
                            POLKIT_RULE_DST.unlink()
                        except PermissionError:
                            pass
                    print("Cleaned up broken polkit rule")
    except (OSError, PermissionError):
        # Ignore cleanup errors
        pass

# ---------------- Drag & Drop frame ----------------
class DropFrame(QFrame):
    fileDropped = Signal(str)
    def __init__(self):
        super().__init__()
        self.setObjectName("drop")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QFrame#drop {
                border: 2px dashed #4a5568;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3748, stop:1 #1a202c);
                min-height: 80px;
                max-height: 150px;
            }
            QFrame#drop:hover {
                border-color: #4299e1;
                border-style: solid;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #1a202c);
            }
        """)
        self.setAcceptDrops(True)
        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            color: #a0aec0;
            font-size: 14px;
            font-weight: 500;
            padding: 24px;
            background: transparent;
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if urls:
                for url in urls:
                    path = url.toLocalFile()
                    if path and path.lower().endswith(".iso") and Path(path).is_file():
                        e.acceptProposedAction()
                        return
        e.ignore()
    
    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if urls:
                for url in urls:
                    path = url.toLocalFile()
                    if path and path.lower().endswith(".iso") and Path(path).is_file():
                        self.fileDropped.emit(path)
                        return  # Only handle first valid ISO

# ---------------- Main window ----------------
class MainWindow(QWidget):
    def __init__(self, mount_base: Path):
        super().__init__()

        # Platform sanity
        if not sys.platform.startswith("linux"):
            QMessageBox.critical(self, APP_NAME, "This app works on Linux only.")
            sys.exit(2)

        conf0 = read_conf()
        # Force English as default for new installations
        # If no language is set or it's invalid, default to English
        saved_lang = conf0.get("language", "en")
        if saved_lang in ["en", "hr"]:
            self.lang = saved_lang
        else:
            self.lang = "en"
        self.theme = "System"  # Always use system styling

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(800, 600)
        self.resize(800, 600)

        # Apply modern stylesheet
        self.setStyleSheet(MODERN_STYLESHEET)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Mount tracking - support multiple mounted ISOs
        self.mounted_isos = []  # List of dicts: {iso_path, loop_device, mount_device, mount_point}
        self.mount_base = mount_base

        # Current single mount tracking (for backward compatibility)
        self.loop_device = None
        self.mount_device = None
        self.mount_point = None

        # Settings
        self.auto_unmount_on_exit = conf0.get("auto_unmount_on_exit", True)

        # internal readiness cache (to avoid race while polkit writes the file)
        self._perms_fixed = bool(conf0.get("polkit_rule")) or polkit_rule_present()

        # ====== PERMISSIONS SECTION ======
        self.btn_fixperms = QPushButton()
        self.btn_fixperms.clicked.connect(self.on_fix_permissions)
        self.btn_fixperms.setStyleSheet(BTN_STYLES['danger'])
        self.btn_fixperms.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_why = QPushButton()
        self.btn_why.clicked.connect(self.show_why_fix)
        self.btn_why.setStyleSheet(BTN_STYLES['info'])
        self.btn_why.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_why.setFixedWidth(100)

        # blinking setup
        self._blink_on = False
        self._orig_fix_style = self.btn_fixperms.styleSheet()
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(600)
        self.blink_timer.timeout.connect(self._tick_blink)

        # Fix permissions button with why button on the right
        perm_layout = QHBoxLayout()
        perm_layout.addWidget(self.btn_fixperms, 1)  # Fix permissions takes most space (like path field)
        perm_layout.addSpacing(1)  # Spacing between buttons
        perm_layout.addWidget(self.btn_why)  # Why button on the right
        
        # ====== MAIN CONTROLS (disabled until permissions fixed) ======
        # ISO path field with browse button on the right
        self.path_edit = QLineEdit()
        self.btn_browse = QPushButton()
        self.btn_browse.clicked.connect(self.browse_iso)
        self.btn_browse.setText("Browse")
        self.btn_browse.setStyleSheet(BTN_STYLES['secondary'])
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setFixedWidth(100)

        # Horizontal layout for path field and browse button
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit, 1)  # Path field takes most space
        path_layout.addWidget(self.btn_browse)     # Browse button on the right

        # Recent files dropdown
        self.dd_recent = QComboBox()
        self.dd_recent.addItem("-- Recent Files --")
        self._populate_recent_files()
        self.dd_recent.currentIndexChanged.connect(self.on_recent_selected)

        # Drop zone below the path field
        self.drop = DropFrame()
        self.drop.fileDropped.connect(self.set_iso_path)

        # Action buttons row
        self.btn_mount = QPushButton()
        self.btn_unmount = QPushButton()
        self.btn_open_fm = QPushButton()
        self.btn_checksum = QPushButton()

        self.btn_mount.clicked.connect(self.do_mount)
        self.btn_unmount.clicked.connect(self.do_unmount)
        self.btn_open_fm.clicked.connect(self.open_in_file_manager)
        self.btn_checksum.clicked.connect(self.show_checksum)

        self.btn_unmount.setEnabled(False)
        self.btn_open_fm.setEnabled(False)

        self.btn_mount.setStyleSheet(BTN_STYLES['success'])
        self.btn_unmount.setStyleSheet(BTN_STYLES['warning'])
        self.btn_open_fm.setStyleSheet(BTN_STYLES['primary'])
        self.btn_checksum.setStyleSheet(BTN_STYLES['info'])

        for btn in [self.btn_mount, self.btn_unmount, self.btn_open_fm, self.btn_checksum]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        row_btns = QHBoxLayout()
        row_btns.addWidget(self.btn_checksum)
        row_btns.addStretch(1)
        row_btns.addWidget(self.btn_mount)
        row_btns.addWidget(self.btn_open_fm)
        row_btns.addWidget(self.btn_unmount)

        # Mounted ISOs list
        self.lbl_mounted = QLabel()
        self.mounted_list = QListWidget()
        self.mounted_list.setMinimumHeight(60)
        self.mounted_list.setMaximumHeight(100)
        self.mounted_list.setStyleSheet("""
            QListWidget {
                background-color: #2b3038;
                border: 1px solid #3d4450;
                border-radius: 6px;
                color: #e9ecef;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
            QListWidget::item:selected {
                background-color: #007bff;
            }
        """)
        self.mounted_list.itemClicked.connect(self.on_mounted_item_selected)

        # Options (simplified layout)
        self.box_opts = QGroupBox()
        self.cb_autostart = QCheckBox()
        self.cb_autostart.setChecked(bool(conf0.get("autostart", False)))
        self.cb_auto_unmount = QCheckBox()
        self.cb_auto_unmount.setChecked(self.auto_unmount_on_exit)
        self.cb_auto_unmount.stateChanged.connect(self.on_auto_unmount_changed)

        self.btn_help = QPushButton()
        self.btn_help.clicked.connect(self.show_help)
        self.btn_license = QPushButton()
        self.btn_license.clicked.connect(self.show_license)

        self.btn_install_toggle = QPushButton()
        self.btn_install_toggle.clicked.connect(self.toggle_install)
        self.update_install_btn_text()
        self.btn_help.setStyleSheet(BTN_STYLES['info'])
        self.btn_license.setStyleSheet(BTN_STYLES['info'])
        self.btn_install_toggle.setStyleSheet(BTN_STYLES['purple'])
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_license.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install_toggle.setCursor(Qt.CursorShape.PointingHandCursor)

        # Clean vertical layout
        opts_layout = QVBoxLayout()
        opts_layout.addWidget(self.cb_autostart)
        opts_layout.addWidget(self.cb_auto_unmount)
        opts_layout.addSpacing(10)
        
        # Button row
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_help)
        btn_row.addWidget(self.btn_license)
        btn_row.addWidget(self.btn_install_toggle)
        btn_row.addStretch()
        
        opts_layout.addLayout(btn_row)
        self.box_opts.setLayout(opts_layout)

        # Preferences: language only (system styling only)
        self.box_prefs = QGroupBox()
        self.lbl_lang = QLabel()
        self.dd_lang = QComboBox()
        self.dd_lang.addItems(["English", "Hrvatski"])
        self.lang_index = {"en": 0, "hr": 1}
        self.dd_lang.setCurrentIndex(self.lang_index.get(self.lang, 0))

        # Simple centered layout
        prefs_layout = QHBoxLayout()
        prefs_layout.addStretch(1)
        prefs_layout.addWidget(self.lbl_lang)
        prefs_layout.addWidget(self.dd_lang)
        prefs_layout.addStretch(1)
        self.box_prefs.setLayout(prefs_layout)

        # Status
        self.status = QLabel()
        self.status.setObjectName("status")

        # Main vertical layout with proper spacing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # Top section - permissions
        perm_layout.setSpacing(8)
        main_layout.addLayout(perm_layout)

        # ISO path section - path field with browse button
        path_layout.setSpacing(8)
        main_layout.addLayout(path_layout)

        # Recent files dropdown
        main_layout.addWidget(self.dd_recent)

        # Drop zone section - takes available space
        main_layout.addWidget(self.drop, 1)

        # Mounted ISOs list
        main_layout.addWidget(self.lbl_mounted)
        main_layout.addWidget(self.mounted_list)

        # Bottom section - buttons row (fixed height)
        row_btns.setSpacing(8)
        main_layout.addLayout(row_btns)

        # Options and preferences in horizontal row
        options_row = QHBoxLayout()
        options_row.setSpacing(12)
        options_row.addWidget(self.box_opts, 1)
        options_row.addWidget(self.box_prefs, 1)
        main_layout.addLayout(options_row)

        # Status at bottom
        main_layout.addWidget(self.status)

        # Tray
        self.tray = self.build_tray()
        self.setWindowIcon(app_icon())

        # Keep tray alive even if window closed
        # System will handle tray behavior automatically

        # Connectors
        self.cb_autostart.stateChanged.connect(self.on_autostart_changed)
        self.dd_lang.currentIndexChanged.connect(self.on_language_changed)

        # Init texts & theme and try to restore last mount
        self.apply_language()
        self.apply_theme()
        self.restore_previous_mount()

        # Initialize mounted list visibility (hidden when empty)
        self._update_mounted_list()

        # Update button state after everything is created
        self._update_permissions_button()

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
        # Only blink if permissions are NOT fixed
        if not self.has_permission_rules():
            self._blink_on = not self._blink_on
            if self._blink_on:
                # Blink state - lighter red with glow effect
                self.btn_fixperms.setStyleSheet(
                    "QPushButton { background-color: #e74c3c; color: white; border: 2px solid #ff6b6b; }"
                    "QPushButton:hover { background-color: #c0392b; }"
                )
            else:
                # Normal state - restore original red style
                self.btn_fixperms.setStyleSheet(BTN_STYLES['danger'])

    def _update_permissions_button(self):
        """Update permissions button text, color, and state based on current permissions."""
        has_perms = self.has_permission_rules()

        if has_perms:
            # Permissions are fixed - green button, disabled
            self.btn_fixperms.setText(self.t("fixperms_fixed"))
            self.btn_fixperms.setStyleSheet(BTN_STYLES['success'])
            self.btn_fixperms.setEnabled(False)
            self.btn_fixperms.setCursor(Qt.CursorShape.ArrowCursor)
            self.blink_timer.stop()
        else:
            # Permissions not fixed - red button, enabled, blinking
            self.btn_fixperms.setText(self.t("fixperms"))
            self.btn_fixperms.setStyleSheet(BTN_STYLES['danger'])
            self.btn_fixperms.setEnabled(True)
            self.btn_fixperms.setCursor(Qt.CursorShape.PointingHandCursor)
            if not self.blink_timer.isActive():
                self._blink_on = False
                self.blink_timer.start()
        
        # Update main interface based on permissions
        self.set_main_enabled(has_perms)

    def _update_blinking(self):
        self._update_permissions_button()

    # ---------- Language & Theme ----------
    def t(self, key, **kwargs):
        translations = TRANSLATIONS.get(self.lang, TRANSLATIONS["en"])
        msg = translations.get(key, key)
        if msg is None:
            msg = key
        return msg.format(**kwargs) if kwargs else msg or ""

    def apply_language(self):
        self.btn_why.setText(self.t("why"))
        self.btn_why.setToolTip(self.t("why_fix_title"))
        # Update permissions button with correct language
        self._update_permissions_button()

        self.path_edit.setPlaceholderText(self.t("pick_iso_title"))
        self.btn_browse.setText(self.t("browse"))
        self.drop.label.setText(self.t("drop_hint"))
        self.btn_mount.setText(self.t("mount"))
        self.btn_unmount.setText(self.t("unmount"))

        self.box_opts.setTitle(self.t("options"))
        self.box_prefs.setTitle(self.t("preferences"))

        self.cb_autostart.setText(self.t("autostart"))
        self.cb_auto_unmount.setText(self.t("auto_unmount"))
        self.btn_open_fm.setText(self.t("open_fm"))
        self.btn_checksum.setText(self.t("checksum"))
        self.lbl_mounted.setText(self.t("mounted_isos"))
        self.btn_help.setText(self.t("help"))
        self.btn_license.setText(self.t("license"))
        self.update_install_btn_text()
        self.lbl_lang.setText(self.t("language"))

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
        # System styling is always active - no custom stylesheets
        self.theme = "System"
        
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

            # Add to mounted ISOs list
            mount_info = {
                "iso_path": lm.get("iso_path", ""),
                "loop_device": self.loop_device,
                "mount_device": self.mount_device,
                "mount_point": mp,
            }
            self.mounted_isos.append(mount_info)

            self.btn_mount.setEnabled(False)
            self.btn_unmount.setEnabled(True)
            self.btn_open_fm.setEnabled(True)
            self.info(self.t("restored_mount", mp=mp))

    # ---------- Readiness & locking ----------
    def has_permission_rules(self):
        # Check both config and actual file existence
        # Also check internal state to catch recent changes
        if getattr(self, "_perms_fixed", False):
            return True
            
        conf = read_conf()
        config_has_rule = bool(conf.get("polkit_rule"))
        file_exists = polkit_rule_present()
        
        # Only return True if both config and file agree
        result = config_has_rule and file_exists
        
        # Update internal state to match
        self._perms_fixed = result
        
        return result

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
        """Set ISO path with validation."""
        if not path or not isinstance(path, str):
            self.error(self.t("bad_path"))
            return
        
        try:
            iso_path = Path(path).resolve()
            if not iso_path.is_file():
                self.error(self.t("bad_path"))
                return
            if not iso_path.suffix.lower() == '.iso':
                self.error(self.t("invalid_iso"))
                return
            
            self.path_edit.setText(str(iso_path))
            self.status.setText(self.t("selected_iso", path=str(iso_path)))
        except (OSError, ValueError) as e:
            self.error(self.t("bad_path"))

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
        app = QApplication.instance()
        if app:
            self.act_exit.triggered.connect(app.quit)
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
        btn_github = mb.addButton("GitHub", QMessageBox.ButtonRole.AcceptRole)
        mb.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        mb.exec()
        if mb.clickedButton() == btn_open:
            open_url(LICENSE_URL)
        elif mb.clickedButton() == btn_github:
            open_url("https://github.com/NeleBiH")

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
        enabled = state == 2
        exec_path = APP_BIN if is_installed() else Path(__file__).resolve()
        set_autostart(enabled, exec_path)

    # ---------- Fix permissions ----------
    def on_fix_permissions(self):
        if self.has_permission_rules():
            self.info(self.t("fixperms_exists"))
            self._perms_fixed = True
            self._update_permissions_button()
            self.set_main_enabled(True)
            self.update_ready_status()
            return

        ok, err_or_cmd = install_polkit_rule()
        if ok:
            self.info(self.t("fixperms_ok"))
            data = read_conf()
            data["polkit_rule"] = True
            write_conf(data)
            self._perms_fixed = True
            self._update_permissions_button()
            QTimer.singleShot(300, self.update_ready_status)
            self.set_main_enabled(True)
            self.update_ready_status()
            
            # Show logout message if groups were added
            if "groups" in str(err_or_cmd).lower():
                self.info(self.t("logout_required"))
        else:
            # err_or_cmd can be a string (error message) or list (manual command)
            if isinstance(err_or_cmd, list):
                cmd_str = " ".join(err_or_cmd)
                self.error(self.t("fixperms_need_pkexec", cmd=cmd_str))
            elif "install -m 0644" in str(err_or_cmd):
                self.error(self.t("fixperms_need_pkexec", cmd=err_or_cmd))
            else:
                self.error(self.t("fixperms_failed", err=err_or_cmd))

    # ---------- Mount/Unmount ----------
    def do_mount(self):
        if not self.has_permission_rules():
            self.error(self.t("not_ready"))
            self.error("Please click 'Fix permissions' button first.")
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

        # More robust parsing of loop device from udisksctl output
        dev = None
        for token in out.split():
            token = token.strip().rstrip(".;")
            if token.startswith("/dev/loop") and token.replace("/dev/loop", "").replace("p", "").isdigit():
                dev = token
                break
        
        if not dev:
            self.error(self.t("no_loop_device", out=out))
            return

        # Ensure kernel noticed partitions for isohybrid images
        # These commands may fail without root - that's OK, we capture and ignore errors
        for cmd in (["udevadm","settle"], ["partprobe", dev], ["blockdev","--rereadpt", dev]):
            if shutil.which(cmd[0]):
                try:
                    run(cmd, capture=True, timeout=5)  # capture=True to suppress error output
                except (OSError, subprocess.SubprocessError):
                    pass  # Ignore errors in these helper commands

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

        # Parse mount point from udisksctl output (locale-independent)
        # Output format: "Mounted /dev/loopX at /run/media/$USER/XXXX."
        # Instead of relying on "at" keyword, look for paths starting with /run or /media
        mp_auto = None
        parts = out2.split()
        for part in parts:
            cleaned = part.rstrip(".;")
            if cleaned.startswith(("/run/media/", "/media/", "/mnt/")):
                mp_auto = cleaned
                break
        # Fallback: try "at" keyword for other mount locations
        if not mp_auto and "at" in parts:
            idx = parts.index("at")
            if idx + 1 < len(parts):
                mp_auto = parts[idx + 1].rstrip(".;")
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

        # Add to mounted ISOs list
        mount_info = {
            "iso_path": iso,
            "loop_device": dev,
            "mount_device": mount_dev,
            "mount_point": self.mount_point,
        }
        self.mounted_isos.append(mount_info)
        self._update_mounted_list()

        # Add to recent files
        add_to_recent_files(iso)
        self._populate_recent_files()

        self.btn_mount.setEnabled(False)
        self.btn_unmount.setEnabled(True)
        self.btn_open_fm.setEnabled(True)

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

        # Remove from mounted ISOs list
        self.mounted_isos = [m for m in self.mounted_isos if m.get("loop_device") != dev]
        self._update_mounted_list()

        self.loop_device = None
        self.mount_device = None
        self.mount_point = None
        self.btn_unmount.setEnabled(False)
        self.btn_mount.setEnabled(True)
        self.btn_open_fm.setEnabled(len(self.mounted_isos) > 0)
        self.info(self.t("unmount_ok"))

        data = read_conf()
        if data.get("last_mount"):
            data["last_mount"] = {}
            write_conf(data)

    # ---------- Window -> Tray ----------
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if hasattr(self, 'tray') and self.tray:
            self.tray.showMessage(APP_NAME, self.t("tray_running"), QSystemTrayIcon.MessageIcon.Information, 1800)
    
    def __del__(self):
        """Cleanup resources when object is destroyed."""
        try:
            if hasattr(self, 'blink_timer') and self.blink_timer:
                self.blink_timer.stop()
            if hasattr(self, 'tray') and self.tray:
                self.tray.hide()
        except Exception:
            pass  # Ignore cleanup errors

    # ---------- Recent files ----------
    def _populate_recent_files(self):
        """Populate recent files dropdown."""
        # Clear existing items except first
        while self.dd_recent.count() > 1:
            self.dd_recent.removeItem(1)

        recent = get_recent_files()
        for filepath in recent:
            if Path(filepath).is_file():
                display_name = Path(filepath).name
                self.dd_recent.addItem(display_name, filepath)

    def on_recent_selected(self, idx):
        """Handle recent file selection."""
        if idx <= 0:
            return
        filepath = self.dd_recent.itemData(idx)
        if filepath and Path(filepath).is_file():
            self.set_iso_path(filepath)
        # Reset dropdown to header
        self.dd_recent.setCurrentIndex(0)

    # ---------- Mounted ISOs list ----------
    def _update_mounted_list(self):
        """Update the mounted ISOs list widget."""
        self.mounted_list.clear()
        for mount_info in self.mounted_isos:
            iso_name = Path(mount_info.get("iso_path", "")).name
            mount_point = mount_info.get("mount_point", "")
            item_text = f"{iso_name} → {mount_point}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, mount_info)
            self.mounted_list.addItem(item)

        # Show/hide based on whether there are mounted ISOs
        has_mounts = len(self.mounted_isos) > 0
        self.mounted_list.setVisible(has_mounts)
        self.lbl_mounted.setVisible(has_mounts)
        self.btn_open_fm.setEnabled(has_mounts)

    def on_mounted_item_selected(self, item):
        """Handle selection in mounted ISOs list."""
        mount_info = item.data(Qt.ItemDataRole.UserRole)
        if mount_info:
            # Set the path edit to the selected ISO
            self.path_edit.setText(mount_info.get("iso_path", ""))
            # Store as current for unmount/open operations
            self.loop_device = mount_info.get("loop_device")
            self.mount_device = mount_info.get("mount_device")
            self.mount_point = mount_info.get("mount_point")

    # ---------- Open in File Manager ----------
    def open_in_file_manager(self):
        """Open the current mount point in file manager."""
        if not self.mount_point:
            self.error(self.t("no_mount_point"))
            return
        if not Path(self.mount_point).exists():
            self.error(self.t("mount_point_not_exists"))
            return
        open_file_manager(self.mount_point)
        self.info(self.t("opened_in_fm", path=self.mount_point))

    # ---------- Checksum verification ----------
    def show_checksum(self):
        """Calculate and display checksum for selected ISO."""
        iso = self.path_edit.text().strip()
        if not iso:
            self.error(self.t("no_iso"))
            return
        if not Path(iso).is_file():
            self.error(self.t("bad_path"))
            return

        # Create progress dialog
        progress = QProgressDialog(self.t("calculating_checksum"), self.t("cancel"), 0, 100, self)
        progress.setWindowTitle(self.t("checksum_title"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        cancelled = [False]

        def on_cancel():
            cancelled[0] = True

        progress.canceled.connect(on_cancel)

        def progress_callback(percent):
            if cancelled[0]:
                raise InterruptedError("Cancelled")
            progress.setValue(percent)
            QApplication.processEvents()

        try:
            checksum = calculate_checksum(iso, "sha256", progress_callback)
            progress.close()

            # Show result dialog
            msg = QMessageBox(self)
            msg.setWindowTitle(self.t("checksum_title"))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(f"SHA-256:\n{checksum}")
            msg.setDetailedText(f"File: {iso}\nAlgorithm: SHA-256\nChecksum: {checksum}")

            # Add copy button
            btn_copy = msg.addButton(self.t("copy"), QMessageBox.ButtonRole.ActionRole)
            msg.addButton(QMessageBox.StandardButton.Ok)
            msg.exec()

            if msg.clickedButton() == btn_copy:
                clipboard = QApplication.clipboard()
                clipboard.setText(checksum)
                self.info(self.t("checksum_copied"))

        except InterruptedError:
            progress.close()
            self.info(self.t("checksum_cancelled"))
        except Exception as e:
            progress.close()
            self.error(self.t("checksum_error", err=str(e)))

    # ---------- Auto-unmount on exit ----------
    def on_auto_unmount_changed(self, state):
        """Handle auto-unmount checkbox change."""
        self.auto_unmount_on_exit = (state == 2)
        data = read_conf()
        data["auto_unmount_on_exit"] = self.auto_unmount_on_exit
        write_conf(data)

    def _do_auto_unmount(self):
        """Perform auto-unmount on all mounted ISOs."""
        if not self.auto_unmount_on_exit:
            return

        # Unmount all mounted ISOs
        for mount_info in list(self.mounted_isos):
            loop_dev = mount_info.get("loop_device")
            mount_dev = mount_info.get("mount_device", loop_dev)

            if mount_dev and UDISKSCTL:
                run([UDISKSCTL, "unmount", "-b", mount_dev], capture=False)
            if loop_dev and UDISKSCTL:
                run([UDISKSCTL, "loop-delete", "-b", loop_dev], capture=False)

        # Also unmount the single mount if any
        if self.loop_device:
            mdev = getattr(self, "mount_device", self.loop_device)
            if mdev and UDISKSCTL:
                run([UDISKSCTL, "unmount", "-b", mdev], capture=False)
            if UDISKSCTL:
                run([UDISKSCTL, "loop-delete", "-b", self.loop_device], capture=False)

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

    # Connect app aboutToQuit signal to auto-unmount
    app.aboutToQuit.connect(w._do_auto_unmount)

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
        install_path = get_installed_appimage_path() if is_running_as_appimage() else get_installed_script_path()
        print(f"Installed to {install_path}\nMenu launcher: {APP_LAUNCHER}\nDesktop shortcut: {DESKTOP_SHORTCUT}\nConfig: {CONF_FILE}")
        sys.exit(0)

    if args.uninstall:
        uninstall_self()
        print("Uninstalled.")
        sys.exit(0)

    run_gui(mount_base)

if __name__ == "__main__":
    main()
