# NMount

Small cross-DE Linux GUI to **mount/unmount ISO images
Program code is experimental so your cat may get angry at you for running this😸

## Features

- Drag & drop `.iso` or pick via dialog
- One-click **Mount/Unmount**
- **Tray icon** with Show / Exit
- **Autostart on login** toggle
- **Install** (copies to `~/.local/bin`, app menu entry, **Desktop shortcut**) / **Uninstall** (cleans up and exits)
- **Fix permissions** (installs a tiny PolicyKit rule for your user)
- **Live language switch**: English / Hrvatski
- **Themes**: Indigo Night, Neon Black, Nord, Solarized, Light Minimal, Purple Waves
- Remembers **last mounted** ISO and restores UI if still mounted after restart
- **Failsafe on uninstall**: tries to unmount if you forgot

<img width="898" height="463" alt="Screenshot_20250814_224238" src="https://github.com/user-attachments/assets/26be1cf0-17dc-4cd1-8a19-9490dfa2fe51" />
<img width="889" height="449" alt="Screenshot_20250814_224224" src="https://github.com/user-attachments/assets/b1a488cf-f41e-423a-8d6e-b675b6837660" />
<img width="899" height="455" alt="Screenshot_20250814_224132" src="https://github.com/user-attachments/assets/dc613370-d29e-4365-b05e-09b4c5457c4f" />


## Requirements

- Linux with a system tray (any DE: KDE, GNOME, XFCE, Cinnamon, etc.)
- Python 3.8+ (tested with 3.10/3.11/3.12/3.13)
- Packages/tools on the system:
  - `udisks2` (provides `udisksctl`)
  - `polkit` (provides `pkexec`)
  - `util-linux` (`lsblk`, `blockdev`)
  - `parted` (for `partprobe`) — optional but recommended
- Python deps:
  - `PySide6>=6.5`
---------------------------------------------------------------------------------
On Debian/Ubuntu/KDE neon:
```bash
sudo apt update
sudo apt install udisks2 policykit-1 util-linux parted
----------------------------------------------------------------------------------
Fedora:
```bash
sudo dnf install udisks2 polkit util-linux parted
----------------------------------------------------------------------------------
I use Arch btw people :D
```bash
sudo pacman -S udisks2 polkit util-linux parted
---------------------------------------------------------------------------------


