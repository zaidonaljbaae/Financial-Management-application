from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from core.security import (
    SecurityState,
    is_initialized,
    load_security,
    save_security,
    set_passwords,
    verify_program_password,
    wipe_all_user_data,
)
from core.db import db_init


def authenticate_or_setup(root: tk.Tk) -> bool:
    """Returns True if authentication succeeded. Handles first-run setup.

    Security model:
    - Stores password hashes in data/security.json
    - Uses ONE password for both program and database
    - After 10 failed attempts: wipes user data (DB + prefs + passwords)
    """
    st = load_security()
    if not is_initialized(st):
        return _first_run_setup(root)
    return _login_flow(root, st)


def _bring_to_front(win: tk.Toplevel) -> None:
    # Helps on Windows where dialogs sometimes open behind other windows
    win.lift()
    win.attributes("-topmost", True)
    win.after(200, lambda: win.attributes("-topmost", False))


def _first_run_setup(root: tk.Tk) -> bool:
    win = tk.Toplevel(root)
    win.title("First-time setup")
    win.transient(root)
    win.grab_set()
    win.geometry("520x260")
    _bring_to_front(win)

    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    ttk.Label(frm, text="Set password", font=("Segoe UI", 12, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(
        frm,
        text="This password is required to open the app and unlock the database.",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

    pw1 = tk.StringVar()
    pw2 = tk.StringVar()

    def r(label, var, row):
        ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=var, show="•").grid(row=row, column=1, sticky="ew", pady=6)

    r("Password", pw1, 2)
    r("Confirm password", pw2, 3)

    ok = {"value": False}

    def submit():
        p1 = pw1.get()
        p2 = pw2.get()

        if len(p1) < 4:
            messagebox.showerror("Setup", "Use at least 4 characters.", parent=win)
            return
        if p1 != p2:
            messagebox.showerror("Setup", "Passwords do not match.", parent=win)
            return

        # ONE password for both program and DB (finance.security.set_passwords must accept one arg)
        set_passwords(p1)
        db_init()

        ok["value"] = True
        win.destroy()

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Cancel", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Save", style="Accent.TButton", command=submit).pack(side="right", padx=8)

    root.wait_window(win)
    return ok["value"]


def _login_flow(root: tk.Tk, st: SecurityState) -> bool:
    win = tk.Toplevel(root)
    win.title("Unlock")
    win.transient(root)
    win.grab_set()
    win.geometry("480x220")
    _bring_to_front(win)

    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    ttk.Label(frm, text="Enter password", font=("Segoe UI", 12, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    attempts_txt = tk.StringVar(value=f"Failed attempts: {int(st.failed_attempts or 0)}/10")
    ttk.Label(frm, textvariable=attempts_txt).grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 10)
    )

    pw = tk.StringVar()

    ttk.Label(frm, text="Password").grid(row=2, column=0, sticky="w", pady=6)
    e1 = ttk.Entry(frm, textvariable=pw, show="•")
    e1.grid(row=2, column=1, sticky="ew", pady=6)

    ok = {"value": False}
    e1.bind("<Return>", lambda _e: attempt())
    win.bind("<Return>", lambda _e: attempt())
    
    def attempt():
        nonlocal st

        if verify_program_password(st, pw.get()):
            st.failed_attempts = 0
            save_security(st)
            ok["value"] = True
            win.destroy()
            return

        # wrong password
        st.failed_attempts = int(st.failed_attempts or 0) + 1
        save_security(st)
        attempts_txt.set(f"Failed attempts: {st.failed_attempts}/10")

        if st.failed_attempts >= 10:
            wipe_all_user_data()
            db_init()
            messagebox.showerror(
                "Locked",
                "10 wrong attempts. All user data was deleted and the app was reset.\n\n"
                "Restart the app to set a new password.",
                parent=win,
            )
            win.destroy()
            ok["value"] = False
            return

        messagebox.showerror("Unlock", "Wrong password.", parent=win)
        pw.set("")
        e1.focus_set()

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Exit", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Unlock", style="Accent.TButton", command=attempt).pack(side="right", padx=8)

    e1.focus_set()
    root.wait_window(win)
    return ok["value"]
