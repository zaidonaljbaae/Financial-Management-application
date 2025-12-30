from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser

from core.prefs import DEFAULT_PREFS, save_prefs
from core.security import (
    load_security,
    save_security,
    set_passwords,
    wipe_all_user_data,
)
from core.db import db_init


class SettingsWindow(tk.Toplevel):
    """All theme/color/layout controls live here (no buttons in the main top bar)."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.transient(app)
        self.grab_set()
        self.geometry("760x520")

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True)

        self.tab_appearance = ttk.Frame(self.nb)
        self.tab_colors = ttk.Frame(self.nb)
        self.tab_lists = ttk.Frame(self.nb)
        self.tab_security = ttk.Frame(self.nb)
        self.nb.add(self.tab_appearance, text="Appearance")
        self.nb.add(self.tab_colors, text="Colors")
        self.nb.add(self.tab_lists, text="Lists")
        self.nb.add(self.tab_security, text="Security")

        self._build_appearance()
        self._build_colors()
        self._build_lists()
        self._build_security()

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")

    # ---------------- Appearance ----------------
    def _build_appearance(self):
        frm = self.tab_appearance
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Theme", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.theme_var = tk.StringVar(value=self.app.prefs.get("theme", "dark"))
        ttk.Radiobutton(frm, text="Dark", variable=self.theme_var, value="dark").grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(frm, text="Light", variable=self.theme_var, value="light").grid(row=2, column=0, sticky="w")

        ttk.Separator(frm).grid(row=3, column=0, columnspan=2, sticky="ew", pady=16)

        ttk.Label(frm, text="Tabs", font=("Segoe UI", 12, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 10))
        ttk.Label(frm, text="Selected tab background is automatically darker in dark theme.").grid(row=5, column=0, columnspan=2, sticky="w")

        ttk.Button(frm, text="Apply Theme", style="Accent.TButton", command=self._apply_theme).grid(row=10, column=1, sticky="e", pady=(20, 0))

    def _apply_theme(self):
        self.app.prefs["theme"] = self.theme_var.get().strip() or "dark"
        save_prefs(self.app.prefs)
        self.app.apply_theme(self.app.prefs["theme"])
        self.app.refresh_all()

    # ---------------- Colors ----------------
    def _build_colors(self):
        frm = self.tab_colors
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Main colors", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.accent_var = tk.StringVar(value=self.app.prefs.get("accent", DEFAULT_PREFS["accent"]))
        self.topbar_bg_var = tk.StringVar(value=self.app.prefs.get("topbar_bg", DEFAULT_PREFS["topbar_bg"]))
        self.topbar_fg_var = tk.StringVar(value=self.app.prefs.get("topbar_fg", DEFAULT_PREFS["topbar_fg"]))
        self.pos_var = tk.StringVar(value=self.app.prefs.get("pos_amount_color", DEFAULT_PREFS["pos_amount_color"]))
        self.neg_var = tk.StringVar(value=self.app.prefs.get("neg_amount_color", DEFAULT_PREFS["neg_amount_color"]))

        def pick(var: tk.StringVar):
            c = colorchooser.askcolor(initialcolor=var.get(), parent=self)
            if c and c[1]:
                var.set(c[1])

        def color_row(r, label, var):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=6)
            ent = ttk.Entry(frm, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", pady=6, padx=(0, 10))
            ttk.Button(frm, text="Pick", command=lambda v=var: pick(v)).grid(row=r, column=2, sticky="e")

        color_row(1, "Accent", self.accent_var)
        color_row(2, "Top bar background", self.topbar_bg_var)
        color_row(3, "Top bar text", self.topbar_fg_var)
        color_row(4, "Positive amount", self.pos_var)
        color_row(5, "Negative amount", self.neg_var)

        ttk.Separator(frm).grid(row=6, column=0, columnspan=3, sticky="ew", pady=16)

        ttk.Label(frm, text="Category colors (optional)", font=("Segoe UI", 12, "bold")).grid(row=7, column=0, sticky="w")
        ttk.Label(frm, text="If a category has a custom color, it overrides +/− amount colors.").grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.cat_tree = ttk.Treeview(frm, columns=("category", "color"), show="headings", height=10)
        self.cat_tree.heading("category", text="Category")
        self.cat_tree.heading("color", text="Color")
        self.cat_tree.column("category", width=280)
        self.cat_tree.column("color", width=140)
        self.cat_tree.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=6)
        frm.rowconfigure(9, weight=1)

        cat_btns = ttk.Frame(frm)
        cat_btns.grid(row=9, column=2, sticky="ns", padx=(10, 0))
        ttk.Button(cat_btns, text="Add", command=self._cat_add).pack(fill="x", pady=(0, 6))
        ttk.Button(cat_btns, text="Edit", command=self._cat_edit).pack(fill="x", pady=(0, 6))
        ttk.Button(cat_btns, text="Remove", command=self._cat_remove).pack(fill="x")

        self._reload_cat_tree()

        ttk.Button(frm, text="Apply Colors", style="Accent.TButton", command=self._apply_colors).grid(row=20, column=2, sticky="e", pady=(12, 0))

    def _reload_cat_tree(self):
        for i in self.cat_tree.get_children():
            self.cat_tree.delete(i)
        cats = dict(self.app.prefs.get("category_colors", {}) or {})
        for k in sorted(cats.keys()):
            self.cat_tree.insert("", "end", values=(k, cats[k]))

    def _cat_selected(self):
        sel = self.cat_tree.selection()
        if not sel:
            return None
        vals = self.cat_tree.item(sel[0], "values")
        return vals[0], vals[1]

    def _cat_add(self):
        self._cat_editor(None)

    def _cat_edit(self):
        sel = self._cat_selected()
        if not sel:
            messagebox.showinfo("Category Colors", "Select a category first.")
            return
        self._cat_editor(sel)

    def _cat_remove(self):
        sel = self._cat_selected()
        if not sel:
            messagebox.showinfo("Category Colors", "Select a category first.")
            return
        cat, _ = sel
        cats = dict(self.app.prefs.get("category_colors", {}) or {})
        cats.pop(cat, None)
        self.app.prefs["category_colors"] = cats
        save_prefs(self.app.prefs)
        self._reload_cat_tree()

    def _cat_editor(self, existing):
        win = tk.Toplevel(self)
        win.title("Category Color")
        win.transient(self)
        win.grab_set()
        win.geometry("420x220")

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        cat_var = tk.StringVar(value=(existing[0] if existing else ""))
        col_var = tk.StringVar(value=(existing[1] if existing else "#ffffff"))

        ttk.Label(frm, text="Category").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=cat_var).grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(frm, text="Color").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=col_var).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(frm, text="Pick", command=lambda: self._pick(col_var)).grid(row=1, column=2, padx=(8, 0))

        def save():
            cat = cat_var.get().strip()
            if not cat:
                messagebox.showerror("Category", "Category name is required.")
                return
            cats = dict(self.app.prefs.get("category_colors", {}) or {})
            cats[cat] = col_var.get().strip() or "#ffffff"
            self.app.prefs["category_colors"] = cats
            save_prefs(self.app.prefs)
            win.destroy()
            self._reload_cat_tree()

        actions = ttk.Frame(frm)
        actions.grid(row=10, column=0, columnspan=3, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(actions, text="Save", style="Accent.TButton", command=save).pack(side="right", padx=8)

    def _pick(self, var: tk.StringVar):
        c = colorchooser.askcolor(initialcolor=var.get(), parent=self)
        if c and c[1]:
            var.set(c[1])

    def _apply_colors(self):
        self.app.prefs.update(
            {
                "accent": self.accent_var.get().strip() or DEFAULT_PREFS["accent"],
                "topbar_bg": self.topbar_bg_var.get().strip() or DEFAULT_PREFS["topbar_bg"],
                "topbar_fg": self.topbar_fg_var.get().strip() or DEFAULT_PREFS["topbar_fg"],
                "pos_amount_color": self.pos_var.get().strip() or DEFAULT_PREFS["pos_amount_color"],
                "neg_amount_color": self.neg_var.get().strip() or DEFAULT_PREFS["neg_amount_color"],
            }
        )
        save_prefs(self.app.prefs)
        self.app.apply_theme(self.app.prefs.get("theme", "dark"))
        self.app.refresh_all()

    # ---------------- Lists ----------------
    def _build_lists(self):
        frm = self.tab_lists
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Sources", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        ttk.Label(frm, text="Used in Transactions → Source (supermarket, bakery, ...). You can type a new source there and it will be added automatically.").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        self.src_list = tk.Listbox(frm, height=14)
        self.src_list.grid(row=2, column=0, sticky="nsew")
        frm.rowconfigure(2, weight=1)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=1, sticky="ns", padx=(10, 0))
        ttk.Button(btns, text="Add", command=self._src_add).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Edit", command=self._src_edit).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Remove", command=self._src_remove).pack(fill="x")

        ttk.Button(frm, text="Save Sources", style="Accent.TButton", command=self._src_save).grid(row=3, column=1, sticky="e", pady=(12, 0))

        self._src_reload()

    def _src_reload(self):
        self.src_list.delete(0, tk.END)
        for s in (self.app.prefs.get("sources", []) or []):
            self.src_list.insert(tk.END, s)

    def _src_selected_index(self):
        sel = self.src_list.curselection()
        return sel[0] if sel else None

    def _src_add(self):
        self._src_editor(None)

    def _src_edit(self):
        idx = self._src_selected_index()
        if idx is None:
            messagebox.showinfo("Sources", "Select a source first.")
            return
        self._src_editor((idx, self.src_list.get(idx)))

    def _src_remove(self):
        idx = self._src_selected_index()
        if idx is None:
            messagebox.showinfo("Sources", "Select a source first.")
            return
        self.src_list.delete(idx)

    def _src_editor(self, existing):
        win = tk.Toplevel(self)
        win.title("Source")
        win.transient(self)
        win.grab_set()
        win.geometry("420x180")

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        val = existing[1] if existing else ""
        src_var = tk.StringVar(value=val)

        ttk.Label(frm, text="Source name").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(frm, textvariable=src_var).grid(row=0, column=1, sticky="ew", pady=8)

        def save_one():
            s = src_var.get().strip()
            if not s:
                messagebox.showerror("Source", "Source name is required.")
                return
            if existing:
                idx, _old = existing
                self.src_list.delete(idx)
                self.src_list.insert(idx, s)
            else:
                self.src_list.insert(tk.END, s)
            win.destroy()

        actions = ttk.Frame(frm)
        actions.grid(row=10, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(actions, text="Save", style="Accent.TButton", command=save_one).pack(side="right", padx=8)

    def _src_save(self):
        vals = []
        for i in range(self.src_list.size()):
            v = self.src_list.get(i).strip()
            if v and v not in vals:
                vals.append(v)
        if not vals:
            vals = DEFAULT_PREFS.get("sources", [])
        self.app.prefs["sources"] = vals
        save_prefs(self.app.prefs)
        messagebox.showinfo("Sources", "Saved.")

    # ---------------- Security ----------------
    def _build_security(self):
        frm = self.tab_security
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Passwords", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        ttk.Label(frm, text="Change the program password and the database password.").grid(row=1, column=0, columnspan=2, sticky="w")

        self.new_prog_var = tk.StringVar()
        self.new_db_var = tk.StringVar()

        ttk.Label(frm, text="New program password").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frm, textvariable=self.new_prog_var, show="•").grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Button(frm, text="Save Passwords", style="Accent.TButton", command=self._save_passwords).grid(row=4, column=1, sticky="e", pady=(10, 0))

        ttk.Separator(frm).grid(row=10, column=0, columnspan=2, sticky="ew", pady=16)

        ttk.Label(frm, text="Danger zone", font=("Segoe UI", 12, "bold")).grid(row=11, column=0, sticky="w")
        ttk.Label(frm, text="This deletes ALL user data (database + UI prefs + passwords) and recreates an empty DB.").grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Button(frm, text="Reset all data", command=self._reset_all_data).grid(row=13, column=1, sticky="e")

    def _save_passwords(self):
        p = self.new_prog_var.get()
        d = self.new_db_var.get()
        if len(p) < 4 or len(d) < 4:
            messagebox.showerror("Passwords", "Use at least 4 characters for each password.")
            return
        set_passwords(p, d)
        messagebox.showinfo("Passwords", "Passwords updated.")
        self.new_prog_var.set("")
        self.new_db_var.set("")

    def _reset_all_data(self):
        if not messagebox.askyesno("Reset", "Delete ALL user data (including transactions) and reset the app?"):
            return
        wipe_all_user_data()
        db_init()
        messagebox.showinfo("Reset", "User data deleted and database recreated.")
        self.app.reload_prefs_and_refresh()
