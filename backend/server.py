import asyncio
import json
import logging
import os
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.bot_manager import BotManager

logger = logging.getLogger("Server")

app = FastAPI(title="Telegram Auto-Commenter API")
bot_manager = BotManager()

# Подключенные WebSocket клиенты
active_websockets: Set[WebSocket] = set()


def broadcast_message_sync(msg_dict: dict):
    """Синхронная обертка для отправки сообщения во все вебсокеты через глобальный loop."""
    if bot_manager.loop and bot_manager.loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_json(msg_dict), bot_manager.loop)


async def broadcast_json(data: dict):
    if not active_websockets:
        return
    text = json.dumps(data, ensure_ascii=False)
    to_remove = set()
    for ws in list(active_websockets):
        try:
            await ws.send_text(text)
        except Exception:
            to_remove.add(ws)
    for ws in to_remove:
        active_websockets.discard(ws)


# Регистрируем колбэки в bot_manager
def on_bot_log(log_entry: dict):
    if bot_manager.loop and bot_manager.loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_json({"type": "log", "data": log_entry}),
            bot_manager.loop
        )


def on_bot_status(status_entry: dict):
    if bot_manager.loop and bot_manager.loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_json({"type": "status", "data": status_entry}),
            bot_manager.loop
        )


bot_manager.log_callbacks.append(on_bot_log)
bot_manager.status_callbacks.append(on_bot_status)


# Pydantic модели
class SettingsModel(BaseModel):
    api_id: str = ""
    api_hash: str = ""
    channels: str = ""
    keywords: str = ""
    comment_text: str = "беру"
    delay_seconds: float = 0.0


class PhoneModel(BaseModel):
    phone: str


class CodeModel(BaseModel):
    code: str


class PasswordModel(BaseModel):
    password: str


@app.on_event("startup")
async def startup_event():
    bot_manager.loop = asyncio.get_running_loop()
    # Пробуем проверить статус авторизации при старте
    try:
        if bot_manager.settings.get("api_id") and bot_manager.settings.get("api_hash"):
            await bot_manager.check_auth_status()
    except Exception as e:
        logger.warning(f"Startup auth check warning: {e}")


@app.get("/api/status")
async def get_status():
    return {
        "is_running": bot_manager.is_running,
        "is_authorized": bool(bot_manager.user_info),
        "user_info": bot_manager.user_info,
        "stats": bot_manager.stats
    }


@app.get("/api/settings")
async def get_settings():
    return bot_manager.settings


@app.post("/api/settings")
async def save_settings(data: SettingsModel):
    bot_manager.save_settings(data.dict())
    return {"status": "saved", "settings": bot_manager.settings}


@app.post("/api/auth/code")
async def send_code(data: PhoneModel):
    try:
        res = await bot_manager.send_auth_code(data.phone)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/verify")
async def verify_code(data: CodeModel):
    try:
        res = await bot_manager.verify_auth_code(data.code)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/2fa")
async def verify_2fa(data: PasswordModel):
    try:
        res = await bot_manager.verify_2fa_password(data.password)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/logout")
async def logout():
    try:
        res = await bot_manager.logout()
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bot/start")
async def start_bot():
    try:
        res = await bot_manager.start_monitoring()
        return res
    except Exception as e:
        bot_manager.log("ERROR", f"Не удалось запустить: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bot/stop")
async def stop_bot():
    try:
        res = await bot_manager.stop_monitoring()
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    # Сразу отправляем текущее состояние
    try:
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": {
                "is_running": bot_manager.is_running,
                "is_authorized": bool(bot_manager.user_info),
                "user_info": bot_manager.user_info,
                "stats": bot_manager.stats
            }
        }, ensure_ascii=False))

        while True:
            data = await websocket.receive_text()
            # Echo / ping
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        active_websockets.discard(websocket)
    except Exception:
        active_websockets.discard(websocket)


# Раздача статики web
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(web_dir, "index.html"))
