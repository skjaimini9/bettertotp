import os
import sys
import getpass
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from btotp.vault import Vault
from btotp.core import generate_code
from btotp.clipboard import copy_to_clipboard
from btotp.secret import generate_secret, b32_to_secret
from btotp.uri import parse_otpauth
from btotp.config import load_config


ICON_PATH = None
_icon_dir = os.path.join(os.path.dirname(__file__), "assets")
if os.path.exists(_icon_dir):
    icon_candidates = ["icon.png", "icon.ico", "icon.gif"]
    for name in icon_candidates:
        p = os.path.join(_icon_dir, name)
        if os.path.exists(p):
            ICON_PATH = p
            break


class UnlockView(tk.Frame):
    def __init__(self, parent, switch_to_main):
        super().__init__(parent)
        self.switch_to_main = switch_to_main
        self.vault = Vault()
        self._build()

    def _build(self):
        self.configure(bg="#f0f0f0")
        frame = tk.Frame(self, bg="#f0f0f0")
        frame.place(relx=0.5, rely=0.4, anchor="center")

        tk.Label(frame, text="BetterTOTP", font=("Helvetica", 24, "bold"),
                 bg="#f0f0f0", fg="#1565C0").pack(pady=(0, 4))
        tk.Label(frame, text="Time-based one-time passwords", font=("Helvetica", 10),
                 bg="#f0f0f0", fg="#666").pack(pady=(0, 20))

        tk.Label(frame, text="Master password:", bg="#f0f0f0",
                 anchor="w").pack(fill="x")
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(frame, textvariable=self.password_var,
                                        show="*", width=30, font=("Helvetica", 12))
        self.password_entry.pack(fill="x", pady=(4, 12))
        self.password_entry.focus_set()

        self.status_var = tk.StringVar()
        tk.Label(frame, textvariable=self.status_var, fg="red",
                 bg="#f0f0f0").pack()

        btn_frame = tk.Frame(frame, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=(4, 0))

        if self.vault.exists():
            tk.Button(btn_frame, text="Unlock", command=self._unlock,
                      bg="#1565C0", fg="white", width=12,
                      font=("Helvetica", 11)).pack(side="left", padx=(0, 8))
        else:
            tk.Button(btn_frame, text="Create Vault", command=self._create,
                      bg="#1565C0", fg="white", width=12,
                      font=("Helvetica", 11)).pack(side="left", padx=(0, 8))

        self.password_entry.bind("<Return>", lambda e: self._unlock() if self.vault.exists() else self._create())

    def _unlock(self):
        pw = self.password_var.get()
        if not pw:
            self.status_var.set("Enter a password")
            return
        try:
            self.vault.unlock(pw)
            self.switch_to_main(self.vault)
        except Exception as e:
            self.status_var.set(f"Wrong password: {e}")

    def _create(self):
        pw = self.password_var.get()
        if len(pw) < 4:
            self.status_var.set("Password must be at least 4 chars")
            return
        try:
            self.vault.create(pw)
            self.switch_to_main(self.vault)
        except Exception as e:
            self.status_var.set(f"Error: {e}")


