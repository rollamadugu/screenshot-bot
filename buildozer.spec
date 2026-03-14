[app]
title = Screenshot Bot
package.name = screenshotbot
package.domain = com.screenshot
source.dir = .
source.include_exts = py,png,jpg,kv
version = 1.0
requirements = python3,kivy,requests,pillow,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.arch = armeabi-v7a
android.allow_backup = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
