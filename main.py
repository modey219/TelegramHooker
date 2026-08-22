import os, sys, asyncio, threading, json, base64, hashlib, time, traceback, uuid
from pathlib import Path

_CRASH_LOG = Path("/sdcard/Download/crash.log")

def _write_crash(tb_str):
    try:
        _CRASH_LOG.write_text(tb_str, "utf-8")
    except Exception:
        pass

_init_excepthook = sys.excepthook
def _my_excepthook(exc_type, exc_value, exc_tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _write_crash(tb_str)
    _init_excepthook(exc_type, exc_value, exc_tb)
sys.excepthook = _my_excepthook

_orig_thread_run = threading.Thread.run
def _safe_thread_run(self):
    try:
        _orig_thread_run(self)
    except Exception:
        tb_str = "".join(traceback.format_exception(*sys.exc_info()))
        _write_crash(tb_str)
threading.Thread.run = _safe_thread_run

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_LOG_LEVEL"] = "critical"

try:
    import certifi
except ImportError:
    pass

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import platform

APP_NAME = "Telegram Hooker"
APP_VERSION = "8.0"
COPYRIGHT = "@ASEQX12"

BG = (0.05, 0.05, 0.10, 1)
CARD = (0.10, 0.10, 0.18, 1)
INPUT_BG = (0.14, 0.14, 0.24, 1)
ACCENT = (0.25, 0.65, 1.0, 1)
GREEN = (0.18, 0.80, 0.44, 1)
RED = (1.0, 0.30, 0.30, 1)
YELLOW = (1.0, 0.82, 0.20, 1)
ORANGE = (1.0, 0.55, 0.15, 1)
WHITE = (1, 1, 1, 1)
DIM = (0.45, 0.45, 0.55, 1)
DIM2 = (0.30, 0.30, 0.40, 1)

if platform == "android":
    HOME = Path("/sdcard/Download")
else:
    HOME = Path(os.path.expanduser("~"))
CONFIG_DIR = HOME / ".telegram_hooker"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"
KEY_FILE = CONFIG_DIR / ".key"
LICENSE_FILE = CONFIG_DIR / ".license"

SUPABASE_URL = "https://wsvvxmsgarpwbjbbskar.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndzdnZ4bXNnYXJwd2JqYmJza2FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcyNDIyNTMsImV4cCI6MjEwMjgxODI1M30.Ds2Xi3Q5P6HIF4mG2TrsLQlqxeww80V8LHWzt9fQRA8"

if platform == "android":
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.INTERNET,
            Permission.RECORD_AUDIO,
            Permission.MODIFY_AUDIO_SETTINGS,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.READ_EXTERNAL_STORAGE,
        ])
    except Exception:
        pass


def get_device_id():
    try:
        if platform == "android":
            from jnius import autoclass
            Settings = autoclass('android.provider.Settings')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            android_id = Settings.Secure.getString(
                activity.getContentResolver(),
                Settings.Secure.ANDROID_ID
            )
            if android_id and android_id != "unknown":
                return hashlib.sha256(android_id.encode()).hexdigest()[:32]
        import platform as pf
        machine_id = str(uuid.getnode())
        return hashlib.sha256(machine_id.encode()).hexdigest()[:32]
    except Exception:
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
        resp = urllib.request.urlopen(req, timeout=20)
        raw = json.loads(resp.read().decode("utf-8"))
        if isinstance(raw, bool):
            valid = raw
        elif isinstance(raw, dict):
            valid = raw.get("valid", True)
        elif isinstance(raw, str):
            valid = raw.lower() in ("true", "ok", "activated", "valid")
        else:
            valid = bool(raw)
        if valid:
            try:
                url2 = f"{SUPABASE_URL}/rest/v1/rpc/get_license_info"
                req2 = urllib.request.Request(url2,
                       json.dumps({"p_code": code}).encode(), method="POST")
                req2.add_header("apikey", SUPABASE_ANON_KEY)
                req2.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
                req2.add_header("Content-Type", "application/json")
                resp2 = urllib.request.urlopen(req2, timeout=10)
                info = json.loads(resp2.read().decode())
                if info:
                    return {"valid": True, "expires_at": info.get("expires_at"),
                            "is_active": info.get("is_active")}
            except Exception:
                pass
            return {"valid": True}
        return {"valid": False, "error": "Invalid activation code"}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if "Invalid activation code" in body:
            return {"valid": False, "error": "Invalid activation code"}
        elif "Code already activated" in body:
            return {"valid": False, "error": "Code already activated on another device"}
        return {"valid": False, "error": f"Server error: {e.code}"}
    except Exception as e:
        return {"valid": False, "error": f"Connection failed: {str(e)[:60]}"}


