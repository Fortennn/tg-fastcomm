import os
import sys
import traceback

# Настройка кодировки на Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log_crash(e):
    err_text = traceback.format_exc()
    print("CRITICAL ERROR:\n", err_text)
    for path in ["/sdcard/Download/tg_crash.log", "/sdcard/tg_crash.log", "tg_crash.log"]:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(err_text)
            break
        except Exception:
            pass


if __name__ in ("__main__", "android_entrypoint"):
    try:
        from backend.flask_server import app, bot_manager

        PORT = int(os.environ.get("PORT", 5000))
        print(f"🚀 TG FastCommenter Server starting on 0.0.0.0:{PORT}...")

        # На Android p4a webview запускает main.py, и WebView подключается к 127.0.0.1:5000
        app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)

    except Exception as err:
        log_crash(err)
        raise err
