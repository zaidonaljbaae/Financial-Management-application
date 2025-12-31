from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from core.app_paths import bundled_data_dir, user_data_dir
from core.session import get_current_user


def get_db_path(username: str | None = None) -> Path:
    """Per-user database path (writable)."""
    uname = (username or get_current_user() or "default").strip().lower()
    return user_data_dir() / f"finance_{uname}.db"


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a sqlite connection (foreign keys ON)."""
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def db_init() -> None:
    # Ensure per-user DB exists and has schema.
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            parent_id INTEGER NULL,
            currency TEXT NOT NULL DEFAULT 'BRL',
            initial_balance REAL NOT NULL DEFAULT 0.0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT,
            category TEXT,
            amount REAL NOT NULL,
            account_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        );
        """
    )

    # Credit-card linkage (optional): which account pays the credit statement.
    # Stored separately to keep backwards compatibility with old DB files.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS card_links (
            credit_account_id INTEGER PRIMARY KEY,
            pay_from_account_id INTEGER NOT NULL,
            statement_day INTEGER NOT NULL DEFAULT 30,
            created_at TEXT NOT NULL,
            FOREIGN KEY(credit_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY(pay_from_account_id) REFERENCES accounts(id) ON DELETE CASCADE
        );
        """
    )
    con.commit()

    con.close()


def ensure_db_present() -> None:
    """Create a new per-user DB if missing.

    When packaged, the bundled ./data/finance.db is read-only and lives in a
    temp folder. We always write to the user data directory.
    """
    path = get_db_path()
    if path.exists():
        return
    # If a bundled template DB exists, try to copy it as a starting point.
    try:
        template = bundled_data_dir() / "finance.db"
        if template.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(template.read_bytes())
    except Exception:
        pass
    # Always enforce schema.
    db_init()


def fetch_accounts(*, include_inactive: bool = False):
    con = db_connect()
    cur = con.cursor()
    if include_inactive:
        cur.execute(
            "SELECT id, name, account_type, parent_id, currency, initial_balance, is_active FROM accounts ORDER BY COALESCE(parent_id, id), parent_id IS NOT NULL, id;"
        )
    else:
        cur.execute(
            "SELECT id, name, account_type, parent_id, currency, initial_balance, is_active FROM accounts WHERE is_active=1 ORDER BY COALESCE(parent_id, id), parent_id IS NOT NULL, id;"
        )
    rows = cur.fetchall()
    con.close()
    return rows


def fetch_transactions(*, account_id=None, start=None, end=None):
    con = db_connect()
    cur = con.cursor()
    q = "SELECT id, tx_date, description, location, category, amount, account_id FROM transactions WHERE 1=1"
    params = []
    if account_id:
        q += " AND account_id=?"
        params.append(account_id)
    if start:
        q += " AND tx_date>=?"
        params.append(start)
    if end:
        q += " AND tx_date<=?"
        params.append(end)
    q += " ORDER BY tx_date DESC, id DESC"
    cur.execute(q, params)
    rows = cur.fetchall()
    con.close()
    return rows


def insert_account(name, account_type, parent_id, currency, initial_balance, is_active=1):
    con = db_connect()
    cur = con.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """INSERT INTO accounts(name, account_type, parent_id, currency, initial_balance, is_active, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (name, account_type, parent_id, currency, float(initial_balance), int(is_active), now),
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return new_id


def update_account(account_id, name, account_type, parent_id, currency, initial_balance, is_active):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """UPDATE accounts
           SET name=?, account_type=?, parent_id=?, currency=?, initial_balance=?, is_active=?
           WHERE id=?""",
        (name, account_type, parent_id, currency, float(initial_balance), int(is_active), int(account_id)),
    )
    con.commit()
    con.close()


def delete_account(account_id):
    con = db_connect()
    cur = con.cursor()
    cur.execute("DELETE FROM accounts WHERE id=?", (int(account_id),))
    con.commit()
    con.close()


