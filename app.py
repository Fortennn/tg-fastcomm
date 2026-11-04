import os
import socket
import sys
import threading
import time
import webbrowser
import uvicorn

# Настройка кодировки на Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_free_port(default_port=28492):
    """Находит свободный порт для локального сервера."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", default_port))
        sock.close()
        return default_port
    except OSError:
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port


def wait_for_server(port, timeout=10.0):
    """Ожидает, пока локальный сервер начнет принимать соединения."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)
    return False


def run_server(port):
    """Запускает Flask сервер в отдельном потоке."""
    try:
        from backend.flask_server import app
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ Ошибка Flask сервера: {e}")


def main():
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print("🚀 Запуск TG FastCommenter (Glassmorphism Desktop App)...")
    print(f"🔗 Сервер запущен: {url}")
    print("=" * 60)

    # Запускаем локальный веб-сервер в фоне
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Дожидаемся готовности сервера
    if not wait_for_server(port):
        print("❌ Ошибка: Локальный сервер не запустился в течение 10 секунд!")
        input("Нажмите Enter для выхода...")
        return

    print("✅ Локальный сервер готов к работе!")

    # Пробуем запустить нативное десктопное окно через PySide6 QtWebEngine
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QColor, QPalette

        qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("TG FastCommenter")

        # Тёмная тема для нативного окна
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#07090e"))
        qt_app.setPalette(palette)

        window = QMainWindow()
        window.setWindowTitle("TG FastCommenter — Smart Glassmorphism Userbot")
        window.resize(1220, 840)
        window.setMinimumSize(980, 680)

        web_view = QWebEngineView()
        # Темный фон при загрузке страницы
        web_view.page().setBackgroundColor(QColor("#07090e"))
        web_view.setUrl(QUrl(url))

        window.setCentralWidget(web_view)
        window.show()

        sys.exit(qt_app.exec())

    except Exception as e:
        print(f"⚠️ Открытие встроенного окна: {e}. Запуск в браузере...")
        webbrowser.open(url)
        # Держим процесс активным
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("🛑 Приложение остановлено.")


if __name__ == "__main__":
    main()
