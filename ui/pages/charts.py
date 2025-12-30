from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from core.db import fetch_transactions


def build(app, parent):
    top = ttk.Frame(parent, padding=12)
    top.pack(fill="x")
    ttk.Label(top, text="Charts", font=("Segoe UI", 16, "bold")).pack(side="left")

    controls = ttk.Frame(parent, padding=(12, 0, 12, 8))
    controls.pack(fill="x")
    ttk.Label(controls, text="From").pack(side="left")
    app.ch_start_var = tk.StringVar(value="")
    ttk.Entry(controls, textvariable=app.ch_start_var, width=12).pack(side="left", padx=6)
    ttk.Label(controls, text="To").pack(side="left")
    app.ch_end_var = tk.StringVar(value="")
    ttk.Entry(controls, textvariable=app.ch_end_var, width=12).pack(side="left", padx=6)
    ttk.Button(controls, text="Apply", command=lambda: refresh(app)).pack(side="left", padx=(10, 0))

    app.ch_note = ttk.Label(parent, text="", style="Muted.TLabel")
    app.ch_note.pack(anchor="w", padx=12, pady=(0, 6))

    # Matplotlib figure
    fig = Figure(figsize=(7.4, 4.2), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_title("Income vs Expenses over time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount")

    app._ch_fig = fig
    app._ch_ax = ax

    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))
    app._ch_canvas = canvas

    # Default range: this month
    today = date.today()
    app.ch_start_var.set(f"{today.year:04d}-{today.month:02d}-01")
    app.ch_end_var.set(today.isoformat())


def refresh(app):
    start = (app.ch_start_var.get() or "").strip() or None
    end = (app.ch_end_var.get() or "").strip() or None

    txs = fetch_transactions(start=start, end=end)

    # aggregate daily
    daily_income = {}
    daily_expense = {}
    for _tid, tx_date, _desc, _src, _cat, amt, _aid in txs:
        if amt > 0:
            daily_income[tx_date] = daily_income.get(tx_date, 0.0) + float(amt)
        elif amt < 0:
            daily_expense[tx_date] = daily_expense.get(tx_date, 0.0) + (-float(amt))

    dates = sorted(set(daily_income.keys()) | set(daily_expense.keys()))
    incomes = [daily_income.get(d, 0.0) for d in dates]
    expenses = [daily_expense.get(d, 0.0) for d in dates]

    pal = getattr(app, 'palette', {'bg': '#ffffff', 'fg': '#000000', 'panel': '#ffffff', 'muted': '#666666', 'border': '#cccccc'})
    ax = app._ch_ax
    ax.clear()
    ax.set_facecolor(pal['panel'])
    ax.plot(dates, incomes, label="Income")
    ax.plot(dates, expenses, label="Expenses")
    ax.legend(loc="upper left")
    ax.set_title("Income vs Expenses over time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount")
    ax.tick_params(axis="x", labelrotation=45)

    total_in = sum(incomes)
    total_ex = sum(expenses)
    app.ch_note.config(text=f"Range: {start or '—'} → {end or '—'}   Income {total_in:,.2f}   Expenses {total_ex:,.2f}")
    app._ch_canvas.draw_idle()
