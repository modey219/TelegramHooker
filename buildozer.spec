[app]
title = Telegram Hooker
package.name = telegramhooker
package.domain = com.aseqx12
source.dir = .
source.main = main.py
source.include_exts = py,png
source.include_patterns = icon.png
version = 8.0.0
requirements = python3,kivy,pyrogram,certifi,pysocks,pyaes,tgcrypto
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename =
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,POST_NOTIFICATIONS,MANAGE_EXTERNAL_STORAGE
android.debug_artifact = apk
android.enable_androidx = True
source.exclude_patterns = .github/*,terminal/*,docker/*,ios/*,src/*
log_level = 2
# p4a.branch handled by buildozer Docker image
[buildozer]
warn_on_root = 0
