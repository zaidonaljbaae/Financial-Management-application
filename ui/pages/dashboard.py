from __future__ import annotations

from datetime import date
from tkinter import ttk

from core.db import calc_balance_upto, fetch_transactions


def build(app, parent):
    app.dashboard_parent = parent  # keep reference for refresh()

    top = ttk.Frame(parent, padding=12)
    top.pack(fill="x")
    ttk.Label(top, text="Overview", font=("Segoe UI", 16, "bold")).pack(side="left")

    cards = ttk.Frame(parent, padding=(12, 0, 12, 0))
    cards.pack(fill="x", pady=(0, 6))
    for col in range(4):
        cards.columnconfigure(col, weight=1)

    def make_card(col, title, style_idx):
        f = ttk.Frame(cards, style=f"Card{style_idx}.TFrame", padding=12)
        f.grid(row=0, column=col, sticky="nsew", padx=6, pady=6)
        ttk.Label(f, text=title, style=f"Card{style_idx}.Title.TLabel").pack(anchor="w")
        val = ttk.Label(f, text="—", style=f"Card{style_idx}.Value.TLabel")
        val.pack(anchor="w", pady=(6, 0))
        return val

    app.card_balance = make_card(0, "Total Balance (Active)", 1)
    app.card_income = make_card(1, "Income (This Month)", 2)
    app.card_expense = make_card(2, "Expenses (This Month)", 3)
    app.card_net = make_card(3, "Net (This Month)", 4)

    app.lbl_month_summary = ttk.Label(parent, text="", font=("Segoe UI", 11))
    app.lbl_month_summary.pack(anchor="w", padx=12, pady=(6, 0))

    ttk.Label(parent, text="Account Totals", font=("Segoe UI", 12, "bold")).pack(
        anchor="w", padx=12, pady=(16, 6)
    )
    app.acct_cards_frame = ttk.Frame(parent, padding=(12, 0, 12, 12))
    app.acct_cards_frame.pack(fill="x")

    ttk.Label(parent, text="Recent Transactions", font=("Segoe UI", 12, "bold")).pack(
        anchor="w", padx=12, pady=(8, 6)
    )
    app.recent_tree = ttk.Treeview(
        parent, columns=("date", "desc", "amount", "account"), show="headings", height=10
    )
    for c, w in [("date", 110), ("desc", 520), ("amount", 130), ("account", 260)]:
        app.recent_tree.heading(c, text=c.title())
        app.recent_tree.column(c, width=w, anchor="w")
    app.recent_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))


def refresh(app):
    today = date.today()
    start = f"{today.year:04d}-{today.month:02d}-01"
    end = today.isoformat()

    # This month transactions
    txs = fetch_transactions(start=start, end=end)

    income = sum(t[5] for t in txs if t[5] > 0)
    expense = sum(-t[5] for t in txs if t[5] < 0)
    net = income - expense

    # Total balance of active accounts up to today
    total = 0.0
    for aid in app.active_account_ids():
        total += calc_balance_upto(int(aid), end)

    app.card_balance.config(text=f"{total:,.2f}")
    app.card_income.config(text=f"{income:,.2f}")
    app.card_expense.config(text=f"{expense:,.2f}")
    app.card_net.config(text=f"{net:,.2f}")

    app.lbl_month_summary.config(
        text=f"This month ({today.year}-{today.month:02d}) • Income: {income:,.2f}  Expense: {expense:,.2f}  Net: {net:,.2f}"
    )

    # Per-account totals (up to today)
    for w in app.acct_cards_frame.winfo_children():
        w.destroy()

    cols = 4
    r = c = 0
    for acc in app.accounts:
        aid = int(acc[0])
        name = app.account_map.get(aid, str(aid))
        bal = calc_balance_upto(aid, end)

        card = ttk.Frame(app.acct_cards_frame, style="Card.TFrame", padding=10)
        card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

        ttk.Label(card, text=name, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, text=f"{bal:,.2f}", style="CardValue.TLabel").pack(anchor="w", pady=(2, 0))

        app.acct_cards_frame.columnconfigure(c, weight=1)

        c += 1
        if c >= cols:
            r += 1
            c = 0

    # Recent transactions list (show last 25 from this month)
    for i in app.recent_tree.get_children():
        app.recent_tree.delete(i)

    for tid, tx_date, desc, loc, cat, amt, aid in txs[:25]:
        acc = app.account_map.get(aid, str(aid))
        app.recent_tree.insert("", "end", values=(tx_date, desc, f"{amt:,.2f}", acc))
