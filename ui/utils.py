from __future__ import annotations


def attach_treeview_sorting(tree, columns: list[tuple[str, str]]):
    """Enable click-to-sort on a ttk.Treeview.

    columns: list of (col_id, kind) where kind is one of:
        - "text"  : case-insensitive string
        - "float" : numeric (supports 1,234.56 format)
        - "date"  : ISO date strings (YYYY-MM-DD)
    """

    state = {"col": None, "reverse": False}

    def _key(kind: str, val: str):
        v = (val or "").strip()
        if kind == "float":
            try:
                return float(v.replace(",", ""))
            except Exception:
                return 0.0
        if kind == "date":
            return v  # ISO strings sort lexicographically
        return v.lower()

    def sort_by(col_id: str, kind: str):
        if state["col"] == col_id:
            state["reverse"] = not state["reverse"]
        else:
            state["col"] = col_id
            state["reverse"] = False

        items = [(tree.set(k, col_id), k) for k in tree.get_children("")]
        items.sort(key=lambda x: _key(kind, x[0]), reverse=state["reverse"])

        for idx, (_, k) in enumerate(items):
            tree.move(k, "", idx)

    for col_id, kind in columns:
        tree.heading(col_id, command=lambda c=col_id, k=kind: sort_by(c, k))
