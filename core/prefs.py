from __future__ import annotations

import json
from pathlib import Path

from core.app_paths import user_data_dir
from core.session import get_current_user


def get_prefs_path(username: str | None = None) -> Path:
    uname = (username or get_current_user() or "default").strip().lower()
    return user_data_dir() / f"ui_prefs_{uname}.json"


DEFAULT_PREFS = {
    "theme": "dark",
    "accent": "#2a6fe3",
    "topbar_bg": "#121826",
    "topbar_fg": "#e6e6e6",
    "pos_amount_color": "#2a6fe3",
    "neg_amount_color": "#ff4d4d",
    # Used in the Add Transaction form ("Source").
    # Users can add new sources directly from the form.
    "sources": [
        "Supermarket",
        "Bakery",
        "Restaurant",
        "Transport",
        "Online",
        "Bills",
        "Other",
    ],
    # Optional custom colors by category (e.g., {"Salary": "#2ecc71"})
    "category_colors": {},
}


def load_prefs() -> dict:
    try:
        p = get_prefs_path()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = dict(DEFAULT_PREFS)
                merged.update(data)
                if not isinstance(merged.get("category_colors"), dict):
                    merged["category_colors"] = {}
                if not isinstance(merged.get("sources"), list):
                    merged["sources"] = list(DEFAULT_PREFS["sources"])
                return merged
    except Exception:
        pass
    return dict(DEFAULT_PREFS)


def save_prefs(prefs: dict) -> None:
    try:
        p = get_prefs_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass
