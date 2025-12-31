from __future__ import annotations

"""Simple in-memory session state (current logged-in user)."""

_CURRENT_USER: str = "default"


def set_current_user(username: str) -> None:
    global _CURRENT_USER
    _CURRENT_USER = (username or "default").strip().lower()


def get_current_user() -> str:
    return _CURRENT_USER
