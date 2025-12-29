from __future__ import annotations

import tkinter as tk

from ui.app import run_app, MoneyManagerApp
from ui.auth import authenticate_or_setup


def main():
    # Create a hidden root for auth dialogs
    root = tk.Tk()
    ok = authenticate_or_setup(root)
    root.withdraw()
    print("AUTH START")
    # print("AUTH RESULT:", ok)

    root.destroy()
    if not ok:
        return

    run_app()


if __name__ == "__main__":
    main()
