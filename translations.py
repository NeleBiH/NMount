#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation strings for NMount application.
"""

# License constants
LICENSE_NAME = "MIT License"
LICENSE_URL = "https://opensource.org/license/mit/"
PY_SIDE_LICENSE_URL = "https://doc.qt.io/qtforpython/licenses.html"
UDISKS_LICENSE_URL = "https://gitlab.freedesktop.org/udisks/udisks/-/blob/master/COPYING"
POLKIT_LICENSE_URL = "https://gitlab.freedesktop.org/polkit/polkit/-/blob/master/COPYING"

TRANSLATIONS = {
    "en": {
        "browse": "Browse…",
        "scan": "Scan",
        "drop_hint": "Drop .iso here or click \"Browse…\"",
        "mount": "Mount",
        "mounting": "Mounting...",
        "unmount": "Unmount",
        "unmounting": "Unmounting...",
        "unmount_all": "Unmount All",
        "options": "Options",
        "autostart": "Autostart on login",
        "temp_mount": "Temporary mount",
        "install": "Install",
        "uninstall": "Uninstall",
        "ready": "Ready.",
        "selected_iso": "Selected ISO: {path}",
        "installed": "Installed.",
        "uninstalled": "Uninstalled.",
        "confirm_uninstall": "Are you sure you want to uninstall?",
        "no_iso": "No ISO selected.",
        "bad_path": "Path invalid or file does not exist.",
        "invalid_iso": "Selected file is not a valid ISO image.",
        "mounted_isos": "Mounted ISOs",
        "unmount_selected": "Unmount Selected",
        "open_location": "Open Location",
        "refresh": "Refresh",
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
        "found_isos": "Found ISOs",
        "pick_iso_title": "Pick ISO",
        "ready_to_mount": "Ready to mount.",
        "not_ready": "Not ready: Fix permissions first.",
        "restored_mount": "Restored previous mount: {mp}",
        "fixperms": "Fix permissions",
        "fixperms_fixed": "Permissions fixed",
        "fixperms_hint": "Installs a PolicyKit rule for your user so NMount can set up loop devices and mount ISOs without repeated passwords.",
        "fixperms_ok": "Permissions fixed (polkit rule installed).",
        "fixperms_exists": "Permissions already configured.",
        "logout_required": "User groups updated. Please log out and log back in for changes to take effect.",
        "fixperms_need_pkexec": "pkexec not found; run as root:\n{cmd}",
        "fixperms_failed": "Failed to install polkit rule: {err}",
        "help": "Help",
        "license": "License",
        "backup": "Backup",
        "restore": "Restore",
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
            f"NMount is released under the {LICENSE_NAME}.\n\n"
            f"License URL: {LICENSE_URL}\n\n"
            "The MIT License (MIT)\n"
            "Copyright © 2025 Nele_BiH (https://github.com/NeleBiH)\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy of this software "
            "and associated documentation files (the \"Software\"), to deal in the Software without restriction, "
            "including without limitation the rights to use, copy, modify, merge, publish, distribute, "
            "sublicense, and/or sell copies of the Software, and to permit persons to whom the "
            "Software is furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all copies or "
            "substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, "
            "INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR "
            "PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR "
            "ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, "
            "ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS "
            "IN THE SOFTWARE."
        ),
        "uninstall_quit_title": "Uninstalling",
        "uninstall_quit_text": "The app will exit now because you removed it.",
        # New features
        "auto_unmount": "Auto-unmount on exit",
        "open_fm": "Open Folder",
        "checksum": "Checksum",
        "no_mount_point": "No mount point selected.",
        "mount_point_not_exists": "Mount point does not exist.",
        "opened_in_fm": "Opened: {path}",
        "calculating_checksum": "Calculating checksum...",
        "cancel": "Cancel",
        "checksum_title": "Checksum Verification",
        "copy": "Copy",
        "checksum_copied": "Checksum copied to clipboard.",
        "checksum_cancelled": "Checksum calculation cancelled.",
        "checksum_error": "Checksum error: {err}",
        "recent_files": "Recent Files",
    },
    "hr": {
        "browse": "Odaberi…",
        "scan": "Skeniraj",
        "drop_hint": "Dovuci .iso ovdje ili klikni \"Odaberi…\"",
        "mount": "Mount",
        "mounting": "Mounting...",
        "unmount": "Unmount",
        "unmounting": "Unmounting...",
        "unmount_all": "Unmount All",
        "options": "Opcije",
        "autostart": "Autostart pri prijavi",
        "temp_mount": "Privremeni mount",
        "install": "Instaliraj",
        "uninstall": "Deinstaliraj",
        "ready": "Spremno.",
        "selected_iso": "Izabran ISO: {path}",
        "installed": "Instalirano.",
        "uninstalled": "Deinstalirano.",
        "confirm_uninstall": "Sigurno želiš deinstalirati?",
        "no_iso": "Nisi izabrao ISO.",
        "bad_path": "Putanja ne valja ili fajl ne postoji.",
        "invalid_iso": "Odabrani fajl nije validna ISO slika.",
        "mounted_isos": "Mountani ISO-ovi",
        "unmount_selected": "Odmontiraj Odabrani",
        "open_location": "Otvori Lokaciju",
        "refresh": "Osvježi",
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
        "found_isos": "Pronađeni ISO-ovi",
        "pick_iso_title": "Odaberi ISO",
        "ready_to_mount": "Spremno za mount.",
        "not_ready": "Nije spremno: prvo Sredi dozvole.",
        "restored_mount": "Vraćen prijašnji mount: {mp}",
        "fixperms": "Sredi dozvole",
        "fixperms_fixed": "Dozvole sređene",
        "fixperms_hint": "Instalira PolicyKit pravilo za tvog korisnika kako bi NMount mogao podešavati loop uređaje i montirati ISO bez ponovnog traženja lozinke.",
        "fixperms_ok": "Dozvole sređene (polkit pravilo instalirano).",
        "fixperms_exists": "Dozvole su već podešene.",
        "logout_required": "Korisničke grupe su ažurirane. Molimo odjavite se i ponovo prijavite za primjenu postavki.",
        "fixperms_need_pkexec": "Nema pkexec; pokreni kao root:\n{cmd}",
        "fixperms_failed": "Greška pri instalaciji polkit pravila: {err}",
        "help": "Pomoć",
        "license": "Licenca",
        "backup": "Backup",
        "restore": "Restore",
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
            f"NMount je objavljen pod {LICENSE_NAME}.\n\n"
            f"Licenca URL: {LICENSE_URL}\n\n"
            "The MIT License (MIT)\n"
            "Copyright © 2025 Nele_BiH (https://github.com/NeleBiH)\n\n"
            "Dopuštenje se ovim daje besplatno svakoj osobi koja dobije kopiju ovog softvera "
            "i prateće dokumentacijske datoteke (\"Software\"), da bavi s Softwareom bez ograničenja, "
            "uključujući bez ograničenja prava korištenja, kopiranja, mijenjanja, spajanja, "
            "objavljivanja, distribuiranja, podlicenciranja i/ili prodaje kopija Softwarea, te da dopusti "
            "osobama kojima je Software pružen da čine isto, pod sljedećim uvjetima:\n\n"
            "Gore navedena napomena o autorskim pravima i ova dopuštenja moraju biti uključene u sve "
            "kopije ili bitne dijelove Softwarea.\n\n"
            "SOFTWARE SE PRUŽA \"KAKAV JEST\", BEZ IKAKVIH JAMSTAVA, IZRAŽENIH ILI IMPLICITNIH, "
            "UKLJUČUJUĆI BEZ OGRANIČENJA JAMSTAVA TRGOVINE, PRIKLADNOSTI ZA ODREĐENU SVRHU I "
            "NEKRŠENJE PRAVA. U NIKAKVOM SLUČAJU AUTORI ILI VLASNICI AUTORSKIH PRAVA NEĆE BITI "
            "ODGOVORNI ZA BILO KOJI ZAHTJEV, ŠTETU ILI DRUGU ODGOVORNOST, BILO U AKCIJI UGOVORA, "
            "KRTNJE ILI DRUGČE, NASTALE IZ, VAN ILI U VEZI S SOFTWAREOM ILI KORIŠTENJEM ILI DRUGIM "
            "POSLUPOVANJIMA SOFTWAREA."
        ),
        "uninstall_quit_title": "Deinstalacija",
        "uninstall_quit_text": "Aplikacija će se sada ugasiti jer ste je uklonili.",
        # New features
        "auto_unmount": "Auto-odmontiranje pri izlazu",
        "open_fm": "Otvori mapu",
        "checksum": "Kontrolni zbroj",
        "no_mount_point": "Nema odabrane točke montiranja.",
        "mount_point_not_exists": "Točka montiranja ne postoji.",
        "opened_in_fm": "Otvoreno: {path}",
        "calculating_checksum": "Računam kontrolni zbroj...",
        "cancel": "Odustani",
        "checksum_title": "Provjera kontrolnog zbroja",
        "copy": "Kopiraj",
        "checksum_copied": "Kontrolni zbroj kopiran u međuspremnik.",
        "checksum_cancelled": "Računanje kontrolnog zbroja prekinuto.",
        "checksum_error": "Greška kontrolnog zbroja: {err}",
        "recent_files": "Nedavne datoteke",
    },
}
