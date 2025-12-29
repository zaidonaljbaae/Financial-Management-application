from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

from finance.db import (
    delete_transaction,
    fetch_transactions,
    insert_transaction,
)


def build(app, parent):
    header = ttk.Frame(parent, padding=12)
    header.pack(fill="x")
    ttk.Label(header, text="Transactions", font=("Segoe UI", 16, "bold")).pack(side="left")

    # Filters
    filters = ttk.Frame(parent, padding=(12, 0, 12, 8))
    filters.pack(fill="x")
    ttk.Label(filters, text="Account").pack(side="left")
    app.tx_account_var = tk.StringVar(value="(All)")
    app.tx_account_cb = ttk.Combobox(filters, textvariable=app.tx_account_var, state="readonly", width=34)
    app.tx_account_cb.pack(side="left", padx=6)
    ttk.Label(filters, text="From").pack(side="left", padx=(14, 0))
    app.tx_start_var = tk.StringVar(value="")
    ttk.Entry(filters, textvariable=app.tx_start_var, width=12).pack(side="left", padx=6)
    ttk.Label(filters, text="To").pack(side="left")
    app.tx_end_var = tk.StringVar(value="")
    ttk.Entry(filters, textvariable=app.tx_end_var, width=12).pack(side="left", padx=6)
    ttk.Button(filters, text="Apply", command=lambda: refresh(app)).pack(side="left", padx=(10, 0))

    btns = ttk.Frame(filters)
    btns.pack(side="right")
    ttk.Button(btns, text="Add", style="Accent.TButton", command=lambda: _open_add(app)).pack(side="left", padx=6)
    ttk.Button(btns, text="Delete", command=lambda: _delete_selected(app)).pack(side="left")

    app.tx_tree = ttk.Treeview(
        parent,
        columns=("", "date", "desc", "loc", "cat", "amount", "account"),
        show="headings",
        height=18,
    )
    cols = [
        ("", 40, "e"),
        ("date", 110, "w"),
        ("desc", 360, "w"),
        ("loc", 150, "w"),
        ("cat", 160, "w"),
        ("amount", 120, "e"),
        ("account", 240, "w"),
    ]
    for c, w, anc in cols:
        app.tx_tree.heading(c, text=c.title())
        app.tx_tree.column(c, width=w, anchor=anc)
    app.tx_tree.pack(fill="both", expand=True, padx=12)

    # color tags
    app.tx_tree.tag_configure("pos_amount", foreground=app.pos_amount_color)
    app.tx_tree.tag_configure("neg_amount", foreground=app.neg_amount_color)

    # totals row under table
    app.tx_totals_lbl = ttk.Label(parent, text="", style="Muted.TLabel")
    app.tx_totals_lbl.pack(fill="x", padx=12, pady=(8, 12))


def refresh(app):
    # account combobox options
    options = ["(All)"] + [app.account_map[a[0]] for a in app.accounts]
    app.tx_account_cb.configure(values=options)
    if app.tx_account_var.get() not in options:
        app.tx_account_var.set("(All)")

    # resolve filters
    sel_txt = app.tx_account_var.get()
    account_id = None
    if sel_txt and sel_txt != "(All)":
        for aid, label in app.account_map.items():
            if label == sel_txt:
                account_id = aid
                break
    start = app.tx_start_var.get().strip() or None
    end = app.tx_end_var.get().strip() or None

    rows = fetch_transactions(account_id=account_id, start=start, end=end)

    for i in app.tx_tree.get_children():
        app.tx_tree.delete(i)

    income = 0.0
    expense = 0.0
    net = 0.0

    for tid, tx_date, desc, loc, cat, amt, aid in rows:
        net += float(amt)
        if amt > 0:
            income += float(amt)
        elif amt < 0:
            expense += -float(amt)

        acc = app.account_map.get(aid, str(aid))
        tags = []
        if amt > 0:
            tags.append("pos_amount")
        elif amt < 0:
            tags.append("neg_amount")

        # category-based colors (optional)
        if cat and isinstance(app.category_colors, dict) and cat in app.category_colors:
            tag = f"cat_{cat}"
            if not getattr(app, "_cat_tags", None):
                app._cat_tags = set()
            if tag not in app._cat_tags:
                app.tx_tree.tag_configure(tag, foreground=app.category_colors.get(cat))
                app._cat_tags.add(tag)
            # category overrides amount color (user request)
            tags = [tag]

        app.tx_tree.insert(
            "",
            "end",
            values=(tid, tx_date, desc, loc or "", cat or "", f"{amt:,.2f}", acc),
            tags=tuple(tags),
        )

    app.tx_totals_lbl.config(
        text=f"Totals (current view):  Income {income:,.2f}   Expenses {expense:,.2f}   Net {net:,.2f}   Rows {len(rows)}"
    )


def _selected_id(app):
    sel = app.tx_tree.selection()
    if not sel:
        return None
    vals = app.tx_tree.item(sel[0], "values")
    return int(vals[0])


def _delete_selected(app):
    tid = _selected_id(app)
    if not tid:
        messagebox.showinfo("Transactions", "Select a transaction first.")
        return
    if not messagebox.askyesno("Delete", "Delete selected transaction?"):
        return
    delete_transaction(tid)
    app.refresh_all()


def _open_add(app):
    win = tk.Toplevel(app)
    win.title("Add Transaction")
    win.transient(app)
    win.grab_set()
    win.geometry("640x420")

    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    def row(lbl, widget, r):
        ttk.Label(frm, text=lbl).grid(row=r, column=0, sticky="w", pady=6)
        widget.grid(row=r, column=1, sticky="ew", pady=6)

    tx_date_var = tk.StringVar(value=date.today().isoformat())
    desc_var = tk.StringVar()
    loc_var = tk.StringVar()
    cat_var = tk.StringVar()
    amt_var = tk.StringVar()
    acc_var = tk.StringVar(value="")

    row("Date (YYYY-MM-DD)", ttk.Entry(frm, textvariable=tx_date_var), 0)
    row("Description", ttk.Entry(frm, textvariable=desc_var), 1)
    row("Location", ttk.Entry(frm, textvariable=loc_var), 2)
    row("Category", ttk.Entry(frm, textvariable=cat_var), 3)
    row("Amount (+income / -expense)", ttk.Entry(frm, textvariable=amt_var), 4)

    acc_choices = [app.account_map[a[0]] for a in app.accounts]
    if acc_choices:
        acc_var.set(acc_choices[0])
    row("Account", ttk.Combobox(frm, textvariable=acc_var, values=acc_choices, state="readonly"), 5)

    def save():
        d = tx_date_var.get().strip()
        if len(d) != 10 or d[4] != "-" or d[7] != "-":
            messagebox.showerror("Transaction", "Invalid date format.")
            return
        if not desc_var.get().strip():
            messagebox.showerror("Transaction", "Description is required.")
            return
        try:
            amt = float(amt_var.get())
        except Exception:
            messagebox.showerror("Transaction", "Amount must be a number.")
            return
        account_id = None
        for aid, label in app.account_map.items():
            if label == acc_var.get():
                account_id = aid
                break
        if not account_id:
            messagebox.showerror("Transaction", "Select an account.")
            return
        insert_transaction(d, desc_var.get().strip(), loc_var.get().strip() or None, cat_var.get().strip() or None, amt, account_id)
        win.destroy()
        app.refresh_all()

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Cancel", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Save", style="Accent.TButton", command=save).pack(side="right", padx=8)
