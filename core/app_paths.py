from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "MoneyManager"


def user_data_dir(app_name: str = APP_NAME) -> Path:
    """Return a per-user, writable data directory.

    This fixes the classic "works in source, but not when .exe" problem:
    packaged apps must not write inside the bundled folder.
    """
    # Windows
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / app_name

    # macOS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name

    # Linux / others
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / app_name
    return Path.home() / ".local" / "share" / app_name


def bundled_data_dir() -> Path:
    """Directory where the packaged (read-only) 'data' folder lives.

    In dev/source runs, it's the project's ./data.
    In PyInstaller, it's inside sys._MEIPASS.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / "data"
    return Path(__file__).resolve().parents[1] / "data"
