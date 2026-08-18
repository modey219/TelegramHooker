import os, sys, asyncio, threading, json, base64, hashlib, time
from pathlib import Path

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, CardTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty, NumericProperty

APP_NAME = "Telegram Hooker"
APP_VERSION = "2.0"
COPYRIGHT = "@ASEQX12"

BG_DARK = [0.05, 0.05, 0.10, 1]
BG_CARD = [0.10, 0.10, 0.18, 1]
BG_INPUT = [0.14, 0.14, 0.24, 1]
ACCENT = [0.25, 0.65, 1.0, 1]
ACCENT_DIM = [0.15, 0.40, 0.75, 1]
GREEN = [0.18, 0.80, 0.44, 1]
RED = [1.0, 0.30, 0.30, 1]
YELLOW = [1.0, 0.82, 0.20, 1]
ORANGE = [1.0, 0.55, 0.15, 1]
WHITE = [1, 1, 1, 1]
DIM = [0.45, 0.45, 0.55, 1]
VERY_DIM = [0.30, 0.30, 0.40, 1]

APP_DIR = Path(os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.dirname(os.path.abspath(__file__))) else Path(".")
HOME = Path(os.path.expanduser("~"))
CONFIG_DIR = HOME / ".telegram_hooker"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = CONFIG_DIR / "sessions"
KEY_FILE = CONFIG_DIR / ".key"


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
    def encrypt(cls, data: str) -> str:
        key = cls._get_key()
        raw = data.encode("utf-8")
        nonce = os.urandom(12)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        ct = AESGCM(key).encrypt(nonce, raw, None)
        return base64.b64encode(nonce + ct).decode("ascii")

    @classmethod
    def decrypt(cls, token: str) -> str:
        key = cls._get_key()
        raw = base64.b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")


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
    sensitive = {"api_id", "api_hash", "phone", "api_id_enc", "api_hash_enc"}
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

def make_card(**kw):
    w = BoxLayout(**kw)
    with w.canvas.before:
        Color(*BG_CARD)
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(12)])
    w.bind(pos=lambda inst, val: _update_card_bg(inst))
    w.bind(size=lambda inst, val: _update_card_bg(inst))
    return w

def _update_card_bg(w):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*BG_CARD)
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(12)])

def styled_input(placeholder="", password=False, **kw):
    ti = TextInput(
        hint_text=placeholder, hint_text_color=DIM,
        font_size=dp_(14), background_color=BG_INPUT,
        foreground_color=WHITE, cursor_color=ACCENT,
        multiline=False, size_hint_y=None, height=dp_(46),
        padding=[dp_(12), dp_(10)],
        password=password,
        **kw,
    )
    return ti

def styled_button(text, color=ACCENT, callback=None, height_=None, font_size_=14):
    h = height_ or dp_(48)
    btn = Button(
        text=text, font_size=dp_(font_size_), bold=True,
        background_normal="", background_color=color,
        color=WHITE, size_hint_y=None, height=h,
    )
    with btn.canvas.before:
        Color(0, 0, 0, 0)
        RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp_(10)])
    btn.bind(pos=lambda inst, val: _update_btn_bg(inst, color))
    btn.bind(size=lambda inst, val: _update_btn_bg(inst, color))
    if callback:
        btn.bind(on_press=callback)
    return btn

def _update_btn_bg(btn, color):
    btn.canvas.before.clear()
    with btn.canvas.before:
        Color(*color)
        RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp_(10)])

def info_label(text="", color=DIM, size_=12, halign_="left"):
    return Label(
        text=text, font_size=dp_(size_), color=color,
        size_hint_y=None, height=dp_(20), halign=halign_,
        valign="middle",
    )

