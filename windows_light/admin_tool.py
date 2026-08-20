import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json, urllib.request, urllib.error, hashlib, threading, time
from datetime import datetime

SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY_HERE"

FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
HEADER_FONT = ("Segoe UI", 18, "bold")
TITLE_FONT = ("Consolas", 14, "bold")


def api_call(rpc_name, params):
    url = f"{SUPABASE_URL}/rest/rpc/{rpc_name}"
    payload = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"Server error {e.code}: {body[:100]}"}
    except Exception as e:
        return {"error": f"Connection failed: {str(e)[:80]}"}


def api_get(table, query=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}{query}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return []


def _lighten(hex_color, factor=1.15):
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    except: return "#777777"


def _darken(hex_color, factor=0.75):
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    except: return "#555555"


def _btn(parent, text, cmd=None, bg="#0984e3", fg="white", **kw):
    btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                    font=FONT_BOLD, bd=0, relief='flat', cursor='hand2',
                    activebackground=_darken(bg), activeforeground="white",
                    highlightthickness=0, **kw)
    btn.bind("<Enter>", lambda e, b=btn, c=_lighten(bg): b.config(bg=c))
    btn.bind("<Leave>", lambda e, b=btn, c=bg: b.config(bg=c))
    return btn


class AdminTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Hooker - Code Generator | @ASEQX12")
        self.root.geometry("700x750")
        self.root.configure(bg="#0b0b12")
        self.root.resizable(True, True)

        tk.Label(root, text="CODE GENERATOR", font=HEADER_FONT, fg="#00d2d3", bg="#0b0b12").pack(pady=(15, 5))
        tk.Label(root, text="@ASEQX12 - License Management Tool", font=FONT, fg="#667788", bg="#0b0b12").pack()

        tk.Frame(root, bg="#1a1a2e", height=1).pack(fill='x', padx=15, pady=10)

        gen_frame = tk.Frame(root, bg="#0b0b12")
        gen_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(gen_frame, text="Generate New Code", font=FONT_BOLD, fg="#00d2d3", bg="#0b0b12").pack(anchor="w")

        row = tk.Frame(gen_frame, bg="#0b0b12")
        row.pack(fill="x", pady=3)
        tk.Label(row, text="Max Devices:", font=FONT, fg="#aaa", bg="#0b0b12").pack(side="left")
        self.max_dev = tk.Spinbox(row, from_=1, to=100, width=5, bg="#161624", fg="white", font=FONT, insertbackground="white")
        self.max_dev.pack(side="left", padx=5)
        self.max_dev.delete(0, tk.END)
        self.max_dev.insert(0, "1")

        tk.Label(row, text="Days (0=never):", font=FONT, fg="#aaa", bg="#0b0b12").pack(side="left", padx=(15,0))
        self.days = tk.Spinbox(row, from_=0, to=3650, width=6, bg="#161624", fg="white", font=FONT, insertbackground="white")
        self.days.pack(side="left", padx=5)
        self.days.delete(0, tk.END)
        self.days.insert(0, "30")

        tk.Label(gen_frame, text="Note:", font=FONT, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.note_entry = tk.Entry(gen_frame, width=50, bg="#161624", fg="white", font=FONT,
                                   insertbackground="white", bd=0, highlightthickness=1,
                                   highlightbackground='#2a2a3a', highlightcolor='#00d2d3')
        self.note_entry.pack(fill="x", pady=2)

        btn_frame = tk.Frame(gen_frame, bg="#0b0b12")
        btn_frame.pack(fill="x", pady=5)
        _btn(btn_frame, "GENERATE CODE", cmd=self.do_generate, bg="#00b894", width=20).pack(side="left", padx=3)
        _btn(btn_frame, "GENERATE x5", cmd=self.do_generate5, bg="#6c5ce7", width=15).pack(side="left", padx=3)
        _btn(btn_frame, "GENERATE x10", cmd=self.do_generate10, bg="#e84393", width=15).pack(side="left", padx=3)

        self.result_label = tk.Label(gen_frame, text="", font=("Consolas", 13, "bold"), fg="#00b894",
                                     bg="#0b0b12", wraplength=600, justify="left")
        self.result_label.pack(anchor="w", pady=5)

        tk.Frame(root, bg="#1a1a2e", height=1).pack(fill='x', padx=15, pady=5)

        rev_frame = tk.Frame(root, bg="#0b0b12")
        rev_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(rev_frame, text="Revoke Code", font=FONT_BOLD, fg="#ff4d4d", bg="#0b0b12").pack(anchor="w")
        rev_row = tk.Frame(rev_frame, bg="#0b0b12")
        rev_row.pack(fill="x", pady=2)
        self.revoke_entry = tk.Entry(rev_row, width=35, bg="#161624", fg="white", font=FONT,
                                     insertbackground="white", bd=0, highlightthickness=1,
                                     highlightbackground='#2a2a3a', highlightcolor='#ff4d4d')
        self.revoke_entry.pack(side="left", padx=(0, 8))
        _btn(rev_row, "REVOKE", cmd=self.do_revoke, bg="#d63031", width=12).pack(side="left")
        self.revoke_label = tk.Label(rev_frame, text="", font=FONT, fg="#aaa", bg="#0b0b12")
        self.revoke_label.pack(anchor="w")

        tk.Frame(root, bg="#1a1a2e", height=1).pack(fill='x', padx=15, pady=5)

        top = tk.Frame(root, bg="#0b0b12")
        top.pack(fill="x", padx=20, pady=3)
        tk.Label(top, text="All Licenses", font=FONT_BOLD, fg="#00d2d3", bg="#0b0b12").pack(side="left")
        _btn(top, "REFRESH", cmd=self.do_refresh, bg="#0984e3", width=10).pack(side="right")

        cols = ("code", "devices", "expires", "status", "note")
        tree_frame = tk.Frame(root, bg="#0b0b12")
        tree_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        style = ttk.Style()
        style.configure("Treeview", background="#121220", foreground="#ccc", fieldbackground="#121220", font=("Consolas", 10))
        style.configure("Treeview.Heading", background="#1a1a2e", foreground="#00d2d3", font=FONT_BOLD)
        style.map("Treeview", background=[("selected", "#0984e3")])

        self.tree.heading("code", text="Code")
        self.tree.heading("devices", text="Devices")
        self.tree.heading("expires", text="Expires")
        self.tree.heading("status", text="Status")
        self.tree.heading("note", text="Note")
        self.tree.column("code", width=220)
        self.tree.column("devices", width=80)
        self.tree.column("expires", width=120)
        self.tree.column("status", width=80)
        self.tree.column("note", width=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.status_bar = tk.Label(root, text="Ready", font=("Segoe UI", 9), fg="#444455", bg="#0b0b12", anchor="w")
        self.status_bar.pack(fill="x", padx=10, pady=(3, 8))

        self.do_refresh()

    def _gen_one(self):
        max_d = int(self.max_dev.get())
        d = int(self.days.get())
        n = self.note_entry.get().strip()
        result = api_call("generate_license", {"p_max_devices": max_d, "p_days": d, "p_note": n})
        return result

    def do_generate(self):
        self.result_label.config(text="Generating...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._gen_thread, args=(1,), daemon=True).start()

    def do_generate5(self):
        self.result_label.config(text="Generating 5 codes...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._gen_thread, args=(5,), daemon=True).start()

    def do_generate10(self):
        self.result_label.config(text="Generating 10 codes...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._gen_thread, args=(10,), daemon=True).start()

    def _gen_thread(self, count):
        codes = []
        for i in range(count):
            r = self._gen_one()
            if "code" in r:
                codes.append(r["code"])
            else:
                codes.append(f"Error: {r.get('error', '?')}")
            if count > 1:
                time.sleep(0.3)
        self.root.after(0, lambda: self._gen_done(codes))

    def _gen_done(self, codes):
        text = "\n".join(codes)
        self.result_label.config(text=f"Generated:\n{text}", fg="#00b894")
        self.do_refresh()

    def do_revoke(self):
        code = self.revoke_entry.get().strip()
        if not code:
            self.revoke_label.config(text="Enter a code", fg="#ff4d4d")
            return
        self.revoke_label.config(text="Revoking...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._revoke_thread, args=(code,), daemon=True).start()

    def _revoke_thread(self, code):
        result = api_call("revoke_license", {"p_code": code})
        msg = result.get("message", result.get("error", "Done"))
        color = "#00b894" if result.get("success") else "#ff4d4d"
        self.root.after(0, lambda: self.revoke_label.config(text=msg, fg=color))
        self.root.after(0, self.do_refresh)

    def do_refresh(self):
        self.status_bar.config(text="Loading licenses...")
        self.root.update()
        threading.Thread(target=self._refresh_thread, daemon=True).start()

    def _refresh_thread(self):
        data = api_get("licenses", "?select=*&order=created_at.desc")
        self.root.after(0, lambda: self._refresh_done(data))

    def _refresh_done(self, data):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for lic in (data or []):
            exp = lic.get("expires_at")
            is_expired = False
            if exp:
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    is_expired = exp_dt < datetime.now().astimezone()
                    exp = exp_dt.strftime("%Y-%m-%d")
                except:
                    pass
            else:
                exp = "Never"

            active = lic.get("is_active", True)
            status = "Active" if active and not is_expired else "Expired" if is_expired else "Revoked"

            self.tree.insert("", "end", values=(
                lic.get("code", "?"),
                f"{lic.get('active_devices', 0)}/{lic.get('max_devices', 1)}",
                exp, status, lic.get("note", "")
            ))
        self.status_bar.config(text=f"Loaded {len(data or [])} licenses")


if __name__ == "__main__":
    root = tk.Tk()
    AdminTool(root)
    root.mainloop()
