from __future__ import annotations

import os
import csv
from datetime import date
from pathlib import Path
import subprocess
import sys

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from finance.db import (
    db_init,
    fetch_accounts,
    fetch_transactions,
    calc_balance,
    insert_transaction,
)
from finance.prefs import load_prefs, save_prefs

from .settings_window import SettingsWindow
from .pages import dashboard, accounts, transactions


class MoneyManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Money Manager")
        self._set_initial_geometry()
        self.minsize(980, 620)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        db_init()

        self.prefs = load_prefs()
        self._cat_tags = set()

        self._load_colors_from_prefs()
        self.apply_theme(self.prefs.get("theme", "dark"))

        self._build_menu()
        self._build_topbar()
        self._build_notebook()
        self._build_footer()

        self.refresh_all()

    # --------- global state ---------
    def _load_colors_from_prefs(self):
        self.accent = self.prefs.get("accent", "#2a6fe3")
        self.topbar_bg = self.prefs.get("topbar_bg", "#121826")
        self.topbar_fg = self.prefs.get("topbar_fg", "#e6e6e6")
        self.pos_amount_color = self.prefs.get("pos_amount_color", self.accent)
        self.neg_amount_color = self.prefs.get("neg_amount_color", "#ff4d4d")
        self.category_colors = self.prefs.get("category_colors", {}) or {}

    def reload_prefs_and_refresh(self):
        self.prefs = load_prefs()
        self._load_colors_from_prefs()
        self.apply_theme(self.prefs.get("theme", "dark"))
        self.refresh_all()

    # --------- window ---------
    def _set_initial_geometry(self):
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            w = max(980, int(sw * 0.92))
            h = max(620, int(sh * 0.86))
            self.geometry(f"{w}x{h}")
        except Exception:
            self.geometry("1100x700")

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_m = tk.Menu(menubar, tearoff=0)
        file_m.add_command(label="Import CSV…", command=self._import_csv)
        file_m.add_command(label="Export CSV…", command=self._export_csv)
        file_m.add_separator()
        file_m.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_m)

        tools_m = tk.Menu(menubar, tearoff=0)
        tools_m.add_command(label="Calculator", command=self._open_calculator)
        menubar.add_cascade(label="Tools", menu=tools_m)

        settings_m = tk.Menu(menubar, tearoff=0)
        settings_m.add_command(label="Settings…", command=self._open_settings)
        menubar.add_cascade(label="Settings", menu=settings_m)

        self.config(menu=menubar)

    def _build_topbar(self):
        # user request: no buttons in top bar, only logo + title
        self.topbar = ttk.Frame(self, style="Topbar.TFrame", padding=(16, 14))
        self.topbar.pack(side="top")

        ttk.Label(self.topbar).pack(side="left")

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self, style="App.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_accounts = ttk.Frame(self.notebook)
        self.tab_transactions = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self.notebook.add(self.tab_accounts, text="Accounts")
        self.notebook.add(self.tab_transactions, text="Transactions")

        dashboard.build(self, self.tab_dashboard)
        accounts.build(self, self.tab_accounts)
        transactions.build(self, self.tab_transactions)

    def _build_footer(self):
        self._footer = ttk.Label(self, text="Created by Zaidon", style="Footer.TLabel", anchor="e")
        self._footer.pack(side="bottom", fill="x", padx=10, pady=(0, 8))

    # --------- business data ---------
    def refresh_all(self):
        self.accounts = fetch_accounts(include_inactive=True)
        self.account_map = {a[0]: self._account_display(a) for a in self.accounts}
        dashboard.refresh(self)
        accounts.refresh(self)
        transactions.refresh(self)

    def _account_display(self, arow):
        aid, name, atype, parent_id, currency, initbal, is_active = arow
        status = "" if is_active else " (inactive)"
        return f"[{atype}] {name}{status}"

    def active_account_ids(self):
        return [a[0] for a in self.accounts if a[6] == 1]

    # --------- appearance ---------
    def apply_theme(self, theme: str):
        theme = (theme or "light").lower()
        self.theme = "dark" if theme.startswith("d") else "light"

        if self.theme == "dark":
            palette = {
                "bg": "#1e1e1e",
                "fg": "#e6e6e6",
                "muted": "#b8b8b8",
                "panel": "#252526",
                "border": "#3a3a3a",
                "tab_sel": "#151515",
                "tab_unsel": "#252526",
                "tree_bg": "#1f1f1f",
                "tree_fg": "#e6e6e6",
                "tree_sel": "#3d3d3d",
            }
            card_colors = ["#2b4c7e", "#275d38", "#7a4a1b", "#6b2d5c"]
        else:
            palette = {
                "bg": "#f5f6f8",
                "fg": "#1f1f1f",
                "muted": "#4a4a4a",
                "panel": "#ffffff",
                "border": "#d9d9d9",
                "tab_sel": "#e9eef9",
                "tab_unsel": "#ffffff",
                "tree_bg": "#ffffff",
                "tree_fg": "#1f1f1f",
                "tree_sel": "#dfe8ff",
            }
            card_colors = ["#e9f2ff", "#e8f7ee", "#fff3e5", "#f7e9f5"]

        self._palette = palette
        try:
            self.configure(bg=palette["bg"])
        except Exception:
            pass

        s = self.style
        s.configure("TFrame", background=palette["bg"])
        s.configure("TLabel", background=palette["bg"], foreground=palette["fg"])
        s.configure("TLabelframe", background=palette["bg"], foreground=palette["fg"])
        s.configure("TLabelframe.Label", background=palette["bg"], foreground=palette["fg"])

        s.configure("TEntry", fieldbackground=palette["panel"], foreground=palette["fg"])
        s.configure("TCombobox", fieldbackground=palette["panel"], foreground=palette["fg"])

        # Tabs: selected is darker, size is consistent
        s.configure("App.TNotebook", background=palette["bg"], borderwidth=0)
        s.configure(
            "App.TNotebook.Tab",
            padding=(16, 10),
            background=palette["tab_unsel"],
            foreground=palette["fg"],
        )
        s.map(
            "App.TNotebook.Tab",
            background=[("selected", palette["tab_sel"])],
            foreground=[("selected", palette["fg"])],
        )

        s.configure(
            "Topbar.TFrame"
        )
        s.configure("Topbar.TLabel", background=self.topbar_bg, foreground=self.topbar_fg)
        s.configure(
            "TopbarTitle.TLabel",
            background=self.topbar_bg,
            foreground=self.topbar_fg,
            font=("Segoe UI", 18, "bold"),
        )

        s.configure(
            "Accent.TButton",
            padding=(12, 7),
            background=self.accent,
            foreground="#ffffff",
            bordercolor=self.accent,
            focusthickness=2,
            focuscolor=self.accent,
        )
        s.map("Accent.TButton", background=[("active", self.accent)], foreground=[("active", "#ffffff")])

        s.configure("Muted.TLabel", background=palette["bg"], foreground=palette["muted"])
        s.configure("Footer.TLabel", background=palette["bg"], foreground=palette["muted"])

        s.configure(
            "Treeview",
            background=palette["tree_bg"],
            fieldbackground=palette["tree_bg"],
            foreground=palette["tree_fg"],
            bordercolor=palette["border"],
            rowheight=24,
        )
        s.map(
            "Treeview",
            background=[("selected", palette["tree_sel"])],
            foreground=[("selected", palette["tree_fg"])],
        )
        s.configure("Treeview.Heading", background=palette["panel"], foreground=palette["fg"])

        for idx, c in enumerate(card_colors, start=1):
            s.configure(f"Card{idx}.TFrame", background=c, relief="solid", borderwidth=1)
            s.configure(
                f"Card{idx}.Title.TLabel",
                background=c,
                foreground=palette["muted"],
                font=("Segoe UI", 10, "bold"),
            )
            s.configure(
                f"Card{idx}.Value.TLabel",
                background=c,
                foreground=palette["fg"],
                font=("Segoe UI", 16, "bold"),
            )

        # Update transaction row tags if the widget exists
        try:
            if hasattr(self, "tx_tree"):
                self.tx_tree.tag_configure("pos_amount", foreground=self.pos_amount_color)
                self.tx_tree.tag_configure("neg_amount", foreground=self.neg_amount_color)
        except Exception:
            pass

    # --------- menu actions ---------
    def _open_settings(self):
        SettingsWindow(self)

    def _open_calculator(self):
        # cross-platform attempt
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["calc"], shell=True)
                return
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Calculator"])
                return
            # linux
            for cmd in (["gnome-calculator"], ["kcalc"], ["xcalc"]):
                try:
                    subprocess.Popen(cmd)
                    return
                except Exception:
                    continue
            messagebox.showinfo("Calculator", "Calculator not found on this system.")
        except Exception:
            messagebox.showinfo("Calculator", "Could not open calculator.")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export transactions",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        rows = fetch_transactions()
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "date", "description", "location", "category", "amount", "account_id"])
            for r in rows:
                w.writerow(r)
        messagebox.showinfo("Export", "Transactions exported.")

    def _import_csv(self):
        path = filedialog.askopenfilename(title="Import transactions", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        imported = 0
        with open(path, "r", newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    insert_transaction(
                        row["date"],
                        row["description"],
                        row.get("location") or None,
                        row.get("category") or None,
                        float(row["amount"]),
                        int(row["account_id"]),
                    )
                    imported += 1
                except Exception:
                    continue
        self.refresh_all()
        messagebox.showinfo("Import", f"Imported {imported} transactions.")


def run_app():
    app = MoneyManagerApp()
    app.mainloop()