class Cipher:
    _key = None

    @classmethod
    def _get_key(cls):
        if cls._key:
            return cls._key
        if KEY_FILE.exists():
            cls._key = KEY_FILE.read_bytes()
        else:
            cls._key = hashlib.sha256(os.urandom(32)).digest()
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            KEY_FILE.write_bytes(cls._key)
        return cls._key

    @classmethod
    def _xor(cls, data, key):
        out = bytearray(len(data))
        for i in range(len(data)):
            out[i] = data[i] ^ key[i % len(key)]
        return bytes(out)

    @classmethod
    def encrypt(cls, data):
        key = cls._get_key()
        iv = os.urandom(16)
        raw = data.encode("utf-8")
        encrypted = cls._xor(raw, hashlib.sha256(key + iv).digest() * ((len(raw) // 32) + 1))
        return base64.b64encode(iv + encrypted).decode("ascii")

    @classmethod
    def decrypt(cls, token):
        key = cls._get_key()
        raw = base64.b64decode(token)
        iv, encrypted = raw[:16], raw[16:]
        decrypted = cls._xor(encrypted, hashlib.sha256(key + iv).digest() * ((len(encrypted) // 32) + 1))
        return decrypted.decode("utf-8")


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text("utf-8"))
            out = {}
            for k, v in raw.items():
                if isinstance(v, str) and v.startswith("ENC:"):
                    try:
                        out[k] = Cipher.decrypt(v[4:])
                    except Exception:
                        out[k] = v
                else:
                    out[k] = v
            return out
        except Exception:
            return {}
    return {}


def save_config(cfg):
    ensure_dirs()
    enc = {}
    sensitive = {"api_id", "api_hash", "phone"}
    for k, v in cfg.items():
        if k in sensitive and isinstance(v, str) and v:
            enc[k] = "ENC:" + Cipher.encrypt(v)
        else:
            enc[k] = v
    CONFIG_FILE.write_text(json.dumps(enc, indent=2), "utf-8")


def load_license():
    if LICENSE_FILE.exists():
        try:
            raw = json.loads(LICENSE_FILE.read_text("utf-8"))
            return raw.get("code", ""), raw.get("device_id", "")
        except Exception:
            pass
    return "", ""


def save_license(code, device_id, expires_at=None):
    ensure_dirs()
    data = {
        "code": code, "device_id": device_id,
        "activated_at": time.time(), "time": time.time()
    }
    if expires_at:
        data["expires_at"] = expires_at
    LICENSE_FILE.write_text(json.dumps(data), "utf-8")


def get_license_remaining_days(code):
    if not code:
        return None
    from datetime import datetime, timezone, timedelta
    try:
        if LICENSE_FILE.exists():
            raw = json.loads(LICENSE_FILE.read_text("utf-8"))
            exp = raw.get("expires_at")
            if exp:
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    diff = (exp_dt - datetime.now(timezone.utc)).days
                    return "Lifetime" if diff > 3650 else max(diff, 0)
                except Exception:
                    pass
    except Exception:
        pass
    try:
        import urllib.request
        url = f"{SUPABASE_URL}/rest/v1/rpc/get_license_info"
        req = urllib.request.Request(url,
               json.dumps({"p_code": code}).encode(), method="POST")
        req.add_header("apikey", SUPABASE_ANON_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_ANON_KEY}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=10)
        info = json.loads(resp.read().decode())
        if info and info.get("expires_at"):
            exp_dt = datetime.fromisoformat(info["expires_at"].replace("Z", "+00:00"))
            diff = (exp_dt - datetime.now(timezone.utc)).days
            return "Lifetime" if diff > 3650 else max(diff, 0)
    except Exception:
        pass
    return None


class AsyncThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coro(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


_bg = AsyncThread()
try:
    _bg.start()
except Exception:
    pass


def run_async(coro):
    return _bg.run_coro(coro)


def dp_(v):
    return dp(v)


class StyledButton(Button):
    def __init__(self, text, color=ACCENT, callback=None, h=None, fs=14, **kw):
        super().__init__(
            text=text, font_size=dp_(fs), bold=True,
            background_normal="", background_color=color,
            color=WHITE, size_hint_y=None, height=h or dp_(48), **kw,
        )
        self._btn_color = color
        self.bind(pos=self._draw_bg, size=self._draw_bg)
        if callback:
            self.bind(on_press=callback)

    def _draw_bg(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._btn_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp_(10)])


class StyledInput(TextInput):
    def __init__(self, placeholder="", password=False, **kw):
        super().__init__(
            hint_text=placeholder, hint_text_color=DIM,
            font_size=dp_(14), background_color=INPUT_BG,
            foreground_color=WHITE, cursor_color=ACCENT,
            multiline=False, size_hint_y=None, height=dp_(46),
            padding=[dp_(12), dp_(10)], password=password, **kw,
        )


def draw_card(w):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*CARD)
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(12)])


def _draw_top(w):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*ACCENT[:3], 0.08)
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(20)])


class ActivationScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = BoxLayout(orientation="vertical", padding=dp_(24), spacing=dp_(8))

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=dp_(10), size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))

        top = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_(160))
        top.bind(pos=lambda i, v: _draw_top(i))
        top.bind(size=lambda i, v: _draw_top(i))
        top.add_widget(Label(
            text="[b][color=#40A8FF]TELEGRAM[/color] [color=#FFFFFF]HOOKER[/color][/b]",
            markup=True, font_size=dp_(28),
        ))
        top.add_widget(Label(
            text=f"v{APP_VERSION}  |  {COPYRIGHT}", font_size=dp_(13), color=DIM,
        ))
        top.add_widget(Label(
            text="[color=#FFD700]Activation Required[/color]", markup=True,
            font_size=dp_(14),
        ))
        sc.add_widget(top)

        sc.add_widget(Label(text="[color=#40A8FF]Enter your activation code[/color]", markup=True,
                           font_size=dp_(13), size_hint_y=None, height=dp_(20)))

        self.code_input = StyledInput("TH-XXXX-XXXX-XXXX")
        sc.add_widget(self.code_input)

        sc.add_widget(StyledButton("ACTIVATE", GREEN, self.do_activate, dp_(52), 16))

        self.status = Label(text="", font_size=dp_(13), color=YELLOW,
                           size_hint_y=None, height=dp_(40))
        sc.add_widget(self.status)

        sc.add_widget(Label(
            text="[color=#808090]Get your code from @ASEQX12[/color]", markup=True,
            font_size=dp_(11), size_hint_y=None, height=dp_(20)))

        if _CRASH_LOG.exists():
            sc.add_widget(StyledButton("VIEW CRASH LOG", RED, self._show_crash, dp_(36), 11))

        scroll.add_widget(sc)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def do_activate(self, *a):
        code = self.code_input.text.strip().upper()
        if not code:
            self.status.text = "[color=#FF4D4D]Enter a code[/color]"
            self.status.markup = True
            return

        self.status.text = "[color=#FFD700]Validating...[/color]"
        self.status.markup = True
        Clock.schedule_once(lambda dt: self._validate(code), 0.1)

    def _validate(self, code):
        async def _go():
            try:
                device_id = get_device_id()
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: validate_license_online(code, device_id)
                )
                if result.get("valid"):
                    expires_at = result.get("expires_at")
                    save_license(code, device_id, expires_at)
                    Clock.schedule_once(lambda dt: self._on_success(expires_at), 0)
                else:
                    err = result.get("error", "Invalid code")
                    Clock.schedule_once(lambda dt: self._on_fail(err), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._on_fail(str(e)[:80]), 0)
        run_async(_go())

    def _on_success(self, expires_at=None):
        from datetime import datetime, timezone
        days_str = ""
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                diff = (exp_dt - datetime.now(timezone.utc)).days
                if diff > 3650:
                    days_str = "Lifetime"
                else:
                    days_str = f"{diff} days remaining"
            except Exception:
                pass
        if days_str:
            msg = f"[color=#4DFF88]Activated![/color]  [color=#FFD700]{days_str}[/color]"
        else:
            msg = "[color=#4DFF88]Activated![/color]"
        self.status.text = msg
        self.status.markup = True
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "login"), 1.2)

    def _on_fail(self, err):
        self.status.text = f"[color=#FF4D4D]{err}[/color]"
        self.status.markup = True

    def _show_crash(self, *a):
        try:
            crash_text = _CRASH_LOG.read_text("utf-8")[-300:]
            self.status.text = f"[color=#FF4D4D]{crash_text[:80]}[/color]"
            self.status.markup = True
        except Exception:
            self.status.text = "[color=#FF4D4D]No crash log found[/color]"
            self.status.markup = True


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = BoxLayout(orientation="vertical", padding=dp_(24), spacing=dp_(8))

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=dp_(10), size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))

        top = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_(140))
        top.bind(pos=lambda i, v: _draw_top(i))
        top.bind(size=lambda i, v: _draw_top(i))
        top.add_widget(Label(
            text="[b][color=#40A8FF]TELEGRAM[/color] [color=#FFFFFF]HOOKER[/color][/b]",
            markup=True, font_size=dp_(28),
        ))
        top.add_widget(Label(
            text=f"v{APP_VERSION}  |  {COPYRIGHT}", font_size=dp_(13), color=DIM,
        ))
        sc.add_widget(top)

        sc.add_widget(Label(text="[color=#40A8FF]API Credentials[/color]", markup=True,
                           font_size=dp_(13), size_hint_y=None, height=dp_(20), halign="left"))

        self.api_id = StyledInput("API ID (from my.telegram.org)")
        self.api_hash = StyledInput("API Hash")
        self.phone = StyledInput("+1234567890")
        sc.add_widget(self.api_id)
        sc.add_widget(self.api_hash)
        sc.add_widget(self.phone)

        sc.add_widget(StyledButton("LOGIN", GREEN, self.do_login, dp_(52), 16))
        sc.add_widget(StyledButton("RESTORE SESSION", ACCENT, self.do_restore))

        self.status = Label(text="", font_size=dp_(13), color=YELLOW,
                           size_hint_y=None, height=dp_(28))
        sc.add_widget(self.status)

        sc.add_widget(Label(text=f"  {COPYRIGHT} - All Rights Reserved",
                           font_size=dp_(11), color=DIM2,
                           size_hint_y=None, height=dp_(24)))

        scroll.add_widget(sc)
        layout.add_widget(scroll)
        self.add_widget(layout)

        cfg = load_config()
        self.api_id.text = str(cfg.get("api_id", ""))
        self.api_hash.text = cfg.get("api_hash", "")
        self.phone.text = cfg.get("phone", "")

    def do_login(self, *a):
        ai, ah, ph = self.api_id.text.strip(), self.api_hash.text.strip(), self.phone.text.strip()
        if not ai or not ah or not ph:
            self.status.text = "[color=#FF4D4D]Fill all fields[/color]"
            self.status.markup = True
            return
        self.status.text = "[color=#FFD700]Connecting...[/color]"
        self.status.markup = True
        Clock.schedule_once(lambda dt: self._login(ai, ah, ph), 0.1)

    def _login(self, ai, ah, ph):
        async def _go():
            try:
                from pyrogram import Client
                app = Client(str(SESSIONS_DIR / "session_temp"),
                             api_id=int(ai), api_hash=ah, phone_number=ph)
                await app.start()
                me = await app.get_me()
                await app.stop()
                save_config({"api_id": ai, "api_hash": ah, "phone": ph,
                            "username": me.username or "", "name": me.first_name or ""})
                Clock.schedule_once(lambda dt: self._ok(me), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._err(str(e)), 0)
        run_async(_go())

    def _ok(self, me):
        name = me.first_name or me.username or "User"
        self.status.text = f"[color=#4DFF88]Welcome {name}![/color]"
        self.status.markup = True
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "main"), 0.8)

    def _err(self, e):
        self.status.text = f"[color=#FF4D4D]{e[:80]}[/color]"
        self.status.markup = True

    def do_restore(self, *a):
        sessions = [f.stem for f in SESSIONS_DIR.glob("*.session")]
        if not sessions:
            self.status.text = "[color=#FF4D4D]No saved sessions[/color]"
            self.status.markup = True
            return
        self.status.text = "[color=#FFD700]Restoring...[/color]"
        self.status.markup = True
        Clock.schedule_once(lambda dt: self._restore(sessions[-1]), 0.1)

    def _restore(self, name):
        async def _go():
            try:
                from pyrogram import Client
                cfg = load_config()
                app = Client(str(SESSIONS_DIR / name),
                             api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])
                await app.start()
                me = await app.get_me()
                await app.stop()
                save_config({**cfg, "username": me.username or "", "name": me.first_name or ""})
                Clock.schedule_once(lambda dt: self._ok(me), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._err(str(e)), 0)
        run_async(_go())


