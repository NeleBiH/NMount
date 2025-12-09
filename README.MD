# NMount

A simple, secure, and user-friendly Linux GUI tool to **mount/unmount ISO images** with system tray support.

## Features

### Core Features
- **Drag & drop** `.iso` files or pick via dialog
- **One-click Mount/Unmount** with robust error handling
- **System tray icon** with Show / Exit functionality
- **Autostart on login** toggle
- **Install/Uninstall** - copies to `~/.local/bin`, creates app menu entry and desktop shortcut

### New Features
- **Mounted ISOs list** - view all currently mounted ISOs
- **Recent files** - quick access to recently mounted ISOs
- **Open in File Manager** - open mount point directly in your file manager
- **Checksum verification** - calculate SHA-256 checksum of ISO files with progress indicator
- **Auto-unmount on exit** - automatically unmount all ISOs when closing the app

### Security & Permissions
- **Fix permissions** - installs a PolicyKit rule for passwordless mounting (secure, user-specific)
- **Command injection protection** - all shell commands are properly sanitized
- **Privilege escalation prevention** - secure handling of system operations

### User Experience
- **Live language switch**: English / Hrvatski (Croatian)
- **Modern dark theme** with clean UI
- **Remembers last mounted** ISO and restores state after restart
- **Failsafe unmount** on uninstall

## Requirements

### System Packages
- Linux with a system tray (KDE, GNOME, XFCE, Cinnamon, etc.)
- `udisks2` (provides `udisksctl`)
- `polkit` (provides `pkexec`)
- `util-linux` (`lsblk`, `blockdev`)
- `parted` (for `partprobe`) — optional but recommended

### Python Dependencies (for running from source)
- Python 3.8+
- PySide6 >= 6.5

### Installation Commands

**Debian/Ubuntu/KDE neon:**
```bash
sudo apt update
sudo apt install udisks2 policykit-1 util-linux parted
```

**Fedora:**
```bash
sudo dnf install udisks2 polkit util-linux parted
```

**Arch Linux:**
```bash
sudo pacman -S udisks2 polkit util-linux parted
```

## Usage

### AppImage (Recommended)
1. Download `NMount-x86_64.AppImage`
2. Make it executable: `chmod +x NMount-x86_64.AppImage`
3. Run: `./NMount-x86_64.AppImage`

### From Source
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the application
python3 NMount.py
```

### Installation (From Source)
```bash
# Install for current user
python3 NMount.py --install

# Uninstall completely
python3 NMount.py --uninstall
```

### First Run
1. Click **"Fix permissions"** to install PolicyKit rule (one-time setup)
2. Drag & drop an ISO file or click **"Browse"** to select one
3. Click **"Mount"** to mount the ISO
4. Use **"Open Folder"** to browse the mounted contents
5. Click **"Unmount"** when done
6. Close the window to minimize to system tray

## Troubleshooting

- **"udisksctl not found"**: Install the `udisks2` package
- **Permission denied**: Click "Fix permissions" button
- **Mount fails**: Check if the ISO file is valid and not corrupted

## License

MIT License - Copyright © 2025 Nele_BiH

See [LICENSE](https://opensource.org/license/mit/) for details.
