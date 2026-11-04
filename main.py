import asyncio
import logging
import os
import re
import sys

# Настройка кодировки для корректного вывода в консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Если запуск внутри Android APK (через python-for-android / buildozer webview)
if "ANDROID_ARGUMENT" in os.environ or "ANDROID_BOOTSTRAP" in os.environ or "ANDROID_ENTRYPOINT" in os.environ:
    import uvicorn
    from backend.server import app
    print("🤖 Запуск TG FastCommenter внутри Android APK...")
    uvicorn.run(app, host="127.0.0.1", port=28492, log_level="info")
    sys.exit(0)
from datetime import datetime
from telethon import TelegramClient, events, errors
from telethon.tl.types import Channel

import config

# Настройка красивого логирования
logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger("AutoCommenter")

# Защита от повторных комментариев на один и тот же пост
PROCESSED_POSTS = set()


def normalize_channel_identifier(channel_str: str):
    """Очищает строку канала (ссылка, @username или числовой ID)."""
    channel_str = channel_str.strip()
    if not channel_str:
        return None

    # Если ссылка вида https://t.me/username или t.me/username
    tme_match = re.search(r"(?:https?://)?t\.me/([a-zA-Z0-9_+]+)", channel_str)
    if tme_match:
        val = tme_match.group(1)
        if not val.startswith("+"):
            return f"@{val}"
        return channel_str

    # Если это числовой ID (например -1001234567890)
    if re.fullmatch(r"-?\d+", channel_str):
        return int(channel_str)

    # Если username без @
    if not channel_str.startswith("@") and not channel_str.startswith("-"):
        return f"@{channel_str}"

    return channel_str


async def resolve_target_chats(client: TelegramClient, channels_list: list):
    """Преобразует список каналов из конфига в проверенные сущности Telegram."""
    if not channels_list:
        logger.info("ℹ️ Список каналов пуст. Бот будет слушать ВСЕ каналы, на которые вы подписаны.")
        return None

    resolved = []
    logger.info(f"🔍 Проверка и подключение к целевым каналам ({len(channels_list)} шт.)...")

    for raw_ch in channels_list:
        ident = normalize_channel_identifier(raw_ch)
        if not ident:
            continue
        try:
            entity = await client.get_entity(ident)
            resolved.append(entity)
            title = getattr(entity, "title", str(ident))
            username = getattr(entity, "username", None)
            user_str = f" (@{username})" if username else ""
            logger.info(f"  ✅ Канал подключен: '{title}'{user_str} [ID: {entity.id}]")
        except Exception as e:
            logger.warning(f"  ⚠️ Не удалось подключить канал '{raw_ch}': {e}")

    if not resolved:
        logger.error("❌ Ни один из указанных каналов не удалось найти! Проверьте CHANNELS в файле .env")
    return resolved


def check_keywords_match(text: str, keywords: list) -> tuple[bool, str]:
    """
    Проверяет наличие ключевых слов в тексте поста.
    Возвращает (совпало_ли, найденное_слово).
    """
    if not keywords:
        # Если ключевые слова не заданы - реагируем на любой пост
        return True, "любой пост (KEYWORDS пуст)"

    if not text:
        return False, ""

    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True, kw

    return False, ""


