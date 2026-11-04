[app]

# (str) Title of your application
title = TG FastCommenter

# (str) Package name
package.name = tgcommenter

# (str) Package domain (needed for android/ios packaging)
package.domain = org.tgcommenter

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,html,css,js,json,ttf,woff,woff2,ico

# (list) List of directory to include
source.include_dirs = backend,web

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3, telethon, fastapi, uvicorn, pydantic, websockets, python-dotenv, pyaes, pyasn1, rsa, requests

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# -----------------------------------------------------------------------------
# Android specific
# -----------------------------------------------------------------------------

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (list) Permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WAKE_LOCK, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

# (int) Target Android API
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Android SDK version to use
android.sdk = 34

# (str) Bootstrap to use for android (webview is used for local web app UI)
p4a.bootstrap = webview

# (int) Port to point webview to
android.port = 28492

# (bool) If True, then the app will prevent the screen from turning off
android.wakelock = True

# (list) Android application meta-data to set (key=value format)
android.meta_data = android.webkit.WebView.EnableSafeBrowsing=false

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug with command output)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
