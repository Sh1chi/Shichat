# Импорт стандартных библиотек
import json
import socket


# Импорт компонентов PyQt5
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
)


from ChatWindow import ChatWindow
from theme import DarkTheme as T

# Константы для подключения к серверу
SERVER_HOST = "localhost"
SERVER_PORT = 8080


# -------------------------- Окно входа ----------------------------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shichat — Вход")
        self.resize(300, 120)
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        layout = QVBoxLayout(self)

        # Поле для ввода имени
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите имя")
        self.name_edit.setStyleSheet(T.qss_input())

        # Кнопка "Войти"
        self.join_btn = QPushButton("Войти")
        self.join_btn.clicked.connect(self.try_login)
        self.join_btn.setStyleSheet(T.qss_button())

        layout.addWidget(self.name_edit)
        layout.addWidget(self.join_btn)

    def try_login(self):
        # Получаем имя пользователя
        self.username = self.name_edit.text().strip()
        if not self.username:
            QMessageBox.warning(self, "Ошибка", "Введите имя пользователя")
            return
        try:
            # Создание TCP-соединения
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))

            # Отправка пакета регистрации
            reg = {"type": "register", "from": self.username}
            sock.sendall((json.dumps(reg) + "\n").encode())
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться: {e}")
            return

        # Открываем окно чата
        self.main = ChatWindow(self.username, sock)
        self.main.show()
        self.close()