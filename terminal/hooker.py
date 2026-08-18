# -*- coding: utf-8 -*-
"""
TELEGRAM HOOKER LIGHT — Android Edition (Console)
Works on Pydroid 3 and Termux without tkinter.
Features: Login, session management, voice calls, mic mute/unmute,
real mic state sync from server, group ID cache for speed.
"""

import sys
import os
import asyncio
import threading
import json
import time
import traceback
import contextlib

@contextlib.contextmanager
def _silence():
    _devnull = os.open(os.devnull, os.O_WRONLY)
    _old_stdout = os.dup(sys.stdout.fileno())
    _old_stderr = os.dup(sys.stderr.fileno())
    os.dup2(_devnull, sys.stdout.fileno())
    os.dup2(_devnull, sys.stderr.fileno())
    try:
        yield
    finally:
        os.dup2(_old_stdout, sys.stdout.fileno())
        os.dup2(_old_stderr, sys.stderr.fileno())
        os.close(_devnull)
        os.close(_old_stdout)
        os.close(_old_stderr)

@contextlib.contextmanager
def _silent_logs():
    import logging
    saved = {}
    for name in ("pyrogram", "pytgcalls", "ntgcalls"):
        logger = logging.getLogger(name)
        saved[name] = logger.level
        logger.setLevel(logging.CRITICAL + 10)
    try:
        yield
    finally:
        for name, lvl in saved.items():
            logging.getLogger(name).setLevel(lvl)
import base64
import hashlib
import shutil
import getpass
import re

if os.name == "nt":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

try:
    asyncio.get_running_loop()
except RuntimeError:
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
    except Exception:
        pass

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "hooker_config.json")
SESSIONS_DIR = os.path.join(APP_DIR, "sessions")

try:
    import site as _site
    for _sp in _site.getsitepackages():
        if _sp and _sp not in sys.path:
            sys.path.insert(0, _sp)
except Exception:
    pass


# ---- ANSI Colors (works in Pydroid and Termux)
class C:
    R = "\033[0m"        # reset
    B = "\033[1m"        # bold
    D = "\033[2m"        # dim
    U = "\033[4m"        # underline
    BL = "\033[30m"; R_ = "\033[31m"; G = "\033[32m"; Y = "\033[33m"
    BU = "\033[34m"; M = "\033[35m"; CY = "\033[36m"; W = "\033[37m"
    RBL = "\033[90m"; Rr = "\033[91m"; RG = "\033[92m"; RY = "\033[93m"
    RB = "\033[94m"; RM = "\033[95m"; RC = "\033[96m"; RW = "\033[97m"

LINE = f"{C.CY}\u2501" * 42 + f"{C.R}"

if os.name == "nt":
    try:
        import ctypes
        _k = ctypes.windll.kernel32
        _k.SetConsoleMode(_k.GetStdHandle(-11), 7)
    except Exception:
        pass


_ANSI_SPLIT = re.compile(r"((?:\x1b\[[0-9;]*m)+)")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_get_display
    _RESHAPE_OK = True
except Exception:
    _RESHAPE_OK = False


def _rtl(s):
    return s


def _log_console(msg, color=None):
    try:
        c = color
        if c is None:
            if msg.startswith("[✓]") or msg.startswith("[OK]") or msg.startswith("[+]"):
                c = C.G
            elif msg.startswith("[-]") or msg.startswith("[ERR]") or msg.startswith("[FAIL]"):
                c = C.Rr
            elif msg.startswith("[!]") or msg.startswith("[WARN]"):
                c = C.RY
            elif msg.startswith("["):
                c = C.CY
            else:
                c = C.W
        print(f"{c}{msg}{C.R}", flush=True)
    except Exception:
        try:
            print(msg, flush=True)
        except Exception:
            pass


