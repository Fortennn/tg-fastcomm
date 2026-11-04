import os
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
from backend.bot_manager import BotManager

logger = logging.getLogger("FlaskServer")

web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
app = Flask(__name__, static_folder=web_dir, static_url_path="/static")
bot_manager = BotManager()


@app.route("/")
def index():
    return send_from_directory(web_dir, "index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify({
        "is_running": bot_manager.is_running,
        "is_authorized": bool(bot_manager.user_info),
        "user_info": bot_manager.user_info,
        "stats": bot_manager.stats
    })


@app.route("/api/updates", methods=["GET"])
def get_updates():
    after_id = int(request.args.get("after", 0))
    logs = [log for log in bot_manager.logs_history if log["id"] > after_id]
    return jsonify({
        "status": {
            "is_running": bot_manager.is_running,
            "is_authorized": bool(bot_manager.user_info),
            "user_info": bot_manager.user_info,
            "stats": bot_manager.stats
        },
        "logs": logs
    })


@app.route("/api/settings", methods=["GET", "POST"])
def settings_route():
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        bot_manager.save_settings(data)
        return jsonify({"status": "saved", "settings": bot_manager.settings})
    return jsonify(bot_manager.settings)


@app.route("/api/auth/code", methods=["POST"])
def auth_code():
    data = request.get_json(force=True) or {}
    phone = data.get("phone", "")
    if not phone:
        return jsonify({"detail": "Введите номер телефона"}), 400
    try:
        res = bot_manager.run_async(bot_manager.send_auth_code(phone))
        return jsonify(res)
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@app.route("/api/auth/verify", methods=["POST"])
def auth_verify():
    data = request.get_json(force=True) or {}
    code = data.get("code", "")
    if not code:
        return jsonify({"detail": "Введите код"}), 400
    try:
        res = bot_manager.run_async(bot_manager.verify_auth_code(code))
        return jsonify(res)
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@app.route("/api/auth/2fa", methods=["POST"])
def auth_2fa():
    data = request.get_json(force=True) or {}
    password = data.get("password", "")
    if not password:
        return jsonify({"detail": "Введите пароль 2FA"}), 400
    try:
        res = bot_manager.run_async(bot_manager.verify_2fa_password(password))
        return jsonify(res)
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    try:
        res = bot_manager.run_async(bot_manager.logout())
        return jsonify(res)
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@app.route("/api/bot/start", methods=["POST"])
def bot_start():
    try:
        res = bot_manager.run_async(bot_manager.start_monitoring())
        return jsonify(res)
    except Exception as e:
        bot_manager.log("ERROR", f"Не удалось запустить: {e}")
        return jsonify({"detail": str(e)}), 400


@app.route("/api/bot/stop", methods=["POST"])
def bot_stop():
    try:
        res = bot_manager.run_async(bot_manager.stop_monitoring())
        return jsonify(res)
    except Exception as e:
        return jsonify({"detail": str(e)}), 400
