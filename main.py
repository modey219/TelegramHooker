import os
import sys
import asyncio
import threading
import json

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import platform

if platform == "android":
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.INTERNET,
        Permission.RECORD_AUDIO,
        Permission.MODIFY_AUDIO_SETTINGS,
    ])

Window.clearcolor = (0.06, 0.06, 0.12, 1)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".telegram_hooker")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SESSIONS_DIR = os.path.join(CONFIG_DIR, "sessions")

BG = (0.06, 0.06, 0.12, 1)
CARD = (0.12, 0.12, 0.2, 1)
ACCENT = (0.3, 0.7, 1, 1)
GREEN = (0.2, 0.8, 0.4, 1)
RED = (1, 0.3, 0.3, 1)
YELLOW = (1, 0.85, 0.2, 1)
WHITE = (1, 1, 1, 1)
DIM = (0.5, 0.5, 0.6, 1)


def ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def load_config():
    ensure_dirs()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


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


def styled_button(text, color=ACCENT, callback=None, **kw):
    btn = Button(
        text=text, font_size=16, bold=True,
        background_normal="", background_color=color,
        color=WHITE, size_hint_y=None, height=50, **kw,
    )
    if callback:
        btn.bind(on_press=callback)
    return btn

def styled_input(placeholder="", multiline=False, **kw):
    return TextInput(
        hint_text=placeholder, hint_text_color=DIM,
        font_size=15, background_color=(0.15, 0.15, 0.25, 1),
        foreground_color=WHITE, cursor_color=ACCENT,
        multiline=multiline, size_hint_y=None, height=45,
        padding=[12, 10], **kw,
    )


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        title = Label(text="[b]TELEGRAM HOOKER[/b]", markup=True,
                      font_size=26, color=ACCENT, size_hint_y=None, height=50)
        subtitle = Label(text="By: @ASEQX12", font_size=14, color=DIM,
                        size_hint_y=None, height=25)
        version = Label(text="v1.0 - Android", font_size=12, color=DIM,
                       size_hint_y=None, height=20)

        self.api_id = styled_input("API ID")
        self.api_hash = styled_input("API Hash")
        self.phone = styled_input("+1234567890")

        login_btn = styled_button("LOGIN", GREEN, self.do_login, height=55)
        restore_btn = styled_button("RESTORE SESSION", ACCENT, self.do_restore)

        self.status = Label(text="", font_size=13, color=YELLOW,
                           size_hint_y=None, height=30)

        scroll = ScrollView()
        sc = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        sc.bind(minimum_height=sc.setter("height"))
        for w in [title, subtitle, version, self.api_id, self.api_hash,
                  self.phone, login_btn, restore_btn, self.status]:
            sc.add_widget(w)
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
            self.status.text = "Fill all fields"
            return
        self.status.text = "Connecting..."
        Clock.schedule_once(lambda dt: self._login(ai, ah, ph), 0.1)

    def _login(self, ai, ah, ph):
        async def _go():
            try:
                from pyrogram import Client
                app = Client(os.path.join(SESSIONS_DIR, "session_temp"),
                             api_id=int(ai), api_hash=ah)
                await app.start()
                me = await app.get_me()
                await app.stop()
                save_config({"api_id": ai, "api_hash": ah, "phone": ph})
                Clock.schedule_once(lambda dt: self._ok(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._err(str(e)), 0)
        run_async(_go())

    def _ok(self):
        self.status.text = "Connected!"
        self.manager.current = "main"

    def _err(self, e):
        self.status.text = f"Error: {e[:80]}"

    def do_restore(self, *a):
        sessions = [f.replace(".json", "") for f in os.listdir(SESSIONS_DIR)
                    if f.endswith(".json")] if os.path.isdir(SESSIONS_DIR) else []
        if not sessions:
            self.status.text = "No saved sessions"
            return
        self.status.text = f"Restoring {sessions[-1]}..."
        Clock.schedule_once(lambda dt: self._restore(sessions[-1]), 0.1)

    def _restore(self, name):
        async def _go():
            try:
                from pyrogram import Client
                cfg = load_config()
                path = os.path.join(SESSIONS_DIR, name)
                app = Client(path, api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])
                await app.start()
                me = await app.get_me()
                await app.stop()
                Clock.schedule_once(lambda dt: self._ok(), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._err(str(e)), 0)
        run_async(_go())