def insert_transaction(tx_date, description, location, category, amount, account_id):
    con = db_connect()
    cur = con.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """INSERT INTO transactions(tx_date, description, location, category, amount, account_id, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (tx_date, description, location, category, float(amount), int(account_id), now),
    )
    con.commit()
    tx_id = cur.lastrowid
    con.close()
    return tx_id


def delete_transaction(tx_id):
    con = db_connect()
    cur = con.cursor()
    cur.execute("DELETE FROM transactions WHERE id=?", (int(tx_id),))
    con.commit()
    con.close()


def upsert_card_link(credit_account_id: int, pay_from_account_id: int, statement_day: int = 30) -> None:
    """Create/update the credit-card settlement relationship."""
    con = db_connect()
    cur = con.cursor()
    now = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """
        INSERT INTO card_links(credit_account_id, pay_from_account_id, statement_day, created_at)
        VALUES (?,?,?,?)
        ON CONFLICT(credit_account_id)
        DO UPDATE SET pay_from_account_id=excluded.pay_from_account_id,
                     statement_day=excluded.statement_day;
        """,
        (int(credit_account_id), int(pay_from_account_id), int(statement_day or 30), now),
    )
    con.commit()
    con.close()


def fetch_card_link(credit_account_id: int):
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        "SELECT credit_account_id, pay_from_account_id, statement_day FROM card_links WHERE credit_account_id=?",
        (int(credit_account_id),),
    )
    row = cur.fetchone()
    con.close()
    return row


def calc_credit_statement(credit_account_id: int, ym: str) -> float:
    """Return statement amount for a month (positive number to pay).

    ym: 'YYYY-MM'
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0)
        FROM transactions
        WHERE account_id=? AND substr(tx_date,1,7)=?
        """,
        (int(credit_account_id), ym),
    )
    amt = float(cur.fetchone()[0] or 0)
    con.close()
    return amt


def settle_credit_statement(*, credit_account_id: int, pay_from_account_id: int, ym: str, description: str | None = None) -> float:
    """Create two transactions to pay a credit-card statement.

    - Pay-from account (debit/cash): -payment
    - Credit account: +payment

    Returns the payment amount created (0 if nothing to pay).
    """
    payment = calc_credit_statement(int(credit_account_id), ym)
    if payment <= 0:
        return 0.0

    # Use a safe day that exists for all months.
    pay_date = f"{ym}-28"
    desc = description or f"Credit card payment ({ym})"
    insert_transaction(pay_date, desc, "Settlement", "Credit Payment", -payment, int(pay_from_account_id))
    insert_transaction(pay_date, desc, "Settlement", "Credit Payment", +payment, int(credit_account_id))
    return float(payment)




def calc_balance_upto(account_id: int, end_date: str | None) -> float:
    """Balance including initial balance plus transactions up to end_date (inclusive).

    end_date: 'YYYY-MM-DD' or None for all.
    """
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT initial_balance FROM accounts WHERE id=?", (int(account_id),))
    row = cur.fetchone()
    if not row:
        con.close()
        return 0.0
    initial = float(row[0])
    if end_date:
        cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account_id=? AND tx_date<=?",
            (int(account_id), str(end_date)),
        )
    else:
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account_id=?", (int(account_id),))
    total = float(cur.fetchone()[0])
    con.close()
    return initial + total


def auto_settle_credit_cards(today: str) -> None:
    """Automatically settle linked credit cards on their statement day.

    - today: 'YYYY-MM-DD'
    On statement_day, creates settlement transactions for the PREVIOUS month (YYYY-MM),
    unless already created.
    """
    from datetime import datetime, timedelta

    try:
        dt = datetime.fromisoformat(today).date()
    except Exception:
        dt = datetime.now().date()

    # previous month
    first = dt.replace(day=1)
    prev_last = first - timedelta(days=1)
    ym = f"{prev_last.year:04d}-{prev_last.month:02d}"

    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT credit_account_id, pay_from_account_id, statement_day FROM card_links")
    links = cur.fetchall()
    con.close()

    for credit_id, pay_from_id, statement_day in links:
        if int(statement_day) != int(dt.day):
            continue

        # prevent duplicates: check if a settlement for this ym already exists
        con2 = db_connect()
        cur2 = con2.cursor()
        cur2.execute(
            """
            SELECT 1 FROM transactions
            WHERE account_id=?
              AND category='Settlement'
              AND source='Credit Payment'
              AND substr(tx_date,1,7)=?
              AND amount>0
            LIMIT 1
            """,
            (int(credit_id), ym),
        )
        exists = cur2.fetchone() is not None
        con2.close()
        if exists:
            continue

        payment = calc_credit_statement(int(credit_id), ym)
        if payment <= 0:
            continue

        desc = f"Credit card payment ({ym})"
        pay_date = dt.isoformat()
        insert_transaction(pay_date, desc, "Settlement", "Credit Payment", -payment, int(pay_from_id))
        insert_transaction(pay_date, desc, "Settlement", "Credit Payment", +payment, int(credit_id))


def calc_balance(account_id) -> float:
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT initial_balance FROM accounts WHERE id=?", (int(account_id),))
    row = cur.fetchone()
    if not row:
        con.close()
        return 0.0
    initial = float(row[0])
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account_id=?", (int(account_id),))
    total = float(cur.fetchone()[0])
    con.close()
    return initial + total


def monthly_totals(*, year=None, account_id=None):
    """Returns list of (YYYY-MM, income, expense, net)."""
    con = db_connect()
    cur = con.cursor()
    q = (
        """
        SELECT substr(tx_date,1,7) as ym,
               SUM(CASE WHEN amount>0 THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN amount<0 THEN -amount ELSE 0 END) as expense
        FROM transactions
        WHERE 1=1
        """
    )
    params = []
    if year:
        q += " AND tx_date>=? AND tx_date<=?"
        params += [f"{year}-01-01", f"{year}-12-31"]
    if account_id:
        q += " AND account_id=?"
        params.append(account_id)
    q += " GROUP BY ym ORDER BY ym"
    cur.execute(q, params)
    rows = []
    for ym, income, expense in cur.fetchall():
        income = float(income or 0)
        expense = float(expense or 0)
        rows.append((ym, income, expense, income - expense))
    con.close()
    return rows
