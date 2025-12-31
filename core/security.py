from __future__ import annotations
import hmac

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from core.app_paths import user_data_dir
from core.db import get_db_path
from core.prefs import get_prefs_path
from core.session import get_current_user


SEC_PATH = user_data_dir() / "security.json"


def _pbkdf2(password: str, salt: bytes, *, rounds: int = 200_000) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)


def _new_salt(n: int = 16) -> bytes:
    return os.urandom(n)


def _hex(b: bytes) -> str:
    return b.hex()


def _unhex(s: str) -> bytes:
    return bytes.fromhex(s)


@dataclass
class SecurityState:
    program_hash: str | None = None
    program_salt: str | None = None
    db_hash: str | None = None
    db_salt: str | None = None
    failed_attempts: int = 0


def load_security() -> SecurityState:
    try:
        if SEC_PATH.exists():
            data = json.loads(SEC_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return SecurityState(
                    program_hash=data.get("program_hash"),
                    program_salt=data.get("program_salt"),
                    db_hash=data.get("db_hash"),
                    db_salt=data.get("db_salt"),
                    failed_attempts=int(data.get("failed_attempts", 0) or 0),
                )
    except Exception:
        pass
    return SecurityState()


def save_security(st: SecurityState) -> None:
    SEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEC_PATH.write_text(
        json.dumps(
            {
                "program_hash": st.program_hash,
                "program_salt": st.program_salt,
                "db_hash": st.db_hash,
                "db_salt": st.db_salt,
                "failed_attempts": st.failed_attempts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def is_initialized(st: SecurityState) -> bool:
    return bool(st.program_hash and st.program_salt and st.db_hash and st.db_salt)


def set_passwords(one_password: str) -> None:
    st = load_security()
    salt = _new_salt()

    st.program_salt = _hex(salt)
    st.db_salt = _hex(salt)

    h = _hex(_pbkdf2(one_password, salt))
    st.program_hash = h
    st.db_hash = h

    st.failed_attempts = 0
    save_security(st)


def verify_master_password(st: SecurityState, password: str) -> bool:
    return verify_program_password(st, password)


def verify_program_password(st: SecurityState, password: str) -> bool:
    if not st.program_hash or not st.program_salt:
        return False
    calc = _hex(_pbkdf2(password, _unhex(st.program_salt)))
    return hmac.compare_digest(calc, st.program_hash)


def verify_db_password(st: SecurityState, password: str) -> bool:
    if not st.db_hash or not st.db_salt:
        return False
    calc = _hex(_pbkdf2(password, _unhex(st.db_salt)))
    return hmac.compare_digest(calc, st.db_hash)

def wipe_all_user_data() -> None:
    """Delete the DB + UI prefs + security file (resets the application)."""
    uname = get_current_user() or "default"
    for p in [get_db_path(uname), get_prefs_path(uname), SEC_PATH]:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
