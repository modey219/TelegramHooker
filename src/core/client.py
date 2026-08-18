import asyncio
import os
from pyrogram import Client
from .config import load_config, save_config, SESSIONS_DIR, ensure_dirs

class TelegramClient:
    def __init__(self):
        self.app = None
        self.is_connected = False
        self.me = None

    async def connect(self, api_id, api_hash, phone=None):
        ensure_dirs()
        self.app = Client(
            os.path.join(SESSIONS_DIR, "session_temp"),
            api_id=int(api_id),
            api_hash=api_hash,
        )
        await self.app.start()
        self.me = await self.app.get_me()
        self.is_connected = True
        return self.me

    async def login(self, api_id, api_hash, phone, code, password=None):
        ensure_dirs()
        self.app = Client(
            os.path.join(SESSIONS_DIR, f"session_{phone.replace('+', '')}"),
            api_id=int(api_id),
            api_hash=api_hash,
        )
        await self.app.start()
        try:
            if password:
                await self.app.check_password(password)
            else:
                await self.app.sign_in(phone, code)
        except Exception as e:
            if "PASSWORD" in str(e).upper():
                return "NEED_PASSWORD"
            raise
        self.me = await self.app.get_me()
        self.is_connected = True
        cfg = load_config()
        cfg["api_id"] = api_id
        cfg["api_hash"] = api_hash
        cfg["phone"] = phone
        save_config(cfg)
        return self.me

    async def restore_session(self, session_name):
        session_path = os.path.join(SESSIONS_DIR, session_name)
        if not os.path.exists(session_path + ".session"):
            return False
        cfg = load_config()
        self.app = Client(
            session_path,
            api_id=int(cfg["api_id"]),
            api_hash=cfg["api_hash"],
        )
        await self.app.start()
        self.me = await self.app.get_me()
        self.is_connected = True
        return True

    async def disconnect(self):
        if self.app:
            try:
                await self.app.stop()
            except Exception:
                pass
        self.app = None
        self.is_connected = False
        self.me = None

    async def get_chat_id(self, target):
        if isinstance(target, str) and target.lstrip("-").isdigit():
            target = int(target)
        chat = await self.app.get_chat(target)
        return chat.id

    async def send_message(self, target, text):
        chat_id = await self.get_chat_id(target)
        await self.app.send_message(chat_id, text)
