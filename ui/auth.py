from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from core.db import db_init
from core.session import set_current_user
from core.users import add_user, has_users, load_users, verify_user


def authenticate_or_setup(root: tk.Tk) -> bool:
    """User login / first-run setup.

    - Stores users in a "secret" file: users.json in the per-user app data folder.
    - Each user gets their own DB + preferences file.
    """
    if not has_users():
        return _first_run_setup(root)
    return _login_flow(root)


def _bring_to_front(win: tk.Toplevel) -> None:
    win.lift()
    win.attributes("-topmost", True)
    win.after(200, lambda: win.attributes("-topmost", False))


def _first_run_setup(root: tk.Tk) -> bool:
    win = tk.Toplevel(root)
    win.title("First-time setup")
    win.transient(root)
    win.grab_set()
    win.geometry("560x320")
    _bring_to_front(win)

    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    ttk.Label(frm, text="Create your first user", font=("Segoe UI", 12, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(
        frm,
        text="This creates a local user account and a private database on this computer.",
        wraplength=520,
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

    username = tk.StringVar()
    pw1 = tk.StringVar()
    pw2 = tk.StringVar()

    def row(label, widget, r):
        ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=6)
        widget.grid(row=r, column=1, sticky="ew", pady=6)

    e_user = ttk.Entry(frm, textvariable=username)
    e_pw1 = ttk.Entry(frm, textvariable=pw1, show="•")
    e_pw2 = ttk.Entry(frm, textvariable=pw2, show="•")

    row("Username", e_user, 2)
    row("Password", e_pw1, 3)
    row("Confirm password", e_pw2, 4)

    ok = {"value": False}

    def submit():
        u = username.get().strip()
        p1 = pw1.get()
        p2 = pw2.get()

        if len(u) < 2:
            messagebox.showerror("Setup", "Username must be at least 2 characters.", parent=win)
            return
        if len(p1) < 4:
            messagebox.showerror("Setup", "Use at least 4 characters for the password.", parent=win)
            return
        if p1 != p2:
            messagebox.showerror("Setup", "Passwords do not match.", parent=win)
            return
        try:
            add_user(u, p1)
        except Exception as e:
            messagebox.showerror("Setup", f"Could not create user: {e}", parent=win)
            return

        set_current_user(u)
        db_init()

        ok["value"] = True
        win.destroy()

    # Enter acts like Save
    win.bind("<Return>", lambda _e: submit())

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Exit", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Create", style="Accent.TButton", command=submit).pack(
        side="right", padx=8
    )

    e_user.focus_set()
    root.wait_window(win)
    return ok["value"]


def _login_flow(root: tk.Tk) -> bool:
    win = tk.Toplevel(root)
    win.title("Sign in")
    win.transient(root)
    win.grab_set()
    win.geometry("520x260")
    _bring_to_front(win)

    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    ttk.Label(frm, text="Sign in", font=("Segoe UI", 12, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )

    users = [u.username for u in load_users()]
    user_var = tk.StringVar(value=users[0] if users else "")
    pw = tk.StringVar()

    ttk.Label(frm, text="User").grid(row=1, column=0, sticky="w", pady=6)
    cb = ttk.Combobox(frm, textvariable=user_var, values=users, state="readonly")
    cb.grid(row=1, column=1, sticky="ew", pady=6)

    ttk.Label(frm, text="Password").grid(row=2, column=0, sticky="w", pady=6)
    e1 = ttk.Entry(frm, textvariable=pw, show="•")
    e1.grid(row=2, column=1, sticky="ew", pady=6)

    ok = {"value": False}

    def attempt():
        u = user_var.get().strip()
        if not u:
            messagebox.showerror("Sign in", "Select a user.", parent=win)
            return
        if verify_user(u, pw.get()):
            set_current_user(u)
            db_init()
            ok["value"] = True
            win.destroy()
            return
        messagebox.showerror("Sign in", "Wrong password.", parent=win)
        pw.set("")
        e1.focus_set()

    # Enter acts like Unlock
    win.bind("<Return>", lambda _e: attempt())

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Exit", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Unlock", style="Accent.TButton", command=attempt).pack(
        side="right", padx=8
    )

    cb.focus_set()
    root.wait_window(win)
    return ok["value"]
