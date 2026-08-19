import os, sys, asyncio, threading, json, base64, hashlib, subprocess, time, shutil
from pathlib import Path

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import platform

APP_NAME = "Telegram Hooker"
APP_VERSION = "2.0"
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

HOME = Path(os.path.expanduser("~"))
CONFIG_DIR = HOME / ".telegram_hooker"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"
KEY_FILE = CONFIG_DIR / ".key"
TERMINAL_DIR = Path("/sdcard/Download/hooker")

if platform == "android":
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.INTERNET,
        Permission.RECORD_AUDIO,
        Permission.MODIFY_AUDIO_SETTINGS,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE,
    ])


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
    def encrypt(cls, data):
        key = cls._get_key()
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        ct = AESGCM(key).encrypt(nonce, data.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("ascii")

    @classmethod
    def decrypt(cls, token):
        key = cls._get_key()
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(token)
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode("utf-8")


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
_bg.start()


def run_async(coro):
    return _bg.run_coro(coro)


def dp_(v):
    return dp(v)


def rounded_rect(canvas_buf, pos, size, color, radius=12):
    with canvas_buf:
        Color(*color)
        RoundedRectangle(pos=pos, size=size, radius=[dp_(radius)])


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


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = BoxLayout(orientation="vertical", padding=dp_(24), spacing=dp_(8))

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=dp_(10), size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))

        top = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_(140))
        top.bind(pos=lambda i, v: self._draw_top(i))
        top.bind(size=lambda i, v: self._draw_top(i))
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

    def _draw_top(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*ACCENT[:3], 0.08)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(20)])

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
        self.current_chat_id = None
        self.is_muted = False
        self._voice_running = False
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp_(16), spacing=dp_(6))

        header = BoxLayout(size_hint_y=None, height=dp_(50))
        header.bind(pos=lambda i, v: self._draw_card(i))
        header.bind(size=lambda i, v: self._draw_card(i))
        hdr_left = BoxLayout(orientation="vertical", size_hint_x=0.7)
        hdr_left.add_widget(Label(text="[b]TELEGRAM HOOKER[/b]", markup=True,
                                  font_size=dp_(17), color=ACCENT, halign="left"))
        hdr_left.add_widget(Label(text=f"v{APP_VERSION} | {COPYRIGHT}", font_size=dp_(10), color=DIM, halign="left"))
        hdr_right = BoxLayout(size_hint_x=0.3)
        btn_s = StyledButton("Settings", DIM, lambda x: setattr(self.manager, "current", "settings"), dp_(32), 11)
        hdr_right.add_widget(btn_s)
        header.add_widget(hdr_left)
        header.add_widget(hdr_right)

        self.status_lbl = Label(text="Ready", font_size=dp_(12), color=GREEN,
                               size_hint_y=None, height=dp_(20), halign="left")
        self.call_lbl = Label(text="[color=#808090]Not in call[/color]", markup=True,
                             font_size=dp_(12), size_hint_y=None, height=dp_(20), halign="left")
        self.mic_lbl = Label(text="[color=#FF4D4D]MUTED[/color]", markup=True,
                            font_size=dp_(12), size_hint_y=None, height=dp_(20), halign="left")

        self.target_input = StyledInput("Group ID or @username")

        voice_card = BoxLayout(orientation="vertical", spacing=dp_(6), size_hint_y=None, height=dp_(130))
        voice_card.bind(pos=lambda i, v: self._draw_card(i))
        voice_card.bind(size=lambda i, v: self._draw_card(i))
        voice_card.add_widget(Label(text="[b]VOICE ENGINE[/b]", markup=True, font_size=dp_(14),
                                   color=ACCENT, size_hint_y=None, height=dp_(28), halign="left"))

        voice_row = BoxLayout(spacing=dp_(8), size_hint_y=None, height=dp_(42))
        self.btn_install = StyledButton("Install Engine", ORANGE, self.do_install_engine, dp_(42), 12)
        self.btn_start = StyledButton("Start", GREEN, self.do_start_voice, dp_(42), 12)
        self.btn_stop = StyledButton("Stop", RED, self.do_stop_voice, dp_(42), 12)
        voice_row.add_widget(self.btn_install)
        voice_row.add_widget(self.btn_start)
        voice_row.add_widget(self.btn_stop)
        voice_card.add_widget(voice_row)

        call_row = BoxLayout(spacing=dp_(8), size_hint_y=None, height=dp_(42))
        call_row.add_widget(StyledButton("JOIN", GREEN, self.do_join, dp_(42), 13))
        call_row.add_widget(StyledButton("LEAVE", RED, self.do_leave, dp_(42), 13))
        voice_card.add_widget(call_row)

        mute_row = BoxLayout(spacing=dp_(8), size_hint_y=None, height=dp_(36))
        mute_row.add_widget(StyledButton("MUTE", ORANGE, self.do_mute, dp_(36), 12))
        mute_row.add_widget(StyledButton("UNMUTE", YELLOW, self.do_unmute, dp_(36), 12))
        voice_card.add_widget(mute_row)

        msg_card = BoxLayout(orientation="vertical", spacing=dp_(4), size_hint_y=None, height=dp_(90))
        msg_card.bind(pos=lambda i, v: self._draw_card(i))
        msg_card.bind(size=lambda i, v: self._draw_card(i))
        self.msg_input = StyledInput("Message to send...")
        msg_card.add_widget(self.msg_input)
        msg_card.add_widget(StyledButton("SEND MESSAGE", ACCENT, self.do_send, dp_(34), 12))

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
                  self.target_input, voice_card, msg_card, log_scroll, btn_logout]:
            content.add_widget(w)
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def _draw_card(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(12)])

    def log(self, msg, color=DIM):
        c = "#{:02x}{:02x}{:02x}".format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self.log_lbl.text = f"[color={c}]{msg}[/color]"
        self.log_lbl.markup = True

    def on_enter(self):
        cfg = load_config()
        user = cfg.get("name") or cfg.get("username") or ""
        if user:
            self.status_lbl.text = f"Logged in: {user}"
        self._check_voice_engine()

    def _check_voice_engine(self):
        if TERMINAL_DIR.exists() and (TERMINAL_DIR / "1_light_android.py").exists():
            self.log("Voice engine found", GREEN)
        else:
            self.log("Voice engine not installed", ORANGE)

    def _run_termux_cmd(self, cmd):
        try:
            result = subprocess.run(
                ["termux-exec", "-c", cmd],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip(), result.returncode
        except FileNotFoundError:
            pass
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["su", "-c", f"run-as com.termux termux-exec -c '{cmd}'"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip(), result.returncode
        except Exception:
            pass
        return None, -1

    def do_install_engine(self, *a):
        self.log("Installing voice engine...", YELLOW)
        Clock.schedule_once(lambda dt: self._install_engine(), 0.1)

    def _install_engine(self):
        try:
            termux_dir = Path("/data/data/com.termux")
            if not termux_dir.exists():
                self.log("Termux not installed!", RED)
                return
            pkg_dir = Path("/data/data/com.termux/files/usr")
            if not pkg_dir.exists():
                self.log("Termux not configured!", RED)
                return

            scripts_dir = TERMINAL_DIR
            scripts_dir.mkdir(parents=True, exist_ok=True)

            src_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            for name in ["start.sh", "hooker.py"]:
                src = src_dir / "terminal" / name
                if src.exists():
                    shutil.copy2(str(src), str(scripts_dir / name))

            boot = scripts_dir / "start.sh"
            if boot.exists():
                import stat
                boot.chmod(boot.stat().st_mode | stat.S_IEXEC)

            self.log("Voice engine installed!", GREEN)
        except Exception as e:
            self.log(f"Install failed: {str(e)[:60]}", RED)

    def do_start_voice(self, *a):
        self.log("Starting voice engine...", YELLOW)
        Clock.schedule_once(lambda dt: self._start_voice(), 0.1)

    def _start_voice(self):
        try:
            script = TERMINAL_DIR / "start.sh"
            if not script.exists():
                self.log("Engine not installed - tap Install", RED)
                return
            subprocess.Popen(
                ["sh", str(script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._voice_running = True
            self.log("Voice engine started!", GREEN)
            self.status_lbl.text = "Voice engine active"
            self.status_lbl.color = GREEN
        except Exception as e:
            self.log(f"Start failed: {str(e)[:60]}", RED)

    def do_stop_voice(self, *a):
        try:
            subprocess.run(["pkill", "-f", "hooker.py"], capture_output=True, timeout=5)
            subprocess.run(["pkill", "-f", "start.sh"], capture_output=True, timeout=5)
            self._voice_running = False
            self.log("Voice engine stopped", ORANGE)
            self.status_lbl.text = "Engine stopped"
            self.status_lbl.color = DIM
        except Exception as e:
            self.log(f"Stop failed: {str(e)[:60]}", RED)

    def do_join(self, *a):
        target = self.target_input.text.strip()
        if not target:
            self.log("Enter a group ID first", RED)
            return
        self.log("Joining...", YELLOW)
        Clock.schedule_once(lambda dt: self._join(target), 0.1)

    def _join(self, target):
        async def _go():
            try:
                from pyrogram import Client
                from pytgcalls import PyTgCalls
                from pytgcalls.media_devices import InputDevice, SpeakerDevice
                from pytgcalls.types.stream.media_stream import MediaStream

                cfg = load_config()
                sessions = [f.stem for f in SESSIONS_DIR.glob("*.session")]
                if not sessions:
                    Clock.schedule_once(lambda dt: self.log("Not logged in", RED), 0)
                    return
                path = str(SESSIONS_DIR / sessions[-1])
                client = Client(path, api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])
                await client.start()

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
                Clock.schedule_once(lambda dt: self.log(f"Error: {str(e)[:100]}", RED), 0)
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
                Clock.schedule_once(lambda dt: self.log(f"Mute failed: {e}", RED), 0)
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
                Clock.schedule_once(lambda dt: self.log(f"Unmute failed: {e}", RED), 0)
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
                cfg = load_config()
                sessions = [f.stem for f in SESSIONS_DIR.glob("*.session")]
                if not sessions:
                    Clock.schedule_once(lambda dt: self.log("Not logged in", RED), 0); return
                from pyrogram import Client
                client = Client(str(SESSIONS_DIR / sessions[-1]),
                                api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])
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
        sc.add_widget(info(f"Engine path: {TERMINAL_DIR}", DIM, 11))
        sc.add_widget(info("Install Termux from F-Droid first", ORANGE, 11))
        sc.add_widget(info("Engine uses PulseAudio for real mic", DIM, 11))

        sc.add_widget(section("Security"))
        sc.add_widget(info("AES-256-GCM encryption", GREEN, 11))
        sc.add_widget(info("API keys stored encrypted on device", GREEN, 11))
        sc.add_widget(info("Session files local only", GREEN, 11))

        sc.add_widget(section("About"))
        sc.add_widget(info(f"{APP_NAME} v{APP_VERSION}", WHITE, 13))
        sc.add_widget(info(f"Copyright {COPYRIGHT} - All Rights Reserved", DIM, 12))
        sc.add_widget(info("Kivy + Pyrogram + PyTgCalls + ntgcalls", DIM, 10))
        sc.add_widget(info("Audio: Telegram WebRTC engine", DIM, 10))

        sc.add_widget(Label(text="", size_hint_y=None, height=dp_(20)))
        sc.add_widget(info(f"  {COPYRIGHT} 2026 - Made with passion", DIM2, 11))

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
        icon_path = Path(os.path.dirname(os.path.abspath(__file__))) / "icon.png"
        if icon_path.exists():
            self.icon = str(icon_path)

        sm = ScreenManager(transition=SlideTransition(direction="left", duration=0.2))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    ensure_dirs()
    TelegramHookerApp().run()
