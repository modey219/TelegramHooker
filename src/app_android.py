# -*- coding: utf-8 -*-
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
from kivy.utils import platform

Window.clearcolor = (0.06, 0.06, 0.12, 1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from core.config import load_config, save_config, get_sessions, ensure_dirs
from core.client import TelegramClient
from core.voice import VoiceCallManager


class AsyncLoopThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coro(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


_bg = AsyncLoopThread()
_bg.start()


def run_async(coro):
    return _bg.run_coro(coro)


BG = (0.06, 0.06, 0.12, 1)
CARD = (0.12, 0.12, 0.2, 1)
ACCENT = (0.3, 0.7, 1, 1)
GREEN = (0.2, 0.8, 0.4, 1)
RED = (1, 0.3, 0.3, 1)
YELLOW = (1, 0.85, 0.2, 1)
WHITE = (1, 1, 1, 1)
DIM = (0.5, 0.5, 0.6, 1)


def styled_button(text, color=ACCENT, callback=None, **kw):
    btn = Button(
        text=text,
        font_size=16,
        bold=True,
        background_normal="",
        background_color=color,
        color=WHITE,
        size_hint_y=None,
        height=50,
        **kw,
    )
    if callback:
        btn.bind(on_press=callback)
    return btn


def styled_input(placeholder="", multiline=False, **kw):
    ti = TextInput(
        hint_text=placeholder,
        hint_text_color=DIM,
        font_size=15,
        background_color=(0.15, 0.15, 0.25, 1),
        foreground_color=WHITE,
        cursor_color=ACCENT,
        multiline=multiline,
        size_hint_y=None,
        height=45,
        padding=[12, 10],
        **kw,
    )
    return ti


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        title = Label(
            text="[b]TELEGRAM HOOKER[/b]",
            markup=True,
            font_size=26,
            color=ACCENT,
            size_hint_y=None,
            height=50,
        )
        subtitle = Label(
            text="By: @ASEQX12",
            font_size=14,
            color=DIM,
            size_hint_y=None,
            height=25,
        )

        self.api_id = styled_input("API ID")
        self.api_hash = styled_input("API Hash")
        self.phone = styled_input("+1234567890")

        login_btn = styled_button("LOGIN", GREEN, self.do_login, height=55)
        restore_btn = styled_button("RESTORE SESSION", ACCENT, self.do_restore)

        self.status = Label(
            text="",
            font_size=13,
            color=YELLOW,
            size_hint_y=None,
            height=30,
        )

        scroll = ScrollView()
        scroll_content = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter("height"))
        for w in [title, subtitle, self.api_id, self.api_hash, self.phone, login_btn, restore_btn, self.status]:
            scroll_content.add_widget(w)
        scroll.add_widget(scroll_content)
        layout.add_widget(scroll)
        self.add_widget(layout)

        cfg = load_config()
        self.api_id.text = str(cfg.get("api_id", ""))
        self.api_hash.text = cfg.get("api_hash", "")
        self.phone.text = cfg.get("phone", "")

    def do_login(self, *a):
        api_id = self.api_id.text.strip()
        api_hash = self.api_hash.text.strip()
        phone = self.phone.text.strip()
        if not api_id or not api_hash or not phone:
            self.status.text = "Fill all fields"
            return
        self.status.text = "Connecting..."
        Clock.schedule_once(lambda dt: self._do_login(api_id, api_hash, phone), 0.1)

    def _do_login(self, api_id, api_hash, phone):
        async def _login():
            try:
                client = TelegramClient()
                await client.connect(api_id, api_hash, phone)
                save_config({"api_id": api_id, "api_hash": api_hash, "phone": phone})
                Clock.schedule_once(lambda dt: self._on_success(), 0)
            except Exception as e:
                _emsg = str(e)
                Clock.schedule_once(lambda dt, m=_emsg: self._on_error(m), 0)
        run_async(_login())

    def _on_success(self):
        self.status.text = "Connected!"
        self.manager.current = "main"

    def _on_error(self, err):
        self.status.text = f"Error: {err[:80]}"

    def do_restore(self, *a):
        sessions = get_sessions()
        if not sessions:
            self.status.text = "No saved sessions"
            return
        self.status.text = f"Found {len(sessions)} sessions, restoring last..."
        Clock.schedule_once(lambda dt: self._do_restore(sessions[-1]), 0.1)

    def _do_restore(self, name):
        async def _restore():
            try:
                client = TelegramClient()
                ok = await client.restore_session(name)
                if ok:
                    Clock.schedule_once(lambda dt: self._on_success(), 0)
                else:
                    Clock.schedule_once(lambda dt: self._on_error("Session not authorized"), 0)
            except Exception as e:
                _emsg = str(e)
                Clock.schedule_once(lambda dt, m=_emsg: self._on_error(m), 0)
        run_async(_restore())


class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.client = TelegramClient()
        self.voice = None

        layout = BoxLayout(orientation="vertical", padding=10, spacing=6)

        header = Label(
            text="[b]TELEGRAM HOOKER[/b]  v1.0",
            markup=True,
            font_size=18,
            color=ACCENT,
            size_hint_y=None,
            height=35,
        )
        self.status_label = Label(
            text="Connected",
            font_size=13,
            color=GREEN,
            size_hint_y=None,
            height=22,
        )
        self.call_label = Label(
            text="Not in call",
            font_size=13,
            color=DIM,
            size_hint_y=None,
            height=22,
        )
        self.mic_label = Label(
            text="Muted",
            font_size=13,
            color=RED,
            size_hint_y=None,
            height=22,
        )

        self.target_input = styled_input("Group ID or @username")

        self.log_label = Label(
            text="",
            font_size=12,
            color=DIM,
            halign="left",
            valign="top",
            text_size=(Window.width - 40, None),
            size_hint_y=None,
            height=120,
        )

        btn_join = styled_button("JOIN VOICE CALL", GREEN, self.do_join, height=50)
        btn_mute = styled_button("MUTE", RED, self.do_mute)
        btn_unmute = styled_button("UNMUTE", YELLOW, self.do_unmute)
        btn_leave = styled_button("LEAVE CALL", (0.6, 0.2, 0.2, 1), self.do_leave)

        mute_row = BoxLayout(spacing=8, size_hint_y=None, height=50)
        mute_row.add_widget(btn_mute)
        mute_row.add_widget(btn_unmute)

        send_input = styled_input("Message to send...")
        btn_send = styled_button("SEND MESSAGE", ACCENT, self.do_send, height=45)

        btn_logout = styled_button("LOGOUT", (0.3, 0.3, 0.3, 1), self.do_logout, height=40)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        for w in [header, self.status_label, self.call_label, self.mic_label,
                  self.target_input, btn_join, mute_row, btn_leave,
                  send_input, btn_send, self.log_label, btn_logout]:
            content.add_widget(w)
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def log(self, msg):
        self.log_label.text = msg

    def do_join(self, *a):
        target = self.target_input.text.strip()
        if not target:
            self.log("Enter a group ID")
            return
        self.log("Joining...")
        Clock.schedule_once(lambda dt: self._do_join(target), 0.1)

    def _do_join(self, target):
        async def _join():
            try:
                if not self.client.is_connected:
                    cfg = load_config()
                    await self.client.connect(cfg["api_id"], cfg["api_hash"])
                if not self.voice:
                    self.voice = VoiceCallManager(self.client)
                await self.voice.join(target)
                Clock.schedule_once(lambda dt: self._update_status("In call"), 0)
            except Exception as e:
                _emsg = str(e)[:100]
                Clock.schedule_once(lambda dt, m=_emsg: self.log(f"Error: {m}"), 0)
        run_async(_join())

    def do_mute(self, *a):
        if self.voice:
            run_async(self.voice.mute())
            self.mic_label.text = "Muted"
            self.mic_label.color = RED

    def do_unmute(self, *a):
        if self.voice:
            run_async(self.voice.unmute())
            self.mic_label.text = "Unmuted"
            self.mic_label.color = GREEN

    def do_leave(self, *a):
        if self.voice:
            async def _leave():
                await self.voice.leave()
                Clock.schedule_once(lambda dt: self._update_status("Left call"), 0)
            run_async(_leave())

    def do_send(self, *a):
        target = self.target_input.text.strip()
        text = self.log_label.parent.children[-3].text.strip() if False else ""
        self.log("Message feature: use target input + message input")

    def do_logout(self, *a):
        run_async(self.client.disconnect())
        self.manager.current = "login"

    def _update_status(self, msg):
        self.call_label.text = msg
        if "call" in msg.lower() and "left" not in msg.lower():
            self.call_label.color = GREEN
        else:
            self.call_label.color = DIM
        self.log(msg)


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
