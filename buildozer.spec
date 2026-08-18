[app]
title = Telegram Hooker
package.name = telegramhooker
package.domain = com.aseqx12
source.dir = .
source.main = main.py
source.include_exts = py,png
source.include_patterns = icon.png
version = 2.0.0
requirements = python3,kivy,pyrogram,py-tgcalls==2.2.0,ntgcalls==2.2.5,cryptography,tgcrypto,certifi
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,POST_NOTIFICATIONS
android.debug_artifact = apk
android.gradle_dependencies = com.google.android.material:material:1.11.0
android.enable_androidx = True
proguard = True
log_level = 2
p4a.branch = develop
[buildozer]
warn_on_root = 0
