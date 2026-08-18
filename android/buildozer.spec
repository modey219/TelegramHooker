[app]
title = Telegram Hooker
package.name = telegramhooker
package.domain = com.aseqx12

source.dir = src
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = core/*.py

version = 1.0.0

requirements = python3,
    pyrogram>=2.0.106,
    py-tgcalls==2.2.0,
    ntgcalls==2.2.5,
    aiohttp>=3.8.0,
    pyaes>=1.6.1,
    kivy==2.3.0

orientation = portrait
fullscreen = 0
android.minapi = 24
android.api = 33
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

# Permissions
android.permissions = INTERNET,
    RECORD_AUDIO,
    MODIFY_AUDIO_SETTINGS,
    ACCESS_NETWORK_STATE,
    WAKE_LOCK,
    FOREGROUND_SERVICE

# Build
android.release_artifact = apk
android.debug_artifact = apk

# Icon and splash
#icon.filename = %(source.dir)s/icon.png
#presplash.filename = %(source.dir)s/presplash.png

# Log level
log_level = 2

# P4A recipe
p4a.branch = develop

# Android specific
android.enable_androidx = True
android.add_gradle_maven_repos = True

# Service
#android.service = hooker

[buildozer]
warn_on_root = 0
