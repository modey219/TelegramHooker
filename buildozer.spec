[app]
title = Telegram Hooker
package.name = telegramhooker
package.domain = com.aseqx12

source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas
source.exclude_patterns = .git*,.github*,terminal*,src*,ios*,android*,libs*,buildozer*,README*,LICENSE*,setup*,requirements*

version = 1.0.0

requirements = python3,kivy,pyrogram,py-tgcalls==2.2.0,ntgcalls==2.2.5,aiohttp,pyaes,tgcrypto,certifi

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,ACCESS_NETWORK_STATE,WAKE_LOCK

android.release_artifact = aab
android.debug_artifact = apk

log_level = 2

p4a.branch = develop
android.enable_androidx = True

[buildozer]
warn_on_root = 0
