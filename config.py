import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials (получить на https://my.telegram.org)
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()

# Список каналов для отслеживания (username, ссылка или ID через запятую)
# Пример: "@my_channel, https://t.me/another_channel, -1001234567890"
# Если оставить пустым, бот будет слушать ВСЕ каналы, на которые подписан ваш аккаунт.
CHANNELS_RAW = os.getenv("CHANNELS", "")
CHANNELS = [
    ch.strip() for ch in CHANNELS_RAW.split(",") if ch.strip()
]

# Ключевые слова для поиска в посте (через запятую, регистр не имеет значения)
# Например: "раздача, бесплатно, отдам, конкурс"
# Если оставить пустым, бот будет комментировать КАЖДЫЙ новый пост.
KEYWORDS_RAW = os.getenv("KEYWORDS", "")
KEYWORDS = [
    kw.strip().lower() for kw in KEYWORDS_RAW.split(",") if kw.strip()
]

# Текст комментария
COMMENT_TEXT = os.getenv("COMMENT_TEXT", "беру").strip()

# Задержка перед отправкой комментария в секундах (0 = мгновенно)
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "0"))

# Имя файла сессии Telethon
SESSION_NAME = os.getenv("SESSION_NAME", "user_session")
