#!/data/data/com.termux/files/usr/bin/bash
# Скрипт быстрой установки и запуска на телефоне (Android / Termux)

echo "==============================================="
echo "  Установка TG FastCommenter на Android"
echo "==============================================="

# Обновление пакетов и установка Python
pkg update -y
pkg install -y python git

# Установка необходимых библиотек
pip install --upgrade pip
pip install telethon python-dotenv fastapi uvicorn pydantic websockets

# Запрет Android усыплять процессор (чтобы бот работал при выключенном экране)
termux-wake-lock

echo "==============================================="
echo "  Запуск сервера и интерфейса..."
echo "  Откройте в браузере телефона:"
echo "  http://localhost:28492"
echo "==============================================="

python app.py