class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.pytgcalls = None
        self.current_chat_id = None
        self.is_muted = False

        layout = BoxLayout(orientation="vertical", padding=10, spacing=6)

        header = Label(text="[b]TELEGRAM HOOKER[/b]  v1.0", markup=True,
                      font_size=18, color=ACCENT, size_hint_y=None, height=35)
        self.status_label = Label(text="Ready", font_size=13, color=GREEN,
                                  size_hint_y=None, height=22)
        self.call_label = Label(text="Not in call", font_size=13, color=DIM,
                                size_hint_y=None, height=22)
        self.mic_label = Label(text="Muted", font_size=13, color=RED,
                               size_hint_y=None, height=22)

        self.target_input = styled_input("Group ID or @username")

        self.log_label = Label(text="Ready", font_size=12, color=DIM,
                              halign="left", valign="top",
                              size_hint_y=None, height=100)

        btn_join = styled_button("JOIN VOICE CALL", GREEN, self.do_join, height=50)
        btn_mute = styled_button("MUTE", RED, self.do_mute)
        btn_unmute = styled_button("UNMUTE", YELLOW, self.do_unmute)
        btn_leave = styled_button("LEAVE CALL", (0.6, 0.2, 0.2, 1), self.do_leave, height=50)

        mute_row = BoxLayout(spacing=8, size_hint_y=None, height=50)
        mute_row.add_widget(btn_mute)
        mute_row.add_widget(btn_unmute)

        msg_input = styled_input("Message to send...", size_hint_y=None, height=45)
        btn_send = styled_button("SEND MESSAGE", ACCENT, self.do_send, height=45)
        self._msg_input = msg_input

        btn_logout = styled_button("LOGOUT", (0.3, 0.3, 0.3, 1), self.do_logout, height=40)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        for w in [header, self.status_label, self.call_label, self.mic_label,
                  self.target_input, btn_join, mute_row, btn_leave,
                  msg_input, btn_send, self.log_label, btn_logout]:
            content.add_widget(w)
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def log(self, msg):
        self.log_label.text = msg

    def _get_client(self):
        cfg = load_config()
        if not cfg.get("api_id"):
            return None
        from pyrogram import Client
        sessions = [f.replace(".session", "") for f in os.listdir(SESSIONS_DIR)
                    if f.endswith(".session")] if os.path.isdir(SESSIONS_DIR) else []
        if sessions:
            path = os.path.join(SESSIONS_DIR, sessions[-1])
        else:
            path = os.path.join(SESSIONS_DIR, "session_temp")
        return Client(path, api_id=int(cfg["api_id"]), api_hash=cfg["api_hash"])

    def do_join(self, *a):
        target = self.target_input.text.strip()
        if not target:
            self.log("Enter a group ID first")
            return
        self.log("Joining...")
        Clock.schedule_once(lambda dt: self._join(target), 0.1)

    def _join(self, target):
        async def _go():
            try:
                from pytgcalls import PyTgCalls
                from pytgcalls.media_devices import InputDevice, SpeakerDevice
                from pytgcalls.types.stream.media_stream import MediaStream
                from pytgcalls.types.calls.group_call_config import GroupCallConfig

                client = self._get_client()
                if not client:
                    Clock.schedule_once(lambda dt: self.log("Not logged in"), 0)
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
                await self.pytgcalls.play(chat_id, stream, GroupCallConfig(auto_start=True))

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
                Clock.schedule_once(lambda dt: self._on_joined(chat_id), 0)

            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {str(e)[:100]}"), 0)
        run_async(_go())

    def _on_joined(self, chat_id):
        self.call_label.text = f"In call: {chat_id}"
        self.call_label.color = GREEN
        self.mic_label.text = "Muted"
        self.mic_label.color = RED
        self.log("Joined call successfully")

    def do_mute(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call")
            return
        async def _go():
            await self.pytgcalls.mute(self.current_chat_id)
            Clock.schedule_once(lambda dt: self._set_mic(True), 0)
        run_async(_go())

    def do_unmute(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call")
            return
        async def _go():
            await self.pytgcalls.unmute(self.current_chat_id)
            Clock.schedule_once(lambda dt: self._set_mic(False), 0)
        run_async(_go())

    def _set_mic(self, muted):
        self.is_muted = muted
        self.mic_label.text = "Muted" if muted else "Unmuted"
        self.mic_label.color = RED if muted else GREEN

    def do_leave(self, *a):
        if not self.pytgcalls or not self.current_chat_id:
            self.log("Not in a call")
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
        self.call_label.text = "Not in call"
        self.call_label.color = DIM
        self.mic_label.text = "Muted"
        self.mic_label.color = RED
        self.log("Left call")

    def do_send(self, *a):
        target = self.target_input.text.strip()
        text = self._msg_input.text.strip()
        if not target or not text:
            self.log("Enter target and message")
            return
        self.log("Sending...")
        async def _go():
            try:
                client = self._get_client()
                if not client:
                    Clock.schedule_once(lambda dt: self.log("Not logged in"), 0)
                    return
                await client.start()
                chat = await client.get_chat(target)
                await client.send_message(chat.id, text)
                await client.stop()
                Clock.schedule_once(lambda dt: self.log(f"Sent to {target}"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log(f"Error: {str(e)[:80]}"), 0)
        run_async(_go())

    def do_logout(self, *a):
        if self.pytgcalls and self.current_chat_id:
            run_async(self.pytgcalls.leave_call(self.current_chat_id))
        save_config({})
        self.manager.current = "login"


class TelegramHookerApp(App):
    def build(self):
        self.title = "Telegram Hooker"
        sm = ScreenManager(transition=SlideTransition(direction="left"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        return sm


if __name__ == "__main__":
    ensure_dirs()
    TelegramHookerApp().run()
