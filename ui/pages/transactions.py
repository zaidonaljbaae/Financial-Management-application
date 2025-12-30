from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

from core.db import (
    delete_transaction,
    fetch_transactions,
    insert_transaction,
    calc_balance_upto,
)

from ui.utils import attach_treeview_sorting

def _make_balance_card(parent, r, c, title, value):
    card = ttk.Frame(parent, style="Card.TFrame", padding=10)
    card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
    ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
    ttk.Label(card, text=f"{value:,.2f}", style="CardValue.TLabel").pack(anchor="w", pady=(2, 0))

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
        columns=("date", "desc", "source", "cat", "amount", "account"),
        show="headings",
        height=18,
    )
    cols = [
        ("date", 110, "w"),
        ("desc", 360, "w"),
        ("source", 180, "w"),
        ("cat", 180, "w"),
        ("amount", 120, "e"),
        ("account", 240, "w"),
    ]
    for c, w, anc in cols:
        app.tx_tree.heading(c, text=c.title())
        app.tx_tree.column(c, width=w, anchor=anc)
    app.tx_tree.pack(fill="both", expand=True, padx=12)

    attach_treeview_sorting(
        app.tx_tree,
        [
            ("date", "date"),
            ("desc", "text"),
            ("source", "text"),
            ("cat", "text"),
            ("amount", "float"),
            ("account", "text"),
        ],
    )

    # color tags
    app.tx_tree.tag_configure("pos_amount", foreground=app.pos_amount_color)
    app.tx_tree.tag_configure("neg_amount", foreground=app.neg_amount_color)

    # totals row under table
    app.tx_totals_lbl = ttk.Label(parent, text="", style="Muted.TLabel")
    app.tx_totals_lbl.pack(fill="x", padx=12, pady=(8, 12))

    app.tx_balances_frame = ttk.Frame(parent, padding=(12, 6, 12, 6))
    app.tx_balances_frame.pack(fill="x")
    for col in range(4):
        app.tx_balances_frame.columnconfigure(col, weight=1)

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

    end_for_balance = end or date.today().isoformat()

    # Render per-account balances up to end date
    for w in app.tx_balances_frame.winfo_children():
        w.destroy()
    cols = 4
    r = c = 0
    # overall total
    total_all = 0.0
    for acc in app.accounts:
        aid = acc[0]
        total_all += calc_balance_upto(int(aid), end_for_balance)
    _make_balance_card(app.tx_balances_frame, r, c, "Total", total_all)
    c += 1
    for acc in app.accounts:
        aid = acc[0]
        name = app.account_map.get(aid, str(aid))
        bal = calc_balance_upto(int(aid), end_for_balance)
        _make_balance_card(app.tx_balances_frame, r, c, name, bal)
        c += 1
        if c >= cols:
            r += 1
            c = 0

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
            iid=str(tid),
            values=(tx_date, desc, loc or "", cat or "", f"{amt:,.2f}", acc),
            tags=tuple(tags),
        )

    app.tx_totals_lbl.config(
        text=f"Totals (current view):  Income {income:,.2f}   Expenses {expense:,.2f}   Net {net:,.2f}   Rows {len(rows)}"
    )


def _selected_id(app):
    sel = app.tx_tree.selection()
    if not sel:
        return None
    return int(sel[0])


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
    source_var = tk.StringVar()
    cat_var = tk.StringVar()
    amt_var = tk.StringVar()
    acc_var = tk.StringVar(value="")

    row("Date (YYYY-MM-DD)", ttk.Entry(frm, textvariable=tx_date_var), 0)
    row("Description", ttk.Entry(frm, textvariable=desc_var), 1)
    sources = list(app.prefs.get("sources", []) or [])
    if not sources:
        sources = ["Other"]
    source_var.set(sources[0])
    src_cb = ttk.Combobox(frm, textvariable=source_var, values=sources, state="normal")
    row("Source (supermarket, bakery...)", src_cb, 2)
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
        src = source_var.get().strip()
        # If user typed a new source, store it for next time
        if src:
            srcs = list(app.prefs.get("sources", []) or [])
            if src not in srcs:
                srcs.append(src)
                app.prefs["sources"] = srcs
                from core.prefs import save_prefs

                save_prefs(app.prefs)
        insert_transaction(d, desc_var.get().strip(), src or None, cat_var.get().strip() or None, amt, account_id)
        win.destroy()
        app.refresh_all()

    actions = ttk.Frame(frm)
    actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
    ttk.Button(actions, text="Cancel", command=win.destroy).pack(side="right")
    ttk.Button(actions, text="Save", style="Accent.TButton", command=save).pack(side="right", padx=8)