class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.pytgcalls = None
        self.client = None
        self.current_chat_id = None
        self.is_muted = False
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp_(16), spacing=dp_(6))

        header = BoxLayout(size_hint_y=None, height=dp_(50))
        header.bind(pos=draw_card)
        header.bind(size=draw_card)
        hdr_left = BoxLayout(orientation="vertical", size_hint_x=0.7)
        hdr_left.add_widget(Label(text="[b]TELEGRAM HOOKER[/b]", markup=True,
                                  font_size=dp_(17), color=ACCENT, halign="left"))
        hdr_left.add_widget(Label(text=f"v{APP_VERSION} | {COPYRIGHT}", font_size=dp_(10), color=DIM, halign="left"))
        saved_code3, _ = load_license()
        rd3 = get_license_remaining_days(saved_code3)
        if rd3 == "Lifetime":
            lic_txt = "License: Lifetime"
            lic_col = GREEN
        elif rd3 is not None:
            lic_txt = f"License: {rd3}d left" if rd3 > 0 else "License: EXPIRED"
            lic_col = GREEN if rd3 > 7 else YELLOW if rd3 > 0 else RED
        elif saved_code3:
            lic_txt = "License: Active"
            lic_col = GREEN
        else:
            lic_txt = "No License"
            lic_col = RED
        hdr_left.add_widget(Label(text=lic_txt, font_size=dp_(9), color=lic_col, halign="left"))
        hdr_right = BoxLayout(size_hint_x=0.3)
        hdr_right.add_widget(StyledButton("Settings", DIM, lambda x: setattr(self.manager, "current", "settings"), dp_(32), 11))
        header.add_widget(hdr_left)
        header.add_widget(hdr_right)

        self.status_lbl = Label(text="Ready", font_size=dp_(12), color=GREEN,
                               size_hint_y=None, height=dp_(20), halign="left")
        self.call_lbl = Label(text="[color=#808090]Not in call[/color]", markup=True,
                             font_size=dp_(12), size_hint_y=None, height=dp_(20), halign="left")
        self.mic_lbl = Label(text="[color=#FF4D4D]MUTED[/color]", markup=True,
                            font_size=dp_(12), size_hint_y=None, height=dp_(20), halign="left")

        self.target_input = StyledInput("Group ID or @username")

        call_card = BoxLayout(orientation="vertical", spacing=dp_(6), size_hint_y=None, height=dp_(170))
        call_card.bind(pos=draw_card)
        call_card.bind(size=draw_card)
        call_card.add_widget(Label(text="[b]VOICE CALL[/b]", markup=True, font_size=dp_(14),
                                  color=ACCENT, size_hint_y=None, height=dp_(26), halign="left"))

        row1 = BoxLayout(spacing=dp_(8), size_hint_y=None, height=dp_(42))
        row1.add_widget(StyledButton("JOIN", GREEN, self.do_join, dp_(42), 13))
        row1.add_widget(StyledButton("LEAVE", RED, self.do_leave, dp_(42), 13))
        call_card.add_widget(row1)

        row2 = BoxLayout(spacing=dp_(8), size_hint_y=None, height=dp_(42))
        row2.add_widget(StyledButton("MUTE", ORANGE, self.do_mute, dp_(42), 13))
        row2.add_widget(StyledButton("UNMUTE", YELLOW, self.do_unmute, dp_(42), 13))
        call_card.add_widget(row2)

        self.engine_lbl = Label(text="Engine: checking...", font_size=dp_(11), color=DIM,
                               size_hint_y=None, height=dp_(20), halign="left")
        call_card.add_widget(self.engine_lbl)

        row3 = BoxLayout(spacing=dp_(8), size_hint_y=None, height=dp_(42))
        row3.add_widget(StyledButton("START ENGINE", GREEN, self.do_start_engine, dp_(42), 12))
        call_card.add_widget(row3)

        msg_card = BoxLayout(orientation="vertical", spacing=dp_(4), size_hint_y=None, height=dp_(90))
        msg_card.bind(pos=draw_card)
        msg_card.bind(size=draw_card)
        self.msg_input = StyledInput("Message to send...")
        msg_card.add_widget(self.msg_input)
        msg_card.add_widget(StyledButton("SEND", ACCENT, self.do_send, dp_(34), 12))

        log_scroll = ScrollView(size_hint_y=None, height=dp_(80))
        self.log_lbl = Label(text="[color=#808090]Ready[/color]", markup=True,
                            font_size=dp_(11), halign="left", valign="top",
                            size_hint_y=None, text_size=(Window.width - dp_(40), None))
        self.log_lbl.bind(texture_size=lambda i, v: setattr(self.log_lbl, "height", max(dp_(60), v[1] + dp_(8))))
        log_scroll.add_widget(self.log_lbl)

        btn_logout = StyledButton("LOGOUT", DIM2, self.do_logout, dp_(36), 11)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", spacing=dp_(6), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        for w in [header, self.status_lbl, self.call_lbl, self.mic_lbl,
                  self.target_input, call_card, msg_card, log_scroll, btn_logout]:
            content.add_widget(w)
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def log(self, msg, color=DIM):
        c = "#{:02x}{:02x}{:02x}".format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self.log_lbl.text = f"[color={c}]{msg}[/color]"
        self.log_lbl.markup = True

    def on_enter(self):
        cfg = load_config()
        user = cfg.get("name") or cfg.get("username") or ""
        if user:
            self.status_lbl.text = f"Logged in: {user}"
        self._check_engine()

    def _check_engine(self):
        try:
            import ntgcalls
            import pytgcalls
            self.engine_lbl.text = "Engine: READY (ntgcalls + pytgcalls)"
            self.engine_lbl.color = GREEN
            self.log("Voice engine loaded!", GREEN)
        except Exception:
            self.engine_lbl.text = "Engine: Not installed (optional)"
            self.engine_lbl.color = YELLOW
            self.log("Voice engine not available", ORANGE)

    def do_start_engine(self, *a):
        self.log("Checking voice engine...", YELLOW)
        self._check_engine()

    def _get_client(self):
        cfg = load_config()
        if not cfg.get("api_id"):
            return None
        sessions = [f.stem for f in SESSIONS_DIR.glob("*.session")]
        if not sessions:
            return None
        from pyrogram import Client
        return Client(str(SESSIONS_DIR / sessions[-1]),
                      api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])

    def do_join(self, *a):
        target = self.target_input.text.strip()
        if not target:
            self.log("Enter a group ID first", RED)
            return
        self.log("Connecting to call...", YELLOW)
        Clock.schedule_once(lambda dt: self._join(target), 0.1)

    def _join(self, target):
        async def _go():
            try:
                from pytgcalls import PyTgCalls
                from pytgcalls.media_devices import InputDevice, SpeakerDevice
                from pytgcalls.types.stream.media_stream import MediaStream

                client = self._get_client()
                if not client:
                    Clock.schedule_once(lambda dt: self.log("Not logged in", RED), 0)
                    return
                await client.start()

                self.client = client
                if not self.pytgcalls:
                    self.pytgcalls = PyTgCalls(client)
                    await self.pytgcalls.start()

                chat = await client.get_chat(target)
                chat_id = chat.id

                if self.current_chat_id and self.current_chat_id != chat_id:
                    try:
                        await self.pytgcalls.leave_call(self.current_chat_id)
                    except Exception:
                        pass

                mic = InputDevice("pulse_input", "pulse", False)
                stream = MediaStream(mic, audio_flags=MediaStream.Flags.REQUIRED)
                await self.pytgcalls.play(chat_id, stream)

                speaker = SpeakerDevice("pulse_output", "pulse")
                try:
                    await self.pytgcalls.record(chat_id, speaker)
                except Exception:
                    pass

                try:
                    await self.pytgcalls.mute(chat_id)
                    self.is_muted = True
                except Exception:
                    pass

                self.current_chat_id = chat_id
                Clock.schedule_once(lambda dt: self._on_joined(chat_id, target), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {str(e)[:120]}", RED), 0)
        run_async(_go())

    def _on_joined(self, chat_id, target):
        self.call_lbl.text = f"[color=#4DFF88]In call: {target}[/color]"
        self.call_lbl.markup = True
        self.mic_lbl.text = "[color=#FF4D4D]MUTED[/color]"
        self.mic_lbl.markup = True
        self.log("Joined!", GREEN)

    def do_mute(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call", RED); return
        async def _go():
            try:
                await self.pytgcalls.mute(self.current_chat_id)
                self.is_muted = True
                Clock.schedule_once(lambda dt: self._mic_state(True), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {e}", RED), 0)
        run_async(_go())

    def do_unmute(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call", RED); return
        async def _go():
            try:
                await self.pytgcalls.unmute(self.current_chat_id)
                self.is_muted = False
                Clock.schedule_once(lambda dt: self._mic_state(False), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {e}", RED), 0)
        run_async(_go())

    def _mic_state(self, muted):
        self.mic_lbl.text = "[color=#FF4D4D]MUTED[/color]" if muted else "[color=#4DFF88]LIVE[/color]"
        self.mic_lbl.markup = True
        self.log("Mic muted" if muted else "Mic active", ORANGE if muted else GREEN)

    def do_leave(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call", RED); return
        async def _go():
            try:
                await self.pytgcalls.leave_call(self.current_chat_id)
            except Exception:
                pass
            self.current_chat_id = None
            self.is_muted = False
            Clock.schedule_once(lambda dt: self._on_leave(), 0)
        run_async(_go())

    def _on_leave(self):
        self.call_lbl.text = "[color=#808090]Not in call[/color]"
        self.call_lbl.markup = True
        self.mic_lbl.text = "[color=#FF4D4D]MUTED[/color]"
        self.mic_lbl.markup = True
        self.log("Left call", YELLOW)

    def do_send(self, *a):
        target = self.target_input.text.strip()
        text = self.msg_input.text.strip()
        if not target or not text:
            self.log("Enter target + message", RED); return
        self.log("Sending...", YELLOW)
        async def _go():
            try:
                client = self._get_client()
                if not client:
                    Clock.schedule_once(lambda dt: self.log("Not logged in", RED), 0); return
                await client.start()
                chat = await client.get_chat(target)
                await client.send_message(chat.id, text)
                await client.stop()
                self.msg_input.text = ""
                Clock.schedule_once(lambda dt: self.log(f"Sent to {target}", GREEN), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {str(e)[:80]}", RED), 0)
        run_async(_go())

    def do_logout(self, *a):
        async def _go():
            if self.pytgcalls and self.current_chat_id:
                try:
                    await self.pytgcalls.leave_call(self.current_chat_id)
                except Exception:
                    pass
        run_async(_go())
        self.current_chat_id = None
        self.pytgcalls = None
        self.client = None
        save_config({})
        self.manager.current = "login"


class SettingsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=dp_(16), spacing=dp_(8))

        header = BoxLayout(size_hint_y=None, height=dp_(48))
        header.add_widget(Label(text="[b]SETTINGS[/b]", markup=True, font_size=dp_(20),
                               color=ACCENT, halign="left", valign="middle"))
        header.add_widget(StyledButton("Back", DIM, lambda x: setattr(self.manager, "current", "main"), dp_(36), 12))
        root.add_widget(header)

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=dp_(8), size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))

        def section(t):
            return Label(text=f"[b]{t}[/b]", markup=True, font_size=dp_(15), color=ACCENT,
                        size_hint_y=None, height=dp_(32), halign="left")

        def info(t, c=DIM, s=12):
            return Label(text=t, font_size=dp_(s), color=c, size_hint_y=None, height=dp_(18), halign="left")

        sc.add_widget(section("Account"))
        self.api_id_lbl = info("---")
        self.api_hash_lbl = info("---")
        self.user_lbl = info("---")
        sc.add_widget(self.api_id_lbl)
        sc.add_widget(self.api_hash_lbl)
        sc.add_widget(self.user_lbl)

        sc.add_widget(section("Voice Engine"))
        try:
            import ntgcalls
            import pytgcalls
            sc.add_widget(info("ntgcalls: OK", GREEN, 11))
            sc.add_widget(info("pytgcalls: OK", GREEN, 11))
        except Exception:
            sc.add_widget(info("Not available (optional)", ORANGE, 11))
        sc.add_widget(info("Audio: PulseAudio + ALSA", DIM, 11))
        sc.add_widget(info("Codec: Opus 48kHz", DIM, 11))

        sc.add_widget(section("Security"))
        saved_code2, _ = load_license()
        rd = get_license_remaining_days(saved_code2)
        if rd == "Lifetime":
            sc.add_widget(info("License: Lifetime", GREEN, 11))
        elif rd is not None:
            color = GREEN if rd > 7 else YELLOW if rd > 0 else RED
            sc.add_widget(info(f"License: {rd} days left", color, 11))
        elif saved_code2:
            sc.add_widget(info("License: Active", GREEN, 11))
        else:
            sc.add_widget(info("License: None", RED, 11))
        sc.add_widget(info("Device binding: active", GREEN, 11))
        sc.add_widget(info("API keys encrypted on device", GREEN, 11))
        sc.add_widget(info("Session files local only", GREEN, 11))

        sc.add_widget(section("About"))
        sc.add_widget(info(f"{APP_NAME} v{APP_VERSION}", WHITE, 13))
        sc.add_widget(info(f"Copyright {COPYRIGHT} - All Rights Reserved", DIM, 12))
        sc.add_widget(info("Kivy + Pyrogram + PyTgCalls", DIM, 10))

        sc.add_widget(Label(text="", size_hint_y=None, height=dp_(20)))
        sc.add_widget(info(f"  {COPYRIGHT} 2026", DIM2, 11))

        scroll.add_widget(sc)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        cfg = load_config()
        ai = cfg.get("api_id", "")
        ah = cfg.get("api_hash", "")
        user = cfg.get("name") or cfg.get("username") or "---"
        if ai:
            self.api_id_lbl.text = f"API ID: {ai[:4]}{'*' * max(0, len(ai)-4)}"
        if ah:
            masked = ah[:4] + "****" + ah[-4:] if len(ah) > 8 else "****"
            self.api_hash_lbl.text = f"API Hash: {masked}"
        self.user_lbl.text = f"User: {user}"


class TelegramHookerApp(App):
    def build(self):
        self.title = APP_NAME
        try:
            icon_path = Path(os.path.dirname(os.path.abspath(__file__))) / "icon.png"
            if icon_path.exists():
                self.icon = str(icon_path)
        except Exception:
            pass

        sm = ScreenManager(transition=SlideTransition(direction="left", duration=0.2))

        saved_code, saved_device = load_license()
        device_id = get_device_id()
        license_ok = saved_code and saved_device == device_id

        sm.add_widget(ActivationScreen(name="activation"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(SettingsScreen(name="settings"))

        if license_ok:
            sm.current = "login"
        else:
            sm.current = "activation"

        return sm

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    try:
        ensure_dirs()
        TelegramHookerApp().run()
    except Exception:
        tb_str = "".join(traceback.format_exception(*sys.exc_info()))
        _write_crash(tb_str)
