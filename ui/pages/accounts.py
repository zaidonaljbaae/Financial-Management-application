from __future__ import annotations

from tkinter import ttk, messagebox
import tkinter as tk

from finance.db import (
    delete_account,
    fetch_accounts,
    insert_account,
    update_account,
)


ACCOUNT_TYPES = ["bank", "debit", "credit", "savings", "cash", "wallet", "investment"]


def build(app, parent):
    header = ttk.Frame(parent, padding=12)
    header.pack(fill="x")
    ttk.Label(header, text="Accounts & Cards", font=("Segoe UI", 16, "bold")).pack(side="left")

    btns = ttk.Frame(header)
    btns.pack(side="right")
    ttk.Button(btns, text="Add", style="Accent.TButton", command=lambda: _open_editor(app)).pack(side="left", padx=6)
    ttk.Button(btns, text="Edit", command=lambda: _open_editor(app, _selected_id(app))).pack(side="left", padx=6)
    ttk.Button(btns, text="Delete", command=lambda: _delete_selected(app)).pack(side="left")

    app.acc_tree = ttk.Treeview(
        parent,
        columns=("", "name", "type", "currency", "initial", "active"),
        show="headings",
        height=18,
    )
    for col, w, anc in [
        ("", 40, "e"),
        ("name", 340, "w"),
        ("type", 110, "w"),
        ("currency", 80, "w"),
        ("initial", 120, "e"),
        ("active", 80, "center"),
    ]:
        app.acc_tree.heading(col, text=col.title())
        app.acc_tree.column(col, width=w, anchor=anc)
    app.acc_tree.pack(fill="both", expand=True, padx=12, pady=12)


def refresh(app):
    for i in app.acc_tree.get_children():
        app.acc_tree.delete(i)
    rows = fetch_accounts(include_inactive=True)
    for aid, name, atype, parent_id, currency, initbal, is_active in rows:
        active_txt = "Yes" if is_active else "No"
        app.acc_tree.insert(
            "",
            "end",
            values=(aid, name, atype, currency, f"{float(initbal):,.2f}", active_txt),
        )


def _selected_id(app):
    sel = app.acc_tree.selection()
    if not sel:
        return None
    vals = app.acc_tree.item(sel[0], "values")
    return int(vals[0])


def _delete_selected(app):
    aid = _selected_id(app)
    if not aid:
        messagebox.showinfo("Accounts", "Select an account first.")
        return
    if not messagebox.askyesno("Delete", "Delete selected account? (Transactions will be deleted too)"):
        return
    delete_account(aid)
    app.refresh_all()


def _open_editor(app, account_id: int | None = None):
    win = tk.Toplevel(app)
    win.title("Account" if account_id else "Add Account")
    win.transient(app)
    win.grab_set()
    win.geometry("520x360")

    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)

    # load existing
    existing = None
    if account_id:
        for r in app.accounts:
            if r[0] == account_id:
                existing = r
                break

    def row(lbl, widget, r):
        ttk.Label(frm, text=lbl).grid(row=r, column=0, sticky="w", pady=6)
        widget.grid(row=r, column=1, sticky="ew", pady=6)

    frm.columnconfigure(1, weight=1)

    name_var = tk.StringVar(value=existing[1] if existing else "")
    type_var = tk.StringVar(value=existing[2] if existing else "debit")
    currency_var = tk.StringVar(value=existing[4] if existing else "BRL")
    init_var = tk.StringVar(value=str(existing[5]) if existing else "0.0")
    active_var = tk.IntVar(value=int(existing[6]) if existing else 1)

    row("Name", ttk.Entry(frm, textvariable=name_var), 0)
    row("Type", ttk.Combobox(frm, textvariable=type_var, values=ACCOUNT_TYPES, state="readonly"), 1)
    row("Currency", ttk.Entry(frm, textvariable=currency_var), 2)
    row("Initial Balance", ttk.Entry(frm, textvariable=init_var), 3)
    ttk.Checkbutton(frm, text="Active", variable=active_var).grid(row=4, column=1, sticky="w", pady=8)

    # parent account (optional)
    parent_map = [(None, "(None)")]
    for aid, nm, at, pid, cur, ib, act in app.accounts:
        if at == "bank":
            parent_map.append((aid, f"{nm} (bank)"))
    parent_var = tk.StringVar()
    parent_choices = [txt for _, txt in parent_map]
    existing_parent_id = existing[3] if existing else None
    initial_parent_txt = "(None)"
    for pid, txt in parent_map:
        if pid == existing_parent_id:
            initial_parent_txt = txt
            break
    parent_var.set(initial_parent_txt)
    row("Parent (optional)", ttk.Combobox(frm, textvariable=parent_var, values=parent_choices, state="readonly"), 5)

    def save():
        nm = name_var.get().strip()
        if not nm:
            messagebox.showerror("Account", "Name is required.")
            return
        try:
            init = float(init_var.get())
        except Exception:
            messagebox.showerror("Account", "Initial balance must be a number.")
            return
        parent_id = None
        for pid, txt in parent_map:
            if txt == parent_var.get():
                parent_id = pid
                break
        if account_id:
            update_account(account_id, nm, type_var.get(), parent_id, currency_var.get().strip() or "BRL", init, active_var.get())
        else:
            insert_account(nm, type_var.get(), parent_id, currency_var.get().strip() or "BRL", init, active_var.get())
        win.destroy()
        app.refresh_all()

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Cancel", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Save", style="Accent.TButton", command=save).pack(side="right", padx=8)