class MainView(tk.Frame):
    def __init__(self, parent, vault: Vault, on_logout):
        super().__init__(parent)
        self.vault = vault
        self.on_logout = on_logout
        self._running = True
        self._build()
        self._refresh_loop()

    def _build(self):
        self.configure(bg="#f0f0f0")

        # Top bar
        top = tk.Frame(self, bg="#1565C0", height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="BetterTOTP", font=("Helvetica", 14, "bold"),
                 bg="#1565C0", fg="white").pack(side="left", padx=12)
        tk.Button(top, text="Lock", command=self._do_logout,
                  bg="#1565C0", fg="white", bd=1, relief="solid",
                  font=("Helvetica", 10)).pack(side="right", padx=8)
        tk.Button(top, text="+ Add", command=self._add_account,
                  bg="#1565C0", fg="white", bd=1, relief="solid",
                  font=("Helvetica", 10)).pack(side="right", padx=8)

        # Account list
        list_frame = tk.Frame(self, bg="#f0f0f0")
        list_frame.pack(fill="both", expand=True, padx=12, pady=(12, 4))

        columns = ("name", "issuer", "code", "period")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                 selectmode="browse", height=15)
        self.tree.heading("name", text="Account")
        self.tree.heading("issuer", text="Issuer")
        self.tree.heading("code", text="Current Code")
        self.tree.heading("period", text="Period")

        self.tree.column("name", width=180, minwidth=120)
        self.tree.column("issuer", width=120, minwidth=80)
        self.tree.column("code", width=180, minwidth=140, anchor="center")
        self.tree.column("period", width=80, minwidth=60, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<ButtonRelease-1>", self._on_single_click)

        # Bottom action bar
        bottom = tk.Frame(self, bg="#f0f0f0")
        bottom.pack(fill="x", padx=12, pady=(4, 12))

        tk.Button(bottom, text="Copy Selected", command=self._copy_selected,
                  font=("Helvetica", 10)).pack(side="left", padx=(0, 8))
        tk.Button(bottom, text="Copy All", command=self._copy_all,
                  font=("Helvetica", 10)).pack(side="left", padx=(0, 8))
        tk.Button(bottom, text="Delete Selected", command=self._delete_selected,
                  font=("Helvetica", 10)).pack(side="right")

        self._click_timer = None
        self._populate()

    def _populate(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            accounts = self.vault.list_accounts()
            for acc in accounts:
                code = "------"
                try:
                    secret = bytes.fromhex(acc["secret"])
                    code = generate_code(
                        secret,
                        algorithm=acc.get("algorithm", "sha512"),
                        code_length=acc.get("digits", 12),
                        time_step=acc.get("period", 45),
                    )
                except Exception:
                    pass
                issuer = acc.get("issuer", "")
                period = f"{acc.get('period', 45)}s"
                self.tree.insert("", "end", iid=acc["name"],
                                 values=(acc["name"], issuer, code, period))
        except Exception:
            pass

    def _refresh_loop(self):
        if not self._running:
            return
        self._populate()
        self.after(1000, self._refresh_loop)

    def _on_single_click(self, event):
        if self._click_timer:
            self.after_cancel(self._click_timer)
            self._click_timer = None
        self._click_timer = self.after(400, self._copy_selected)

    def _on_double_click(self, event):
        if self._click_timer:
            self.after_cancel(self._click_timer)
            self._click_timer = None
        self._show_detail()

    def _copy_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if values:
            copy_to_clipboard(values[2])
            self._flash_status(f"Copied {values[2]}")

    def _copy_all(self):
        codes = []
        for child in self.tree.get_children():
            v = self.tree.item(child, "values")
            if v:
                codes.append(f"{v[0]}: {v[2]}")
        text = "\n".join(codes)
        copy_to_clipboard(text)
        self._flash_status(f"Copied {len(codes)} codes")

    def _show_detail(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        name = values[0]
        try:
            acc = self.vault.get(name)
            secret_hex = acc["secret"]
            msg = (
                f"Account: {name}\n"
                f"Issuer: {acc.get('issuer', '—')}\n"
                f"Algorithm: {acc.get('algorithm', 'sha512')}\n"
                f"Digits: {acc.get('digits', 12)}\n"
                f"Period: {acc.get('period', 45)}s\n"
                f"Secret: {secret_hex[:16]}...\n\n"
                f"Current code: {values[2]}"
            )
            messagebox.showinfo("Account Detail", msg, parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        name = sel[0]
        if messagebox.askyesno("Delete", f"Delete account '{name}'?", parent=self):
            try:
                self.vault.remove(name)
                self.tree.delete(name)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)

    def _add_account(self):
        AddAccountDialog(self, self.vault)

    def _do_logout(self):
        self._running = False
        self.vault._password = None
        self.on_logout()

    def _flash_status(self, msg):
        self.status_bar = getattr(self, "_status_label", None)
        if not self.status_bar:
            self.status_bar = tk.Label(self, text="", bg="#e0e0e0", anchor="w")
            self.status_bar.pack(fill="x", side="bottom")
            self._status_label = self.status_bar
        self.status_bar.config(text=msg)
        self.after(2500, lambda: self.status_bar.config(text=""))


class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, vault):
        super().__init__(parent)
        self.vault = vault
        self.title("Add Account")
        self.geometry("420x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, padx=16, pady=16)
        frame.pack(fill="both", expand=True)

        row = 0
        tk.Label(frame, text="Account name:").grid(row=row, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.name_var, width=30).grid(row=row, column=1, pady=4)
        row += 1

        tk.Label(frame, text="Secret (hex or empty to generate):").grid(row=row, column=0, sticky="w", pady=4)
        self.secret_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.secret_var, width=30).grid(row=row, column=1, pady=4)
        row += 1

        tk.Label(frame, text="Issuer:").grid(row=row, column=0, sticky="w", pady=4)
        self.issuer_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.issuer_var, width=30).grid(row=row, column=1, pady=4)
        row += 1

        tk.Label(frame, text="Algorithm:").grid(row=row, column=0, sticky="w", pady=4)
        self.algo_var = tk.StringVar(value="sha512")
        ttk.Combobox(frame, textvariable=self.algo_var,
                     values=["sha1", "sha256", "sha512"], state="readonly",
                     width=12).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        tk.Label(frame, text="Digits:").grid(row=row, column=0, sticky="w", pady=4)
        self.digits_var = tk.StringVar(value="12")
        tk.Spinbox(frame, from_=4, to=20, textvariable=self.digits_var,
                   width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        tk.Label(frame, text="Period (s):").grid(row=row, column=0, sticky="w", pady=4)
        self.period_var = tk.StringVar(value="45")
        tk.Spinbox(frame, from_=10, to=120, textvariable=self.period_var,
                   width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(16, 0))
        tk.Button(btn_frame, text="Add", command=self._add,
                  bg="#1565C0", fg="white", width=10).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left")

        self.status_var = tk.StringVar()
        tk.Label(frame, textvariable=self.status_var, fg="red").grid(
            row=row + 1, column=0, columnspan=2, pady=4)

    def _add(self):
        name = self.name_var.get().strip()
        if not name:
            self.status_var.set("Name is required")
            return

        secret_hex = self.secret_var.get().strip()
        if not secret_hex:
            secret_hex = generate_secret().hex()

        try:
            self.vault.add(
                name, secret_hex,
                issuer=self.issuer_var.get().strip(),
                algorithm=self.algo_var.get(),
                digits=int(self.digits_var.get()),
                period=int(self.period_var.get()),
            )
            self.destroy()
        except Exception as e:
            self.status_var.set(str(e))


def main():
    root = tk.Tk()
    root.title("BetterTOTP")
    root.geometry("700x500")
    root.minsize(600, 400)
    if ICON_PATH:
        try:
            icon = tk.PhotoImage(file=ICON_PATH)
            root.iconphoto(True, icon)
        except Exception:
            pass

    container = tk.Frame(root)
    container.pack(fill="both", expand=True)

    def show_unlock():
        for w in container.winfo_children():
            w.destroy()
        UnlockView(container, show_main).pack(fill="both", expand=True)

    def show_main(vault):
        for w in container.winfo_children():
            w.destroy()
        MainView(container, vault, show_unlock).pack(fill="both", expand=True)

    show_unlock()
    root.mainloop()


if __name__ == "__main__":
    main()
