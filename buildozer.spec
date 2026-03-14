[app]
title = Screenshot Bot
package.name = screenshotbot
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 4.0
requirements = python3,kivy==2.2.1,requests,urllib3,charset-normalizer,idna,certifi,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,SYSTEM_ALERT_WINDOW
android.archs = arm64-v8a
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
services = ScreenshotService:./service.py:foreground

[buildozer]
log_level = 2
warn_on_root = 0
