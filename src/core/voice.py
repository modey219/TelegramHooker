import asyncio
from pytgcalls import PyTgCalls
from pytgcalls.media_devices import InputDevice, SpeakerDevice
from pytgcalls.types.stream.media_stream import MediaStream
from pytgcalls.types.stream.record_stream import RecordStream
from pytgcalls.types.calls.group_call_config import GroupCallConfig

class VoiceCallManager:
    def __init__(self, pyrogram_client):
        self.client = pyrogram_client
        self.pytgcalls = None
        self.current_chat_id = None
        self.is_muted = False

    async def start(self):
        if not self.pytgcalls:
            self.pytgcalls = PyTgCalls(self.client)
        await self.pytgcalls.start()

    async def join(self, target_id, mute_on_join=True):
        if not self.pytgcalls:
            await self.start()
        chat_id = target_id
        if isinstance(target_id, str):
            chat = await self.client.app.get_chat(target_id)
            chat_id = chat.id

        if self.current_chat_id and self.current_chat_id != chat_id:
            await self.leave()

        mic = InputDevice("pulse_input", "pulse", False)
        speaker = SpeakerDevice("pulse_output", "pulse")

        stream = MediaStream(mic, audio_flags=MediaStream.Flags.REQUIRED)
        await self.pytgcalls.play(chat_id, stream, GroupCallConfig(auto_start=True))

        try:
            await self.pytgcalls.record(chat_id, speaker)
        except Exception:
            pass

        if mute_on_join:
            await self.mute()

        self.current_chat_id = chat_id
        return True

    async def leave(self):
        if self.pytgcalls and self.current_chat_id:
            try:
                await self.pytgcalls.leave_call(self.current_chat_id)
            except Exception:
                pass
            self.current_chat_id = None
            self.is_muted = False

    async def mute(self):
        if self.pytgcalls and self.current_chat_id:
            await self.pytgcalls.mute(self.current_chat_id)
            self.is_muted = True

    async def unmute(self):
        if self.pytgcalls and self.current_chat_id:
            await self.pytgcalls.unmute(self.current_chat_id)
            self.is_muted = False

    async def toggle_mute(self):
        if self.is_muted:
            await self.unmute()
        else:
            await self.mute()
