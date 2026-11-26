"""NGlobe installer — our own UI, per-user install (no admin rights needed).

Built by build.cmd into dist\\NGlobe-Setup.exe with the app (payload.zip) inside.
Installs to %LOCALAPPDATA%\\Programs\\NGlobe, adds Start-menu/Desktop shortcuts and
an entry in Settings > Apps, and drops unins.exe next to the app.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import winreg
import zipfile
from pathlib import Path
from tkinter import filedialog

from nglobe import __version__
from nglobe.winpaths import APP, EXE, UNINSTALL_KEY, UNINSTALLER, default_install_dir, desktop_dir, start_menu_dir

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
PAYLOAD, ICON, LOGO = BASE / "payload.zip", BASE / "icon.png", BASE / "logo.png"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

BG, CARD, FG, MUTED, ACCENT, ACCENT_HOVER, ERROR = (
    "#0b1020",
    "#141b2d",
    "#e2e8f0",
    "#94a3b8",
    "#6366f1",
    "#4f46e5",
    "#f87171",
)
FONT = "Segoe UI"


# ── install steps ───────────────────────────────────────────────


def _shortcut(link: Path, target: Path, description: str) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    q = lambda p: str(p).replace("'", "''")  # noqa: E731 — PowerShell single-quote escaping
    script = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(link)}');"
        f"$s.TargetPath='{q(target)}';$s.WorkingDirectory='{q(target.parent)}';"
        f"$s.IconLocation='{q(target)},0';$s.Description='{q(description)}';$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True, creationflags=NO_WINDOW
    )


def install(target: Path, desktop: bool, progress) -> None:
    # Close a running copy so its files can be replaced; then put its proxy settings back
    subprocess.run(["taskkill", "/F", "/IM", EXE], capture_output=True, creationflags=NO_WINDOW)
    if target.name == APP and (target / EXE).exists():
        shutil.rmtree(target)  # previous version — always a folder named NGlobe that we created

    with zipfile.ZipFile(PAYLOAD) as zf:
        members = zf.infolist()
        total = sum(m.file_size for m in members) or 1
        done = 0
        for m in members:
            zf.extract(m, target)
            done += m.file_size
            progress(0.9 * done / total, "Copying files…")

    exe, unins = target / EXE, target / UNINSTALLER
    shutil.copy2(exe, unins)
    subprocess.run([str(exe), "recover"], capture_output=True, creationflags=NO_WINDOW)

    progress(0.95, "Creating shortcuts…")
    _shortcut(start_menu_dir() / f"{APP}.lnk", exe, "See where your traffic goes, live on a globe")
    _shortcut(start_menu_dir() / f"Uninstall {APP}.lnk", unins, f"Remove {APP} completely")
    if desktop:
        _shortcut(desktop_dir() / f"{APP}.lnk", exe, "See where your traffic goes, live on a globe")

    size_kb = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) // 1024
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        for name, value in {
            "DisplayName": APP,
            "DisplayVersion": __version__,
            "Publisher": APP,
            "DisplayIcon": f"{exe},0",
            "InstallLocation": str(target),
            "UninstallString": f'"{unins}"',
            "QuietUninstallString": f'"{unins}" --quiet',
            "URLInfoAbout": "https://github.com/Shashwat-Gupta57/NGlobe",
        }.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        for name, value in {"EstimatedSize": size_kb, "NoModify": 1, "NoRepair": 1}.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
    progress(1.0, "Done")


def installed_dir() -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            return Path(winreg.QueryValueEx(key, "InstallLocation")[0])
    except OSError:
        return None


def _short(path: Path) -> str:
    return str(path).replace(str(Path.home()), "~", 1)


# ── UI ──────────────────────────────────────────────────────────


class Installer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP} Setup")
        self.configure(bg=BG, padx=32, pady=28)
        self.resizable(False, False)
        self.logo = tk.PhotoImage(file=str(ICON))
        self.iconphoto(True, self.logo)
        existing = installed_dir()
        self.target = existing or default_install_dir()

        big = tk.PhotoImage(file=str(LOGO))  # light-on-transparent version of icon.png for the dark UI
        small = big.subsample(max(1, big.width() // 96))
        self.small_logo = small
        tk.Label(self, image=small, bg=BG).pack()
        tk.Label(self, text=APP, font=(FONT, 22, "bold"), fg=FG, bg=BG).pack(pady=(12, 0))
        tk.Label(
            self, text="See where your internet traffic goes, live on a globe.", font=(FONT, 10), fg=MUTED, bg=BG
        ).pack(pady=(2, 20))

        card = tk.Frame(self, bg=CARD, padx=16, pady=14)
        card.pack(fill="x")
        tk.Label(card, text="Install location", font=(FONT, 9), fg=MUTED, bg=CARD).pack(anchor="w")
        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", pady=(4, 10))
        self.path_label = tk.Label(row, text=_short(self.target), font=(FONT, 9), fg=FG, bg=CARD, anchor="w", width=46)
        self.path_label.pack(side="left", fill="x", expand=True)
        self.change_btn = self._button(row, "Change…", self._choose, primary=False)
        self.change_btn.pack(side="right")

        self.desktop = tk.BooleanVar(value=True)
        self.launch = tk.BooleanVar(value=True)
        for text, var in [("Create a desktop shortcut", self.desktop), ("Launch NGlobe when done", self.launch)]:
            tk.Checkbutton(
                card,
                text=text,
                variable=var,
                font=(FONT, 9),
                fg=FG,
                bg=CARD,
                selectcolor=BG,
                activebackground=CARD,
                activeforeground=FG,
                highlightthickness=0,
                bd=0,
            ).pack(anchor="w")

        self.bar = tk.Canvas(self, height=6, bg=CARD, highlightthickness=0)
        self.bar.pack(fill="x", pady=(20, 6))
        self.fill = self.bar.create_rectangle(0, 0, 0, 6, fill=ACCENT, width=0)
        self.status = tk.Label(
            self, text=f"Version {__version__} · about 150 MB · no admin rights needed", font=(FONT, 9), fg=MUTED, bg=BG
        )
        self.status.pack()

        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill="x", pady=(18, 0))
        self.main_btn = self._button(buttons, "Update" if existing else "Install", self._start)
        self.main_btn.pack(side="right")
        self.cancel_btn = self._button(buttons, "Cancel", self.destroy, primary=False)
        self.cancel_btn.pack(side="right", padx=(0, 8))

    def _button(self, parent: tk.Widget, text: str, command, primary: bool = True) -> tk.Button:
        bg = ACCENT if primary else CARD
        hover = ACCENT_HOVER if primary else BG
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=(FONT, 10, "bold" if primary else "normal"),
            fg=FG,
            bg=bg,
            activebackground=hover,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=18,
            pady=7,
            cursor="hand2",
        )
        btn.bind("<Enter>", lambda _: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda _: btn.configure(bg=bg))
        return btn

    def _choose(self) -> None:
        if chosen := filedialog.askdirectory(initialdir=self.target.parent, title="Choose where to install NGlobe"):
            path = Path(chosen)
            self.target = path if path.name == APP else path / APP  # always a dedicated folder
            self.path_label.configure(text=_short(self.target))

    def _progress(self, value: float, text: str) -> None:
        def update() -> None:
            self.bar.coords(self.fill, 0, 0, self.bar.winfo_width() * value, 6)
            self.status.configure(text=text, fg=MUTED)

        self.after(0, update)

    def _start(self) -> None:
        for widget in (self.main_btn, self.cancel_btn, self.change_btn):
            widget.configure(state="disabled")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            install(self.target, self.desktop.get(), self._progress)
        except Exception:  # show any failure in the window instead of vanishing
            self.after(0, lambda: self._failed(e))
            return
        self.after(0, self._done)

    def _failed(self, error: Exception) -> None:
        self.status.configure(text=f"Install failed: {error}", fg=ERROR, wraplength=420)
        for widget in (self.main_btn, self.cancel_btn, self.change_btn):
            widget.configure(state="normal")

    def _done(self) -> None:
        self.status.configure(text=f"{APP} is installed. Find it in the Start menu anytime.", fg=FG)
        self.cancel_btn.pack_forget()
        self.main_btn.configure(text="Finish", state="normal", command=self._finish)

    def _finish(self) -> None:
        if self.launch.get():
            os.startfile(self.target / EXE)  # noqa: S606 — same as a double-click
        self.destroy()


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
    except (AttributeError, OSError):
        pass
    Installer().mainloop()
