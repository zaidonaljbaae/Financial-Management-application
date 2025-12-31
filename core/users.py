from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from core.app_paths import user_data_dir


USERS_PATH = user_data_dir() / "users.json"


def _pbkdf2(password: str, salt: bytes, *, rounds: int = 200_000) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)


def _new_salt(n: int = 16) -> bytes:
    return os.urandom(n)


@dataclass
class UserRec:
    username: str
    salt_hex: str
    hash_hex: str


def load_users() -> List[UserRec]:
    try:
        if USERS_PATH.exists():
            data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
            out: List[UserRec] = []
            for u in (data.get("users") or []):
                if not isinstance(u, dict):
                    continue
                username = str(u.get("username") or "").strip().lower()
                salt_hex = str(u.get("salt") or "")
                hash_hex = str(u.get("hash") or "")
                if username and salt_hex and hash_hex:
                    out.append(UserRec(username=username, salt_hex=salt_hex, hash_hex=hash_hex))
            return out
    except Exception:
        pass
    return []


def save_users(users: List[UserRec]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(
        json.dumps(
            {
                "users": [
                    {"username": u.username, "salt": u.salt_hex, "hash": u.hash_hex}
                    for u in users
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def has_users() -> bool:
    return len(load_users()) > 0


def add_user(username: str, password: str) -> None:
    uname = (username or "").strip().lower()
    if not uname:
        raise ValueError("username required")
    users = load_users()
    if any(u.username == uname for u in users):
        raise ValueError("user already exists")
    salt = _new_salt()
    h = _pbkdf2(password, salt)
    users.append(UserRec(username=uname, salt_hex=salt.hex(), hash_hex=h.hex()))
    save_users(users)


def verify_user(username: str, password: str) -> bool:
    uname = (username or "").strip().lower()
    if not uname:
        return False
    for u in load_users():
        if u.username != uname:
            continue
        try:
            salt = bytes.fromhex(u.salt_hex)
        except Exception:
            return False
        calc = _pbkdf2(password, salt).hex()
        return hmac.compare_digest(calc, u.hash_hex)
    return False


def set_user_password(username: str, new_password: str) -> None:
    uname = (username or "").strip().lower()
    if not uname:
        raise ValueError("username required")
    users = load_users()
    for i, u in enumerate(users):
        if u.username == uname:
            salt = _new_salt()
            h = _pbkdf2(new_password, salt)
            users[i] = UserRec(username=uname, salt_hex=salt.hex(), hash_hex=h.hex())
            save_users(users)
            return
    raise ValueError("user not found")
