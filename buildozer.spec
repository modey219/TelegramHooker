[app]
title = Telegram Hooker
package.name = telegramhooker
package.domain = com.aseqx12

source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas,so,txt
source.exclude_patterns = terminal/*,.git*,buildozer*,.github*

version = 1.0.0

requirements = python3==3.11.9,
    kivy==2.3.0,
    pyrogram>=2.0.106,
    py-tgcalls==2.2.0,
    ntgcalls==2.2.5,
    aiohttp>=3.8.0,
    pyaes>=1.6.1,
    tgcrypto,
    certifi,
    sqlite3

orientation = portrait
fullscreen = 0
android.minapi = 24
android.api = 34
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

android.permissions = INTERNET,
    RECORD_AUDIO,
    MODIFY_AUDIO_SETTINGS,
    ACCESS_NETWORK_STATE,
    WAKE_LOCK,
    FOREGROUND_SERVICE,
    POST_NOTIFICATIONS

android.release_artifact = apk
android.debug_artifact = apk

log_level = 2

p4a.branch = develop

android.enable_androidx = True
android.add_gradle_maven_repos = True

presplash.color = #1a1a2e
presplash.color_mode = RGB

[buildozer]
warn_on_root = 0