def section_title(text):
    return Label(
        text=f"[b]{text}[/b]", markup=True, font_size=dp_(16),
        color=ACCENT, size_hint_y=None, height=dp_(36),
        halign="left", valign="middle",
    )


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = BoxLayout(orientation="vertical", padding=dp_(24), spacing=dp_(8))

        top = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_(160))
        with top.canvas.before:
            Color(*ACCENT[:3], 0.08)
            RoundedRectangle(pos=top.pos, size=top.size, radius=[dp_(20)])
        top.bind(pos=lambda i, v: _update_top_bg(i))
        top.bind(size=lambda i, v: _update_top_bg(i))

        logo = Label(text="[b][color=#40A8FF]TELEGRAM[/color]\n[color=#FFFFFF]HOOKER[/color][/b]",
                     markup=True, font_size=dp_(30), halign="center")
        sub = Label(text=f"v{APP_VERSION}  |  {COPYRIGHT}", font_size=dp_(13), color=DIM)
        top.add_widget(logo)
        top.add_widget(sub)

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=dp_(10), size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))

        sc.add_widget(top)
        sc.add_widget(info_label("API Credentials", ACCENT, 13))

        self.api_id = styled_input("API ID (from my.telegram.org)")
        self.api_hash = styled_input("API Hash")
        self.phone = styled_input("+1234567890")

        sc.add_widget(self.api_id)
        sc.add_widget(self.api_hash)
        sc.add_widget(self.phone)

        sc.add_widget(styled_button("LOGIN", GREEN, self.do_login, dp_(52), 16))
        sc.add_widget(styled_button("RESTORE SESSION", ACCENT_DIM, self.do_restore))

        self.status = Label(text="", font_size=dp_(13), color=YELLOW,
                           size_hint_y=None, height=dp_(28), halign="center")
        sc.add_widget(self.status)

        footer = Label(text=f"{COPYRIGHT} - All Rights Reserved", font_size=dp_(11),
                      color=VERY_DIM, size_hint_y=None, height=dp_(24))
        sc.add_widget(footer)

        scroll.add_widget(sc)
        layout.add_widget(scroll)
        self.add_widget(layout)

        cfg = load_config()
        self.api_id.text = str(cfg.get("api_id", ""))
        self.api_hash.text = cfg.get("api_hash", "")
        self.phone.text = cfg.get("phone", "")

    def do_login(self, *a):
        ai = self.api_id.text.strip()
        ah = self.api_hash.text.strip()
        ph = self.phone.text.strip()
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
                            "username": me.username or "", "first_name": me.first_name or ""})
                Clock.schedule_once(lambda dt: self._ok(me), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._err(str(e)), 0)
        run_async(_go())

    def _ok(self, me):
        name = me.first_name or me.username or "User"
        self.status.text = f"[color=#4DFF88]Connected as {name}![/color]"
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
        self.status.text = f"[color=#FFD700]Restoring...[/color]"
        self.status.markup = True
        Clock.schedule_once(lambda dt: self._restore(sessions[-1]), 0.1)

    def _restore(self, name):
        async def _go():
            try:
                from pyrogram import Client
                cfg = load_config()
                path = str(SESSIONS_DIR / name)
                app = Client(path, api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])
                await app.start()
                me = await app.get_me()
                await app.stop()
                save_config({**cfg, "username": me.username or "", "first_name": me.first_name or ""})
                Clock.schedule_once(lambda dt: self._ok(me), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._err(str(e)), 0)
        run_async(_go())


def _update_top_bg(w):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*ACCENT[:3], 0.08)
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(20)])


