# Импорт стандартных библиотек
import json
import socket
import threading

# Импорт компонентов Qt для сигналов и событий
from PyQt5.QtCore import Qt, pyqtSignal, QObject


# Класс NetworkWorker — сетевой обработчик, работающий в фоне.
# Отвечает за приём сообщений от сервера через сокет,
# обработку полученных данных и отправку сигналов в интерфейс (GUI).
# Также позволяет инициировать отправку сообщений: поиск пользователей, создание чатов и групп.
class NetworkWorker(QObject):
    # Сигналы, по которым другие окна могут реагировать на события от сервера
    message_received = pyqtSignal(dict)        # Пришло сообщение
    chatlist_received = pyqtSignal(list)       # Обновился список чатов
    connection_lost = pyqtSignal()             # Потеря соединения с сервером
    user_search_result = pyqtSignal(list)      # Результат поиска пользователей
    chat_created = pyqtSignal(dict)            # Создан приватный чат
    group_created = pyqtSignal(dict)           # Создан групповой чат


    def __init__(self, sock: socket.socket):
        super().__init__()
        self.sock = sock
        self._running = True  # флаг, указывающий, запущен ли поток


    # Запускает фоновый поток, который будет постоянно слушать сокет
    def start(self):
        threading.Thread(target=self._read_loop, daemon=True).start()


    # Останавливает работу: завершает поток и закрывает сокет
    def stop(self):
        self._running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except OSError:
            pass


    # Цикл чтения данных из сокета. Вызывается в отдельном потоке.
    # Считывает данные построчно (до \n), превращает в JSON и вызывает нужный сигнал.
    def _read_loop(self):
        buffer = ""
        while self._running:
            try:
                part = self.sock.recv(4096)
                if not part:
                    break  # соединение закрыто со стороны сервера

                buffer += part.decode()

                # Обрабатываем каждую строку по \n
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line:
                        continue

                    pkt = json.loads(line)
                    ptype = pkt.get("type")

                    # Определяем тип полученного пакета и испускаем соответствующий сигнал
                    if ptype == "chatlist":
                        self.chatlist_received.emit(pkt.get("chats", []))
                    elif ptype == "message":
                        self.message_received.emit(pkt)
                    elif ptype == "user_search_result":
                        self.user_search_result.emit(pkt.get("users", []))
                    elif ptype == "chat_created":
                        self.chat_created.emit(pkt)
                    elif ptype == "group_created":
                        self.group_created.emit(pkt)

            except (ConnectionResetError, OSError, json.JSONDecodeError):
                break
        # Если вышли из цикла — сигнал об отключении
        self.connection_lost.emit()


    # Отправляет запрос на поиск пользователей по строке запроса
    def send_user_search(self, query: str):
        pkt = {"type": "user_search", "query": query}
        self.sock.sendall((json.dumps(pkt) + "\n").encode())


    # Отправляет запрос на создание приватного чата с другим пользователем
    def send_start_chat(self, peer: str):
        pkt = {"type": "start_chat", "to": peer}
        self.sock.sendall((json.dumps(pkt) + "\n").encode())


    # Отправляет запрос на создание группового чата с заданными участниками
    def send_create_group(self, name: str, participants: list[str]):
        pkt = {
            "type": "create_group",
            "name": name,
            "participants": participants
        }
        self.sock.sendall((json.dumps(pkt) + "\n").encode())