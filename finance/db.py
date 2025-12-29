from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "finance.db"


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a sqlite connection (foreign keys ON)."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def db_init() -> None:
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
    con.commit()

    con.close()


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