async def post_comment(client: TelegramClient, event, matched_keyword: str):
    """Отправляет комментарий к посту канала."""
    post_id = event.message.id
    chat_id = event.chat_id
    post_key = (chat_id, post_id)

    if post_key in PROCESSED_POSTS:
        return
    PROCESSED_POSTS.add(post_key)

    chat_title = getattr(event.chat, "title", f"Chat_{chat_id}")
    logger.info(f"🎯 Сработал триггер по слову '{matched_keyword}' в канале '{chat_title}' (ID поста: {post_id})")

    # Превью текста поста (до 100 символов)
    preview = (event.raw_text or "").replace("\n", " ").strip()
    if len(preview) > 100:
        preview = preview[:97] + "..."
    if preview:
        logger.info(f"   Текст поста: \"{preview}\"")

    # Задержка, если указана в настройках
    if config.DELAY_SECONDS > 0:
        logger.info(f"   ⏳ Ожидание {config.DELAY_SECONDS} сек. перед отправкой комментария...")
        await asyncio.sleep(config.DELAY_SECONDS)

    try:
        logger.info(f"   🚀 Отправка комментария: \"{config.COMMENT_TEXT}\"...")
        # Telethon параметр comment_to автоматически находит связанную группу обсуждения
        sent_msg = await client.send_message(
            entity=event.chat_id,
            message=config.COMMENT_TEXT,
            comment_to=event.message.id
        )
        logger.info(f"   ✅ Комментарий успешно отправлен! (ID сообщения: {sent_msg.id})")

    except errors.rpcerrorlist.MsgIdInvalidError:
        logger.warning("   ❌ Ошибка: В этом канале отключены комментарии или нет привязанной группы обсуждения.")
    except errors.rpcerrorlist.ChatWriteForbiddenError:
        logger.warning("   ❌ Ошибка: У вас нет прав писать комментарии в этом канале / группе (возможно, мут или бан).")
    except errors.rpcerrorlist.ChannelPrivateError:
        logger.warning("   ❌ Ошибка: Группа комментариев приватная. Вступите в нее со своего аккаунта вручную.")
    except errors.rpcerrorlist.SlowModeWaitError as e:
        logger.warning(f"   ⏳ Медленный режим (SlowMode): нужно подождать {e.seconds} сек.")
    except errors.rpcerrorlist.FloodWaitError as e:
        logger.warning(f"   ⚠️ Telegram FloodWait: ограничение запросов на {e.seconds} сек.")
    except Exception as e:
        logger.error(f"   ❌ Не удалось оставить комментарий: {type(e).__name__} - {e}")


async def main():
    if not config.API_ID or not config.API_HASH:
        sep = "=" * 60
        logger.error(
            f"\n{sep}\n"
            "❌ ОШИБКА: Не заполнены API_ID и API_HASH в файле .env!\n\n"
            "Как их получить:\n"
            "1. Зайдите на сайт https://my.telegram.org\n"
            "2. Войдите под своим номером телефона Telegram\n"
            "3. Перейдите в раздел 'API development tools'\n"
            "4. Введите любое название (например 'Commenter') и создайте приложение\n"
            "5. Скопируйте api_id и api_hash в файл .env в папке бота\n"
            f"{sep}"
        )
        return

    try:
        api_id = int(config.API_ID)
    except ValueError:
        logger.error("❌ API_ID должен быть числом! Проверьте файл .env")
        return

    client = TelegramClient(config.SESSION_NAME, api_id, config.API_HASH)

    print("=" * 60)
    print("🤖 Запуск Telegram Auto-Commenter (Userbot)")
    print("=" * 60)

    await client.start()
    me = await client.get_me()
    logger.info(f"👤 Успешный вход под аккаунтом: {me.first_name} (@{me.username or 'без_юзернейма'}, ID: {me.id})")

    # Получаем целевые чаты/каналы
    target_chats = await resolve_target_chats(client, config.CHANNELS)

    logger.info(f"📝 Текст комментария: \"{config.COMMENT_TEXT}\"")
    if config.KEYWORDS:
        logger.info(f"🔎 Ключевые слова: {config.KEYWORDS}")
    else:
        logger.info("🔎 Ключевые слова: [НЕ ЗАДАНЫ] (комментировать каждый новый пост)")
    logger.info(f"⏱️ Задержка: {config.DELAY_SECONDS} сек.")

    # Регистрация обработчика новых сообщений
    # chats=target_chats фильтрует сообщения на уровне библиотеки, если список задан
    @client.on(events.NewMessage(chats=target_chats))
    async def handler(event):
        # Реагируем только на публикации в каналах (post=True)
        # Это исключает обычные сообщения в чатах или ответы в самих комментариях
        if not getattr(event.message, "post", False):
            # Если целевой канал был явно указан, проверим, не является ли он широковещательным
            if target_chats and isinstance(getattr(event, "chat", None), Channel):
                if not getattr(event.chat, "broadcast", False):
                    return
            else:
                return

        post_text = event.raw_text or ""
        matched, kw = check_keywords_match(post_text, config.KEYWORDS)
        if matched:
            await post_comment(client, event, kw)

    logger.info("🟢 Бот успешно запущен и слушает новые посты...")
    logger.info("Нажмите Ctrl+C для остановки.")

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот остановлен пользователем.")
