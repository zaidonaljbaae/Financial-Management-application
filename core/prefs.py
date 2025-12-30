from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PREFS_PATH = DATA_DIR / "ui_prefs.json"


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
        if PREFS_PATH.exists():
            data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
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
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PREFS_PATH.write_text(
            json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass
