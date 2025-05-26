# Импорт стандартных библиотек
import json
import socket
import threading


# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt, pyqtSignal, QObject


# ------------------------ Сетевой обработчик ------------------------
class NetworkWorker(QObject):
    # Сигналы для отправки событий в GUI
    message_received = pyqtSignal(dict)      # Пришло сообщение
    userlist_received = pyqtSignal(list)     # Обновился список пользователей
    connection_lost = pyqtSignal()           # Соединение разорвано

    def __init__(self, sock: socket.socket):
        super().__init__()
        self.sock = sock
        self._running = True  # флаг для остановки потока

    def start(self):
        # Запуск отдельного фонового потока
        threading.Thread(target=self._read_loop, daemon=True).start()

    def stop(self):
        # Остановка потока и закрытие сокета
        self._running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except OSError:
            pass

    def _read_loop(self):
        # Основной цикл чтения данных из сокета
        buffer = ""
        while self._running:
            try:
                part = self.sock.recv(4096)
                if not part:
                    break  # сервер закрыл соединение
                buffer += part.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line:
                        continue
                    pkt = json.loads(line)
                    ptype = pkt.get("type")
                    # Обработка полученных пакетов
                    if ptype == "userlist":
                        self.userlist_received.emit(pkt.get("users", []))
                    elif ptype == "message":
                        self.message_received.emit(pkt)
            except (ConnectionResetError, OSError, json.JSONDecodeError):
                break
        # Если вышли из цикла — сигнал об отключении
        self.connection_lost.emit()