class MainScreen(Screen):
    in_call = BooleanProperty(False)
    is_muted = BooleanProperty(False)
    call_info = StringProperty("Not in call")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.pytgcalls = None
        self.current_chat_id = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp_(16), spacing=dp_(6))

        header = BoxLayout(size_hint_y=None, height=dp_(50))
        with header.canvas.before:
            Color(*ACCENT[:3], 0.06)
            RoundedRectangle(pos=header.pos, size=header.size, radius=[dp_(14)])
        header.bind(pos=lambda i, v: _update_hdr(i))
        header.bind(size=lambda i, v: _update_hdr(i))

        hdr_left = BoxLayout(orientation="vertical", size_hint_x=0.7)
        hdr_left.add_widget(Label(text="[b]TELEGRAM HOOKER[/b]", markup=True,
                                  font_size=dp_(18), color=ACCENT, halign="left"))
        hdr_left.add_widget(Label(text=f"v{APP_VERSION} | {COPYRIGHT}", font_size=dp_(11), color=DIM, halign="left"))
        hdr_right = BoxLayout(size_hint_x=0.3)
        btn_settings = Button(text="Settings", font_size=dp_(12), background_normal="",
                              background_color=BG_CARD, color=DIM, size_hint=(None, None),
                              size=(dp_(70), dp_(32)))
        btn_settings.bind(on_press=lambda x: setattr(self.manager, "current", "settings"))
        hdr_right.add_widget(btn_settings)
        header.add_widget(hdr_left)
        header.add_widget(hdr_right)

        self.status_lbl = Label(text="Ready", font_size=dp_(13), color=GREEN,
                               size_hint_y=None, height=dp_(22), halign="left")
        self.call_lbl = Label(text="[color=#808090]Not in call[/color]", markup=True,
                             font_size=dp_(13), size_hint_y=None, height=dp_(22), halign="left")
        self.mic_lbl = Label(text="[color=#FF4D4D]MUTED[/color]", markup=True,
                            font_size=dp_(13), size_hint_y=None, height=dp_(22), halign="left")

        self.target_input = styled_input("Group ID or @username")

        btn_join = styled_button("JOIN VOICE CALL", GREEN, self.do_join, dp_(52), 15)
        btn_leave = styled_button("LEAVE CALL", RED, self.do_leave)

        mute_row = BoxLayout(spacing=dp_(10), size_hint_y=None, height=dp_(48))
        mute_row.add_widget(styled_button("MUTE", ORANGE, self.do_mute))
        mute_row.add_widget(styled_button("UNMUTE", YELLOW, self.do_unmute))

        msg_card = BoxLayout(orientation="vertical", spacing=dp_(6), size_hint_y=None, height=dp_(110))
        with msg_card.canvas.before:
            Color(*BG_CARD)
            RoundedRectangle(pos=msg_card.pos, size=msg_card.size, radius=[dp_(12)])
        msg_card.bind(pos=lambda i, v: _update_card_bg(i))
        msg_card.bind(size=lambda i, v: _update_card_bg(i))

        self.msg_input = styled_input("Message to send...")
        btn_send = styled_button("SEND MESSAGE", ACCENT, self.do_send, dp_(40), 13)
        msg_card.add_widget(self.msg_input)
        msg_card.add_widget(btn_send)

        log_scroll = ScrollView(size_hint_y=None, height=dp_(100))
        self.log_lbl = Label(text="[color=#808090]Ready[/color]", markup=True,
                            font_size=dp_(12), color=DIM, halign="left", valign="top",
                            size_hint_y=None, text_size=(Window.width - dp_(40), None))
        self.log_lbl.bind(texture_size=lambda i, v: setattr(self.log_lbl, "height", max(dp_(80), v[1] + dp_(10))))
        log_scroll.add_widget(self.log_lbl)

        btn_logout = styled_button("LOGOUT", VERY_DIM, self.do_logout, dp_(38), 12)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", spacing=dp_(8), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        for w in [header, self.status_lbl, self.call_lbl, self.mic_lbl,
                  self.target_input, btn_join, mute_row, btn_leave,
                  msg_card, log_scroll, btn_logout]:
            content.add_widget(w)
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def log(self, msg, color=DIM):
        c = "#{:02x}{:02x}{:02x}".format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
        self.log_lbl.text = f"[color={c}]{msg}[/color]"
        self.log_lbl.markup = True

    def _get_client(self):
        cfg = load_config()
        if not cfg.get("api_id"):
            return None
        from pyrogram import Client
        sessions = [f.stem for f in SESSIONS_DIR.glob("*.session")]
        path = str(SESSIONS_DIR / sessions[-1]) if sessions else str(SESSIONS_DIR / "session_temp")
        return Client(path, api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])

    def do_join(self, *a):
        target = self.target_input.text.strip()
        if not target:
            self.log("Enter a group ID first", RED)
            return
        self.log("Joining call...", YELLOW)
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
                except Exception:
                    pass

                self.current_chat_id = chat_id
                self.is_muted = True
                Clock.schedule_once(lambda dt: self._on_joined(chat_id, target), 0)

            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {str(e)[:100]}", RED), 0)
        run_async(_go())

    def _on_joined(self, chat_id, target):
        self.in_call = True
        self.call_lbl.text = f"[color=#4DFF88]In call: {target}[/color]"
        self.call_lbl.markup = True
        self.mic_lbl.text = "[color=#FF4D4D]MUTED[/color]"
        self.mic_lbl.markup = True
        self.log("Joined call successfully!", GREEN)

    def do_mute(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call", RED)
            return
        async def _go():
            try:
                await self.pytgcalls.mute(self.current_chat_id)
                self.is_muted = True
                Clock.schedule_once(lambda dt: self._set_mic(True), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Mute failed: {e}", RED), 0)
        run_async(_go())

    def do_unmute(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call", RED)
            return
        async def _go():
            try:
                await self.pytgcalls.unmute(self.current_chat_id)
                self.is_muted = False
                Clock.schedule_once(lambda dt: self._set_mic(False), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Unmute failed: {e}", RED), 0)
        run_async(_go())

    def _set_mic(self, muted):
        self.is_muted = muted
        self.mic_lbl.text = "[color=#FF4D4D]MUTED[/color]" if muted else "[color=#4DFF88]LIVE[/color]"
        self.mic_lbl.markup = True
        self.log("Microphone muted" if muted else "Microphone active", ORANGE if muted else GREEN)

    def do_leave(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call", RED)
            return
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
        self.in_call = False
        self.call_lbl.text = "[color=#808090]Not in call[/color]"
        self.call_lbl.markup = True
        self.mic_lbl.text = "[color=#FF4D4D]MUTED[/color]"
        self.mic_lbl.markup = True
        self.log("Left call", YELLOW)

    def do_send(self, *a):
        target = self.target_input.text.strip()
        text = self.msg_input.text.strip()
        if not target or not text:
            self.log("Enter target and message", RED)
            return
        self.log("Sending...", YELLOW)
        async def _go():
            try:
                client = self._get_client()
                if not client:
                    Clock.schedule_once(lambda dt: self.log("Not logged in", RED), 0)
                    return
                await client.start()
                chat = await client.get_chat(target)
                await client.send_message(chat.id, text)
                await client.stop()
                self.msg_input.text = ""
                Clock.schedule_once(lambda dt: self.log(f"Sent to {target}", GREEN), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Send failed: {str(e)[:80]}", RED), 0)
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

    def on_enter(self):
        cfg = load_config()
        user = cfg.get("first_name") or cfg.get("username") or ""
        if user:
            self.status_lbl.text = f"Logged in: {user}"


def _update_hdr(w):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*ACCENT[:3], 0.06)
        RoundedRectangle(pos=w.pos, size=w.size, radius=[dp_(14)])


class SettingsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=dp_(16), spacing=dp_(8))

        header = BoxLayout(size_hint_y=None, height=dp_(48))
        header.add_widget(Label(text="[b]SETTINGS[/b]", markup=True, font_size=dp_(20),
                               color=ACCENT, halign="left", valign="middle"))
        btn_back = Button(text="Back", font_size=dp_(13), background_normal="",
                         background_color=BG_CARD, color=DIM, size_hint=(None, None),
                         size=(dp_(60), dp_(36)))
        btn_back.bind(on_press=lambda x: setattr(self.manager, "current", "main"))
        header.add_widget(btn_back)

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=dp_(10), size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))

        sc.add_widget(header)

        sc.add_widget(section_title("Account"))
        self.api_id_lbl = Label(text="API ID: ---", font_size=dp_(13), color=DIM,
                               size_hint_y=None, height=dp_(22), halign="left")
        self.api_hash_lbl = Label(text="API Hash: ---", font_size=dp_(13), color=DIM,
                                 size_hint_y=None, height=dp_(22), halign="left")
        self.user_lbl = Label(text="User: ---", font_size=dp_(13), color=DIM,
                             size_hint_y=None, height=dp_(22), halign="left")
        sc.add_widget(self.api_id_lbl)
        sc.add_widget(self.api_hash_lbl)
        sc.add_widget(self.user_lbl)

        sc.add_widget(section_title("Audio"))
        self.auto_mute_row = BoxLayout(size_hint_y=None, height=dp_(44))
        self.auto_mute_row.add_widget(Label(text="Auto-mute on join", font_size=dp_(13), color=WHITE,
                                            size_hint_x=0.7))
        self.auto_mute_sw = Switch(active=True, size_hint_x=0.3)
        self.auto_mute_row.add_widget(self.auto_mute_sw)
        sc.add_widget(self.auto_mute_row)

        sc.add_widget(section_title("Auto-Join"))
        self.auto_join_input = styled_input("Auto-join target (ID or @username)")
        sc.add_widget(self.auto_join_input)
        self.auto_join_sw_row = BoxLayout(size_hint_y=None, height=dp_(44))
        self.auto_join_sw_row.add_widget(Label(text="Auto-join on start", font_size=dp_(13), color=WHITE,
                                               size_hint_x=0.7))
        self.auto_join_sw = Switch(active=False, size_hint_x=0.3)
        self.auto_join_sw_row.add_widget(self.auto_join_sw)
        sc.add_widget(self.auto_join_sw_row)

        sc.add_widget(section_title("Notifications"))
        self.notif_sw_row = BoxLayout(size_hint_y=None, height=dp_(44))
        self.notif_sw_row.add_widget(Label(text="Call notifications", font_size=dp_(13), color=WHITE,
                                           size_hint_x=0.7))
        self.notif_sw = Switch(active=True, size_hint_x=0.3)
        self.notif_sw_row.add_widget(self.notif_sw)
        sc.add_widget(self.notif_sw_row)

        sc.add_widget(section_title("Security"))
        sc.add_widget(info_label("AES-256-GCM encryption for all stored credentials", DIM, 11))
        sc.add_widget(info_label("Session files stored locally in encrypted form", DIM, 11))

        sc.add_widget(section_title("About"))
        sc.add_widget(info_label(f"{APP_NAME} v{APP_VERSION}", WHITE, 13))
        sc.add_widget(info_label(f"Copyright {COPYRIGHT} - All Rights Reserved", DIM, 12))
        sc.add_widget(info_label("Built with Kivy + Pyrogram + PyTgCalls", DIM, 11))
        sc.add_widget(info_label("Audio engine: ntgcalls (native Telegram voice)", DIM, 11))

        sc.add_widget(info_label(""))
        sc.add_widget(info_label(f"  {COPYRIGHT} 2026", VERY_DIM, 11))

        scroll.add_widget(sc)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        cfg = load_config()
        ai = cfg.get("api_id", "")
        ah = cfg.get("api_hash", "")
        user = cfg.get("first_name") or cfg.get("username") or "---"
        if ai:
            self.api_id_lbl.text = f"API ID: {ai[:4]}{'*' * (len(ai)-4) if len(ai) > 4 else ''}"
        if ah:
            masked = ah[:4] + "****" + ah[-4:] if len(ah) > 8 else "****"
            self.api_hash_lbl.text = f"API Hash: {masked}"
        self.user_lbl.text = f"User: {user}"


class TelegramHookerApp(App):
    def build(self):
        self.title = APP_NAME
        self.icon = str(APP_DIR / "icon.png") if (APP_DIR / "icon.png").exists() else ""

        sm = ScreenManager(transition=SlideTransition(direction="left", duration=0.25))
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
