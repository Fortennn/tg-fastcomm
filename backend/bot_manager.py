import asyncio
import logging
import os
import re
import threading
from datetime import datetime
from telethon import TelegramClient, events, errors
from telethon.tl.types import Channel

logger = logging.getLogger("BotManager")


class BotManager:
    def __init__(self, settings_file=".env", session_name="user_session"):
        self.settings_file = settings_file
        self.session_name = session_name
        self.client: TelegramClient = None
        self.is_running = False
        self.is_connected = False
        self.user_info = None

        # Auth state
        self.phone = None
        self.phone_code_hash = None

        # Settings
        self.settings = {
            "api_id": "",
            "api_hash": "",
            "channels": "",
            "keywords": "",
            "comment_text": "беру",
            "delay_seconds": 0.0
        }
        self.load_settings()

        # Stats
        self.stats = {
            "posts_checked": 0,
            "triggers_fired": 0,
            "comments_sent": 0
        }

        # Deduplication
        self.processed_posts = set()

        # Callbacks & Logs history
        self.log_callbacks = []
        self.status_callbacks = []
        self.logs_history = []
        self.next_log_id = 1

        # Создаем и запускаем фоновый asyncio event loop в отдельном потоке
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()

        # Проверяем авторизацию при старте
        if self.settings.get("api_id") and self.settings.get("api_hash"):
            asyncio.run_coroutine_threadsafe(self.check_auth_status(), self.loop)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro, timeout=40):
        """Синхронно ожидает выполнение async корутины в фоновом цикле."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def log(self, level: str, message: str, meta: dict = None):
        """Отправляет лог и сохраняет в истории с ID."""
        entry = {
            "id": self.next_log_id,
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level.upper(),  # INFO, SUCCESS, TRIGGER, WARNING, ERROR
            "message": message,
            "meta": meta or {}
        }
        self.next_log_id += 1
        self.logs_history.append(entry)
        if len(self.logs_history) > 300:
            self.logs_history = self.logs_history[-300:]

        for cb in self.log_callbacks:
            try:
                cb(entry)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")

    def notify_status(self):
        status_data = {
            "is_running": self.is_running,
            "is_authorized": bool(self.user_info),
            "user_info": self.user_info,
            "stats": self.stats
        }
        for cb in self.status_callbacks:
            try:
                cb(status_data)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return self.settings

        with open(self.settings_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "api_id":
                    self.settings["api_id"] = val
                elif key == "api_hash":
                    self.settings["api_hash"] = val
                elif key == "channels":
                    self.settings["channels"] = val
                elif key == "keywords":
                    self.settings["keywords"] = val
                elif key == "comment_text":
                    self.settings["comment_text"] = val
                elif key == "delay_seconds":
                    try:
                        self.settings["delay_seconds"] = float(val)
                    except ValueError:
                        self.settings["delay_seconds"] = 0.0
        return self.settings

    def save_settings(self, new_settings: dict):
        self.settings.update(new_settings)
        lines = [
            f"API_ID={self.settings.get('api_id', '')}",
            f"API_HASH={self.settings.get('api_hash', '')}",
            f"CHANNELS={self.settings.get('channels', '')}",
            f"KEYWORDS={self.settings.get('keywords', '')}",
            f"COMMENT_TEXT={self.settings.get('comment_text', 'беру')}",
            f"DELAY_SECONDS={self.settings.get('delay_seconds', 0.0)}"
        ]
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.log("INFO", "💾 Настройки сохранены в файл .env")
        return True

    def get_parsed_channels(self):
        raw = self.settings.get("channels", "")
        return [ch.strip() for ch in raw.split(",") if ch.strip()]

    def get_parsed_keywords(self):
        raw = self.settings.get("keywords", "")
        return [kw.strip().lower() for kw in raw.split(",") if kw.strip()]

    def _get_client(self):
        api_id_str = str(self.settings.get("api_id", "")).strip()
        api_hash = str(self.settings.get("api_hash", "")).strip()
        if not api_id_str or not api_hash:
            raise ValueError("Не указаны API_ID или API_HASH")
        api_id = int(api_id_str)

        if not self.client:
            self.client = TelegramClient(self.session_name, api_id, api_hash)
        return self.client

    async def check_auth_status(self):
        """Проверяет, авторизован ли пользователь в Telegram."""
        try:
            client = self._get_client()
            if not client.is_connected():
                await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                self.user_info = {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name or "",
                    "username": me.username or "",
                    "phone": me.phone or ""
                }
                self.log("INFO", f"Авторизован как: {me.first_name} (@{me.username or me.id})")
                self.notify_status()
                return {"authorized": True, "user": self.user_info}
            else:
                self.user_info = None
                self.notify_status()
                return {"authorized": False, "user": None}
        except Exception as e:
            self.user_info = None
            self.notify_status()
            return {"authorized": False, "error": str(e)}

    async def send_auth_code(self, phone: str):
        """Запрашивает код подтверждения в Telegram."""
        phone = phone.strip().replace(" ", "").replace("-", "")
        self.phone = phone
        client = self._get_client()
        if not client.is_connected():
            await client.connect()

        self.log("INFO", f"📲 Запрос кода подтверждения для {phone}...")
        res = await client.send_code_request(phone)
        self.phone_code_hash = res.phone_code_hash
        self.log("SUCCESS", f"📩 Код отправлен в Telegram на номер {phone}")
        return {"status": "code_sent"}

    async def verify_auth_code(self, code: str):
        """Проверяет введенный код."""
        if not self.phone or not self.phone_code_hash:
            raise ValueError("Сначала запросите код на номер телефона")

        client = self._get_client()
        code = code.strip().replace(" ", "")
        try:
            await client.sign_in(phone=self.phone, code=code, phone_code_hash=self.phone_code_hash)
            me = await client.get_me()
            self.user_info = {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone or ""
            }
            self.log("SUCCESS", f"🎉 Успешный вход! Добро пожаловать, {me.first_name}!")
            self.notify_status()
            return {"status": "success", "user": self.user_info}
        except errors.SessionPasswordNeededError:
            self.log("WARNING", "🔐 Требуется пароль двухфакторной аутентификации (2FA)")
            return {"status": "2fa_required"}
        except Exception as e:
            self.log("ERROR", f"❌ Ошибка входа: {e}")
            raise e

    async def verify_2fa_password(self, password: str):
        """Проверяет пароль 2FA."""
        client = self._get_client()
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            self.user_info = {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone or ""
            }
            self.log("SUCCESS", f"🎉 Успешный вход по 2FA! Аккаунт: {me.first_name}")
            self.notify_status()
            return {"status": "success", "user": self.user_info}
        except Exception as e:
            self.log("ERROR", f"❌ Неверный пароль 2FA: {e}")
            raise e

    async def logout(self):
        """Выход из аккаунта."""
        if self.is_running:
            await self.stop_monitoring()
        if self.client and await self.client.is_user_authorized():
            await self.client.log_out()
        self.user_info = None
        self.notify_status()
        self.log("INFO", "🚪 Вы вышли из аккаунта Telegram")
        return {"status": "logged_out"}

    def _normalize_channel_ident(self, ch_str: str):
        ch_str = ch_str.strip()
        if not ch_str:
            return None
        tme_match = re.search(r"(?:https?://)?t\.me/([a-zA-Z0-9_+]+)", ch_str)
        if tme_match:
            val = tme_match.group(1)
            if not val.startswith("+"):
                return f"@{val}"
            return ch_str
        if re.fullmatch(r"-?\d+", ch_str):
            return int(ch_str)
        if not ch_str.startswith("@") and not ch_str.startswith("-"):
            return f"@{ch_str}"
        return ch_str

    async def start_monitoring(self):
        """Запускает прослушивание каналов и авто-комментирование."""
        if self.is_running:
            return {"status": "already_running"}

        client = self._get_client()
        if not client.is_connected():
            await client.connect()

        if not await client.is_user_authorized():
            raise ValueError("Сначала необходимо авторизоваться в Telegram")

        me = await client.get_me()
        self.user_info = {
            "id": me.id,
            "first_name": me.first_name,
            "last_name": me.last_name or "",
            "username": me.username or "",
            "phone": me.phone or ""
        }

        # Разрешаем целевые каналы
        channels_raw = self.get_parsed_channels()
        target_entities = []

        if channels_raw:
            self.log("INFO", f"🔍 Поиск и подключение целевых каналов ({len(channels_raw)})...")
            for raw_ch in channels_raw:
                ident = self._normalize_channel_ident(raw_ch)
                if not ident:
                    continue
                try:
                    entity = await client.get_entity(ident)
                    target_entities.append(entity)
                    title = getattr(entity, "title", str(ident))
                    self.log("INFO", f"  ✅ Подключен: '{title}' [ID: {entity.id}]")
                except Exception as e:
                    self.log("WARNING", f"  ⚠️ Не удалось найти канал '{raw_ch}': {e}")
            if not target_entities:
                self.log("WARNING", "⚠️ Ни один из указанных каналов не найден, но бот запущен.")
        else:
            self.log("INFO", "🌐 Целевые каналы не указаны: бот слушает ВСЕ каналы подписки.")

        keywords = self.get_parsed_keywords()
        comment_text = self.settings.get("comment_text", "беру")
        delay_sec = float(self.settings.get("delay_seconds", 0.0))

        self.log("INFO", f"💬 Текст комментария: \"{comment_text}\"")
        if keywords:
            self.log("INFO", f"🔎 Ключевые слова: {keywords}")
        else:
            self.log("INFO", "🔎 Ключевые слова: [НЕ ЗАДАНЫ] (комментировать каждый пост)")
        self.log("INFO", f"⏱️ Задержка перед отправкой: {delay_sec} сек.")

        @client.on(events.NewMessage(chats=target_entities if target_entities else None))
        async def on_new_message(event):
            if not self.is_running:
                return

            # Проверяем, что это публикация в канале
            if not getattr(event.message, "post", False):
                if target_entities and isinstance(getattr(event, "chat", None), Channel):
                    if not getattr(event.chat, "broadcast", False):
                        return
                else:
                    return

            self.stats["posts_checked"] += 1
            self.notify_status()

            chat_title = getattr(event.chat, "title", f"Чат {event.chat_id}")
            post_id = event.message.id
            post_key = (event.chat_id, post_id)

            if post_key in self.processed_posts:
                return
            self.processed_posts.add(post_key)

            post_text = event.raw_text or ""
            text_lower = post_text.lower()

            matched_kw = None
            if not keywords:
                matched_kw = "[любой пост]"
            else:
                for kw in keywords:
                    if kw in text_lower:
                        matched_kw = kw
                        break

            if not matched_kw:
                return

            # Сработал триггер!
            self.stats["triggers_fired"] += 1
            self.notify_status()

            preview = post_text.replace("\n", " ").strip()
            if len(preview) > 120:
                preview = preview[:117] + "..."

            self.log(
                "TRIGGER",
                f"🎯 Сработал триггер по слову '{matched_kw}' в канале '{chat_title}' (пост #{post_id})",
                {"chat": chat_title, "keyword": matched_kw, "preview": preview}
            )

            if delay_sec > 0:
                self.log("INFO", f"⏳ Ожидание {delay_sec} сек. перед отправкой комментария...")
                await asyncio.sleep(delay_sec)

            try:
                self.log("INFO", f"🚀 Отправка комментария: \"{comment_text}\"...")
                sent = await client.send_message(
                    entity=event.chat_id,
                    message=comment_text,
                    comment_to=event.message.id
                )
                self.stats["comments_sent"] += 1
                self.notify_status()
                self.log("SUCCESS", f"✅ Комментарий \"{comment_text}\" успешно оставлен к посту #{post_id}!", {
                    "chat": chat_title,
                    "comment_id": sent.id
                })

            except errors.rpcerrorlist.MsgIdInvalidError:
                self.log("WARNING", f"❌ В канале '{chat_title}' отключены комментарии или нет группы обсуждения.")
            except errors.rpcerrorlist.ChatWriteForbiddenError:
                self.log("WARNING", f"❌ Запрещено писать комментарии в канале '{chat_title}' (ограничение или бан).")
            except errors.rpcerrorlist.ChannelPrivateError:
                self.log("WARNING", f"❌ Группа комментариев канала '{chat_title}' приватная. Вступите в неё вручную.")
            except errors.rpcerrorlist.SlowModeWaitError as e:
                self.log("WARNING", f"⏳ В канале медленный режим (SlowMode): ожидание {e.seconds} сек.")
            except errors.rpcerrorlist.FloodWaitError as e:
                self.log("WARNING", f"⚠️ Telegram FloodWait: ограничение на {e.seconds} сек.")
            except Exception as e:
                self.log("ERROR", f"❌ Ошибка отправки комментария: {type(e).__name__} - {e}")

        self.is_running = True
        self.notify_status()
        self.log("SUCCESS", "🟢 Мониторинг запущен! Ожидание новых постов...")
        return {"status": "started"}

    async def stop_monitoring(self):
        """Останавливает мониторинг постов."""
        if not self.is_running:
            return {"status": "already_stopped"}

        self.is_running = False
        self.notify_status()
        self.log("INFO", "⏹ Мониторинг остановлен.")
        return {"status": "stopped"}