class AndroidHooker:
    def __init__(self):
        self.app = None
        self.pytgcalls = None
        self._pytgcalls_available = False
        try:
            with _silence():
                from pytgcalls import PyTgCalls
            self._pytgcalls_available = True
        except Exception:
            self._pytgcalls_available = False
        self.current_chat_id = None
        self._chat_id_cache = {}
        self.vc_mic_is_muted = False
        self._mic_devices = []
        self._speaker_devices = []
        self.active_session_name = None
        self.me_name = None
        self.latency_ms = 0.0
        self._stop_spam = False
        self._quick_replies = []
        self.bg_loop = asyncio.new_event_loop()
        self.bg_thread = threading.Thread(target=self._run_background_loop, daemon=True)
        self.bg_thread.start()

    def _run_background_loop(self):
        asyncio.set_event_loop(self.bg_loop)
        self.bg_loop.run_forever()

    def run_async(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.bg_loop)

    # ---------------------------------------------------------------- paths
    def _get_sessions_dir(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        return SESSIONS_DIR

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_config(self, api_id, api_hash, phone):
        cfg = self.load_config()
        cfg.update({"api_id": api_id, "api_hash": api_hash, "phone": phone})
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False)
        except Exception as e:
            _log_console(f"[-] Failed to save config: {e}")

    def _derive_key(self, password):
        return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())

    def _encrypt_data(self, data_str, password):
        from cryptography.fernet import Fernet
        return Fernet(self._derive_key(password)).encrypt(data_str.encode()).decode()

    def _decrypt_data(self, encrypted_str, password):
        from cryptography.fernet import Fernet
        return Fernet(self._derive_key(password)).decrypt(encrypted_str.encode()).decode()

    def _get_session_password(self):
        pw = os.environ.get("HOOKER_SESSION_PW", "").strip()
        return pw

    def _save_current_session(self, name, session_string=""):
        if not self.app or not name:
            return
        sessions_dir = self._get_sessions_dir()
        info_path = os.path.join(sessions_dir, f"{name}.json")
        if not session_string:
            try:
                session_string = self.app.export_session_string()
            except Exception as e:
                _log_console(f"[-] Failed to export session: {e}")
                session_string = ""
        data = {
            "api_id": self.load_config().get("api_id", ""),
            "api_hash": self.load_config().get("api_hash", ""),
            "phone": self.load_config().get("phone", ""),
            "session_string": session_string or "",
        }
        try:
            pw = self._get_session_password()
            if pw:
                with open(info_path, "w", encoding="utf-8") as f:
                    f.write(self._encrypt_data(json.dumps(data, ensure_ascii=False), pw))
                _log_console(f"[sessions] Session saved and encrypted: {name}")
            else:
                with open(info_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                _log_console(f"[sessions] Session saved: {name}")
        except Exception as e:
            _log_console(f"[-] Failed to save session: {e}")

    def _get_saved_sessions(self):
        sessions_dir = self._get_sessions_dir()
        sessions = []
        try:
            for f in os.listdir(sessions_dir):
                if f.endswith(".json"):
                    sessions.append(f.replace(".json", ""))
        except Exception:
            pass
        return sorted(sessions)

    def _read_session_data(self, name):
        info_path = os.path.join(self._get_sessions_dir(), f"{name}.json")
        if not os.path.exists(info_path):
            return None
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pw = self._get_session_password()
                if pw:
                    return json.loads(self._decrypt_data(content, pw))
        except Exception:
            return None
        return None

    # ------------------------------------------------------ quick replies
    def _load_quick_replies(self):
        try:
            path = os.path.join(APP_DIR, "quick_replies.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self._quick_replies = json.load(f)
        except Exception:
            self._quick_replies = []
        if not isinstance(self._quick_replies, list):
            self._quick_replies = []
        return self._quick_replies

    def _save_quick_replies(self):
        try:
            path = os.path.join(APP_DIR, "quick_replies.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._quick_replies, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _log_console(f"[-] Failed to save quick replies: {e}")

    async def send_quick_text(self, target, text, times=1, delay=0.0):
        if not self.app or not self.app.is_connected:
            _log_console("[-] Not connected. Please login first.")
            return
        if not target:
            target = self.current_chat_id
        if not target:
            _log_console("[-] Specify a group ID (or be in a call).")
            return
        try:
            chat_id = await self._update_cache_and_get_id(target)
            for i in range(max(1, int(times))):
                if self._stop_spam:
                    _log_console("[!] Sending stopped manually.")
                    break
                await self.app.send_message(chat_id, text)
                _log_console(f"[✓] Message sent: {i + 1}")
                if delay > 0:
                    await asyncio.sleep(delay)
        except Exception as e:
            _log_console(f"[-] Failed to send message: {e}")

    def parse_target(self, target_str):
        target_str = (target_str or "").strip()
        if not target_str:
            return None
        if "t.me/" in target_str:
            target_str = target_str.split("t.me/")[-1].split("/")[0]
        if target_str.lstrip('-').isdigit():
            return int(target_str)
        if not target_str.startswith('@'):
            target_str = f"@{target_str}"
        return target_str

    # ---------------------------------------------------------------- login
    def _run(self, coro):
        fut = self.run_async(coro)
        try:
            return fut.result(timeout=120)
        except Exception:
            raise

    async def _disconnect_app(self):
        if self.app:
            try:
                if self.app.is_connected:
                    await self.app.stop()
            except Exception:
                pass
            self.app = None

    async def _send_code(self, api_id, api_hash, phone):
        from pyrogram import Client
        await self._disconnect_app()
        try:
            for f in os.listdir(APP_DIR):
                if f.startswith("spider_session"):
                    os.remove(os.path.join(APP_DIR, f))
        except Exception:
            pass
        self.app = Client(os.path.join(APP_DIR, "spider_session"), api_id=int(api_id), api_hash=api_hash)
        with _silence():
            await self.app.connect()
        self.sent_code = await self.app.send_code(phone)
        return self.sent_code

    async def _resend_code(self, phone):
        self.sent_code = await self.app.resend_code(phone, self.sent_code.phone_code_hash)
        return self.sent_code

    async def _complete_login(self, phone, code, password=None):
        try:
            if password:
                await self.app.check_password(password)
            else:
                await self.app.sign_in(phone, self.sent_code.phone_code_hash, code)
        except Exception as pe:
            if "PASSWORD" in str(pe).upper() or "Two-Step" in str(pe):
                return "NEED_PASSWORD"
            raise
        try:
            session_string = await self.app.export_session_string()
        except Exception:
            session_string = ""
        name = f"session_{phone.replace('+', '')}"
        self.active_session_name = name
        self._save_current_session(name, session_string)
        return await self.app.get_me()

    def login_flow(self):
        cfg = self.load_config()
        print(f"\n{C.RB}{C.B}┌────────── LOGIN ──────────┐{C.R}")
        print(f"{C.RC}   Enter your credentials from my.telegram.org{C.R}")
        print(f"{C.RB}{C.B}└──────────────────────────────────┘{C.R}")
        api_id = input(f"{C.RG}{C.B}  API ID{C.R}: ").strip() or str(cfg.get("api_id", ""))
        api_hash = input(f"{C.RG}{C.B}  API HASH{C.R}: ").strip() or str(cfg.get("api_hash", ""))
        phone = input(f"{C.RG}{C.B}  Phone number with country code (+1...){C.R}: ").strip() or str(cfg.get("phone", ""))
        if not api_id or not api_hash or not phone:
            _log_console("[-] Please fill in API ID / API HASH / Phone number.")
            return
        self.save_config(api_id, api_hash, phone)
        try:
            from pyrogram import Client  # noqa: F401
        except Exception as e:
            _log_console(f"[-] pyrogram not found: {e} | Install: pip install pyrogram")
            return
        try:
            _log_console("[...] Connecting to Telegram and sending code...")
            self.sent_code = self._run(self._send_code(api_id, api_hash, phone))
            print(f"{C.G}  Verification code sent.{C.R}")
            print(f"  {C.Y}  - You'll receive it inside Telegram app (if the number is registered){C.R}")
            print(f"  {C.Y}  - Or via SMS. Wait 1-2 minutes before resending.{C.R}")
            code = ""
            while True:
                code = input(f"{C.RG}{C.B}  Verification code (or r to resend){C.R}: ").strip()
                if code.lower() == "r":
                    try:
                        _log_console("[...] Resending code...")
                        self.sent_code = self._run(self._resend_code(phone))
                        print(f"{C.G}  Code resent. Check again.{C.R}")
                        continue
                    except Exception as re_:
                        _log_console(f"[-] Resend failed (may be rate-limited): {re_}")
                        continue
                if code:
                    break
            res = self._run(self._complete_login(phone, code))
            if res == "NEED_PASSWORD":
                pwd = getpass.getpass(f"{C.RY}{C.B}  Two-step verification password{C.R}: ")
                res = self._run(self._complete_login(phone, code, password=pwd))
            if res is None or res == "NEED_PASSWORD":
                _log_console("[-] Login failed.")
                self.app = None
                return
            _log_console(f"[OK] Logged in: {res.first_name}")
            self.me_name = res.first_name
        except Exception as e:
            _log_console(f"[-] Login failed: {e}")
            self.app = None

    async def restore_session(self, name, silent=False):
        data = self._read_session_data(name)
        if not data:
            if not silent:
                _log_console("[-] Session data not found.")
            return False
        api_id = data.get("api_id") or self.load_config().get("api_id")
        api_hash = data.get("api_hash") or self.load_config().get("api_hash")
        session_string = data.get("session_string", "")
        if not api_id or not api_hash:
            if not silent:
                _log_console("[-] API ID / API HASH missing.")
            return False
        await self._disconnect_app()
        try:
            from pyrogram import Client
            with _silence(), _silent_logs():
                if session_string:
                    self.app = Client("session_tmp", session_string=session_string, api_id=int(api_id), api_hash=api_hash)
                else:
                    self.app = Client(os.path.join(self._get_sessions_dir(), name), api_id=int(api_id), api_hash=api_hash)
                await self.app.start()
            user = await self.app.get_me()
            if user:
                self.active_session_name = name
                self.me_name = user.first_name
                if not silent:
                    _log_console(f"[OK] Connected as: {user.first_name}")
                return True
            if not silent:
                _log_console("[-] Session not authorized.")
            self.app = None
            return False
        except Exception as e:
            if not silent:
                _log_console(f"[-] Failed to restore session: {e}")
            self.app = None
            return False

    # ---------------------------------------------------------------- voice

    async def _init_pytgcalls(self):
        if not self.app:
            raise RuntimeError("Please login first.")
        if not self.app.is_connected:
            await self.app.start()
        try:
            with _silence():
                from pytgcalls import PyTgCalls
        except Exception as e:
            self.pytgcalls = None
            self._pytgcalls_available = False
            raise RuntimeError(f"Voice call library unavailable: {e}\nInstall: pip install py-tgcalls==2.2.0 ntgcalls==2.2.5")
        if not self.pytgcalls:
            self.pytgcalls = PyTgCalls(self.app)
        if not getattr(self.pytgcalls, '_hooker_started', False):
            try:
                with _silence():
                    await self.pytgcalls.start()
                self.pytgcalls._hooker_started = True
            except Exception as e:
                _log_console(f"[WARN] pytgcalls.start(): {e}")
        try:
            self._patch_ffmpeg()
        except Exception:
            pass

    def _patch_ffmpeg(self):
        """Point pytgcalls to ffmpeg in PATH on Android"""
        try:
            ffmpeg_bin = shutil.which("ffmpeg")
            if not ffmpeg_bin:
                return
            import pytgcalls.ffmpeg as _ffmpeg_mod
            _orig = _ffmpeg_mod.build_command
            _bin = ffmpeg_bin
            def _patched(name, *args, **kwargs):
                if name == 'ffmpeg':
                    name = _bin
                return _orig(name, *args, **kwargs)
            _ffmpeg_mod.build_command = _patched
            try:
                import pytgcalls.types.stream.media_stream as _ms
                _ms.build_command = _patched
            except Exception:
                pass
        except Exception:
            pass

    async def _update_cache_and_get_id(self, target_id):
        cache_key = str(target_id).strip().lstrip('@').lower()
        if cache_key in self._chat_id_cache:
            return self._chat_id_cache[cache_key]
        _log_console(f"[z3] Resolving ID [{target_id}]...")
        chat_id = None
        try:
            chat = await self.app.get_chat(target_id)
            chat_id = chat.id
        except Exception as e:
            _log_console(f"[!] Direct lookup unavailable ({e})")
            try:
                async for dialog in self.app.get_dialogs():
                    if isinstance(target_id, int) and dialog.chat.id == target_id:
                        chat_id = dialog.chat.id
                        break
                    elif isinstance(target_id, str) and dialog.chat.username and dialog.chat.username.lower() == target_id.replace('@', '').lower():
                        chat_id = dialog.chat.id
                        break
            except Exception:
                pass
        if not chat_id:
            _log_console("[!] Group not found.")
            return target_id
        self._chat_id_cache[cache_key] = chat_id
        try:
            peer = await self.app.resolve_peer(chat_id)
            from pyrogram.raw.functions.channels import GetFullChannel
            from pyrogram.raw.functions.messages import GetFullChat
            if "Channel" in peer.__class__.__name__:
                await self.app.invoke(GetFullChannel(channel=peer))
            else:
                await self.app.invoke(GetFullChat(chat_id=peer.chat_id))
        except Exception:
            pass
        return chat_id

    def _mic_index(self):
        return 0

    async def join_vc(self, raw_target, mic_index, auto_mute=False):
        if not raw_target:
            _log_console("[-] Enter a group ID.")
            return
        try:
            target_id = await self._update_cache_and_get_id(raw_target)
            if not self.pytgcalls:
                await self._init_pytgcalls()
            from pytgcalls.media_devices import InputDevice, SpeakerDevice
            from pytgcalls.types.stream.media_stream import MediaStream
            from pytgcalls.types.stream.record_stream import RecordStream
            from pytgcalls.types.calls.group_call_config import GroupCallConfig

            if self.current_chat_id and self.current_chat_id != target_id:
                try:
                    await self.pytgcalls.leave_call(self.current_chat_id)
                except Exception:
                    pass
                await asyncio.sleep(1.5)

            pulse_speaker = SpeakerDevice("pulse_output", "pulse")
            pulse_mic = InputDevice("pulse_input", "pulse", False)

            if mic_index > 0 and self._mic_devices:
                if mic_index - 1 < len(self._mic_devices):
                    mic_info = self._mic_devices[mic_index - 1]
                else:
                    mic_info = self._mic_devices[0]
                stream = MediaStream(
                    mic_info,
                    audio_flags=MediaStream.Flags.REQUIRED,
                    video_flags=MediaStream.Flags.IGNORE,
                )
                _log_console("[+] Sending mic audio...")
                await self.pytgcalls.play(target_id, stream, GroupCallConfig(auto_start=True))
            else:
                _log_console("[+] Joining with mic ready...")
                stream = MediaStream(
                    pulse_mic,
                    audio_flags=MediaStream.Flags.REQUIRED,
                    video_flags=MediaStream.Flags.IGNORE,
                )
                await self.pytgcalls.play(target_id, stream, GroupCallConfig(auto_start=True))

            try:
                await self.pytgcalls.record(target_id, pulse_speaker)
            except Exception:
                _log_console("[!] PulseAudio speaker unavailable.")
                try:
                    fallback_speaker = SpeakerDevice("default", "default")
                    await self.pytgcalls.record(target_id, fallback_speaker)
                except Exception:
                    _log_console("[!] No speaker device found.")

            if auto_mute or mic_index == 0:
                try:
                    await self.pytgcalls.mute(target_id)
                    self.vc_mic_is_muted = True
                    _log_console("[MUTE] Mic muted.")
                except Exception:
                    self.vc_mic_is_muted = False
            else:
                self.vc_mic_is_muted = False
            self.current_chat_id = target_id
            _log_console(f"[✓] In call. Group ID: {target_id}")
        except Exception as e:
            _log_console(f"[-] Failed to join: {e}")
            if "NoActiveGroupCall" in str(e) or "GROUP_CALL_NOT_FOUND" in str(e):
                _log_console("[!] No active call. Start a voice chat in the group first.")

    async def toggle_mute(self):
        if not self.current_chat_id:
            _log_console("[-] Not in a call.")
            return
        if self.vc_mic_is_muted:
            await self.unmute()
        else:
            await self.mute()

    async def mute(self):
        if not self.current_chat_id:
            _log_console("[-] Not in a call.")
            return
        try:
            await self.pytgcalls.mute(self.current_chat_id)
            self.vc_mic_is_muted = True
            _log_console("[MUTE] Mic muted.")
        except Exception as e:
            _log_console(f"[-] Mute failed: {e}")

    async def unmute(self):
        if not self.current_chat_id:
            _log_console("[-] Not in a call.")
            return
        try:
            await self.pytgcalls.unmute(self.current_chat_id)
            self.vc_mic_is_muted = False
            _log_console("[UNMUTE] Mic unmuted.")
        except Exception as e:
            _log_console(f"[-] Unmute failed: {e}")

    async def leave(self):
        if not self.current_chat_id:
            _log_console("[-] Not in a call.")
            return
        try:
            await self.pytgcalls.leave_call(self.current_chat_id)
            _log_console("[✓] Left the call.")
        except Exception:
            _log_console("[✓] Left the call.")
        self.current_chat_id = None
        self.vc_mic_is_muted = False

    async def _measure_latency(self):
        try:
            start = time.monotonic()
            if self.pytgcalls and self.current_chat_id:
                try:
                    participants = await self.pytgcalls.get_participants(self.current_chat_id)
                    self._sync_mic_state(participants)
                except Exception:
                    pass
            self.latency_ms = round((time.monotonic() - start) * 1000, 1)
        except Exception:
            pass

    def _sync_mic_state(self, participants):
        try:
            if participants is None or self.app is None:
                return
            me_id = None
            try:
                me = self.app.me
                if me is not None:
                    me_id = me.id
            except Exception:
                pass
            if not me_id:
                return
            for p in participants:
                try:
                    if getattr(p, "user_id", None) == me_id:
                        real_muted = bool(getattr(p, "muted", False))
                        if real_muted != bool(self.vc_mic_is_muted):
                            self.vc_mic_is_muted = real_muted
                        break
                except Exception:
                    continue
        except Exception:
            pass

    async def _latency_loop(self):
        while True:
            await self._measure_latency()
            await asyncio.sleep(1)

    # ---------------------------------------------------------------- menu
    def _banner(self):
        print()
        print(f"{C.RB}{C.B}┌──────────────────────────────────────────────┐{C.R}")
        print(f"{C.RB}{C.B}│  ████████ ██    ██ ██   ██ ██  ██████       │{C.R}")
        print(f"{C.RB}{C.B}│     ██    ██    ██ ██  ██  ██ ██   ██       │{C.R}")
        print(f"{C.RB}{C.B}│     ██    ██    ██ █████   ██ ██   ██       │{C.R}")
        print(f"{C.RB}{C.B}│     ██    ██    ██ ██ ██  ██ ██   ██       │{C.R}")
        print(f"{C.RB}{C.B}│     ██     ██████  ██  ██ ██  ██████  V8    │{C.R}")
        print(f"{C.RB}{C.B}│                    Android • LIGHT          │{C.R}")
        print(f"{C.RB}{C.B}│                 By: @ASEQX12                │{C.R}")
        print(f"{C.RB}{C.B}└──────────────────────────────────────────────┘{C.R}")

    def _status(self):
        if self.app:
            acc = self.me_name or self.active_session_name or "Connected"
            state = f"{C.G}{C.B}● {acc}{C.R}"
        else:
            state = f"{C.Rr}{C.B}● Disconnected{C.R}"
        if self.current_chat_id:
            call = f"{C.CY}In call{C.R}"
        else:
            call = f"{C.RBL}Not in call{C.R}"
        if self.vc_mic_is_muted:
            mic = f"{C.Rr}🔇 Muted{C.R}"
        else:
            mic = f"{C.G}🎤 Open{C.R}"
        lat = self.latency_ms
        if lat == 0:
            lat_c = f"{C.RBL}--{C.R}"
        elif lat < 100:
            lat_c = f"{C.G}{lat:.0f}ms{C.R}"
        elif lat < 300:
            lat_c = f"{C.RY}{lat:.0f}ms{C.R}"
        else:
            lat_c = f"{C.Rr}{lat:.0f}ms{C.R}"
        print(f"  {C.RBL}Account:{C.R} {state}   {C.RBL}Call:{C.R} {call}")
        print(f"  {C.RBL}Mic:{C.R}  {mic}   {C.RBL}Latency:{C.R} {lat_c}")

    def _section(self, title):
        print(f"  {C.RC}{C.B}  {title}{C.R}")

    def _opt(self, num, label, accent=C.W):
        print(f"    {C.CY}{num}{C.R} {accent}{label}{C.R}")

    def menu(self):
        self._banner()
        print(f"{LINE}")
        self._status()
        print(f"{LINE}")
        self._section("ACCOUNT")
        self._opt("1", "Login (new code)")
        self._opt("2", "Restore saved session")
        self._opt("3", "List sessions")
        self._opt("13", "Delete session", C.Rr)
        print()
        self._section("VOICE CALLS")
        self._opt("4", "Join voice call", C.RG)
        self._opt("5", "Mute mic")
        self._opt("6", "Unmute mic")
        self._opt("7", "Toggle mic", C.RY)
        self._opt("8", "Leave call", C.Rr)
        self._opt("12", "Current mic status")
        print()
        self._section("MESSAGES")
        self._opt("9", "Send quick message", C.RG)
        self._opt("10", "Send spam messages", C.RY)
        self._opt("11", "Saved quick replies")
        print()
        self._section("SYSTEM")
        self._opt("0", "Quit", C.Rr)
        print(f"{LINE}")

    def _pick_session(self, prompt):
        sessions = self._get_saved_sessions()
        if not sessions:
            _log_console("[-] No saved sessions.")
            return None
        print(f"{C.RC}{C.B}Available sessions:{C.R}")
        for i, s in enumerate(sessions, start=1):
            mark = "●" if s == self.active_session_name else "○"
            print(f"  {C.CY}{i}){C.R} {mark} {s}")
        try:
            sel = int(input(prompt).strip())
            if 1 <= sel <= len(sessions):
                return sessions[sel - 1]
        except Exception:
            pass
        _log_console("[-] Invalid choice.")
        return None

    def loop(self):
        self.run_async(self._latency_loop())
        self._load_quick_replies()
        sessions = self._get_saved_sessions()
        if sessions and not self.active_session_name:
            target = sessions[-1]
            future = self.run_async(self.restore_session(target, silent=True))
            try:
                future.result(timeout=30)
            except Exception:
                pass
        while True:
            try:
                self.menu()
                choice = input(f"{C.RG}{C.B}  > {C.R}").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if choice == "1":
                self.login_flow()
            elif choice == "2":
                name = self._pick_session("Choose session number: ")
                if name:
                    self.run_async(self.restore_session(name))
            elif choice == "3":
                sessions = self._get_saved_sessions()
                if not sessions:
                    _log_console("[-] No saved sessions.")
                else:
                    print(f"{C.RC}{C.B}Saved sessions ({len(sessions)}):{C.R}")
                    for s in sessions:
                        mark = f"{C.G}●" if s == self.active_session_name else f"{C.RBL}○"
                        name = f"{C.B}{s}{C.R}" if s == self.active_session_name else f"{C.W}{s}{C.R}"
                        print(f"  {mark} {name}")
            elif choice == "4":
                cfg = self.load_config()
                last_target = cfg.get("last_target", "")
                target = input(f"Group ID [default: {last_target}]: ").strip() or last_target
                if not target:
                    _log_console("[-] Enter a group ID.")
                    continue
                cfg["last_target"] = target
                try:
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, ensure_ascii=False)
                except Exception:
                    pass
                mic_index = self._mic_index()
                am = input("Auto-mute on join? (y/n) [y]: ").strip().lower()
                auto_mute = am != "n"
                future = self.run_async(self.join_vc(self.parse_target(target), mic_index, auto_mute))
                try:
                    future.result(timeout=30)
                except Exception:
                    pass
            elif choice == "5":
                f = self.run_async(self.mute())
                try: f.result(timeout=10)
                except Exception: pass
            elif choice == "6":
                f = self.run_async(self.unmute())
                try: f.result(timeout=10)
                except Exception: pass
            elif choice == "7":
                f = self.run_async(self.toggle_mute())
                try: f.result(timeout=10)
                except Exception: pass
            elif choice == "8":
                f = self.run_async(self.leave())
                try: f.result(timeout=10)
                except Exception: pass
            elif choice == "9":
                cfg = self.load_config()
                last_target = cfg.get("last_target", "")
                target = input(f"Group [default: {last_target}]: ").strip() or last_target
                text = input("Message text: ").strip()
                if text:
                    self.run_async(self.send_quick_text(self.parse_target(target), text))
                    time.sleep(1)
            elif choice == "10":
                cfg = self.load_config()
                last_target = cfg.get("last_target", "")
                target = input(f"Group [default: {last_target}]: ").strip() or last_target
                text = input("Message text: ").strip()
                try:
                    times = int(input("Number of times: ").strip() or "1")
                except ValueError:
                    times = 1
                try:
                    delay = float(input("Delay between messages (seconds, 0 = instant): ").strip() or "0")
                except ValueError:
                    delay = 0.0
                if text:
                    self._stop_spam = False
                    self.run_async(self.send_quick_text(self.parse_target(target), text, times, delay))
            elif choice == "11":
                if not self._quick_replies:
                    _log_console("[-] No quick replies. Add one first.")
                    continue
                for i, r in enumerate(self._quick_replies, start=1):
                    print(f"  {i}) {r}")
                sel = input("Choose reply (number) or 0 to add new: ").strip()
                if sel == "0":
                    new_r = input("New reply text: ").strip()
                    if new_r:
                        self._quick_replies.append(new_r)
                        self._save_quick_replies()
                        _log_console("[✓] Reply added.")
                else:
                    try:
                        idx = int(sel) - 1
                        if 0 <= idx < len(self._quick_replies):
                            cfg = self.load_config()
                            last_target = cfg.get("last_target", "")
                            target = input(f"Group [default: {last_target}]: ").strip() or last_target
                            self.run_async(self.send_quick_text(self.parse_target(target), self._quick_replies[idx]))
                            time.sleep(1)
                    except (ValueError, IndexError):
                        _log_console("[-] Invalid choice.")
            elif choice == "12":
                if self.current_chat_id and self.pytgcalls:
                    self.run_async(self._measure_latency())
                state = "MUTED" if self.vc_mic_is_muted else "OPEN"
                _log_console(f"Mic status: {state}")
            elif choice == "13":
                name = self._pick_session("Choose session to delete: ")
                if name:
                    try:
                        for ext in [".json", ".session", ".session-journal", ".session-wal", ".session-shm"]:
                            p = os.path.join(self._get_sessions_dir(), name + ext)
                            if os.path.exists(p):
                                os.remove(p)
                        _log_console(f"[✓] Session deleted: {name}")
                    except Exception as e:
                        _log_console(f"[-] Delete failed: {e}")
            elif choice == "0":
                try:
                    if self.pytgcalls and self.current_chat_id:
                        self.run_async(self.leave())
                except Exception:
                    pass
                break
            else:
                _log_console("Invalid choice.")
            time.sleep(0.3)


def check_missing_libs():
    import importlib.util
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkgver
    reqs = [
        ("pyrogram", "pyrogram", None),
        ("pytgcalls", "py-tgcalls==2.2.0", "2.2.0"),
        ("ntgcalls", "ntgcalls==2.2.5", None),
        ("aiohttp", "aiohttp", None),
        ("pyaes", "pyaes", None),
    ]
    missing = []
    if os.environ.get("HOOKER_SESSION_PW", "").strip():
        reqs.append(("cryptography", "cryptography", None))
    for mod, pkg, want in reqs:
        try:
            if importlib.util.find_spec(mod) is None:
                missing.append(pkg)
                continue
            __import__(mod)
            if want:
                try:
                    cur = _pkgver(pkg.split("==")[0])
                except PackageNotFoundError:
                    missing.append(pkg)
                    continue
                cur_parts = [int(x) for x in cur.split(".")[:2]]
                want_parts = [int(x) for x in want.split(".")[:2]]
                if cur_parts < want_parts:
                    missing.append(pkg)
        except (ValueError, ModuleNotFoundError, ImportError):
            missing.append(pkg)
    return missing


def _draw_bar(label, pct, width=22):
    try:
        import sys
        pct = max(0, min(100, pct))
        filled = int(pct / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        sys.stdout.write(
            f"\r{C.CY}{C.B}{label}{C.R} [{C.G}{bar}{C.R}] {pct:3d}%  "
        )
        sys.stdout.flush()
    except Exception:
        pass


def _pip_install_with_progress(label, cmd, timeout=900):
    import re
    import subprocess
    import sys
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    last_pct = -1
    done_msg = None
    try:
        for raw in proc.stderr:
            line = raw.rstrip("\n")
            m = re.search(r"(\d+)%\|", line)
            if m:
                pct = int(m.group(1))
                if pct != last_pct:
                    _draw_bar(label, pct)
                    last_pct = pct
                continue
            if "Successfully installed" in line:
                done_msg = line
            elif "ERROR" in line or "error" in line.lower():
                done_msg = line
    except Exception:
        pass
    proc.wait(timeout=timeout)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return proc.returncode, done_msg


def _wheel_abi_ok(fp):
    import zipfile
    try:
        with zipfile.ZipFile(fp) as zf:
            wheel_name = next(
                (n for n in zf.namelist()
                 if n.endswith(".dist-info/WHEEL")), None)
            if not wheel_name:
                return True
            data = zf.read(wheel_name).decode("utf-8", "replace")
    except Exception:
        return True
    tags = []
    for line in data.splitlines():
        if line.lower().startswith("tag:"):
            tags.append(line.split(":", 1)[1].strip())
    if not tags:
        return True
    cur = sys.version_info
    cur_py = f"cp{cur[0]}{cur[1]}"
    cur_abi = cur_py
    is_aarch64 = any(x in os.uname().machine for x in ("aarch64", "arm64")) if hasattr(os, "uname") else False
    for tag in tags:
        parts = [p.strip() for p in tag.split("-")]
        if len(parts) < 3:
            continue
        py, abi, plat = parts[0], parts[1], "-".join(parts[2:])
        if py == "py3" and abi == "none" and plat == "any":
            return True
        if py == cur_py and abi == cur_abi and (
                plat == "any" or "aarch64" in plat or not is_aarch64):
            return True
    return False


def _extract_all_offline(src_dir):
    try:
        import site
        import zipfile
        sp = site.getsitepackages()[0]
        fresh_bases = {}
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".whl"):
                continue
            fp = os.path.join(src_dir, f)
            if not _wheel_abi_ok(fp):
                continue
            with zipfile.ZipFile(fp) as zf:
                zf.extractall(sp)
                for n in zf.namelist():
                    head = n.split("/")[0]
                    if head.endswith(".dist-info"):
                        base = head.rsplit("-", 1)[0].lower().replace("_", "-")
                        fresh_bases[base] = head.lower()
        for d in list(os.listdir(sp)):
            dl = d.lower()
            if dl.endswith(".dist-info"):
                base = d.rsplit("-", 1)[0].lower().replace("_", "-")
                if base in fresh_bases and dl != fresh_bases[base]:
                    try:
                        shutil.rmtree(os.path.join(sp, d))
                    except Exception:
                        pass
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".so"):
                continue
            dst = os.path.join(sp, f)
            try:
                shutil.copyfile(os.path.join(src_dir, f), dst)
                fresh_bases["ntgcalls"] = f.lower()
                _log_console(f"[✓] Copied prebuilt library: {f}")
            except Exception:
                pass
        return bool(fresh_bases)
    except Exception:
        return False


def _is_termux():
    return os.path.isdir("/data/data/com.termux")

def _is_proot():
    if sys.version_info[:2] == (3, 11):
        return True
    try:
        with open("/proc/1/status") as f:
            for line in f:
                if line.startswith("TracerPid:"):
                    return True
    except Exception:
        pass
    return os.path.exists("/etc/os-release") and _is_termux()


def _try_termux_ntgcalls_build():
    try:
        build_sh = os.path.join(APP_DIR, "build_ntgcalls_termux.sh")
        if not os.path.exists(build_sh):
            return False
        _log_console("[...] Running build_ntgcalls_termux.sh (building ntgcalls from source)...")
        import subprocess
        rc = subprocess.run(
            ["bash", build_sh], timeout=3600, text=True
        ).returncode
        if rc == 0:
            return True
        _log_console(f"[-] Build script failed (code: {rc}).")
        return False
    except Exception as e:
        _log_console(f"[-] Failed to run build script: {e}")
        return False


def _mod_of(pkg):
    name = pkg.split("==")[0].strip().replace("-", "_")
    return "pytgcalls" if name == "py_tgcalls" else name


def _importable(mod):
    import importlib
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def _remove_stale(prefixes):
    import site as _site
    try:
        sp = _site.getsitepackages()[0]
    except Exception:
        return
    if not sp or not os.path.isdir(sp):
        return
    for name in os.listdir(sp):
        if name.lower().startswith(prefixes):
            path = os.path.join(sp, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                _log_console(f"[...] Removing old glibc file: {name}")
            except Exception:
                pass


def auto_install(missing):
    import subprocess
    import sys
    libs_dir = os.path.join(APP_DIR, "libs")
    has_offline = os.path.isdir(libs_dir) and any(
        f.endswith((".whl", ".zip", ".tar.gz", ".so")) for f in os.listdir(libs_dir)
    )
    total = len(missing)
    done = 0
    failed_pkgs = []
    if has_offline:
        _draw_bar("libs", 0)
        if _extract_all_offline(libs_dir):
            _draw_bar("libs", 100)
            print()
            still = check_missing_libs()
            if not still:
                _test_voice_imports()
                return
            missing = still
            total = len(missing)
        else:
            _draw_bar("libs", 100)
            print()
            failed_pkgs.append(("libs", "Extraction failed or files corrupted"))
    for pkg in sorted(missing, key=lambda p: (0 if p.startswith("ntgcalls") else 1)):
        mod = _mod_of(pkg)
        if pkg.startswith("ntgcalls") and _is_termux():
            _remove_stale(("ntgcalls",))
            if _try_termux_ntgcalls_build():
                done += 1
            else:
                failed_pkgs.append((pkg, "Build from source failed"))
            continue
        if pkg.startswith("aiohttp") and _is_termux():
            try:
                subprocess.run(["pkg", "install", "-y", "python-aiohttp"],
                               timeout=1200, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                failed_pkgs.append((pkg, str(e)))
                done += 1
                continue
            if _importable("aiohttp"):
                done += 1
            else:
                failed_pkgs.append((pkg, "pkg install succeeded but still not importable"))
            continue
        cmd = [sys.executable, "-m", "pip", "install", pkg, "--disable-pip-version-check", "--quiet"]
        if pkg.startswith("py-tgcalls"):
            cmd.append("--no-deps")
        try:
            rc, msg = _pip_install_with_progress(pkg, cmd)
            if rc == 0 and _importable(mod):
                done += 1
                continue
            err = msg or "Import failed after install"
            failed_pkgs.append((pkg, err))
            done += 1
        except Exception as e:
            failed_pkgs.append((pkg, str(e)))
            done += 1
        if has_offline:
            try:
                rc, msg = _pip_install_with_progress(
                    f"{pkg} (libs)",
                    [sys.executable, "-m", "pip", "install", pkg,
                     "--no-index", "--find-links", libs_dir, "--quiet"],
                )
                if rc == 0 and _importable(mod):
                    if failed_pkgs and failed_pkgs[-1][0] == pkg:
                        failed_pkgs.pop()
                    done += 1
                    continue
            except Exception:
                pass
    if failed_pkgs:
        print(f"{C.Rr}  Failed packages:{C.R}")
        for pkg, err in failed_pkgs:
            print(f"{C.Rr}    - {pkg}: {err}{C.R}")
        print()
    _test_voice_imports()


def _test_voice_imports():
    ok = True
    for m in ("ntgcalls", "pytgcalls"):
        try:
            __import__(m)
        except Exception:
            ok = False
    if not ok:
        print(f"{C.Rr}  Voice libs missing (voice calls unavailable){C.R}")


def main():
    import logging
    for name in ("pyrogram", "pytgcalls", "ntgcalls"):
        logging.getLogger(name).setLevel(logging.CRITICAL + 10)
    hooker = AndroidHooker()
    if _is_proot():
        _test_voice_imports()
    else:
        missing = check_missing_libs()
        if missing:
            auto_install(missing)
            still = check_missing_libs()
            if still:
                print(f"{C.Rr}  Voice libs missing (voice calls unavailable): {', '.join(still)}{C.R}")
    hooker.loop()


if __name__ == "__main__":
    main()
