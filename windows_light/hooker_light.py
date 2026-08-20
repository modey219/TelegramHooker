import sys, subprocess, os, asyncio, threading, random, json, time, hashlib, uuid, traceback
from datetime import datetime

if os.name == 'nt':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

required_libs = {"pyrogram": "pyrogram"}
optional_libs = {"pytgcalls": "pytgcalls"}

for lib_name, pip_name in required_libs.items():
    try:
        __import__(lib_name)
    except ImportError:
        print(f"[!] {pip_name} not installed. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", pip_name])
        except Exception as e:
            print(f"[-] Failed to install {pip_name}: {e}")

for lib_name, pip_name in optional_libs.items():
    try:
        __import__(lib_name)
    except ImportError:
        print(f"[!] {pip_name} not available (optional)")

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from pyrogram import Client
from pyrogram import utils
def patched_get_peer_type(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"): return "user"
    elif peer_id_str.startswith("-100"): return "channel"
    else: return "chat"
utils.get_peer_type = patched_get_peer_type

FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
HEADER_FONT = ("Segoe UI", 16, "bold")
CONFIG_FILE = "hooker_light_config.json"
LICENSE_FILE = "hooker_light.license"
ADMIN_SECRET = "ASEQX12"

SUPABASE_URL = "https://wsvvxmsgarpwbjbbskar.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndzdnZ4bXNnYXJwd2JqYmJza2FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcyNDIyNTMsImV4cCI6MjEwMjgxODI1M30.Ds2Xi3Q5P6HIF4mG2TrsLQlqxeww80V8LHWzt9fQRA8"


def get_machine_id():
    try:
        import subprocess
        result = subprocess.run(
            ["wmic", "csproduct", "get", "UUID"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and line != "UUID" and len(line) > 10:
                return hashlib.sha256(line.encode()).hexdigest()[:32]
    except Exception:
        pass
    return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:32]


def validate_license_online(code, device_id):
    import urllib.request, urllib.error
    url = f"{SUPABASE_URL}/rest/v1/rpc/validate_license"
    payload = json.dumps({"p_code": code, "p_device_id": device_id}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"valid": False, "error": f"Server error: {e.code}"}
    except Exception as e:
        return {"valid": False, "error": f"Connection failed: {str(e)[:60]}"}


def generate_license_online(max_devices, days, note):
    import urllib.request, urllib.error
    url = f"{SUPABASE_URL}/rest/v1/rpc/generate_license"
    payload = json.dumps({
        "p_max_devices": max_devices,
        "p_days": days,
        "p_note": note
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def revoke_license_online(code):
    import urllib.request, urllib.error
    url = f"{SUPABASE_URL}/rest/v1/rpc/revoke_license"
    payload = json.dumps({"p_code": code}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def list_licenses_online():
    import urllib.request, urllib.error
    url = f"{SUPABASE_URL}/rest/v1/licenses?select=*&order=created_at.desc"
    req = urllib.request.Request(url, method="GET")
    req.add_header("apikey", SUPABASE_ANON_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return []


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_license():
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                data = json.load(f)
                return data.get("code", "")
        except: pass
    return ""


def save_license(code, days_left=-1, expires_at=None):
    with open(LICENSE_FILE, "w") as f:
        f.write(json.dumps({"code": code, "time": time.time(), "days_left": days_left, "expires_at": expires_at}))


def _lighten(hex_color, factor=1.15):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    except: return "#777777"


def _darken(hex_color, factor=0.75):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    except: return "#555555"


def _mkbtn(parent, text, cmd=None, bg="#0984e3", fg="white", **kw):
    btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                    font=FONT_BOLD, bd=0, relief='flat', cursor='hand2',
                    activebackground=_darken(bg), activeforeground="white",
                    highlightthickness=0, **kw)
    btn.bind("<Enter>", lambda e, b=btn, c=_lighten(bg): b.config(bg=c))
    btn.bind("<Leave>", lambda e, b=btn, c=bg: b.config(bg=c))
    return btn


def _sep(parent, color="#1a1a2e", pady=8):
    tk.Frame(parent, bg=color, height=1, bd=0).pack(fill='x', padx=10, pady=pady)


def _entry(parent, width=30, **kw):
    bg = kw.pop('bg', '#161624')
    fg = kw.pop('fg', '#ffffff')
    e = tk.Entry(parent, width=width, bg=bg, fg=fg, insertbackground="white",
                 bd=0, relief='flat', font=FONT, highlightthickness=1,
                 highlightbackground='#2a2a3a', highlightcolor='#00d2d3', **kw)
    e.bind("<FocusIn>", lambda ev, ent=e: ent.config(highlightbackground='#00d2d3'))
    e.bind("<FocusOut>", lambda ev, ent=e: ent.config(highlightbackground='#2a2a3a'))
    return e


class ActivationWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("TELEGRAM HOOKER - Activation")
        self.root.geometry("500x450")
        self.root.configure(bg="#0b0b12")
        self.root.resizable(False, False)

        frame = tk.Frame(root, bg="#0b0b12")
        frame.pack(expand=True, fill="both", padx=30, pady=20)

        tk.Label(frame, text="TELEGRAM HOOKER", font=("Segoe UI", 22, "bold"),
                 fg="#00d2d3", bg="#0b0b12").pack(pady=(10, 5))
        tk.Label(frame, text="Light Edition v1.0 | @ASEQX12",
                 font=FONT, fg="#667788", bg="#0b0b12").pack(pady=(0, 20))

        tk.Label(frame, text="Enter Activation Code", font=FONT_BOLD,
                 fg="#00d2d3", bg="#0b0b12").pack(anchor="w")

        self.code_entry = _entry(frame, width=40)
        self.code_entry.pack(fill="x", pady=(5, 15))
        self.code_entry.insert(0, "TH-")
        self.code_entry.icursor(3)

        _mkbtn(frame, "ACTIVATE", cmd=self.do_activate, bg="#00b894", width=25).pack(pady=5)

        self.status_label = tk.Label(frame, text="", font=FONT, fg="#ffd700", bg="#0b0b12",
                                     wraplength=400)
        self.status_label.pack(pady=10)

        tk.Label(frame, text="Get code from @ASEQX12", font=("Segoe UI", 10),
                 fg="#444455", bg="#0b0b12").pack(side="bottom")

    def do_activate(self):
        code = self.code_entry.get().strip().upper()
        if not code or code == "TH-":
            self.status_label.config(text="Enter a valid code", fg="#ff4d4d")
            return
        self.status_label.config(text="Validating...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._validate, args=(code,), daemon=True).start()

    def _validate(self, code):
        device_id = get_machine_id()
        result = validate_license_online(code, device_id)
        self.root.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result):
        if result.get("valid"):
            code = self.code_entry.get().strip().upper()
            days_left = result.get("days_left", -1)
            expires_at = result.get("expires_at")
            save_license(code, days_left, expires_at)
            if days_left and days_left > 0:
                msg = f"Activated! {days_left} days remaining"
            elif days_left == -1:
                msg = "Activated! Lifetime license"
            else:
                msg = "Activated!"
            self.status_label.config(text=msg, fg="#00b894")
            self.root.after(1500, self.on_success)
        else:
            err = result.get("error", "Invalid code")
            self.status_label.config(text=err, fg="#ff4d4d")


class TelegramHookerApp:
    def __init__(self, root, is_admin=False):
        self.root = root
        self.is_admin = is_admin
        self.root.title("TELEGRAM HOOKER - Light Edition | @ASEQX12")
        self.root.geometry("850x900")
        self.root.configure(bg="#0b0b12")
        self.root.report_callback_exception = self._report_exception

        self.app = None
        self.pytgcalls = None
        self.current_call = None
        self.current_chat_id = None
        self.is_muted = False
        self.log_suppressed = False
        self.config_data = load_config()

        self.bg_loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_bg_loop, daemon=True).start()

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#0b0b12', foreground='#ffffff')
        self.style.configure('TNotebook', background='#06060e', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#121220', foreground='#667788',
                             padding=[18, 10], font=FONT_BOLD)
        self.style.map('TNotebook.Tab',
                       background=[('selected', '#0b0b12')],
                       foreground=[('selected', '#00d2d3')])

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_main = tk.Frame(self.notebook, bg="#0b0b12")
        self.tab_log = tk.Frame(self.notebook, bg="#0b0b12")
        self.notebook.add(self.tab_main, text="  Main  ")
        self.notebook.add(self.tab_log, text="  Log  ")

        if self.is_admin:
            self.tab_admin = tk.Frame(self.notebook, bg="#0b0b12")
            self.notebook.add(self.tab_admin, text="  Admin  ")
            self._build_admin_tab()

        self._build_main_tab()
        self._build_log_tab()
        self.run_async(self.auto_connect())

    def _report_exception(self, exc, val, tb):
        self.log(f"Error: {val}")

    def _run_bg_loop(self):
        asyncio.set_event_loop(self.bg_loop)
        self.bg_loop.run_forever()

    def run_async(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.bg_loop)

    def log(self, text):
        if self.log_suppressed: return
        t = datetime.now().strftime("%H:%M:%S")
        self.root.after_idle(lambda: self.log_area.insert(tk.END, f"[{t}] {text}\n"))
        self.root.after_idle(lambda: self.log_area.see(tk.END))

    def _build_main_tab(self):
        f = self.tab_main
        tk.Label(f, text="TELEGRAM HOOKER", font=HEADER_FONT, fg="#00d2d3", bg="#0b0b12").pack(pady=8)
        tk.Label(f, text="Light Edition v1.0 | @ASEQX12", font=FONT, fg="#667788", bg="#0b0b12").pack()

        _sep(f)

        creds = tk.Frame(f, bg="#0b0b12")
        creds.pack(fill="x", padx=20, pady=5)
        tk.Label(creds, text="API ID:", font=FONT_BOLD, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.api_id_entry = _entry(creds, width=50)
        self.api_id_entry.pack(fill="x", pady=2)
        tk.Label(creds, text="API Hash:", font=FONT_BOLD, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.api_hash_entry = _entry(creds, width=50)
        self.api_hash_entry.pack(fill="x", pady=2)
        tk.Label(creds, text="Phone:", font=FONT_BOLD, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.phone_entry = _entry(creds, width=50)
        self.phone_entry.pack(fill="x", pady=2)

        cfg = load_config()
        self.api_id_entry.insert(0, cfg.get("api_id", ""))
        self.api_hash_entry.insert(0, cfg.get("api_hash", ""))
        self.phone_entry.insert(0, cfg.get("phone", ""))

        btns = tk.Frame(f, bg="#0b0b12")
        btns.pack(fill="x", padx=20, pady=5)
        _mkbtn(btns, "LOGIN", cmd=self.do_login, bg="#00b894", width=15).pack(side="left", padx=3)
        _mkbtn(btns, "RESTORE", cmd=self.do_restore, bg="#0984e3", width=15).pack(side="left", padx=3)
        _mkbtn(btns, "LOGOUT", cmd=self.do_logout, bg="#636e72", width=15).pack(side="left", padx=3)

        _sep(f)

        target_frame = tk.Frame(f, bg="#0b0b12")
        target_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(target_frame, text="Target (Group ID or @username):", font=FONT_BOLD, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.target_entry = _entry(target_frame, width=50)
        self.target_entry.pack(fill="x", pady=2)

        call_btns = tk.Frame(f, bg="#0b0b12")
        call_btns.pack(fill="x", padx=20, pady=5)
        _mkbtn(call_btns, "JOIN", cmd=self.do_join, bg="#00b894", width=12).pack(side="left", padx=3)
        _mkbtn(call_btns, "LEAVE", cmd=self.do_leave, bg="#d63031", width=12).pack(side="left", padx=3)
        _mkbtn(call_btns, "MUTE", cmd=self.do_mute, bg="#e17055", width=12).pack(side="left", padx=3)
        _mkbtn(call_btns, "UNMUTE", cmd=self.do_unmute, bg="#fdcb6e", width=12).pack(side="left", padx=3)

        _sep(f)

        msg_frame = tk.Frame(f, bg="#0b0b12")
        msg_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(msg_frame, text="Message:", font=FONT_BOLD, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.msg_entry = _entry(msg_frame, width=50)
        self.msg_entry.pack(fill="x", pady=2)
        _mkbtn(msg_frame, "SEND MESSAGE", cmd=self.do_send_msg, bg="#0984e3", width=20).pack(anchor="w", pady=3)

        self.status_label = tk.Label(f, text="Status: Ready", font=FONT, fg="#00b894", bg="#0b0b12")
        self.status_label.pack(anchor="w", padx=20, pady=5)

    def _build_log_tab(self):
        self.log_area = scrolledtext.ScrolledText(self.tab_log, bg="#06060e", fg="#aaa",
                                                  font=("Consolas", 10), insertbackground="white",
                                                  bd=0, relief='flat', state='normal')
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)

    def _build_admin_tab(self):
        f = self.tab_admin
        tk.Label(f, text="ADMIN PANEL", font=HEADER_FONT, fg="#00d2d3", bg="#0b0b12").pack(pady=8)
        tk.Label(f, text="Generate & Manage License Codes", font=FONT, fg="#667788", bg="#0b0b12").pack()

        _sep(f)

        gen = tk.Frame(f, bg="#0b0b12")
        gen.pack(fill="x", padx=20, pady=5)
        tk.Label(gen, text="Generate New Code", font=FONT_BOLD, fg="#00d2d3", bg="#0b0b12").pack(anchor="w")

        row1 = tk.Frame(gen, bg="#0b0b12")
        row1.pack(fill="x", pady=3)
        tk.Label(row1, text="Max Devices:", font=FONT, fg="#aaa", bg="#0b0b12").pack(side="left")
        self.admin_max_dev = tk.Spinbox(row1, from_=1, to=100, width=5, bg="#161624", fg="white",
                                         font=FONT, insertbackground="white")
        self.admin_max_dev.pack(side="left", padx=5)
        self.admin_max_dev.delete(0, tk.END)
        self.admin_max_dev.insert(0, "1")

        tk.Label(row1, text="Days (0=never):", font=FONT, fg="#aaa", bg="#0b0b12").pack(side="left", padx=(15,0))
        self.admin_days = tk.Spinbox(row1, from_=0, to=3650, width=5, bg="#161624", fg="white",
                                      font=FONT, insertbackground="white")
        self.admin_days.pack(side="left", padx=5)
        self.admin_days.delete(0, tk.END)
        self.admin_days.insert(0, "30")

        tk.Label(gen, text="Note:", font=FONT, fg="#aaa", bg="#0b0b12").pack(anchor="w")
        self.admin_note = _entry(gen, width=50)
        self.admin_note.pack(fill="x", pady=2)

        _mkbtn(gen, "GENERATE CODE", cmd=self.admin_generate, bg="#00b894", width=25).pack(anchor="w", pady=5)

        self.admin_result = tk.Label(gen, text="", font=("Consolas", 12, "bold"), fg="#00b894",
                                     bg="#0b0b12", wraplength=500, justify="left")
        self.admin_result.pack(anchor="w", pady=5)

        _sep(f)

        rev = tk.Frame(f, bg="#0b0b12")
        rev.pack(fill="x", padx=20, pady=5)
        tk.Label(rev, text="Revoke Code", font=FONT_BOLD, fg="#ff4d4d", bg="#0b0b12").pack(anchor="w")
        self.admin_revoke_entry = _entry(rev, width=40)
        self.admin_revoke_entry.pack(fill="x", pady=2)
        _mkbtn(rev, "REVOKE", cmd=self.admin_revoke, bg="#d63031", width=25).pack(anchor="w", pady=3)

        self.admin_revoke_result = tk.Label(rev, text="", font=FONT, fg="#aaa", bg="#0b0b12")
        self.admin_revoke_result.pack(anchor="w")

        _sep(f)

        tk.Label(f, text="All Licenses", font=FONT_BOLD, fg="#00d2d3", bg="#0b0b12").pack(anchor="w", padx=20)
        _mkbtn(f, "REFRESH LIST", cmd=self.admin_refresh, bg="#0984e3", width=15).pack(anchor="w", padx=20, pady=3)

        cols = ("code", "devices", "expires", "status", "note")
        self.admin_tree = ttk.Treeview(f, columns=cols, show="headings", height=10)
        self.admin_tree.heading("code", text="Code")
        self.admin_tree.heading("devices", text="Devices")
        self.admin_tree.heading("expires", text="Expires")
        self.admin_tree.heading("status", text="Status")
        self.admin_tree.heading("note", text="Note")
        self.admin_tree.column("code", width=200)
        self.admin_tree.column("devices", width=80)
        self.admin_tree.column("expires", width=120)
        self.admin_tree.column("status", width=80)
        self.admin_tree.column("note", width=150)
        self.admin_tree.pack(fill="x", padx=20, pady=5)

    def admin_generate(self):
        max_dev = int(self.admin_max_dev.get())
        days = int(self.admin_days.get())
        note = self.admin_note.get().strip()
        self.admin_result.config(text="Generating...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._admin_gen_thread, args=(max_dev, days, note), daemon=True).start()

    def _admin_gen_thread(self, max_dev, days, note):
        result = generate_license_online(max_dev, days, note)
        self.root.after(0, lambda: self._admin_gen_done(result))

    def _admin_gen_done(self, result):
        if "code" in result:
            self.admin_result.config(
                text=f"Code: {result['code']}\nMax Devices: {result['max_devices']}\nExpires: {result.get('expires_at', 'Never')}",
                fg="#00b894"
            )
            self.admin_note.delete(0, tk.END)
            self.admin_refresh()
        else:
            self.admin_result.config(text=f"Error: {result.get('error', 'Unknown')}", fg="#ff4d4d")

    def admin_revoke(self):
        code = self.admin_revoke_entry.get().strip()
        if not code:
            self.admin_revoke_result.config(text="Enter a code first", fg="#ff4d4d")
            return
        self.admin_revoke_result.config(text="Revoking...", fg="#ffd700")
        self.root.update()
        threading.Thread(target=self._admin_revoke_thread, args=(code,), daemon=True).start()

    def _admin_revoke_thread(self, code):
        result = revoke_license_online(code)
        msg = result.get("message", result.get("error", "Done"))
        color = "#00b894" if result.get("success") else "#ff4d4d"
        self.root.after(0, lambda: self.admin_revoke_result.config(text=msg, fg=color))
        self.root.after(0, self.admin_refresh)

    def admin_refresh(self):
        for item in self.admin_tree.get_children():
            self.admin_tree.delete(item)
        threading.Thread(target=self._admin_refresh_thread, daemon=True).start()

    def _admin_refresh_thread(self):
        licenses = list_licenses_online()
        self.root.after(0, lambda: self._admin_refresh_done(licenses))

    def _admin_refresh_done(self, licenses):
        for lic in licenses:
            is_expired = lic.get("expires_at") and datetime.fromisoformat(lic["expires_at"].replace("Z", "+00:00")) < datetime.now().astimezone()
            status = "Active" if lic.get("is_active") and not is_expired else "Expired" if is_expired else "Revoked"
            expires = lic.get("expires_at", "Never")
            if expires and expires != "Never":
                try:
                    expires = datetime.fromisoformat(expires.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                except: pass
            self.admin_tree.insert("", "end", values=(
                lic.get("code", "?"),
                f"{lic.get('active_devices', 0)}/{lic.get('max_devices', 1)}",
                expires,
                status,
                lic.get("note", "")
            ))

    async def auto_connect(self):
        cfg = load_config()
        if cfg.get("api_id") and cfg.get("session_name"):
            self.log("Auto-connecting...")
            await self._connect(cfg)

    async def _connect(self, cfg):
        try:
            from pyrogram import Client
            self.app = Client(
                cfg.get("session_name", "hooker_session"),
                api_id=int(cfg["api_id"]),
                api_hash=cfg["api_hash"]
            )
            await self.app.start()
            me = await self.app.get_me()
            self.root.after(0, lambda: self.status_label.config(
                text=f"Logged in: {me.first_name} (@{me.username})", fg="#00b894"))
            self.log(f"Connected as {me.first_name} (@{me.username})")
        except Exception as e:
            self.log(f"Connection error: {e}")

    def do_login(self):
        ai = self.api_id_entry.get().strip()
        ah = self.api_hash_entry.get().strip()
        ph = self.phone_entry.get().strip()
        if not ai or not ah or not ph:
            messagebox.showerror("Error", "Fill all fields")
            return
        self.status_label.config(text="Connecting...", fg="#ffd700")
        self.log("Logging in...")
        threading.Thread(target=self._login_thread, args=(ai, ah, ph), daemon=True).start()

    def _login_thread(self, ai, ah, ph):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from pyrogram import Client
            session_name = str(int(time.time()))
            app = Client(f"sessions/{session_name}", api_id=int(ai), api_hash=ah, phone_number=ph)
            loop.run_until_complete(app.start())
            me = loop.run_until_complete(app.get_me())
            loop.run_until_complete(app.stop())
            save_config({"api_id": ai, "api_hash": ah, "phone": ph,
                         "session_name": session_name, "username": me.username or "",
                         "name": me.first_name or ""})
            self.root.after(0, lambda: self._login_ok(me))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)[:80]}", fg="#ff4d4d"))

    def _login_ok(self, me):
        self.status_label.config(text=f"Logged in: {me.first_name}", fg="#00b894")
        self.log(f"Logged in as {me.first_name}")
        self.run_async(self.auto_connect())

    def do_restore(self):
        sessions = [f for f in os.listdir("sessions") if f.endswith(".session")] if os.path.exists("sessions") else []
        if not sessions:
            messagebox.showinfo("Info", "No saved sessions")
            return
        cfg = load_config()
        if cfg.get("session_name"):
            self.run_async(self.auto_connect())

    def do_logout(self):
        if self.app:
            self.run_async(self._logout())

    async def _logout(self):
        try:
            if self.app:
                await self.app.stop()
        except: pass
        self.app = None
        save_config({})
        self.status_label.config(text="Logged out", fg="#667788")
        self.log("Logged out")

    def do_join(self):
        target = self.target_entry.get().strip()
        if not target:
            messagebox.showerror("Error", "Enter a target")
            return
        self.log(f"Joining {target}...")
        self.run_async(self._join(target))

    async def _join(self, target):
        try:
            if not self.app:
                self.log("Not logged in!")
                return
            from pytgcalls import PyTgCalls
            self.pytgcalls = PyTgCalls(self.app)
            await self.pytgcalls.start()
            chat = await self.app.get_chat(target)
            await self.pytgcalls.join_group_call(chat.id, None)
            self.current_chat_id = chat.id
            self.root.after(0, lambda: self.status_label.config(text=f"In call: {target}", fg="#00b894"))
            self.log(f"Joined call: {target}")
        except Exception as e:
            self.log(f"Join error: {e}")

    def do_leave(self):
        if not self.pytgcalls or not self.current_chat_id:
            return
        self.run_async(self._leave())

    async def _leave(self):
        try:
            await self.pytgcalls.leave_group_call(self.current_chat_id)
            self.current_chat_id = None
            self.root.after(0, lambda: self.status_label.config(text="Left call", fg="#ffd700"))
            self.log("Left call")
        except Exception as e:
            self.log(f"Leave error: {e}")

    def do_mute(self):
        if not self.pytgcalls or not self.current_chat_id: return
        self.run_async(self._mute(True))

    def do_unmute(self):
        if not self.pytgcalls or not self.current_chat_id: return
        self.run_async(self._mute(False))

    async def _mute(self, mute):
        try:
            if mute:
                await self.pytgcalls.mute(self.current_chat_id)
            else:
                await self.pytgcalls.unmute(self.current_chat_id)
        except Exception as e:
            self.log(f"Mute error: {e}")

    def do_send_msg(self):
        target = self.target_entry.get().strip()
        text = self.msg_entry.get().strip()
        if not target or not text:
            messagebox.showerror("Error", "Enter target + message")
            return
        self.run_async(self._send_msg(target, text))

    async def _send_msg(self, target, text):
        try:
            chat = await self.app.get_chat(target)
            await self.app.send_message(chat.id, text)
            self.root.after(0, lambda: self.msg_entry.delete(0, tk.END))
            self.log(f"Sent to {target}")
        except Exception as e:
            self.log(f"Send error: {e}")


def main():
    root = tk.Tk()
    root.withdraw()

    saved_code = load_license()
    if saved_code:
        device_id = get_machine_id()
        result = validate_license_online(saved_code, device_id)
        if result.get("valid"):
            is_admin = saved_code == ADMIN_SECRET
            root.deiconify()
            TelegramHookerApp(root, is_admin=is_admin)
            root.mainloop()
        else:
            root.deiconify()
            ActivationWindow(root, on_success=lambda: restart_app(root))
            root.mainloop()
    else:
        root.deiconify()
        ActivationWindow(root, on_success=lambda: restart_app(root))
        root.mainloop()


def restart_app(root):
    root.destroy()
    os.execl(sys.executable, sys.executable, *sys.argv)


if __name__ == "__main__":
    os.makedirs("sessions", exist_ok=True)
    main()
