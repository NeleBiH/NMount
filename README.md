# NMount

Small cross-DE Linux GUI to **mount/unmount ISO images** via `udisksctl`, with a **system tray**, **drag & drop**, **autostart**, **desktop shortcut**, **live language switch (EN/HR)**, themed UI, and a **one-click “Fix permissions”** (polkit rule) so you don’t get root prompts every time.

> License: MIT

<img width="898" height="463" alt="Screenshot_20250814_224238" src="https://github.com/user-attachments/assets/00e1ff5f-8e79-4b39-9f17-28011e584baa" />
<img width="889" height="449" alt="Screenshot_20250814_224224" src="https://github.com/user-attachments/assets/6790b359-875c-45cf-af5e-382a9c0b0a42" />
<img width="899" height="455" alt="Screenshot_20250814_224132" src="https://github.com/user-attachments/assets/29a418ca-d767-405e-a5f6-b64fc5f11b1f" />


---

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

---

## Requirements

- Linux with a system tray (any DE: KDE, GNOME, XFCE, Cinnamon, etc.)
- Python 3.8+ (tested with 3.10/3.11/3.12/3.13)
- System packages:
  - `udisks2` (provides `udisksctl`)
  - `polkit` (provides `pkexec`)
  - `util-linux` (`lsblk`, `blockdev`)
  - `parted` (for `partprobe`) — optional but recommended
- Python deps:
  - `PySide6>=6.5`

### Install required packages

#### Debian / Ubuntu / KDE Neon

```bash
sudo apt update
sudo apt install udisks2 policykit-1 util-linux parted
```

#### Fedora

```bash
sudo dnf install udisks2 polkit util-linux parted
```

#### I use Arch btw 😎

```bash
sudo pacman -S udisks2 polkit util-linux parted
```

---

## Install (Dev / Run from source)

```bash
git clone https://github.com/<youruser>/NMount.git
cd NMount
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python NMount.py
```

---

## “Fix permissions” (PolicyKit rule)

By default, `udisksctl` operations may require root.  
**Fix permissions** installs a small **polkit rule** to allow your logged-in user to:
- set up loop devices,
- mount filesystems,
- unmount devices

**Scope**: only your **current username**, only when **locally active**  
**Location**: `/etc/polkit-1/rules.d/90-nmount.rules`

Internally it runs:
```bash
install -m 0644 /tmp/90-nmount.rules /etc/polkit-1/rules.d/90-nmount.rules
```

Remove it manually:
```bash
sudo rm /etc/polkit-1/rules.d/90-nmount.rules
```

> The UI stays locked until permissions are fixed (big top button). It blinks to draw attention; after success the whole UI unlocks and the status reads **Ready to mount**.

---

## Installer / Uninstaller

- **Install** copies:
  - binary to `~/.local/bin/nmount`
  - app shortcut to `~/.local/share/applications/nmount.desktop`
  - desktop shortcut to `~/Desktop/NMount.desktop`
- **Autostart toggle** creates: `~/.config/autostart/nmount.desktop`
- **Uninstall**:
  - tries to unmount any mounted ISO (failsafe)
  - removes all installed files (tracked in config)
  - deletes polkit rule
  - kills the app immediately

---

## Usage

1. Start `NMount.py`
2. Click **Fix permissions** (enter password)
3. Drag a `.iso` file or click **Browse**
4. Click **Mount**
5. Click **Unmount** when done
6. Use **Install** to make it persistent

Language & Theme change instantly via dropdowns. Tray menu supports language switch too.

---

## Troubleshooting

- **udisksctl not found**  
  → Install `udisks2` (see packages above)

- **loop0 is not a mountable filesystem**  
  → Ubuntu-based ISOs use partitions. NMount now auto-detects those and mounts the right one.

- **Desktop shortcut doesn't work on KDE**  
  → KDE will ask you to **trust** it the first time. NMount marks it executable.

- **Nothing appears in Dolphin**  
  → NMount calls `kioclient5/6 refresh /`. You can also manually refresh Dolphin with F5.

- **No tray?**  
  → Use a DE with a working system tray or extension.

---

## License

MIT — see [LICENSE](LICENSE) or https://opensource.org/license/mit/

Third-party tools used: PySide6 (Qt), udisks2, polkit, standard GNU/Linux tools.
